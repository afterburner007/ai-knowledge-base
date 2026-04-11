---
title: "Ceres 非线性优化"
category: tools
tags:
  - Ceres Solver
  - 非线性优化
  - 车道线约束
  - 重投影优化
  - 代价函数
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/debug_tools/project-knowledge-points.md
  - raw/fusion/fusion-notes.md
---

# Ceres 非线性优化

## 概述

Ceres Solver 是 Google 开源的非线性最小二乘优化库，广泛应用于相机标定、SLAM、三维重建等领域。在自动泊车与环视标定系统中，Ceres 用于求解车道线几何约束、重投影误差最小化、外参标定等核心问题。

## 优化问题建模

Ceres 求解的标准形式为：

$$
\min_{\mathbf{x}} \frac{1}{2} \sum_i \rho_i \left( \|f_i(\mathbf{x}_{i_1}, \ldots, \mathbf{x}_{i_k})\|^2 \right)
$$

其中：
- $\mathbf{x}$ 为待优化的参数块（Parameter Block）
- $f_i(\cdot)$ 为残差函数（Residual Block）
- $\rho_i$ 为损失函数（Loss Function），用于降低异常值影响
- $\|\cdot\|^2$ 为残差的 L2 范数平方

## 代价函数设计

### 1. 车道线平行约束因子

**应用场景**：在线道路标定中，假设同一车道的左右车道线在 3D 空间中平行。

**残差定义**：对于两条车道线的方向向量 $\mathbf{d}_1$ 和 $\mathbf{d}_2$，平行约束残差为它们叉积的模：

$$
r_{\text{parallel}} = \|\mathbf{d}_1 \times \mathbf{d}_2\|
$$

理想情况下 $r_{\text{parallel}} = 0$ 表示完全平行。

### 2. 车道线等宽约束因子

**应用场景**：同一车道的左右车道线间距应保持恒定。

**残差定义**：在多个采样点处，计算左右车道线的垂直距离，与期望车道宽度 $w_{\text{target}}$ 的偏差：

$$
r_{\text{width}, j} = w_j - w_{\text{target}}
$$

其中 $w_j$ 为第 $j$ 个采样点处左右车道线的距离。

### 3. 共轴优化因子

**应用场景**：多相机外参标定时，约束各相机光轴的一致性。

### 4. 重投影约束因子（云端质检）

**应用场景**：将点云投影至图像分割生成的 DT (Distance Transform) 图，最小化重投影距离和。

**残差定义**：

$$
r_{\text{reproj}, i} = \text{DT}(\pi(\mathbf{P}_i; \mathbf{R}, \mathbf{t}, \mathbf{K}))
$$

其中：
- $\mathbf{P}_i$ 为第 $i$ 个点云的 3D 坐标
- $\pi(\cdot)$ 为相机投影函数
- $\mathbf{R}, \mathbf{t}$ 为待优化的外参
- $\mathbf{K}$ 为相机内参
- $\text{DT}(\cdot)$ 为 DT 图中对应像素的距离值

### 5. 形状约束（KL 散度）

**应用场景**：点云生成的图像与图像分割结果之间的形状一致性。

**KL 散度公式**：

$$
D_{KL}(P \| Q) = \sum_x P(x) \log \frac{P(x)}{Q(x)}
$$

将激光点云拟合凸包生成的概率分布 $P$ 与图像分割的概率分布 $Q$ 进行 KL 散度计算，最小化该值作为优化目标。

### 6. 边缘约束

**应用场景**：最小化点云轮廓点到图像轮廓的距离。

- 使用传统 CV 算法提取图像轮廓
- 基于轮廓生成 DT 图
- 提取点云轮廓点集
- 残差 = 点到图像轮廓的最短距离

### 7. 角度约束（杆子/立柱）

**应用场景**：对图像中的杆子/立柱进行直线拟合，最小化点云到直线的距离。

**残差定义**：对于拟合直线 $Ax + By + C = 0$ 和点云投影点 $(x_0, y_0)$：

$$
r_{\text{angle}} = \frac{|Ax_0 + By_0 + C|}{\sqrt{A^2 + B^2}}
$$

## Ceres 求解器配置

### Solver 选项

```cpp
ceres::Solver::Options options;
options.linear_solver_type = ceres::DENSE_SCHUR;  // 或 SPARSE_NORMAL_CHOLESky
options.minimizer_progress_to_stdout = true;
options.max_num_iterations = 100;
options.function_tolerance = 1e-6;
options.gradient_tolerance = 1e-8;
```

### 损失函数选择

| 损失函数 | 公式 | 适用场景 |
|----------|------|----------|
| **TrivialLoss** | $\rho(s) = s$ | 无异常值，线性最小二乘 |
| **HuberLoss** | $\rho(s) = \begin{cases} s & s \leq 1 \\ 2\sqrt{s} - 1 & s > 1 \end{cases}$ | 中等异常值 |
| **CauchyLoss** | $\rho(s) = \log(1 + s)$ | 大量异常值 |
| **SoftLOneLoss** | $\rho(s) = 2(\sqrt{1+s} - 1)$ | 温和的鲁棒性 |

### 自动求导

Ceres 支持自动求导（AutoDiff），通过模板化代价函数自动计算雅可比矩阵：

```cpp
ceres::CostFunction* cost_function =
    new ceres::AutoDiffCostFunction<LaneParallelCost, 1, 6>(
        new LaneParallelCost(observed_direction));
problem.AddResidualBlock(cost_function, loss_function, extrinsics);
```

其中模板参数 `<1, 6>` 表示残差维度为 1，参数块维度为 6（3 维旋转 + 3 维平移）。

## 优化流程

```
1. 构建 Problem 对象
   ↓
2. 添加 Parameter Block（外参、内参、3D 点等）
   ↓
3. 添加 Residual Block（各种代价函数 + 损失函数）
   ↓
4. 调用 ceres::Solve(options, &problem, &summary)
   ↓
5. 检查收敛状态，提取优化结果
```

## 相关页面

- [TDA4 OpenVX 系统优化](../platform/tda4-openvx-optimization.md) — DSP 加速的底层计算平台
- [匈牙利匹配算法](./hungarian-matching.md) — 车道线匹配作为优化的前置步骤
- [Douglas-Peucker 抽稀算法](./douglas-peucker.md) — 轮廓简化减少优化计算量
- [EMA 平滑算法](./ema-smoothing.md) — 优化结果的时序平滑
