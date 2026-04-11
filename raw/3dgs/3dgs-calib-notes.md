# 3DGS-Calib 架构与算法

## 基于 MLP 的 3D Gaussian Splatting 参数预测与外参联合标定系统

---

## 一、系统概述

### 1.1 项目背景

3DGS-Calib 是一个基于 3D Gaussian Splatting (3DGS) 技术的神经渲染系统，核心创新在于使用 HashGrid 编码的 MLP 网络直接预测 3D 高斯参数，而非像原始 3DGS 那样通过逐点优化获得。这种方法具有以下优势：

- **参数效率高**：MLP 隐式表示场景，避免存储数百万独立高斯参数
- **泛化能力强**：学习到的特征可以泛化到未见视角
- **支持在线标定**：可联合优化相机外参，实现自标定功能

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        输入：点云 PCD                            │
│                     N 个三维点 {x_i, y_i, z_i}                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. 点云预处理                                                   │
│     - 归一化：x' = (x - x_min) / (x_max - x_min) ∈ [0,1]        │
│     - 输出：xyz_normalized [N, 3], xyz_original [N, 3]          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. HashGrid 编码                                                │
│     输入：xyz_normalized [N, 3]                                  │
│     输出：features [N, 32]  (16 层 × 2 特征/层)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. FullyFusedMLP 预测                                          │
│     输入：features [N, 32]                                       │
│     输出：raw [N, 11] → color(3) + opacity(1) + scale(3) + rot(4)│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 参数激活与约束                                               │
│     - color = sigmoid(·) ∈ [0,1]                                 │
│     - opacity = sigmoid(·) ∈ [0,1]                               │
│     - scale = sigmoid(·) × scale_size ∈ [0, scale_size]          │
│     - rotation = normalize(·)  单位四元数                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. 3DGS 可微光栅化                                              │
│     3D 高斯 → 2D 投影 → Alpha Blending → 渲染图像 [H, W, 3]        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. 损失计算与反向传播                                           │
│     L = L1(render, gt) + λ_scale × L_scale_reg                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、核心算法原理

### 2.1 Hash Grid 编码

#### 2.1.1 动机与优势

传统的位置编码（Positional Encoding）存在以下局限：

| 问题 | 描述 |
|------|------|
| 高频信息丢失 | 低频基函数难以捕捉细节 |
| 计算效率低 | 需要多个频率分量 |

HashGrid（Müller et al., 2022）通过多分辨率哈希特征网格解决上述问题：

| 特性 | 描述 |
|------|------|
| 空间局部性 | 相近点共享哈希特征，实现平滑插值 |
| 多尺度表示 | 不同分辨率捕获不同频率信息 |
| 内存高效 | 哈希表大小固定，不随场景增大 |

#### 2.1.2 数学表达

对于输入点 `x ∈ [0,1]³`，HashGrid 编码过程：

**步骤 1：多分辨率网格采样**

在第 `l` 层的分辨率：`b_l = ⌊b₀ · α^l⌋`

其中：
- `b₀ = 16`：基础分辨率
- `α = 2.0`：每层分辨率缩放因子
- `l = 0, 1, ..., L-1`，`L = 16` 为总层数

**步骤 2：顶点坐标计算**

对第 `l` 层，计算 `x` 所在网格单元的 8 个顶点：

```
v_l,i = floor(b_l · x) + δ_i,  i = 0, ..., 7
```

其中 `δ_i ∈ {0,1}³` 为顶点偏移。

**步骤 3：哈希映射**

将顶点坐标映射到哈希表索引：

```
h_l,i = (∏(d=0 to 2) π_d ⊕ v_l,i,d) mod T
```

其中：
- `T = 2^19`：哈希表大小
- `π_d`：素数（用于打散空间相关性）
- `⊕`：异或操作

**步骤 4：特征插值**

从哈希表取出特征并三线性插值：

```
f_l(x) = Σ(i=0 to 7) w_l,i · E[h_l,i]
```

其中 `E ∈ R^(T×2)` 为可学习特征表（每层 2 特征）。

**步骤 5：层级拼接**

```
Enc_HashGrid(x) = f_0(x) ⊕ f_1(x) ⊕ ... ⊕ f_{L-1}(x)
```

最终输出维度：`16 × 2 = 32`

#### 2.1.3 本项目配置

```json
{
    "otype": "HashGrid",
    "n_levels": 16,              // L = 16 层
    "n_features_per_level": 2,   // 每层 2 个特征
    "log2_hashmap_size": 19,     // T = 2^19 ≈ 524,288
    "base_resolution": 16,       // b_0 = 16
    "per_level_scale": 2.0       // α = 2.0
}
```

### 2.2 MLP 参数预测器

#### 2.2.1 网络架构

采用 NVIDIA `tiny-cuda-nn` 的 `FullyFusedMLP`，特点：

| 特性 | 描述 |
|------|------|
| GPU 优化 | 利用 Tensor Core 加速矩阵乘法 |
| 共享权重 | 所有点共享同一 MLP，参数高效 |
| 深度监督 | 跳过连接促进梯度流动 |

```json
{
    "otype": "FullyFusedMLP",
    "activation": "ReLU",
    "output_activation": "None",  // 输出层无激活，由后处理约束
    "n_neurons": 64,              // 每层 64 神经元
    "n_hidden_layers": 2          // 2 层隐藏层
}
```

**网络结构：** `32 → 64 → 64 → 11`

#### 2.2.2 输出参数分解

MLP 输出 `o ∈ R^11` 分解为 4 组 3DGS 参数：

```
o = [c₀, c₁, c₂, α, s₀, s₁, s₂, q₀, q₁, q₂, q₃]
     └─────┬─────┘ └─┬─┘ └─────┬─────┘ └──────┬──────┘
       color      opacity    scale       rotation
```

| 参数 | 维度 | 物理意义 | 约束条件 |
|------|------|----------|----------|
| color | 3 | RGB 颜色 | [0, 1] |
| opacity | 1 | 不透明度 | [0, 1] |
| scale | 3 | 高斯球三轴半径 | (0, scale_size] |
| rotation | 4 | 旋转四元数 | 单位四元数 \|q\|=1 |

#### 2.2.3 参数激活函数

**颜色激活：**
```
c = σ(o₀:₂) = 1 / (1 + e^(-o₀:₂)) ∈ [0,1]³
```

**不透明度激活：**
```
α = σ(o₃) = 1 / (1 + e^(-o₃)) ∈ [0,1]
```

**尺度激活：**
```
s = σ(o₄:₆) × scale_size ∈ [0, scale_size]³
```

其中 `scale_size = voxel_size / 4 = 0.02 / 4 = 0.005` 米

**旋转归一化：**
```
q = o₇:₁₀ / (‖o₇:₁₀‖₂ + ε)
```

其中 `ε = 10⁻⁸` 防止除零。

#### 2.2.4 前向传播

```
features = Enc_HashGrid(x_norm)
o        = MLP(features)
(c, α, s, q) = Activate(o)
```

### 2.3 3DGS 渲染原理

#### 2.3.1 3D 高斯表示

每个高斯球由以下参数定义：

| 参数 | 维度 | 描述 |
|------|------|------|
| μ ∈ R³ | 中心位置 | 本项目使用原始点云坐标，不优化 |
| Σ ∈ R^(3×3) | 协方差矩阵 | 由缩放和旋转分解 |
| c ∈ R³ | 颜色 | MLP 预测 |
| α ∈ [0,1] | 不透明度 | MLP 预测 |

**协方差矩阵分解：**

```
Σ = R · S · S^T · R^T
```

其中：
- `S = diag(s₀, s₁, s₂)`：缩放矩阵
- `R`：旋转矩阵（由四元数 `q` 转换）

#### 2.3.2 可微光栅化

**步骤 1：3D 到 2D 投影**

3D 高斯投影到图像平面形成 2D 高斯：

```
Σ' = J · W · Σ · W^T · J^T
```

其中：
- `W ∈ R^(4×4)`：视图矩阵（世界→相机）
- `J ∈ R^(3×3)`：投影雅可比矩阵

**步骤 2：像素贡献计算**

对像素 `u = (u, v)`，高斯 `i` 的贡献权重：

```
w_i(u) = α_i · exp(-0.5 · (u - μ'_i)^T · Σ'^(-1)_i · (u - μ'_i))
```

**步骤 3：Alpha Blending**

按深度排序后混合：

```
C(u) = Σ(i∈N) c_i · w_i(u) · Π(j=1 to i-1) (1 - w_j(u))
```

其中 `N` 为对像素有贡献的高斯集合（通过 tile-based culling 加速）。

#### 2.3.3 可微性

光栅化过程对所有参数可微：

```
∂C/∂μ,  ∂C/∂Σ,  ∂C/∂c,  ∂C/∂α
```

这使得可以通过梯度下降优化高斯参数。

### 2.4 外参参数化

#### 2.4.1 视图矩阵分解

视图矩阵 `V ∈ R^(4×4)`（世界→相机变换）：

```
    [ R   t ]
V = [       ]
    [ 0   1 ]
```

其中：
- `R ∈ R^(3×3)`：旋转矩阵（正交矩阵，R^T · R = I）
- `t ∈ R³`：平移向量

#### 2.4.2 可优化参数设计

本项目将 `R` 和 `t` 作为独立可学习参数：

```python
self.viewmat_rotation = Parameter(torch.randn(3, 3, requires_grad=True))
self.viewmat_translation = Parameter(torch.randn(3, requires_grad=True))
```

**约束保持：**
- 旋转矩阵通过梯度下降更新后，需重新正交化（代码中暂未显式处理，依赖小学习率维持近似正交）
- 平移向量无约束

#### 2.4.3 外参优化时机

采用延迟优化策略：

| 阶段 | 步数范围 | 优化参数 |
|------|----------|----------|
| Warmup | 0 → N_warmup | 仅 MLP 参数 |
| Finetune | N_warmup → N_total | MLP + 外参 |

```python
extrinsic_start_step = config.get('extrinsic_start_step', num_steps)
if step >= extrinsic_start_step:
    optimize_extrinsic = True
```

默认 `N_warmup = num_steps`，即默认不启用外参优化。

---

## 三、训练优化策略

### 3.1 损失函数设计

#### 3.1.1 总损失函数

```
L = L_L1 + λ_scale · L_scale_reg
```

其中：
- `L_L1`：像素级重建损失
- `L_scale_reg`：尺度正则化
- `λ_scale = 0.001`：平衡系数

#### 3.1.2 L1 重建损失

对渲染图像 `Î` 和真值图像 `I`：

```
L_L1 = (1 / |Ω_ROI|) · Σ(u∈Ω_ROI) |Î(u) - I(u)|
```

其中 `Ω_ROI` 为感兴趣区域（见 3.4 节）。

#### 3.1.3 尺度正则化损失

**动机：** 3DGS 论文指出，无约束的高斯球会过度膨胀，导致几何模糊。

**策略对比：**

| 方法 | 公式 | 特点 |
|------|------|------|
| 3DGS 论文 | \|s - s̄\|₁ | 鼓励高斯间尺度一致 |
| 本项目 | \|s - 0\|₁ | 鼓励小尺度，几何更清晰 |

**本项目采用：**

```
L_scale_reg = (1 / |G_ROI|) · Σ(g∈G_ROI) ‖s_g‖₁
```

其中 `G_ROI` 为投影到 ROI 区域且可见的高斯集合。

**可见性判断：**

```python
visible = (radii > 0).any(dim=-1)  # 半径 > 0 表示对像素有贡献
in_roi = (u_min <= means2d[:, 0] <= u_max) & \
         (v_min <= means2d[:, 1] <= v_max) & \
         visible
```

### 3.2 两阶段训练策略

#### 3.2.1 阶段划分

| 阶段 | 步数范围 | 优化参数 | 优化器 |
|------|----------|----------|--------|
| Stage 1 | 0 → N_warmup | MLP (encoding + network) | Adam |
| Stage 2 | N_warmup → N_total | MLP + 外参 | Adam + Adam_extrinsic |

#### 3.2.2 优化器配置

**MLP 优化器：**

```python
optimizer = Adam([
    {'params': encoding.parameters(), 'lr': 5e-3, 'weight_decay': 1e-4},
    {'params': network.parameters(), 'lr': 1e-2, 'weight_decay': 0}
])
```

**外参优化器（延迟初始化）：**

```python
extrinsic_optimizer = Adam([
    {'params': viewmat_rotation, 'lr': 1e-3},
    {'params': viewmat_translation, 'lr': 5e-3}
])
```

#### 3.2.3 策略优势

| 优势 | 描述 |
|------|------|
| 稳定性 | 先让 MLP 收敛到合理解，再引入外参自由度 |
| 解耦 | 避免初期两个子问题互相干扰 |
| 灵活性 | 可通过 `extrinsic_start_step` 控制外参优化时机 |

### 3.3 学习率策略

#### 3.3.1 分层学习率

| 参数组 | 学习率 | 设计理由 |
|--------|--------|----------|
| HashGrid Encoding | 5×10⁻³ | 特征网格需要较快收敛 |
| MLP Network | 1×10⁻² | 深层网络需要更高学习率 |
| 外参旋转 | 1×10⁻³ | 旋转对渲染影响敏感 |
| 外参平移 | 5×10⁻³ | 平移通常变化幅度更大 |

#### 3.3.2 学习率调度

本项目采用 `ExponentialLR`：

```
lr_t = lr₀ · γ^t
```

其中 `γ = 0.999`，每步衰减 0.1%。

```python
scheduler = ExponentialLR(optimizer, gamma=0.999)
```

> **备注：** 代码中保留了 `OneCycleLR` 的注释配置，可按需切换。

### 3.4 ROI 区域策略

#### 3.4.1 动机

| 原因 | 描述 |
|------|------|
| 计算效率 | 全图损失计算开销大 |
| 噪声抑制 | 天空/墙壁等无点云区域会引入噪声梯度 |
| 场景特性 | 自动驾驶场景中，地面和近场物体更重要 |

#### 3.4.2 配置方式

按相机单独配置 ROI（归一化坐标 [0,1]）：

```json
{
    "camera_front_wide": {
        "x_min": 0.0, "x_max": 1.0,
        "y_min": 0.0, "y_max": 0.7
    }
}
```

#### 3.4.3 实现细节

**ROI 区域定义：**

```python
x_min = int(W * roi['x_min'])
x_max = int(W * roi['x_max'])
y_min = int(H * roi['y_min'])
y_max = int(H * roi['y_max'])
```

**损失计算：**

```python
render_roi = render_image[y_min:y_max, x_min:x_max, :]
gt_roi = gt_image[y_min:y_max, x_min:x_max, :]
l1_loss = F.l1_loss(render_roi, gt_roi)
```

### 3.5 多相机支持

#### 3.5.1 相机权重配置

主相机（如前广）赋予更高权重：

```python
camera_weights = {
    "camera_front_wide": 2.0,   # 主相机
    "camera_left_front": 1.0,
    "camera_right_front": 1.0,
    # ...
}
```

**自动归一化：** `w'_c = w_c / Σ(k) w_k`

#### 3.5.2 数据加载

```python
config = {
    'camera_name': [
        "camera_front_wide",
        "camera_left_front",
        "camera_right_front",
        "camera_left_back",
        "camera_right_back",
    ],
    'image_base_dir': "/path/to/camera/",
    'batch_size': 20,  # 应为相机数量的倍数
}
```

---

## 四、数据流与接口

### 4.1 点云预处理

#### 4.1.1 处理流程

```
原始 PCD → 过滤 NaN/Inf → 过滤离群点 (可选) → 归一化 → CUDA Tensor
```

#### 4.1.2 归一化公式

```
x' = (x - x_min) / (x_max - x_min + ε)
```

其中 `ε = 10⁻⁸` 防止除零。

#### 4.1.3 输出张量

| 张量 | 形状 | 用途 | 范围 |
|------|------|------|------|
| xyz_normalized | [N, 3] | MLP 输入 | [0, 1] |
| xyz_original | [N, 3] | 高斯中心（渲染） | 世界坐标（米） |

### 4.2 训练数据流

```python
# 1. 加载点云 → xyz_normalized, xyz_original
# 2. 加载图像 → gt_image [H, W, 3]
# 3. 加载相机参数 → K [3,3], viewmat [4,4]

# 4. 训练循环
for step in range(num_steps):
    # a. MLP 前向 → (color, opacity, scale, rotation)
    # b. 光栅化 → render_image
    # c. 计算损失 → loss
    # d. 反向传播 → loss.backward()
    # e. 更新参数 → optimizer.step()
```

### 4.3 结果导出

#### 4.3.1 PCD 导出

保存为 CloudCompare 兼容的 `PointXYZRGB` 格式：

```python
save_3dgs_pcd(
    xyz=means,           # [N, 3]
    color=colors,        # [N, 3], range [0,1]
    save_path="output.pcd"
)
```

#### 4.3.2 渲染图像导出

每 500 步保存一帧，最终合成 GIF：

```python
frames = []  # 保存的帧
gif_path = os.path.join(output_dir, "training.gif")
```

---

## 五、关键实现细节

### 5.1 张量形状变换

| 变量 | 形状 | 说明 |
|------|------|------|
| xyz_normalized | [N, 3] | 归一化坐标 |
| features | [N, 32] | HashGrid 编码输出 |
| mlp_output | [N, 11] | MLP 原始输出 |
| color | [N, 3] | 激活后颜色 |
| opacity | [N, 1] | 激活后不透明度 |
| scale | [N, 3] | 激活后尺度 |
| rotation | [N, 4] | 归一化四元数 |
| render_image | [H, W, 3] | 渲染图像 |

### 5.2 数值稳定性处理

| 位置 | 处理 | 代码 |
|------|------|------|
| 归一化 | 防止除零 | `(pts_max - pts_min + 1e-8)` |
| 四元数归一化 | 防止除零 | `rotation / (rotation.norm() + 1e-8)` |
| 颜色裁剪 | 防止 NaN/Inf | `np.nan_to_num(color_np, nan=0.5)` |
| 光栅化 | 混合精度 | `means.float(), quats.float()` |

### 5.3 计算复杂度分析

| 操作 | 时间复杂度 | 空间复杂度 |
|------|------------|------------|
| HashGrid 编码 | O(N·L) | O(N·L·F) |
| MLP 前向 | O(N·d²) | O(N·d_out) |
| 光栅化 | O(N·A) | O(H·W) |

其中：
- `N`：高斯点数
- `L`：HashGrid 层数（16）
- `F`：每层特征数（2）
- `d`：MLP 隐藏层维度（64）
- `A`：单像素覆盖的高斯数

---

## 六、参考文献

1. Kerbl, B., et al. "3D Gaussian Splatting for Real-Time Radiance Field Rendering." SIGGRAPH 2023.
2. Müller, T., et al. "Instant Neural Graphics Primitives with a Multiresolution Hash Encoding." SIGGRAPH 2022.
3. 3DGS-Calib: 本项目代码实现
