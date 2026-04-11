# 3DGS-Calib 架构与算法

## 基于 MLP 的 3D Gaussian Splatting 参数预测与外参联合标定系统

---

## 1. 系统概述

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

### 1.3 相机坐标系下的详细流程

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                           相机坐标系下的 3DGS-Calib 详细流程                              │
└──────────────────────────────────────────────────────────────────────────────────────────┘

                                    世界坐标系
                                        │
                                        │ 点云 P {P_i} (世界坐标)
                                        ▼
                        ┌───────────────────────────────────────┐
                        │     1. 点云预处理 & 坐标归一化         │
                        │   x' = (x - x_min)/(x_max - x_min)   │
                        │   输出：P_norm [N,3] ∈ [0,1]³         │
                        │         P_world [N,3] (原始坐标)       │
                        └───────────────────────────────────────┘
                                        │
                                        │ P_norm (归一化坐标)
                                        ▼
                        ┌───────────────────────────────────────┐
                        │        2. HashGrid 空间编码            │
                        │   - 16 层多分辨率哈希网格               │
                        │   - 每层 2 特征，三线性插值             │
                        │   输出：f [N, 32]                     │
                        └───────────────────────────────────────┘
                                        │
                                        │ f (HashGrid 特征)
                                        ▼
                        ┌───────────────────────────────────────┐
                        │       3. FullyFusedMLP 前向传播        │
                        │   32 → 64 (ReLU) → 64 (ReLU) → 11    │
                        │   输出：[c(3), α(1), s(3), q(4)]     │
                        └───────────────────────────────────────┘
                                        │
                                        │ raw 输出 [N, 11]
                                        ▼
                        ┌───────────────────────────────────────┐
                        │          4. 参数激活与约束             │
                        │   color    = sigmoid(c) ∈ [0,1]³     │
                        │   opacity  = sigmoid(α) ∈ [0,1]      │
                        │   scale    = sigmoid(s) × size       │
                        │   rotation = normalize(q) (单位四元数)│
                        └───────────────────────────────────────┘
                                        │
                                        │ 3DGS 参数
                                        ▼
            ┌───────────────────────────────────────────────────────────────┐
            │                    5. 世界坐标系 → 相机坐标系变换              │
            │                                                                │
            │   输入：外参参数 [R(3,3), t(3)] + 内参 K(3,3)                  │
            │                                                                │
            │   5.1 构建视图矩阵 V ∈ R^(4×4):                               │
            │       V = [ R  t ]                                            │
            │           [ 0  1 ]                                            │
            │                                                                │
            │   5.2 坐标变换 (世界→相机):                                   │
            │       P_cam = V × P_world (齐次坐标)                          │
            │       P_cam = [x_cam, y_cam, z_cam]^T                         │
            │                                                                │
            │   5.3 高斯旋转更新 (相机坐标系下):                              │
            │       q_cam = R^{-1} × q_world                                │
            │                                                                │
            │   5.4 透视投影 (相机→归一化平面):                              │
            │       u_norm = x_cam / z_cam                                  │
            │       v_norm = y_cam / z_cam                                  │
            │                                                                │
            │   5.5 投影到像素平面 (内参变换):                                │
            │       u = f_x × u_norm + c_x                                  │
            │       v = f_y × v_norm + c_y                                  │
            │                                                                │
            │   输出：2D 投影位置 (u,v) ∈ R^(N×2)                            │
            │         2D 协方差 Σ' ∈ R^(N×2×2)                               │
            └───────────────────────────────────────────────────────────────┘
                                        │
                                        │ 2D 投影 + 协方差
                                        ▼
            ┌───────────────────────────────────────────────────────────────┐
            │                    6. 光栅化 (Rasterization)                   │
            │                                                                │
            │   6.1 Tile 划分：将图像划分为 16×16 像素块                       │
            │                                                                │
            │   6.2 可见性剔除：对每个 Tile，筛选覆盖的高斯                  │
            │       - 计算高斯在 Tile 内的贡献权重                          │
            │       - 剔除权重<阈值的低斯                                  │
            │                                                                │
            │   6.3 深度排序：对每个像素，按 z_cam 深度正向排序高斯         │
            │                                                                │
            │   6.4 Alpha Blending (从前到后):                              │
            │       w_i = α_i × exp(-½(u-μ')^T Σ'^{-1} (u-μ'))            │
            │       C(u) = Σ c_i × w_i × Π(1-w_j)  (j<i)                   │
            │                                                                │
            │   输出：渲染图像 I_render ∈ R^(H×W×3)                         │
            │         深度图 D ∈ R^(H×W)                                    │
            │         Alpha 图 A ∈ R^(H×W)                                  │
            └───────────────────────────────────────────────────────────────┘
                                        │
                                        │ I_render (渲染图像)
                                        ▼
            ┌───────────────────────────────────────────────────────────────┐
            │              7. ROI 区域损失计算                               │
            │                                                                │
            │   7.1 ROI 定义 (以相机前广为例):                               │
            │       x_min = 0, x_max = W                                    │
            │       y_min = H/2, y_max = H×0.8 (图像下半部)                │
            │                                                                │
            │   7.2 裁剪 ROI 区域:                                          │
            │       I_roi = I_render[y_min:y_max, x_min:x_max]             │
            │       I_gt_roi = I_gt[y_min:y_max, x_min:x_max]              │
            │                                                                │
            │   7.3 L1 重建损失:                                            │
            │       L_l1 = mean(|I_roi - I_gt_roi|)                        │
            │                                                                │
            │   7.4 Scale 正则化损失 (对 ROI 内可见高斯):                    │
            │       找到投影到 ROI 且 radii>0 的高斯 G_roi                   │
            │       L_scale = mean(||s_g||_1) for g ∈ G_roi                │
            │                                                                │
            │   7.5 总损失:                                                 │
            │       L = L_l1 + λ_scale × L_scale                           │
            │       (λ_scale = 0.001)                                      │
            └───────────────────────────────────────────────────────────────┘
                                        │
                                        │ Loss
                                        ▼
            ┌───────────────────────────────────────────────────────────────┐
            │                  8. 反向传播 & 参数更新                        │
            │                                                                │
            │   8.1 梯度计算:                                               │
            │       ∂L/∂θ (MLP 参数), ∂L/∂R (旋转), ∂L/∂t (平移)            │
            │                                                                │
            │   8.2 优化器 step:                                            │
            │       MLP 优化器：Adam(encoding, network)                     │
            │       外参优化器：Adam(rotation, translation)                 │
            │                                                                │
            │   8.3 学习率调度：ExponentialLR(γ=0.999)                      │
            │                                                                │
            │   循环执行直到收敛                                              │
            └───────────────────────────────────────────────────────────────┘
```

### 1.4 相机参数说明

---

## 2. 核心算法原理

### 2.1 Hash Grid 编码

#### 2.1.1 动机与优势

传统的位置编码（Positional Encoding）存在以下局限：

- **高频信息丢失**：低频基函数难以捕捉细节
- **计算效率低**：需要多个频率分量

HashGrid（Müller et al., 2022）通过多分辨率哈希特征网格解决上述问题：

- **空间局部性**：相近点共享哈希特征，实现平滑插值
- **多尺度表示**：不同分辨率捕获不同频率信息
- **内存高效**：哈希表大小固定，不随场景增大

#### 2.1.2 数学表达

对于输入点 $x \in [0,1]^3$，HashGrid 编码过程：

**步骤 1：多分辨率网格采样**

在 $L$ 个分辨率层级上采样，第 $l$ 层分辨率：

$$b_l = \lfloor b_0 \cdot \alpha^l \rfloor$$

其中：

- $b_0 = 16$：基础分辨率
- $\alpha = 2.0$：每层分辨率缩放因子
- $l = 0, 1, \ldots, L-1$，$L = 16$ 为总层数

**步骤 2：顶点坐标计算**

对第 $l$ 层，计算 $x$ 所在网格单元的 8 个顶点：

$$v_{l,i} = \text{floor}(b_l \cdot x) + \delta_i, \quad i = 0, \ldots, 7$$

其中 $\delta_i \in \{0, 1\}^3$ 为顶点偏移。

**步骤 3：哈希映射**

将顶点坐标映射到哈希表索引：

$$h_{l,i} = \left( \prod_{d=0}^{2} \pi_d \oplus v_{l,i,d} \right) \bmod T$$

其中：

- $T = 2^{19}$：哈希表大小
- $\pi_d$：素数（用于打散空间相关性）
- $\oplus$：异或操作

**步骤 4：特征插值**

从哈希表取出特征并三线性插值：

$$f_l(x) = \sum_{i=0}^{7} w_{l,i} \cdot E[h_{l,i}]$$

其中 $E \in \mathbb{R}^{T \times 2}$ 为可学习特征表（每层 2 特征）。

**步骤 5：层级拼接**

$$\text{Enc}_{\text{HashGrid}}(x) = f_0(x) \oplus f_1(x) \oplus \cdots \oplus f_{L-1}(x)$$

最终输出维度：$16 \times 2 = 32$

#### 2.1.3 本项目配置

```python
encoding_config = {
    "otype": "HashGrid",
    "n_levels": 16,              # L = 16 层
    "n_features_per_level": 2,   # 每层 2 个特征
    "log2_hashmap_size": 19,     # T = 2^19 ≈ 524,288
    "base_resolution": 16,       # b_0 = 16
    "per_level_scale": 2.0,      # α = 2.0
}
```

### 2.2 MLP 参数预测器

#### 2.2.1 网络架构

采用 NVIDIA tiny-cuda-nn 的 FullyFusedMLP，特点：

- **GPU 优化**：利用 Tensor Core 加速矩阵乘法
- **共享权重**：所有点共享同一 MLP，参数高效
- **深度监督**：跳过连接促进梯度流动

```python
network_config = {
    "otype": "FullyFusedMLP",
    "activation": "ReLU",
    "output_activation": "None",  # 输出层无激活，由后处理约束
    "n_neurons": 64,              # 每层 64 神经元
    "n_hidden_layers": 2,         # 2 层隐藏层
}
```

网络结构：$32 \rightarrow 64 \rightarrow 64 \rightarrow 11$

#### 2.2.2 输出参数分解

MLP 输出 $o \in \mathbb{R}^{11}$ 分解为 4 组 3DGS 参数：

```
o = [c₀, c₁, c₂, α, s₀, s₁, s₂, q₀, q₁, q₂, q₃]
     └─────┬─────┘ └─┬─┘ └─────┬─────┘ └──────┬──────┘
       color      opacity    scale       rotation
```

| 参数 | 维度 | 物理意义 | 约束条件 |
|------|------|----------|----------|
| color | 3 | RGB 颜色 | $[0, 1]$ |
| opacity | 1 | 不透明度 | $[0, 1]$ |
| scale | 3 | 高斯球三轴半径 | $(0, \text{scale\_size}]$ |
| rotation | 4 | 旋转四元数 | 单位四元数 $\|q\| = 1$ |

#### 2.2.3 参数激活函数

**颜色激活：**

$$c = \sigma(o_{0:2}) = \frac{1}{1 + e^{-o_{0:2}}} \in [0, 1]^3$$

**不透明度激活：**

$$\alpha = \sigma(o_3) = \frac{1}{1 + e^{-o_3}} \in [0, 1]$$

**尺度激活：**

$$s = \sigma(o_{4:6}) \times \text{scale\_size} \in [0, \text{scale\_size}]^3$$

其中 $\text{scale\_size} = \text{voxel\_size} / 4 = 0.02 / 4 = 0.005$ 米

**旋转归一化：**

$$q = \frac{o_{7:10}}{\|o_{7:10}\|_2 + \epsilon}$$

其中 $\epsilon = 10^{-8}$ 防止除零。

#### 2.2.4 前向传播

$$\begin{aligned}
\text{features} &= \text{Enc}_{\text{HashGrid}}(x_{\text{norm}}) \\
o &= \text{MLP}(\text{features}) \\
(c, \alpha, s, q) &= \text{Activate}(o)
\end{aligned}$$

### 2.3 3DGS 渲染原理

#### 2.3.1 3D 高斯表示

每个高斯球由以下参数定义：

- $\mu \in \mathbb{R}^3$：中心位置（本项目使用原始点云坐标，不优化）
- $\Sigma \in \mathbb{R}^{3 \times 3}$：协方差矩阵
- $c \in \mathbb{R}^3$：颜色（球谐函数或本项目的 MLP 预测）
- $\alpha \in [0, 1]$：不透明度

协方差矩阵分解为：

$$\Sigma = R S S^T R^T$$

其中：

- $S = \text{diag}(s_0, s_1, s_2)$：缩放矩阵
- $R$：旋转矩阵（由四元数 $q$ 转换）

#### 2.3.2 可微光栅化

**步骤 1：3D 到 2D 投影**

3D 高斯投影到图像平面形成 2D 高斯：

$$\Sigma' = J W \Sigma W^T J^T$$

其中：

- $W \in \mathbb{R}^{4 \times 4}$：视图矩阵（世界→相机）
- $J \in \mathbb{R}^{3 \times 3}$：投影雅可比矩阵

**步骤 2：像素贡献计算**

对像素 $u = (u, v)$，高斯 $i$ 的贡献权重：

$$w_i(u) = \alpha_i \cdot \exp\left(-\frac{1}{2} (u - \mu_i')^T {\Sigma_i'}^{-1} (u - \mu_i')\right)$$

**步骤 3：Alpha Blending**

按深度排序后混合：

$$C(u) = \sum_{i \in N} c_i \cdot w_i(u) \cdot \prod_{j=1}^{i-1} (1 - w_j(u))$$

其中 $N$ 为对像素有贡献的高斯集合（通过 tile-based culling 加速）。

#### 2.3.3 可微性

光栅化过程对所有参数可微：

$$\frac{\partial C}{\partial \mu}, \frac{\partial C}{\partial \Sigma}, \frac{\partial C}{\partial c}, \frac{\partial C}{\partial \alpha}$$

这使得可以通过梯度下降优化高斯参数。

### 2.4 外参参数化

#### 2.4.1 视图矩阵分解

视图矩阵 $V \in \mathbb{R}^{4 \times 4}$（世界→相机变换）：

$$V = \begin{bmatrix} R & t \\ 0^T & 1 \end{bmatrix}$$

其中：

- $R \in \mathbb{R}^{3 \times 3}$：旋转矩阵（正交矩阵，$R^T R = I$）
- $t \in \mathbb{R}^3$：平移向量

#### 2.4.2 可优化参数设计

本项目将 $R$ 和 $t$ 作为独立可学习参数：

```python
self.viewmat_rotation = Parameter(
    torch.randn(3, 3, requires_grad=True)
)
self.viewmat_translation = Parameter(
    torch.randn(3, requires_grad=True)
)
```

**约束保持：**

- 旋转矩阵通过梯度下降更新后，需重新正交化（代码中暂未显式处理，依赖小学习率维持近似正交）
- 平移向量无约束

#### 2.4.3 外参优化时机

采用延迟优化策略：

- 前 $N_{\text{warmup}}$ 步：仅优化 MLP 参数
- $N_{\text{warmup}}$ 步后：同时优化 MLP + 外参

```python
extrinsic_start_step = config.get('extrinsic_start_step', num_steps)
if step >= extrinsic_start_step:
    optimize_extrinsic = True
```

默认 $N_{\text{warmup}} = \text{num\_steps}$，即默认不启用外参优化。

---

## 3. 训练优化策略

### 3.1 损失函数设计

#### 3.1.1 总损失函数

$$\mathcal{L} = \mathcal{L}_{\text{L1}} + \lambda_{\text{scale}} \cdot \mathcal{L}_{\text{scale\_reg}}$$

其中：

- $\mathcal{L}_{\text{L1}}$：像素级重建损失
- $\mathcal{L}_{\text{scale\_reg}}$：尺度正则化
- $\lambda_{\text{scale}} = 0.001$：平衡系数

#### 3.1.2 L1 重建损失

对渲染图像 $\hat{I}$ 和真值图像 $I$：

$$\mathcal{L}_{\text{L1}} = \frac{1}{|\Omega_{\text{ROI}}|} \sum_{u \in \Omega_{\text{ROI}}} |\hat{I}(u) - I(u)|$$

其中 $\Omega_{\text{ROI}}$ 为感兴趣区域（见 3.4 节）。

#### 3.1.3 尺度正则化损失

**动机**：3DGS 论文指出，无约束的高斯球会过度膨胀，导致几何模糊。

**策略选择：**

| 方法 | 公式 | 特点 |
|------|------|------|
| 3DGS 论文 | $\|s - \bar{s}\|_1$ | 鼓励高斯间尺度一致 |
| 本项目 | $\|s - 0\|_1$ | 鼓励小尺度，几何更清晰 |

本项目采用：

$$\mathcal{L}_{\text{scale\_reg}} = \frac{1}{|G_{\text{ROI}}|} \sum_{g \in G_{\text{ROI}}} \|s_g\|_1$$

其中 $G_{\text{ROI}}$ 为投影到 ROI 区域且可见的高斯集合。

**可见性判断：**

```python
visible = (radii > 0).any(dim=-1)  # 半径 > 0 表示对像素有贡献
in_roi = (u_min <= means2d[:, 0] <= u_max) &
         (v_min <= means2d[:, 1] <= v_max) &
         visible
```

### 3.2 两阶段训练策略

#### 3.2.1 阶段划分

| 阶段 | 步数范围 | 优化参数 | 优化器 |
|------|----------|----------|--------|
| Stage 1 | $0 \rightarrow N_{\text{warmup}}$ | MLP (encoding + network) | Adam |
| Stage 2 | $N_{\text{warmup}} \rightarrow N_{\text{total}}$ | MLP + 外参 | Adam + Adam_extrinsic |

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

- **稳定性**：先让 MLP 收敛到合理解，再引入外参自由度
- **解耦**：避免初期两个子问题互相干扰
- **灵活性**：可通过 `extrinsic_start_step` 控制外参优化时机

### 3.3 学习率策略

#### 3.3.1 分层学习率

| 参数组 | 学习率 | 设计理由 |
|--------|--------|----------|
| HashGrid Encoding | $5 \times 10^{-3}$ | 特征网格需要较快收敛 |
| MLP Network | $1 \times 10^{-2}$ | 深层网络需要更高学习率 |
| 外参旋转 | $1 \times 10^{-3}$ | 旋转对渲染影响敏感 |
| 外参平移 | $5 \times 10^{-3}$ | 平移通常变化幅度更大 |

### 3.4 优化器参数详解

#### 3.4.1 MLP 优化器

**初始化代码：**

```python
def _init_optimizer(self):
    encoding_lr = self.config.get('encoding_lr', 1e-3)
    mlp_lr = self.config.get('mlp_lr', 1e-3)

    self.optimizer = torch.optim.Adam([
        {'params': self.predictor.encoding.parameters(), 'lr': encoding_lr, 'weight_decay': 1e-4},
        {'params': self.predictor.network.parameters(), 'lr': mlp_lr}
    ])
```

**两个参数组详解：**

| 参数组 | 对应模块 | 参数含义 |
|--------|----------|----------|
| `self.predictor.encoding.parameters()` | HashGrid 编码器 | 哈希表中存储的可学习特征向量 |
| `self.predictor.network.parameters()` | FullyFusedMLP | MLP 各层的权重和偏置 |

**HashGrid 编码器的参数：**

- **结构**：16 层哈希表，每层 $2^{19}$ 个桶，每桶 2 维特征
- **参数量**：$16 \times 2^{19} \times 2 \approx 16.8\text{M}$ 浮点数
- **学习率**：`encoding_lr = 1e-3` (默认)
- **weight_decay**：`1e-4` (L2 正则化，防止过拟合)

**MLP 网络的参数：**

- **结构**：$32 \text{输入} \rightarrow 64 \rightarrow 64 \rightarrow 11 \text{输出}$
- **参数量**：
  - Layer 1: $32 \times 64 + 64 = 2,112$
  - Layer 2: $64 \times 64 + 64 = 4,160$
  - Output: $64 \times 11 + 11 = 715$
  - **总计**：约 7K 参数
- **学习率**：`mlp_lr = 1e-3` (默认)
- **weight_decay**：`0` (不施加 L2 正则化)

**为什么 HashGrid 需要 weight_decay？**

- HashGrid 特征表容量大，容易过拟合
- L2 正则化鼓励特征值趋向于 0，提高泛化能力
- 参考 3DGS-Calib 论文设置

#### 3.4.2 外参优化器

**初始化代码：**

```python
def _init_extrinsic_optimizer(self):
    rotation_lr = self.config.get('rotation_lr', 1e-4)
    translation_lr = self.config.get('translation_lr', 5e-3)

    self.extrinsic_optimizer = torch.optim.Adam([
        {'params': self.viewmat_rotation, 'lr': rotation_lr},
        {'params': self.viewmat_translation, 'lr': translation_lr}
    ])
```

**两个参数详解：**

| 参数 | 形状 | 物理意义 | 学习率 | 优化特性 |
|------|------|----------|--------|----------|
| viewmat_rotation | [3,3] | 旋转矩阵（世界→相机） | $1 \times 10^{-4}$ | 敏感，需小学习率 |
| viewmat_translation | [3] | 平移向量（世界→相机） | $5 \times 10^{-3}$ | 变化幅度大，需大学习率 |

**viewmat_rotation（旋转矩阵）：**

```
R = [ r₀₀  r₀₁  r₀₂ ]    描述相机坐标轴相对于世界坐标系的旋转
    [ r₁₀  r₁₁  r₁₂ ]
    [ r₂₀  r₂₁  r₂₂ ]

约束条件：
- 正交矩阵：R^T · R = I
- 行列式：det(R) = +1（纯旋转，无反射）
```

**viewmat_translation（平移向量）：**

```
t = [ tₓ ]    描述相机原点在世界坐标系中的位置
    [ tᵧ ]
    [ tᵢ ]

单位：米（与点云坐标单位一致）
```

**为什么旋转和平移使用不同学习率？**

| 因素 | 旋转 (R) | 平移 (t) |
|------|----------|----------|
| 对渲染的影响 | 高度非线性，微小变化导致图像大幅偏移 | 相对线性，变化影响较均匀 |
| 约束要求 | 需保持正交性（虽未显式处理） | 无特殊约束 |
| 典型变化量级 | 角度误差通常 < 5° | 平移误差可达数十厘米 |
| 学习率选择 | 小 ($10^{-4}$) | 大 ($5 \times 10^{-3}$) |

**外参参数初始化：**

```python
def _init_extrinsic_params(self):
    # 从初始外参矩阵提取
    self.viewmat_rotation = Parameter(
        self.viewmat[:3, :3].clone().detach().float()
    )
    self.viewmat_translation = Parameter(
        self.viewmat[:3, 3].clone().detach().float()
    )
```

初始值来自 LiDAR SLAM 或 ICP 配准提供的粗略外参。

#### 3.4.3 优化器参数总览

```
┌─────────────────────────────────────────────────────────────┐
│                     优化器架构                               │
├─────────────────────────────────────────────────────────────┤
│  MLP 优化器 (Adam)                                          │
│  ├─ HashGrid Encoding (16.8M 参数)                         │
│  │   ├─ lr: 1e-3                                           │
│  │   └─ weight_decay: 1e-4                                 │
│  └─ MLP Network (7K 参数)                                  │
│      ├─ lr: 1e-3                                           │
│      └─ weight_decay: 0                                    │
├─────────────────────────────────────────────────────────────┤
│  外参优化器 (Adam, 延迟初始化)                               │
│  ├─ viewmat_rotation [3, 3]                                │
│  │   └─ lr: 1e-4                                           │
│  └─ viewmat_translation [3]                                │
│      └─ lr: 5e-3                                           │
└─────────────────────────────────────────────────────────────┘
```

### 3.5 ROI 区域策略

#### 3.5.1 动机

- **计算效率**：全图损失计算开销大
- **噪声抑制**：天空/墙壁等无点云区域会引入噪声梯度
- **场景特性**：自动驾驶场景中，地面和近场物体更重要

#### 3.5.2 配置方式

按相机单独配置 ROI（归一化坐标 $[0, 1]$）：

```python
roi_config = {
    "camera_front_wide": {'x_min': 0.0, 'x_max': 1.0, 'y_min': 0.0, 'y_max': 0.7},
}
```

#### 3.5.3 实现细节

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

### 3.6 多相机支持

#### 3.6.1 相机权重配置

主相机（如前广）赋予更高权重：

```python
camera_weights = {
    "camera_front_wide": 2.0,   # 主相机
    "camera_left_front": 1.0,
    "camera_right_front": 1.0,
    # ...
}
```

**自动归一化：**

$$w_c' = \frac{w_c}{\sum_k w_k}$$

#### 3.6.2 数据加载

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

## 4. 数据流与接口

### 4.1 点云预处理

#### 4.1.1 处理流程

```
原始 PCD → 过滤 NaN/Inf → 过滤离群点 (可选) → 归一化 → CUDA Tensor
```

#### 4.1.2 归一化公式

$$x' = \frac{x - x_{\min}}{x_{\max} - x_{\min} + \epsilon}$$

其中 $\epsilon = 10^{-8}$ 防止除零。

#### 4.1.3 输出张量

| 张量 | 形状 | 用途 | 范围 |
|------|------|------|------|
| xyz_normalized | $[N, 3]$ | MLP 输入 | $[0, 1]$ |
| xyz_original | $[N, 3]$ | 高斯中心（渲染） | 世界坐标（米） |

### 4.2 训练数据流

1. 加载点云 → xyz_normalized, xyz_original
2. 加载图像 → gt_image $[H, W, 3]$
3. 加载相机参数 → $K$ $[3, 3]$, viewmat $[4, 4]$
4. 训练循环：
   ```python
   for step in range(num_steps):
       a. MLP 前向 → (color, opacity, scale, rotation)
       b. 光栅化 → render_image
       c. 计算损失 → loss
       d. 反向传播 → loss.backward()
       e. 更新参数 → optimizer.step()
   ```

### 4.3 结果导出

#### 4.3.1 PCD 导出

保存为 CloudCompare 兼容的 PointXYZRGB 格式：

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

## 5. 关键实现细节

### 5.1 张量形状变换

| 变量 | 形状 | 说明 |
|------|------|------|
| xyz_normalized | $[N, 3]$ | 归一化坐标 |
| features | $[N, 32]$ | HashGrid 编码输出 |
| mlp_output | $[N, 11]$ | MLP 原始输出 |
| color | $[N, 3]$ | 激活后颜色 |
| opacity | $[N, 1]$ | 激活后不透明度 |
| scale | $[N, 3]$ | 激活后尺度 |
| rotation | $[N, 4]$ | 归一化四元数 |
| render_image | $[H, W, 3]$ | 渲染图像 |

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
| HashGrid 编码 | $O(N \cdot L)$ | $O(N \cdot L \cdot F)$ |
| MLP 前向 | $O(N \cdot d^2)$ | $O(N \cdot d_{\text{out}})$ |
| 光栅化 | $O(N \cdot A)$ | $O(H \cdot W)$ |

其中：

- $N$：高斯点数
- $L$：HashGrid 层数（16）
- $F$：每层特征数（2）
- $d$：MLP 隐藏层维度（64）
- $A$：单像素覆盖的高斯数

---

## 6. 核心依赖库详解

### 6.1 gsplat：可微分 3D 高斯光栅化引擎

#### 6.1.1 核心作用

gsplat 是一个高性能的 3D Gaussian Splatting 可微分渲染器，在本项目中负责将 MLP 预测的 3D 高斯参数渲染为 2D 图像：

```
3D 高斯参数 → 2D 投影 → Alpha Blending → 渲染图像
```

#### 6.1.2 使用位置

**文件**: `trainer.py`

```python
from gsplat.rendering import rasterization

# 渲染调用
renders, alphas, meta = rasterization(
    means=means,          # 高斯中心 [N, 3]
    quats=quats,          # 旋转四元数 [N, 4]
    scales=scales,        # 尺度 [N, 3]
    opacities=opacities,  # 不透明度 [N,]
    colors=colors,        # 颜色 [N, 3]
    viewmats=viewmat[None],  # 视图矩阵 [C, 4, 4]
    Ks=self.K[None],      # 内参矩阵 [C, 3, 3]
    width=self.W,
    height=self.H,
    packed=False,         # 非打包模式，适合小场景
)
render_image = renders[0]  # [H, W, 3]
```

#### 6.1.3 关键功能

| 功能 | 说明 |
|------|------|
| 3D→2D 投影 | 将 3D 高斯投影到图像平面，计算 2D 协方差 $\Sigma' = J W \Sigma W^T J^T$ |
| 可见性剔除 | 只渲染对当前视角可见的高斯（radii > 0） |
| Alpha Blending | 按深度排序混合高斯贡献 |
| 可微分 | 支持对所有参数求梯度，用于反向传播优化 |

#### 6.1.4 返回的 meta 信息

```python
means2d = meta['means2d'][0]  # 2D 投影位置 [N, 2]
radii = meta['radii'][0]      # 高斯半径（用于可见性判断）
```

这些用于计算 ROI 区域的 scale 正则化损失：

```python
visible = (radii > 0).any(dim=-1)  # 半径 > 0 表示对像素有贡献
in_roi = (u_min <= means2d[:, 0] <= u_max) &
         (v_min <= means2d[:, 1] <= v_max) &
         visible
```

### 6.2 tiny-cuda-nn：高效神经网络编码器

#### 6.2.1 核心作用

tiny-cuda-nn (NVIDIA) 提供 GPU 优化的神经网络模块，在本项目中用于：

- **HashGrid 编码**：将 3D 坐标编码为高维特征
- **FullyFusedMLP**：预测 3DGS 参数

#### 6.2.2 使用位置

**文件**: `models/gs_param_predictor.py`

```python
import tinycudann as tcnn

class GSParamPredictor(torch.nn.Module):
    def __init__(self, scale_size: float = 0.01):
        # ========== 1. HashGrid 编码 ==========
        self.encoding = tcnn.Encoding(
            n_input_dims=3,
            encoding_config={
                "otype": "HashGrid",
                "n_levels": 16,
                "n_features_per_level": 2,
                "log2_hashmap_size": 19,
                "base_resolution": 16,
                "per_level_scale": 2.0,
            }
        )

        # ========== 2. FullyFusedMLP ==========
        self.network = tcnn.Network(
            n_input_dims=self.encoding.n_output_dims,  # 32
            n_output_dims=11,  # color(3) + opacity(1) + scale(3) + rotation(4)
            network_config={
                "otype": "FullyFusedMLP",
                "activation": "ReLU",
                "output_activation": "None",
                "n_neurons": 64,
                "n_hidden_layers": 2,
            }
        )
```

#### 6.2.3 HashGrid 编码配置详解

**HashGrid 参数：**

```
HashGrid 参数：
├── n_levels: 16           # 16 个分辨率层级
├── n_features_per_level: 2  # 每层 2 个特征
├── log2_hashmap_size: 19  # 哈希表大小 2^19 ≈ 524,288
├── base_resolution: 16    # 最粗层分辨率 16³
└── per_level_scale: 2.0   # 每层分辨率×2

输出维度：16 层 × 2 特征 = 32 维
```

**多分辨率层级：**

| 层级 | 分辨率 | 作用 |
|------|--------|------|
| Level 0 | $16^3$ | 捕获全局/低频结构 |
| Level 1-7 | $18^3 \sim 128^3$ | 中等频率细节 |
| Level 8-15 | $128^3 \sim 2048^3$ | 高频/局部细节 |

#### 6.2.4 MLP 网络架构

```
输入：xyz_normalized [N, 3] (范围 [0,1])
      ↓
HashGrid 编码 → features [N, 32]
      ↓
FullyFusedMLP: 32 → 64 → 64 → 11
      ↓
输出：raw [N, 11] → color(3) + opacity(1) + scale(3) + rotation(4)
```

#### 6.2.5 为什么使用 tiny-cuda-nn？

| 特性 | 优势 |
|------|------|
| CUDA 内核融合 | 减少 GPU 内核启动开销，速度提升 2-10 倍 |
| HashGrid 编码 | 高效的空间局部性编码，支持高频细节 |
| FullyFusedMLP | 利用 Tensor Core，矩阵乘法加速 |
| 内存效率 | 哈希表固定大小，不随场景增大 |

### 6.3 两者协作流程

```
┌────────────────────────────────────────────────────────────┐
│ 1. 点云输入                                                   │
│    xyz_normalized [N, 3] (范围 [0,1])                       │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 2. tiny-cuda-nn: HashGrid 编码                              │
│    features = Encoding(xyz) → [N, 32]                      │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 3. tiny-cuda-nn: MLP 预测                                   │
│    out = MLP(features) → [N, 11]                           │
│    → color, opacity, scale, rotation                       │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 4. gsplat: 可微分光栅化                                     │
│    render_image = rasterization(means, quats, scales,      │
│                                  opacities, colors,        │
│                                  viewmat, K)               │
│    → [H, W, 3]                                             │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│ 5. 损失计算与反向传播                                         │
│    loss = L1(render, gt) + λ·L_scale_reg                   │
│    loss.backward() → 更新 MLP 参数 + 外参                    │
└────────────────────────────────────────────────────────────┘
```

### 6.4 依赖版本与安装

| 库 | 版本 | 作用 | 是否必需 |
|----|------|------|----------|
| gsplat | ≥1.0 | 3D 高斯光栅化渲染 | ✓ 必需 |
| tiny-cuda-nn | ≥1.7 | HashGrid 编码 + MLP | ✓ 必需 |

**安装命令：**

```bash
# 安装 gsplat
pip install gsplat

# 安装 tiny-cuda-nn (需要 CUDA 环境)
pip install ninja
pip install git+https://github.com/NVlabs/tiny-cuda-nn/#subdirectory=bindings/torch
```

### 6.5 与传统 3DGS 的对比

| 组件 | 传统 3DGS | 本项目 (3DGS-Calib) |
|------|-----------|---------------------|
| 参数表示 | 独立优化每个高斯 | MLP 隐式预测 |
| 编码方式 | 无（直接优化） | HashGrid 编码 |
| 网络 | 无 | FullyFusedMLP |
| 渲染器 | 官方 CUDA 渲染器 | gsplat |
| 外参优化 | 不支持 | 支持联合优化 |

**核心创新**：使用 tiny-cuda-nn 的 HashGrid+MLP 替代传统逐点优化，通过 gsplat 实现高效可微渲染，支持相机外参联合标定。
