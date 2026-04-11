---
title: "SuperPoint + LightGlue 特征匹配"
category: perception
tags:
  - feature-matching
  - superpoint
  - lightglue
  - camera-calibration
  - spherical-geometry
  - dbscan
  - transformer
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/calibration_geo/superpoint-lightglue.md
---

# SuperPoint + LightGlue 特征匹配

## 一、概述

本模块用于**侧视鱼眼相机与俯视鱼眼相机之间的外参标定**，基于深度学习特征匹配方法实现相对姿态估计。

```
输入: 侧视相机图像 + 俯视相机图像 + 内参文件
输出: 两相机之间的相对旋转矩阵 R 和平移向量 t
```

## 二、整体流程

```
+---------------------------------------------------------------------------------+
|                                  标定流程                                         |
+---------------------------------------------------------------------------------+
|                                                                                 |
|  +-------------+    +-------------+    +-------------+    +-------------+       |
|  |  加载图像    |--->|  特征提取    |--->|  特征匹配    |--->|  异常剔除    |       |
|  |             |    |  SuperPoint |    |  LightGlue  |    |  DBSCAN     |       |
|  +-------------+    +-------------+    +-------------+    +-------------+       |
|                                                               |                  |
|                                                               v                  |
|  +-------------+    +-------------+    +-------------+    +-------------+       |
|  |  误差评估    |<---|  姿态优化    |<---|  球面变换    |<---|  聚类中心    |       |
|  |             |    |  L-BFGS-B   |    |  等距投影    |    |  计算        |       |
|  +-------------+    +-------------+    +-------------+    +-------------+       |
|                                                                                 |
+---------------------------------------------------------------------------------+
```

### 核心步骤

| 步骤 | 功能 | 工程适配关键点 |
|------|------|-----------------|
| 1. 图像加载 | 加载侧视/俯视相机图像，按时间戳配对 | 适配多相机数据格式 |
| 2. 特征提取 | SuperPoint 检测关键点并提取描述子 | 适配鱼眼相机大视场角 |
| 3. 特征匹配 | LightGlue Transformer 匹配 | 适配不同视角（侧视 $\leftrightarrow$ 俯视） |
| 4. 异常剔除 | DBSCAN 聚类过滤匹配异常点 | 处理纯旋转场景的特征分布 |
| 5. 球面变换 | 像素坐标 $\to$ 单位球面坐标 | **适配鱼眼等距投影模型** |
| 6. 姿态估计 | 球面本质矩阵 + 鲁棒优化 | **适配纯旋转估计（RANSAC-free）** |
| 7. 误差评估 | 计算旋转误差与 GT 对比 | 验证标定精度 |

## 三、SuperPoint 特征提取

### 3.1 原理

SuperPoint 是 CNN-based 关键点检测与描述子提取网络：

```
输入图像 -> 共享编码器(多层卷积) -> 分支
                                +-> 关键点检测头 (65通道 -> NMS -> 关键点)
                                +-> 描述子头 (L2归一化 -> 采样)
```

### 3.2 描述子 (Descriptor)

描述子是一个 **256 维向量**，用于描述图像中某个点周围的局部纹理特征。

**描述子特性：**

| 特性 | 说明 |
|------|------|
| 维度 | 256 维 |
| 归一化 | L2 归一化 (向量长度为 1) |
| 相似度度量 | 余弦相似度 (点积) |

**计算过程：**

1. **共享编码器**输出特征图: $[B, 128, H/8, W/8]$
2. **描述子头**: 卷积 + ReLU -> $[B, 256, H/8, W/8]$，L2 归一化
3. **关键点采样**: 使用双线性插值从特征图中提取描述子向量
4. **输出**: $[B, 256, N]$，$N$ 个关键点各对应一个 256 维向量

**坐标变换**（关键点坐标 $\to$ 描述子采样坐标）：

```python
def sample_descriptors(keypoints, descriptors, s=8):
    # s=8 表示特征图是原图的 1/8 分辨率
    # 1. 坐标偏移 (对齐到特征图网格中心)
    keypoints = keypoints - s / 2 + 0.5
    # 2. 归一化到 [0, 1]
    keypoints /= [(w*s - s/2 - 0.5), (h*s - s/2 - 0.5)]
    # 3. 归一化到 [-1, 1] (grid_sample 要求)
    keypoints = keypoints * 2 - 1
    # 4. 双线性插值采样
    descriptors = F.grid_sample(descriptors, keypoints.view(b, 1, -1, 2))
    # 5. L2 归一化
    descriptors = F.normalize(descriptors, p=2, dim=1)
    return descriptors
```

**相似度计算**（描述子已 L2 归一化，直接点积）：

$$
\text{similarity} = \mathbf{d}_1 \cdot \mathbf{d}_2 \in [-1, 1]
$$

### 3.3 输入输出格式

**输入：**

| 字段 | 形状 | 说明 |
|------|------|------|
| `image` | $[1, C, H, W]$ 或 $[C, H, W]$ | 输入图像，C=1(灰度)或3(RGB) |

**输出：**

| 字段 | 形状 | 说明 |
|------|------|------|
| `keypoints` | $[B, N, 2]$ | $N$ 个关键点的 $(x, y)$ 坐标 |
| `keypoint_scores` | $[B, N]$ | 每个关键点的置信度分数 (0~1) |
| `descriptors` | $[B, 256, N]$ | $N$ 个 256 维的 L2 归一化描述子 |

**工程适配：** 使用 `max_num_keypoints=2048` 适应大视场角鱼眼相机，关键点分布更密集，提高侧视 $\leftrightarrow$ 俯视跨视角匹配成功率。

## 四、LightGlue 特征匹配

### 4.1 原理

LightGlue 是基于 Transformer 架构的图像匹配器：

```
关键点 + 描述子 -> 位置编码 -> 多层 Transformer
                                  +-> Self-Attention (单图像内)
                                  +-> Cross-Attention (双图像间)
                                  +-> 匹配分配矩阵 -> 双向一致性过滤
```

### 4.2 输入输出格式

**输入：**

```python
data = {
    "image0": {
        "keypoints": torch.Tensor,    # [B, M, 2]  图像0的M个关键点
        "descriptors": torch.Tensor,  # [B, D, M]  图像0的描述子
        "image_size": torch.Tensor,   # [B, 2]     (W, H)
    },
    "image1": {
        "keypoints": torch.Tensor,    # [B, N, 2]  图像1的N个关键点
        "descriptors": torch.Tensor,  # [B, D, N]  图像1的描述子
        "image_size": torch.Tensor,   # [B, 2]     (W, H)
    }
}
```

**输出：**

| 字段 | 形状 | 说明 |
|------|------|------|
| `matches0` | $[B, M]$ | 图像0每个点匹配的图像1索引，不匹配=-1 |
| `matches1` | $[B, N]$ | 反向匹配索引 |
| `matching_scores0` | $[B, M]$ | 匹配置信度分数 (0~1) |
| `stop` | int | Early stopping 实际使用的层数 |

**工程适配：**
- `depth_confidence=0.95`: 提前停止，平衡精度与速度
- `filter_threshold=0.1`: 过滤低质量匹配

### 4.3 数据流总览

```
                    SuperPoint                          LightGlue
+-------------+                    +-------------+                    +-------------+
|             |  keypoints:        |             |  matches0:         |             |
|  图像0       |  [B, M, 2]         |  图像0       |  [B, M]            |  匹配结果    |
|  [B,C,H,W]  |  descriptors:      |  特征        |  matches1:         |  m_kpts0    |
|             |  [B, D, M]         |             |  [B, N]            |  m_kpts1    |
+------+------+                    +------+------+                    +------+------+
       |                                |                                 |
       v                                v                                 v
+------+------+                    +------+                          +------+------+
|  图像1       |  keypoints:        |      |                          |  DBSCAN      |
|  [B,C,H,W]  |  [B, N, 2]         |  图像1 |                          |  聚类剔除    |
|             |  descriptors:      |  特征  |                          |             |
|             |  [B, D, N]         |      |                          |             |
+-------------+                    +------+                          +-------------+
```

## 五、工程适配的核心修改

### 5.1 鱼眼等距投影模型

**问题**：标准针孔相机模型不适用于鱼眼相机的大视场角畸变。

**解决方案**：等距投影模型 (Equidistant Projection)

投影方程：

$$
r = f \cdot (\theta + k_1\theta^3 + k_2\theta^5 + k_3\theta^7 + k_4\theta^9)
$$

其中 $r$ 为像素到中心距离，$\theta$ 为入射角，$k_i$ 为畸变系数。

**像素到球面坐标转换：**

```python
def pixel_to_unit_sphere(uv_coords, K, D):
    # 1. 归一化图像坐标: x = (u - cx) / fx
    # 2. 求解 theta (牛顿迭代法)
    # 3. 计算球面坐标: [sin(theta)*x_norm, sin(theta)*y_norm, cos(theta)]
```

在 `utils.py` 中实现了完整的鱼眼相机球面投影变换，将匹配点从像素坐标转换到单位球面。

### 5.2 球面本质矩阵估计

**问题**：侧视与俯视相机之间是纯旋转关系（无平移），标准本质矩阵无法估计。

**解决方案**：球面本质矩阵 (Sphere Essential Matrix)

对于单位球面上的点 $\mathbf{p}, \mathbf{p}'$：

$$
\mathbf{p}'^\top \mathbf{E} \mathbf{p} \approx 0
$$

其中 $\mathbf{E} = [\mathbf{t}]_\times \mathbf{R}$。

**双向几何误差**（适配纯旋转）：

$$
\theta_{\text{sym}} = \arcsin\left( \frac{|\mathbf{p}'^\top \mathbf{E} \mathbf{p}|}{\|\mathbf{E} \mathbf{p}\|} \right)
+ \arcsin\left( \frac{|\mathbf{p}'^\top \mathbf{E} \mathbf{p}|}{\|\mathbf{E}^\top \mathbf{p}'\|} \right)
$$

### 5.3 鲁棒核函数优化

**问题**：匹配存在异常点，直接最小化会导致估计偏差。

**解决方案**：Cauchy 核函数 + L-BFGS-B 优化

$$
\text{Cauchy}(r, c) = \frac{c^2}{2} \log\left(1 + \left(\frac{r}{c}\right)^2\right)
$$

使用 Cauchy 核函数替代标准 RANSAC，在纯旋转估计中更稳定。

### 5.4 DBSCAN 聚类异常剔除

#### 问题分析

在侧视 $\leftrightarrow$ 俯视跨视角匹配中存在：

1. **多对一映射**：俯视相机中的一个特征点可能匹配侧视相机中的多个特征点
2. **双向一致性不足**：LightGlue 的双向一致性过滤不能区分"一对一"和"多对一"匹配
3. **离群点干扰**：错误匹配参与姿态估计会导致较大偏差

#### DBSCAN 原理

DBSCAN 是基于密度的聚类算法：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `eps` | 0.0005 | 邻域半径（归一化坐标后） |
| `min_samples` | 5 | 最小核心点数 |

**实现步骤：**

1. **构建 4 维特征向量**：$[\text{kpts0}_x, \text{kpts0}_y, \text{kpts1}_x, \text{kpts1}_y]$
   - 4 维特征确保：只有两个图像上对应位置都相近的点才会聚在一起
   - 天然过滤了错误匹配
2. **标准化**：使用 StandardScaler 对特征进行标准化
3. **DBSCAN 聚类**：`DBSCAN(eps=0.0005, min_samples=5)`
4. **过滤有效聚类**：类内样本数 $\geq 5$ 且有效聚类总数 $\geq 8$
5. **聚类中心计算**：对每个有效聚类计算均值作为代表点

**参数调优建议：**

| 参数 | 默认值 | 调整建议 |
|------|--------|----------|
| `eps` | 0.0005 | 图像分辨率越高，可适当增大 |
| `min_samples` | 5 | 场景特征丰富可增大，减少噪声 |
| `valid_clusters` | $\geq 8$ | 匹配质量差时可减小 |

## 六、关键参数配置

### 6.1 SuperPoint 特征提取

| 参数 | 值 | 说明 |
|------|-----|------|
| `max_num_keypoints` | 2048 | 大视场角需要更多特征点 |
| `nms_radius` | 4 | NMS 抑制半径 |
| `detection_threshold` | 0.0005 | 关键点检测阈值 |

### 6.2 LightGlue 匹配

| 参数 | 值 | 说明 |
|------|-----|------|
| `n_layers` | 9 | Transformer 层数 |
| `depth_confidence` | 0.95 | 提前停止阈值 |
| `filter_threshold` | 0.1 | 匹配过滤阈值 |

### 6.3 姿态估计

| 参数 | 值 | 说明 |
|------|-----|------|
| `DBSCAN eps` | 0.0005 | 聚类距离阈值 |
| `valid_clusters` | $\geq 8$ | 最少有效聚类数 |
| `SphereEstimator threshold` | 0.01 rad | 内点阈值 ($\approx 0.57^\circ$) |
| `kernel_type` | 'cauchy' | 鲁棒核函数 |

## 七、使用方法

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
+-- calibration.json    # 内参 + 外参
+-- cameras/
    +-- side_cam_f/*.jpg
    +-- side_cam_b/*.jpg
    +-- sur_cam/*.jpg
```

### calibration.json 格式

```json
{
    "side_cam_f": {
        "K": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
        "D": [k1, k2, k3, k4],
        "transform": {"transform_matrix": [...]}
    },
    "sur_cam": {...}
}
```

### 输出格式

```
# res.txt 示例
dataset1: (125/156) side_cam_f sur_cam = 0.32 deg
dataset1: (98/142) side_cam_b sur_cam = 0.45 deg
```

格式: `(inliers/total) side_cam_name sur_cam_name = rotation_error`

## 八、核心代码文件

```
LightGlue/
+-- calib_side_sur.py          # 命令行入口
+-- utils.py                   # 核心标定逻辑 (~1020行)
|   +-- pixel_to_unit_sphere()     # 鱼眼球面投影
|   +-- SphereEssentialEstimator   # 球面姿态估计
|   +-- calib_side_sur()           # 主函数
|
+-- lightglue/                 # 开源特征匹配模块
    +-- lightglue.py           # LightGlue Transformer
    +-- superpoint.py          # SuperPoint 特征提取
    +-- viz2d.py               # 可视化工具
    +-- utils.py               # 图像预处理
```

## 九、工程适配总结

| 开源模块 | 原生用途 | 本工程适配 |
|----------|----------|------------|
| SuperPoint | 标准针孔相机特征提取 | 增加特征点数量适配大视场角 |
| LightGlue | 同尺度图像匹配 | 跨视角（侧视 $\leftrightarrow$ 俯视）匹配 |
| 姿态估计 | 标准本质矩阵 (有平移) | 球面本质矩阵 (纯旋转) |
| 异常剔除 | 双向一致性过滤 | DBSCAN 聚类处理多对一映射 |
| 投影模型 | 针孔投影 | 鱼眼等距投影模型 |

## 相关页面

- [PVLane 检测系统架构](./pvlane-system-architecture.md) - PVLane 车道线检测系统架构、模型配置与标签字典
- [PVLane 推理与后处理](./pvlane-inference-postprocess.md) - PVLane 推理、RLE 编码、连通性分析与坐标转换
- [云端标定质检方案](./cloud-calibration-qa.md) - 基于图像/点云分割与 Ceres 后端优化的标定质量检验
