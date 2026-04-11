---
title: "3DGS-Calib 架构与算法"
category: 3dgs
tags:
  - 3dgs
  - mlp
  - hashgrid
  - 外参标定
  - 可微渲染
  - gsplat
  - tiny-cuda-nn
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/3dgs/3dgs-calib-architecture-notes.md
  - raw/3dgs/3dgs-calib-notes.md
---

# 3DGS-Calib 架构与算法

基于 MLP 的 3D Gaussian Splatting 参数预测与外参联合标定系统。

## 系统概述

### 项目背景

3DGS-Calib 是一个基于 3D Gaussian Splatting (3DGS) 技术的神经渲染系统。其核心创新在于使用 HashGrid 编码的 MLP 网络直接预测 3D 高斯参数，而非像原始 3DGS 那样通过逐点优化获得高斯参数。

相比传统 3DGS，该方法具有以下优势：

- **参数效率高**：MLP 隐式表示场景，避免存储数百万独立高斯参数
- **泛化能力强**：学习到的特征可以泛化到未见视角
- **支持在线标定**：可联合优化相机外参，实现自标定功能

### 与传统 3DGS 的对比

| 组件 | 传统 3DGS | 3DGS-Calib |
|------|-----------|------------|
| 参数表示 | 独立优化每个高斯 | MLP 隐式预测 |
| 编码方式 | 无（直接优化） | HashGrid 编码 |
| 网络 | 无 | FullyFusedMLP |
| 渲染器 | 官方 CUDA 渲染器 | gsplat |
| 外参优化 | 不支持 | 支持联合优化 |

## 整体架构

### 数据流总览

```
输入：点云 PCD {x_i, y_i, z_i}
  │
  ▼
1. 点云预处理
   - 归一化：x' = (x - x_min) / (x_max - x_min) ∈ [0,1]
   - 输出：xyz_normalized [N, 3], xyz_original [N, 3]
  │
  ▼
2. HashGrid 编码 (tiny-cuda-nn)
   - 输入：xyz_normalized [N, 3]
   - 输出：features [N, 32]  (16 层 × 2 特征/层)
  │
  ▼
3. FullyFusedMLP 预测 (tiny-cuda-nn)
   - 输入：features [N, 32]
   - 输出：raw [N, 11] → color(3) + opacity(1) + scale(3) + rot(4)
  │
  ▼
4. 参数激活与约束
   - color    = sigmoid(·) ∈ [0,1]
   - opacity  = sigmoid(·) ∈ [0,1]
   - scale    = sigmoid(·) × scale_size ∈ [0, scale_size]
   - rotation = normalize(·)  单位四元数
  │
  ▼
5. 3DGS 可微光栅化 (gsplat)
   - 3D 高斯 → 2D 投影 → Alpha Blending → 渲染图像 [H, W, 3]
  │
  ▼
6. 损失计算与反向传播
   - L = L1(render, gt) + λ_scale × L_scale_reg
```

### 相机坐标系下的详细流程

```
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
                                   ▼
                   ┌───────────────────────────────────────┐
                   │        2. HashGrid 空间编码            │
                   │   - 16 层多分辨率哈希网格               │
                   │   - 每层 2 特征，三线性插值             │
                   │   输出：f [N, 32]                     │
                   └───────────────────────────────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────────────┐
                   │       3. FullyFusedMLP 前向传播        │
                   │   32 → 64 (ReLU) → 64 (ReLU) → 11    │
                   │   输出：[c(3), α(1), s(3), q(4)]     │
                   └───────────────────────────────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────────────┐
                   │          4. 参数激活与约束             │
                   │   color    = sigmoid(c) ∈ [0,1]³     │
                   │   opacity  = sigmoid(α) ∈ [0,1]      │
                   │   scale    = sigmoid(s) × size       │
                   │   rotation = normalize(q) (单位四元数)│
                   └───────────────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────────┐
       │              5. 世界坐标系 → 相机坐标系变换                    │
       │                                                                │
       │   5.1 构建视图矩阵 V ∈ R^(4×4)                                │
       │   5.2 坐标变换 (世界→相机): P_cam = V × P_world               │
       │   5.3 高斯旋转更新 (相机坐标系): q_cam = R^{-1} × q_world     │
       │   5.4 透视投影 → 2D 投影位置 (u,v)                            │
       └───────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────────┐
       │              6. 光栅化 (gsplat Rasterization)                  │
       │   - Tile 划分 → 可见性剔除 → 深度排序 → Alpha Blending       │
       │   输出：渲染图像 I_render ∈ R^(H×W×3)                         │
       └───────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────────┐
       │              7. ROI 区域损失计算                               │
       │   L = L_l1 + λ_scale × L_scale  (λ_scale = 0.001)            │
       └───────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
       ┌───────────────────────────────────────────────────────────────┐
       │              8. 反向传播 & 参数更新                            │
       │   MLP 优化器：Adam(encoding, network)                         │
       │   外参优化器：Adam(rotation, translation)                      │
       └───────────────────────────────────────────────────────────────┘
```

## HashGrid 编码原理

### 动机与优势

传统的位置编码（Positional Encoding）存在以下局限：

- **高频信息丢失**：低频基函数难以捕捉细节
- **计算效率低**：需要多个频率分量

HashGrid（Müller et al., 2022）通过多分辨率哈希特征网格解决上述问题：

- **空间局部性**：相近点共享哈希特征，实现平滑插值
- **多尺度表示**：不同分辨率捕获不同频率信息
- **内存高效**：哈希表大小固定，不随场景增大

### 数学表达

对于输入点 $x \in [0,1]^3$，HashGrid 编码过程如下：

**步骤 1：多分辨率网格采样**

在 $L$ 个分辨率层级上采样，第 $l$ 层分辨率：

$$b_l = \lfloor b_0 \cdot \alpha^l \rfloor$$

其中 $b_0 = 16$（基础分辨率），$\alpha = 2.0$（缩放因子），$l = 0, 1, \ldots, L-1$，$L = 16$ 为总层数。

**步骤 2：顶点坐标计算**

对第 $l$ 层，计算 $x$ 所在网格单元的 8 个顶点：

$$v_{l,i} = \text{floor}(b_l \cdot x) + \delta_i, \quad i = 0, \ldots, 7$$

其中 $\delta_i \in \{0, 1\}^3$ 为顶点偏移。

**步骤 3：哈希映射**

将顶点坐标映射到哈希表索引：

$$h_{l,i} = \left( \prod_{d=0}^{2} \pi_d \oplus v_{l,i,d} \right) \bmod T$$

其中 $T = 2^{19}$ 为哈希表大小，$\pi_d$ 为素数（用于打散空间相关性），$\oplus$ 为异或操作。

**步骤 4：特征插值**

从哈希表取出特征并三线性插值：

$$f_l(x) = \sum_{i=0}^{7} w_{l,i} \cdot E[h_{l,i}]$$

其中 $E \in \mathbb{R}^{T \times 2}$ 为可学习特征表。

**步骤 5：层级拼接**

$$\text{Enc}_{\text{HashGrid}}(x) = f_0(x) \oplus f_1(x) \oplus \cdots \oplus f_{L-1}(x)$$

最终输出维度为 $16 \times 2 = 32$。

### 多分辨率层级

| 层级 | 分辨率 | 作用 |
|------|--------|------|
| Level 0 | $16^3$ | 捕获全局/低频结构 |
| Level 1-7 | $18^3 \sim 128^3$ | 中等频率细节 |
| Level 8-15 | $128^3 \sim 2048^3$ | 高频/局部细节 |

### 配置参数

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

HashGrid 编码器的参数量约为 $16 \times 2^{19} \times 2 \approx 16.8\text{M}$ 浮点数。

## MLP 参数预测器

### 网络架构

采用 NVIDIA tiny-cuda-nn 的 FullyFusedMLP，特点包括：

- **GPU 优化**：利用 Tensor Core 加速矩阵乘法
- **共享权重**：所有点共享同一 MLP，参数高效
- **深度监督**：跳过连接促进梯度流动

```python
network_config = {
    "otype": "FullyFusedMLP",
    "activation": "ReLU",
    "output_activation": "None",
    "n_neurons": 64,
    "n_hidden_layers": 2,
}
```

网络结构为 $32 \rightarrow 64 \rightarrow 64 \rightarrow 11$，总参数量约 7K：

- Layer 1: $32 \times 64 + 64 = 2,112$
- Layer 2: $64 \times 64 + 64 = 4,160$
- Output: $64 \times 11 + 11 = 715$

### 输出参数分解

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

### 参数激活函数

**颜色激活：**

$$c = \sigma(o_{0:2}) = \frac{1}{1 + e^{-o_{0:2}}} \in [0, 1]^3$$

**不透明度激活：**

$$\alpha = \sigma(o_3) = \frac{1}{1 + e^{-o_3}} \in [0, 1]$$

**尺度激活：**

$$s = \sigma(o_{4:6}) \times \text{scale\_size} \in [0, \text{scale\_size}]^3$$

其中 $\text{scale\_size} = \text{voxel\_size} / 4 = 0.02 / 4 = 0.005$ 米。

**旋转归一化：**

$$q = \frac{o_{7:10}}{\|o_{7:10}\|_2 + \epsilon}$$

其中 $\epsilon = 10^{-8}$ 防止除零。

### 前向传播

$$\begin{aligned}
\text{features} &= \text{Enc}_{\text{HashGrid}}(x_{\text{norm}}) \\
o &= \text{MLP}(\text{features}) \\
(c, \alpha, s, q) &= \text{Activate}(o)
\end{aligned}$$

## 3DGS 渲染管线

### 3D 高斯表示

每个高斯球由以下参数定义：

- $\mu \in \mathbb{R}^3$：中心位置（本项目使用原始点云坐标，不优化）
- $\Sigma \in \mathbb{R}^{3 \times 3}$：协方差矩阵
- $c \in \mathbb{R}^3$：颜色（由 MLP 预测）
- $\alpha \in [0, 1]$：不透明度（由 MLP 预测）

协方差矩阵分解为缩放和旋转：

$$\Sigma = R S S^T R^T$$

其中 $S = \text{diag}(s_0, s_1, s_2)$ 为缩放矩阵，$R$ 为旋转矩阵（由四元数 $q$ 转换）。

### 可微光栅化

**步骤 1：3D 到 2D 投影**

3D 高斯投影到图像平面形成 2D 高斯：

$$\Sigma' = J W \Sigma W^T J^T$$

其中 $W \in \mathbb{R}^{4 \times 4}$ 为视图矩阵（世界到相机），$J \in \mathbb{R}^{3 \times 3}$ 为投影雅可比矩阵。

**步骤 2：像素贡献计算**

对像素 $u = (u, v)$，高斯 $i$ 的贡献权重：

$$w_i(u) = \alpha_i \cdot \exp\left(-\frac{1}{2} (u - \mu_i')^T {\Sigma_i'}^{-1} (u - \mu_i')\right)$$

**步骤 3：Alpha Blending**

按深度排序后从前到后混合：

$$C(u) = \sum_{i \in N} c_i \cdot w_i(u) \cdot \prod_{j=1}^{i-1} (1 - w_j(u))$$

其中 $N$ 为对像素有贡献的高斯集合（通过 tile-based culling 加速）。

### 可微性

光栅化过程对所有参数可微：

$$\frac{\partial C}{\partial \mu}, \quad \frac{\partial C}{\partial \Sigma}, \quad \frac{\partial C}{\partial c}, \quad \frac{\partial C}{\partial \alpha}$$

这使得可以通过梯度下降优化高斯参数和外参。

## 外参参数优化

### 视图矩阵分解

视图矩阵 $V \in \mathbb{R}^{4 \times 4}$（世界到相机变换）：

$$V = \begin{bmatrix} R & t \\ 0^T & 1 \end{bmatrix}$$

其中 $R \in \mathbb{R}^{3 \times 3}$ 为旋转矩阵（正交矩阵，$R^T R = I$），$t \in \mathbb{R}^3$ 为平移向量。

### 可优化参数设计

将 $R$ 和 $t$ 作为独立可学习参数：

```python
self.viewmat_rotation = Parameter(torch.randn(3, 3, requires_grad=True))
self.viewmat_translation = Parameter(torch.randn(3, requires_grad=True))
```

**约束保持：**

- 旋转矩阵通过梯度下降更新后，需重新正交化（代码中暂未显式处理，依赖小学习率维持近似正交）
- 平移向量无约束

### 外参优化时机

采用延迟优化策略：

- 前 $N_{\text{warmup}}$ 步：仅优化 MLP 参数
- $N_{\text{warmup}}$ 步后：同时优化 MLP + 外参

```python
extrinsic_start_step = config.get('extrinsic_start_step', num_steps)
if step >= extrinsic_start_step:
    optimize_extrinsic = True
```

默认 $N_{\text{warmup}} = \text{num\_steps}$，即默认不启用外参优化。初始值来自 LiDAR SLAM 或 ICP 配准提供的粗略外参。

### 坐标变换流程

在相机坐标系下的完整变换：

1. **构建视图矩阵**：$V = \begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix}$
2. **坐标变换**（世界到相机）：$P_{\text{cam}} = V \times P_{\text{world}}$（齐次坐标）
3. **高斯旋转更新**（相机坐标系下）：$q_{\text{cam}} = R^{-1} \times q_{\text{world}}$
4. **透视投影**（相机到归一化平面）：$u_{\text{norm}} = x_{\text{cam}} / z_{\text{cam}}$，$v_{\text{norm}} = y_{\text{cam}} / z_{\text{cam}}$
5. **投影到像素平面**（内参变换）：$u = f_x \times u_{\text{norm}} + c_x$，$v = f_y \times v_{\text{norm}} + c_y$

## 训练策略与损失函数

### 总损失函数

$$\mathcal{L} = \mathcal{L}_{\text{L1}} + \lambda_{\text{scale}} \cdot \mathcal{L}_{\text{scale\_reg}}$$

其中 $\lambda_{\text{scale}} = 0.001$ 为平衡系数。

### L1 重建损失

对渲染图像 $\hat{I}$ 和真值图像 $I$，在 ROI 区域内计算：

$$\mathcal{L}_{\text{L1}} = \frac{1}{|\Omega_{\text{ROI}}|} \sum_{u \in \Omega_{\text{ROI}}} |\hat{I}(u) - I(u)|$$

### 尺度正则化损失

**动机**：3DGS 论文指出，无约束的高斯球会过度膨胀，导致几何模糊。

| 方法 | 公式 | 特点 |
|------|------|------|
| 3DGS 论文 | $\|s - \bar{s}\|_1$ | 鼓励高斯间尺度一致 |
| 本项目 | $\|s - 0\|_1$ | 鼓励小尺度，几何更清晰 |

本项目采用：

$$\mathcal{L}_{\text{scale\_reg}} = \frac{1}{|G_{\text{ROI}}|} \sum_{g \in G_{\text{ROI}}} \|s_g\|_1$$

其中 $G_{\text{ROI}}$ 为投影到 ROI 区域且可见的高斯集合。可见性判断条件为 `radii > 0` 且投影位置在 ROI 边界内。

### 两阶段训练策略

| 阶段 | 步数范围 | 优化参数 | 优化器 |
|------|----------|----------|--------|
| Stage 1 | $0 \rightarrow N_{\text{warmup}}$ | MLP (encoding + network) | Adam |
| Stage 2 | $N_{\text{warmup}} \rightarrow N_{\text{total}}$ | MLP + 外参 | Adam + Adam_extrinsic |

**策略优势**：

- **稳定性**：先让 MLP 收敛到合理解，再引入外参自由度
- **解耦**：避免初期两个子问题互相干扰
- **灵活性**：可通过 `extrinsic_start_step` 控制外参优化时机

### 优化器配置

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

### 分层学习率

| 参数组 | 学习率 | 设计理由 |
|--------|--------|----------|
| HashGrid Encoding | $5 \times 10^{-3}$ | 特征网格需要较快收敛 |
| MLP Network | $1 \times 10^{-2}$ | 深层网络需要更高学习率 |
| 外参旋转 | $1 \times 10^{-3}$ | 旋转对渲染影响敏感 |
| 外参平移 | $5 \times 10^{-3}$ | 平移通常变化幅度更大 |

### 学习率调度

采用指数衰减：

$$\text{lr}_t = \text{lr}_0 \cdot \gamma^t$$

其中 $\gamma = 0.999$，每步衰减 0.1%。

### ROI 区域策略

**动机**：

- **计算效率**：全图损失计算开销大
- **噪声抑制**：天空/墙壁等无点云区域会引入噪声梯度
- **场景特性**：自动驾驶场景中，地面和近场物体更重要

**配置示例**（归一化坐标 $[0, 1]$）：

```python
roi_config = {
    "camera_front_wide": {'x_min': 0.0, 'x_max': 1.0, 'y_min': 0.0, 'y_max': 0.7},
}
```

### 多相机支持

主相机（如前广）赋予更高权重：

```python
camera_weights = {
    "camera_front_wide": 2.0,   # 主相机
    "camera_left_front": 1.0,
    "camera_right_front": 1.0,
}
```

权重自动归一化：$w_c' = w_c / \sum_k w_k$。

## 优化器架构总览

```
优化器架构
├── MLP 优化器 (Adam)
│   ├── HashGrid Encoding (16.8M 参数)
│   │   ├── lr: 1e-3
│   │   └── weight_decay: 1e-4
│   └── MLP Network (7K 参数)
│       ├── lr: 1e-3
│       └── weight_decay: 0
└── 外参优化器 (Adam, 延迟初始化)
    ├── viewmat_rotation [3, 3]
    │   └── lr: 1e-4
    └── viewmat_translation [3]
        └── lr: 5e-3
```

**为什么 HashGrid 需要 weight_decay？** HashGrid 特征表容量大（16.8M 参数），容易过拟合。L2 正则化鼓励特征值趋向于 0，提高泛化能力。

**为什么旋转和平移使用不同学习率？**

| 因素 | 旋转 (R) | 平移 (t) |
|------|----------|----------|
| 对渲染的影响 | 高度非线性，微小变化导致图像大幅偏移 | 相对线性，变化影响较均匀 |
| 约束要求 | 需保持正交性（虽未显式处理） | 无特殊约束 |
| 典型变化量级 | 角度误差通常 < 5 度 | 平移误差可达数十厘米 |
| 学习率选择 | 小 ($10^{-4}$) | 大 ($5 \times 10^{-3}$) |

## 数据流与接口

### 点云预处理

```
原始 PCD → 过滤 NaN/Inf → 过滤离群点 (可选) → 归一化 → CUDA Tensor
```

归一化公式：

$$x' = \frac{x - x_{\min}}{x_{\max} - x_{\min} + \epsilon}$$

其中 $\epsilon = 10^{-8}$ 防止除零。

### 张量形状

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

### 数值稳定性处理

| 位置 | 处理 | 代码 |
|------|------|------|
| 归一化 | 防止除零 | `(pts_max - pts_min + 1e-8)` |
| 四元数归一化 | 防止除零 | `rotation / (rotation.norm() + 1e-8)` |
| 颜色裁剪 | 防止 NaN/Inf | `np.nan_to_num(color_np, nan=0.5)` |
| 光栅化 | 混合精度 | `means.float(), quats.float()` |

### 计算复杂度

| 操作 | 时间复杂度 | 空间复杂度 |
|------|------------|------------|
| HashGrid 编码 | $O(N \cdot L)$ | $O(N \cdot L \cdot F)$ |
| MLP 前向 | $O(N \cdot d^2)$ | $O(N \cdot d_{\text{out}})$ |
| 光栅化 | $O(N \cdot A)$ | $O(H \cdot W)$ |

其中 $N$ 为高斯点数，$L = 16$ 为 HashGrid 层数，$F = 2$ 为每层特征数，$d = 64$ 为 MLP 隐藏层维度，$A$ 为单像素覆盖的高斯数。

## 核心依赖库

### gsplat：可微分 3D 高斯光栅化引擎

gsplat 负责将 MLP 预测的 3D 高斯参数渲染为 2D 图像：

```python
from gsplat.rendering import rasterization

renders, alphas, meta = rasterization(
    means=means,          # 高斯中心 [N, 3]
    quats=quats,          # 旋转四元数 [N, 4]
    scales=scales,        # 尺度 [N, 3]
    opacities=opacities,  # 不透明度 [N,]
    colors=colors,        # 颜色 [N, 3]
    viewmats=viewmat[None],
    Ks=self.K[None],
    width=self.W,
    height=self.H,
    packed=False,
)
```

关键功能包括 3D 到 2D 投影、可见性剔除、Alpha Blending，以及完整的可微分支持。返回的 `meta` 包含 `means2d`（2D 投影位置）和 `radii`（高斯半径，用于可见性判断）。

### tiny-cuda-nn：高效神经网络编码器

提供 GPU 优化的 HashGrid 编码和 FullyFusedMLP：

- **CUDA 内核融合**：减少 GPU 内核启动开销，速度提升 2-10 倍
- **HashGrid 编码**：高效的空间局部性编码，支持高频细节
- **FullyFusedMLP**：利用 Tensor Core，矩阵乘法加速
- **内存效率**：哈希表固定大小，不随场景增大

## 相关页面

- [HashGrid 编码详解](./hashgrid-encoding.md) -- HashGrid 编码的深度技术分析
- [3DGS 外参标定笔记](./3dgs-calib-notes.md) -- 3DGS-Calib 系统的完整笔记
