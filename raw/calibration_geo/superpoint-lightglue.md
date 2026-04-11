# LightGlue 多相机标定模块

## 概述

本模块用于**侧视鱼眼相机与俯视鱼眼相机之间的外参标定**，基于深度学习特征匹配方法实现相对姿态估计。

```
输入: 侧视相机图像 + 俯视相机图像 + 内参文件
输出: 两相机之间的相对旋转矩阵 R 和平移向量 t
```

---

## 1. 整体流程

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              标定流程                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  加载图像   │───▶│  特征提取   │───▶│  特征匹配   │───▶│  异常剔除   │     │
│  │             │    │  SuperPoint │    │  LightGlue  │    │  DBSCAN     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                                    │            │
│                                                                    ▼            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  误差评估   │◀───│  姿态优化   │◀───│  球面变换   │◀───│  聚类中心   │     │
│  │             │    │  L-BFGS-B   │    │  等距投影   │    │  计算       │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 核心步骤说明

| 步骤 | 功能 | 适配工程的关键点 |
|------|------|-----------------|
| 1. 图像加载 | 加载侧视/俯视相机图像，按时间戳配对 | 适配多相机数据格式 |
| 2. 特征提取 | SuperPoint 检测关键点并提取描述子 | 适配鱼眼相机大视场角 |
| 3. 特征匹配 | LightGlue Transformer 匹配 | 适配不同视角（侧视↔俯视） |
| 4. 异常剔除 | DBSCAN 聚类过滤匹配异常点 | 处理纯旋转场景的特征分布 |
| 5. 球面变换 | 像素坐标→单位球面坐标 | **适配鱼眼等距投影模型** |
| 6. 姿态估计 | 球面本质矩阵 + 鲁棒优化 | **适配纯旋转估计（RANSAC-free）** |
| 7. 误差评估 | 计算旋转误差与GT对比 | 验证标定精度 |

---

## 2. 开源模块：SuperPoint 与 LightGlue

> 以下为开源算法原理的简要说明，详细实现见各子模块。

### 2.1 SuperPoint 特征提取

**原理**：CNN-based 关键点检测与描述子提取网络

```
输入图像 → 共享编码器(多层卷积) → 分支
                                    ├→ 关键点检测头 (65通道 → NMS → 关键点)
                                    └→ 描述子头 (L2归一化 → 采样)
```

#### 描述子 (Descriptor) 详解

**什么是描述子？**

描述子是一个**向量**，用于描述图像中某个点周围的局部纹理特征。它的核心作用是：**判断两个图像中的关键点是否对应同一个物理位置**。

```
相似描述子 → 可能是同一个物理点
不相似描述子 → 一定是不同的物理点
```

**描述子的特性**：

| 特性 | 说明 |
|------|------|
| 维度 | 256 维 (本工程) |
| 归一化 | L2 归一化 (向量长度为1) |
| 相似度度量 | 余弦相似度 (点积) |

**描述子的计算过程**：

```
1. 共享编码器输出特征图
   输入: [B, 1, H, W] 灰度图
   输出: [B, 128, H/8, W/8] 特征图 (8倍下采样)

2. 描述子头 (Descriptor Head)
   cDa = ReLU(convDa(特征图))     # [B, 256, H/8, W/8]
   descriptors = convDb(cDa)       # [B, 256, H/8, W/8]
   descriptors = L2normalize()     # L2归一化

3. 在关键点位置采样描述子
   使用双线性插值从特征图中提取:
   - 关键点 (x, y) → 特征图网格坐标
   - grid_sample 双线性插值提取 256 维向量

4. 输出
   descriptors: [B, 256, N]  # N个关键点，每个256维
```

**关键点坐标 → 描述子采样的坐标变换**：

```python
def sample_descriptors(keypoints, descriptors, s: int = 8):
    """在关键点位置采样描述子"""

    # s=8 表示特征图是原图的 1/8 分辨率

    # 1. 坐标偏移 (对齐到特征图网格中心)
    keypoints = keypoints - s / 2 + 0.5

    # 2. 归一化到 [0, 1]
    keypoints /= [(w * s - s / 2 - 0.5), (h * s - s / 2 - 0.5)]

    # 3. 归一化到 [-1, 1] (grid_sample 要求)
    keypoints = keypoints * 2 - 1

    # 4. 双线性插值采样
    descriptors = torch.nn.functional.grid_sample(
        descriptors, keypoints.view(b, 1, -1, 2), mode="bilinear"
    )

    # 5. L2 归一化
    descriptors = torch.nn.functional.normalize(..., p=2, dim=1)

    return descriptors
```

**描述子的物理意义**：

```
图像空间                    描述子空间

  ┌───────────┐             ┌─────────────────┐
  │           │             │                 │
  │    ●      │ 关键点      │  描述子向量      │
  │  ┌───┐    │  ────────▶ │  [d1, d2, ...,  │
  │  │   │    │  特征提取   │   d256]         │
  │  └───┘    │             │                 │
  │  局部区域  │             │  编码纹理信息    │
  │           │             │                 │
  └───────────┘             └─────────────────┘

描述子 = 该点周围 8x8 区域的纹理特征的编码
       (通过 CNN 自动学习得到)
```

**为什么用 256 维？**

- 维度足够高：可以编码丰富的纹理信息
- 维度适中：计算余弦相似度效率高
- CNN 已学习：预训练模型已学会提取有区分性的特征

**如何比较两个描述子？**

```python
# 余弦相似度 (描述子已 L2 归一化，直接点积即可)
similarity = torch.dot(desc1, desc2)  # 结果范围 [-1, 1]
# 接近 1: 相似
# 接近 -1: 不相似
# 接近 0: 正交(无关联)
```

#### 输入格式

```python
# 通过 Extractor.extract() 调用
image: torch.Tensor  # [1, C, H, W] 或 [C, H, W]

# 实际使用示例:
image = load_image(path)  # 加载为 [C, H, W]
feats = extractor.extract(image)  # 自动添加 batch 维度
```

| 字段 | 形状 | 说明 |
|------|------|------|
| `image` | `[1, C, H, W]` 或 `[C, H, W]` | 输入图像，C=1(灰度)或3(RGB) |

#### 输出格式

```python
{
    "keypoints": torch.Tensor,      # [B, N, 2]      关键点坐标 (x, y)
    "keypoint_scores": torch.Tensor, # [B, N]         关键点置信度分数
    "descriptors": torch.Tensor,    # [B, D, N]      描述子向量，D=256
}
```

| 字段 | 形状 | 说明 |
|------|------|------|
| `keypoints` | `[B, N, 2]` | N 个关键点的 (x, y) 坐标，x 和 y 是像素位置 |
| `keypoint_scores` | `[B, N]` | 每个关键点的置信度分数 (0~1) |
| `descriptors` | `[B, D, N]` | N 个 D=256 维的 L2 归一化描述子 |

**本工程的适配**：
- 使用 `max_num_keypoints=2048` 适应大视场角鱼眼相机
- 关键点分布更密集，提高侧视↔俯视跨视角匹配成功率

---

### 2.2 LightGlue 特征匹配

**原理**：Transformer 架构的图像匹配器

```
关键点 + 描述子 → 位置编码 → 多层 Transformer
                                       ├→ Self-Attention (单图像内)
                                       ├→ Cross-Attention (双图像间)
                                       └→ 匹配分配矩阵 → 双向一致性过滤
```

#### 输入格式

```python
data = {
    "image0": {
        "keypoints": torch.Tensor,    # [B, M, 2]  图像0的M个关键点
        "descriptors": torch.Tensor,  # [B, D, M]  图像0的描述子
        "image_size": torch.Tensor,   # [B, 2]     (W, H) 用于坐标归一化
    },
    "image1": {
        "keypoints": torch.Tensor,    # [B, N, 2]  图像1的N个关键点
        "descriptors": torch.Tensor,  # [B, D, N]  图像1的描述子
        "image_size": torch.Tensor,   # [B, 2]     (W, H)
    }
}
```

| 字段 | 形状 | 说明 |
|------|------|------|
| `image0/1.keypoints` | `[B, M/N, 2]` | 来自 SuperPoint 的关键点坐标 |
| `image0/1.descriptors` | `[B, D, M/N]` | 来自 SuperPoint 的描述子向量 |
| `image0/1.image_size` | `[B, 2]` | 原始图像尺寸 (W, H)，用于坐标归一化 |

#### 输出格式

```python
{
    "matches0": torch.Tensor,        # [B, M]    图像0每个点匹配的图像1索引，不匹配=-1
    "matches1": torch.Tensor,        # [B, N]    图像1每个点匹配的图像0索引，不匹配=-1
    "matching_scores0": torch.Tensor,# [B, M]    匹配质量分数
    "matching_scores1": torch.Tensor,# [B, N]    匹配质量分数
    "stop": int,                     # 使用的 Transformer 层数
    "matches": List[torch.Tensor],   # 紧凑格式: [Si, 2] 每行 [idx0, idx1]
    "scores": List[torch.Tensor],    # 对应匹配分数
}
```

| 字段 | 形状 | 说明 |
|------|------|------|
| `matches0` | `[B, M]` | `matches0[i] = j` 表示图像0的第i个点匹配图像1的第j个点，`-1` 表示无匹配 |
| `matches1` | `[B, N]` | 反向匹配索引 |
| `matching_scores0` | `[B, M]` | 每个匹配的置信度分数 (0~1) |
| `stop` | `int` | Early stopping 实际使用的层数 (1~n_layers) |

**本工程的适配**：
- 使用 `depth_confidence=0.95` 提前停止，平衡精度与速度
- 使用 `filter_threshold=0.1` 过滤低质量匹配

---

### 2.3 数据流总览

```
                    SuperPoint                           LightGlue
┌─────────────┐                    ┌─────────────┐                    ┌─────────────┐
│             │  keypoints:        │             │  matches0:         │             │
│  图像0      │  [B, M, 2]         │  图像0      │  [B, M]            │  匹配结果   │
│  [B,C,H,W]  │  descriptors:      │  特征       │  matches1:         │  m_kpts0    │
│             │  [B, D, M]         │             │  [B, N]            │  m_kpts1    │
└─────────────┘                    └─────────────┘                    └─────────────┘
      │                                   │                                   │
      ▼                                   ▼                                   ▼
┌─────────────┐                    ┌─────────────┐                    ┌─────────────┐
│  图像1      │  keypoints:        │             │                    │  DBSCAN     │
│  [B,C,H,W]  │  [B, N, 2]         │  图像1      │                    │  聚类剔除   │
│             │  descriptors:      │  特征       │                    │             │
│             │  [B, D, N]         │             │                    │             │
└─────────────┘                    └─────────────┘                    └─────────────┘
```

---

## 3. 适配工程的核心修改

### 3.1 鱼眼等距投影模型

**问题**：标准针孔相机模型不适用于鱼眼相机的大视场角畸变

**解决方案**：等距投影模型 (Equidistant Projection)

```python
# 投影方程: r = f * (θ + k1*θ³ + k2*θ⁵ + k3*θ⁷ + k4*θ⁹)
# 其中: r=像素到中心距离, θ=入射角, k=畸变系数

# 像素 → 球面坐标转换
def pixel_to_unit_sphere(uv_coords, K, D):
    # 1. 归一化图像坐标: x = (u - cx) / fx
    # 2. 求解 θ (牛顿迭代法)
    # 3. 计算球面坐标: [sin(θ)*x_norm, sin(θ)*y_norm, cos(θ)]
```

**本工程修改**：在 `utils.py` 中实现了完整的鱼眼相机球面投影变换，将匹配点从像素坐标转换到单位球面，以便进行后续的球面极线几何估计。

### 3.2 球面本质矩阵估计

**问题**：侧视与俯视相机之间是纯旋转关系（无平移），标准本质矩阵无法估计

**解决方案**：球面本质矩阵 (Sphere Essential Matrix)

```python
# 球面本质矩阵: E = [t]× @ R
# 对于单位球面上的点 p, p':
#   p'^T @ E @ p ≈ 0

# 双向几何误差 (适配纯旋转)
error1 = arcsin(|p'^T E p| / ||E p||)   # p' 相对 p 的极线
error2 = arcsin(|p^T E^T p'| / ||E^T p'||) # p 相对 p' 的极线
total_error = error1 + error2
```

**本工程修改**：在 `utils.py` 的 `SphereEssentialEstimator` 类中实现了球面极线几何估计，适用于纯旋转场景。

### 3.3 鲁棒核函数优化

**问题**：匹配存在异常点，直接最小化会导致估计偏差

**解决方案**：Cauchy 核函数 + L-BFGS-B 优化

```python
def cauchy_loss(residuals, c):
    """Cauchy 核函数: 平滑抑制大误差"""
    return (c**2 / 2) * np.log(1 + (residuals / c)**2)

# 优化: minimize(cauchy_loss(error), R_init)
```

**本工程修改**：使用 Cauchy 核函数替代标准 RANSAC，在纯旋转估计中更稳定。

### 3.4 DBSCAN 聚类异常剔除

#### 问题分析

在侧视↔俯视跨视角匹配中，存在以下问题：

1. **多对一映射**：俯视相机中的一个特征点可能匹配侧视相机中的多个特征点（因为俯视视角看到地面更大范围）
2. **双向一致性不足**：传统 LightGlue 的双向一致性过滤只能确保 A→B→A 回溯到原点，但不能区分"一对一"和"多对一"匹配
3. **离群点干扰**：错误匹配如果参与姿态估计，会导致较大偏差

#### DBSCAN 聚类原理

DBSCAN (Density-Based Spatial Clustering of Applications with Noise) 是一种基于密度的聚类算法：

```
核心概念:
- eps: 邻域半径 (本工程 0.0005)
- min_samples: 最小点数 (本工程 5)
- 核心点: 半径 eps 内至少有 min_samples 个点
- 密度可达: 点 A 可以通过核心点链式连接到达点 B
```

#### 本工程实现

**步骤1：构建特征向量**

```python
# 每个匹配点构建 4 维特征:
# [kpts0_x, kpts0_y, kpts1_x, kpts1_y]
# 即: 侧视图像坐标 + 俯视图像坐标

features = np.column_stack([
    combined_kpts0[:, 0],  # m_kpts0_x
    combined_kpts0[:, 1],  # m_kpts0_y
    combined_kpts1[:, 0],  # m_kpts1_x
    combined_kpts1[:, 1],  # m_kpts1_y
])

# 标准化 (非常重要！)
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features)
```

**为什么需要 4 维特征？**

- 如果只是空间上的近邻，使用 2 维特征即可
- 4 维特征确保：只有**两个图像上对应位置都相近**的点才会聚在一起
- 这天然过滤了错误匹配（错误匹配的侧视坐标和俯视坐标不构成合理的几何关系）

**步骤2：DBSCAN 聚类**

```python
clustering = DBSCAN(eps=0.0005, min_samples=5).fit(features_scaled)

# eps=0.0005 是归一化坐标后的值
# 相当于在原图中 ~3-5 像素的邻域半径
```

**步骤3：过滤有效聚类**

```python
unique_labels, counts = np.unique(clustering.labels_, return_counts=True)
valid_clusters = unique_labels[counts >= 5]  # 至少 5 个点

if len(valid_clusters) < 8:
    continue  # 有效聚类不足，跳过该数据集
```

**筛选逻辑**：
- `label == -1`: 噪声点（不属于任何聚类），直接丢弃
- `counts < 5`: 小聚类，可能是离群点，丢弃
- `len(valid_clusters) < 8`: 整体匹配质量不足，可能是场景问题

#### 聚类中心计算

对于每个有效聚类，计算其几何中心作为代表点：

```python
robust_clusters = []
for cluster_id in valid_clusters:
    # 1. 提取该聚类的所有匹配点
    cluster_mask = clustering.labels_ == cluster_id

    # 2. 计算聚类中心（均值）
    avg_m_kpts0 = np.mean(cluster_original_features[:, :2], axis=0)  # 侧视图像坐标中心
    avg_m_kpts1 = np.mean(cluster_original_features[:, 2:], axis=0)  # 俯视图像坐标中心

    # 3. 计算平均匹配分数
    avg_match_scores = np.mean(cluster_match_scores, axis=0)

    # 4. 保存
    robust_clusters.append({
        'avg_m_kpts0': avg_m_kpts0,           # [x, y] 侧视坐标中心
        'avg_m_kpts1': avg_m_kpts1,           # [x, y] 俯视坐标中心
        'avg_match_scores': avg_match_scores, # 匹配质量
        'count': len(cluster_original_features), # 聚类大小
    })
```

**为什么用聚类中心而非所有点？**

1. **抗噪声**：聚类中心是多个匹配点的均值，单个错误匹配的影响被稀释
2. **计算效率**：减少后续姿态估计的点数量，加速优化
3. **几何一致性**：中心点代表了该区域最"主流"的匹配关系

#### 效果示意

```
原始匹配 (可能有噪声):
   侧视图像                    俯视图像
    ● ● ●                       ● ● ●
    ● ● ●    ----匹配---->     ● ○ ●  (○ = 错误匹配)
    ● ● ●                       ● ● ●

DBSCAN 聚类后:
  Cluster A (红色): 核心区域的有效匹配
  Cluster B (蓝色): 另一个区域的有效匹配
  噪声点: 被丢弃的错误匹配

聚类中心:
  A 中心点 -----> 参与姿态估计
  B 中心点 -----> 参与姿态估计
```

#### 参数调优建议

| 参数 | 默认值 | 调整建议 |
|------|--------|----------|
| `eps` | 0.0005 | 图像分辨率越高，可适当增大 |
| `min_samples` | 5 | 场景特征丰富可增大，减少噪声 |
| `valid_clusters` | >= 8 | 匹配质量差时可减小 |

**本工程修改**：在 `utils.py` 中完整实现，针对鱼眼图像分辨率选取 eps=0.0005（归一化坐标后）。

---

## 4. 核心代码文件

```
LightGlue/
├── calib_side_sur.py          # 命令行入口
├── utils.py                   # 核心标定逻辑 (~1020行)
│   ├── pixel_to_unit_sphere()     # 鱼眼球面投影
│   ├── SphereEssentialEstimator   # 球面姿态估计
│   ├── calib_side_sur()           # 主函数
│
└── lightglue/                 # 开源特征匹配模块
    ├── lightglue.py           # LightGlue Transformer
    ├── superpoint.py          # SuperPoint 特征提取
    ├── viz2d.py               # 可视化工具
    └── utils.py               # 图像预处理
```

---

## 5. 关键参数配置

### 5.1 SuperPoint 特征提取

| 参数 | 值 | 说明 |
|------|-----|------|
| `max_num_keypoints` | 2048 | 大视场角需要更多特征点 |
| `nms_radius` | 4 | NMS 抑制半径 |
| `detection_threshold` | 0.0005 | 关键点检测阈值 |

### 5.2 LightGlue 匹配

| 参数 | 值 | 说明 |
|------|-----|------|
| `n_layers` | 9 | Transformer 层数 |
| `depth_confidence` | 0.95 | 提前停止阈值 |
| `filter_threshold` | 0.1 | 匹配过滤阈值 |

### 5.3 姿态估计

| 参数 | 值 | 说明 |
|------|-----|------|
| `DBSCAN eps` | 0.0005 | 聚类距离阈值 |
| `valid_clusters` | >= 8 | 最少有效聚类数 |
| `SphereEstimator threshold` | 0.01 rad | 内点阈值 (~0.57°) |
| `kernel_type` | 'cauchy' | 鲁棒核函数 |

---

## 6. 使用方法

```bash
python calib_side_sur.py \
    --side_list "side_cam_f,side_cam_b" \
    --sur_list "sur_cam" \
    --datasets "path/to/datasets" \
    --result_path "path/to/res.txt" \
    --visualize
```

### 输入数据格式

```
datasets/
├── calibration.json    # 内参 + 外参
└── cameras/
    ├── side_cam_f/*.jpg
    ├── side_cam_b/*.jpg
    └── sur_cam/*.jpg
```

### calibration.json 格式

```json
{
    "side_cam_f": {
        "K": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
        "D": [k1, k2, k3, k4],
        "transform": {"transform_matrix": [...]}  // 外参
    },
    "sur_cam": {...}
}
```

---

## 7. 输出格式

```
# res.txt 示例
dataset1: (125/156) side_cam_f sur_cam = 0.32°
dataset1: (98/142) side_cam_b sur_cam = 0.45°
```

格式: `(inliers/total) side_cam_name sur_cam_name = rotation_error`

---

## 8. 工程适配总结

| 开源模块 | 原生用途 | 本工程适配 |
|----------|----------|------------|
| SuperPoint | 标准针孔相机特征提取 | 增加特征点数量适配大视场角 |
| LightGlue | 同尺度图像匹配 | 跨视角（侧视↔俯视）匹配 |
| 姿态估计 | 标准本质矩阵 (有平移) | 球面本质矩阵 (纯旋转) |
| 异常剔除 | 双向一致性过滤 | DBSCAN 聚类处理多对一映射 |
| 投影模型 | 针孔投影 | 鱼眼等距投影模型 |

分析可行性