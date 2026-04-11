---
title: "卡尔曼滤波 (KF)"
category: tracking
tags:
  - 卡尔曼滤波
  - 状态估计
  - CV模型
  - CA模型
  - 目标跟踪
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/fusion/fusion-presentation.md
  - raw/debug_tools/project-knowledge-points.md
---

# 卡尔曼滤波 (Kalman Filter, KF)

## 概述

卡尔曼滤波是一种递归的最优状态估计算法，适用于线性高斯系统。在自动驾驶泊车场景中，广泛用于立柱、墙角等静态目标的跟踪与状态估计。

## 数学模型

### CV 模型（Constant Velocity，匀速模型）

**状态向量**：

$$
\vec{x}(t) = (x, y, v_x, v_y)
$$

**状态转移函数**：

$$
\vec{x}(t + \Delta t) =
\begin{pmatrix}
x(t) + v_x \cdot \Delta t \\
y(t) + v_y \cdot \Delta t \\
v_x \\
v_y
\end{pmatrix}
$$

**状态转移矩阵**：

$$
F = \begin{bmatrix}
1 & 0 & \Delta t & 0 \\
0 & 1 & 0 & \Delta t \\
0 & 0 & 1 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

### CA 模型（Constant Acceleration，匀加速模型）

**状态向量**：

$$
\vec{x}(t) = (x, y, v_x, v_y, a_x, a_y)^T
$$

**状态转移函数**：

$$
\vec{x}(t + \Delta t) =
\begin{pmatrix}
x(t) + v_x \cdot \Delta t + \frac{1}{2} a_x \cdot \Delta t^2 \\
y(t) + v_y \cdot \Delta t + \frac{1}{2} a_y \cdot \Delta t^2 \\
v_x + \Delta t \cdot a_x \\
v_y + \Delta t \cdot a_y \\
a_x \\
a_y
\end{pmatrix}
$$

**状态转移矩阵**：

$$
F = \begin{bmatrix}
1 & 0 & \Delta t & 0 & \frac{1}{2}\Delta t^2 & 0 \\
0 & 1 & 0 & \Delta t & 0 & \frac{1}{2}\Delta t^2 \\
0 & 0 & 1 & 0 & \Delta t & 0 \\
0 & 0 & 0 & 1 & 0 & \Delta t \\
0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}
$$

## 卡尔曼滤波公式

### 预测阶段

$$
\hat{x}_{k|k-1} = F_k \hat{x}_{k-1|k-1} + B_k u_k
$$

$$
P_{k|k-1} = F_k P_{k-1|k-1} F_k^T + Q_k
$$

### 更新阶段

$$
K_k = P_{k|k-1} H_k^T (H_k P_{k|k-1} H_k^T + R_k)^{-1}
$$

$$
\hat{x}_{k|k} = \hat{x}_{k|k-1} + K_k (z_k - H_k \hat{x}_{k|k-1})
$$

$$
P_{k|k} = (I - K_k H_k) P_{k|k-1}
$$

其中：
- $\hat{x}_{k|k-1}$：先验状态估计
- $P_{k|k-1}$：先验协方差
- $K_k$：卡尔曼增益
- $z_k$：观测值
- $H_k$：观测矩阵
- $Q_k$：过程噪声协方差
- $R_k$：观测噪声协方差

## 噪声协方差矩阵设定

### 过程噪声 $Q$

- **CA 模型**：$Q$ 为六维矩阵，每个维度的方差即该维度的过程噪声方差，只有存在直接关联的维度之间协方差非零
- **CV 模型**：$Q$ 为四维矩阵，结构与 CA 类似但维度更低

### 观测噪声 $R$

$R$ 取决于观测值的维度。如果只能观测到位置 $(x, y)$，则 $R$ 为二维对角矩阵，对角线元素为各观测维度的方差。

## 应用场景

- **立柱与墙角跟踪**：使用 KF 对静态障碍物进行状态估计和轨迹平滑
- **行人跟踪**：在 Freespace 边界提取中，结合 PF 用于行人目标跟踪
- **车位角点跟踪**：在巡库阶段对检测到的车位角点进行持续跟踪

## 优缺点

**优点**：
- 计算效率高，适合嵌入式平台实时运行
- 对线性高斯系统是最优估计器
- 递归形式，不需要存储历史数据

**局限性**：
- 仅适用于线性系统
- 假设噪声为高斯分布
- 对于非线性运动模型（如转弯）需要使用 EKF

## 相关页面

- [扩展卡尔曼滤波 (EKF)](./extended-kalman-filter.md)
- [粒子滤波 (PF)](./particle-filter.md)
- [DBSCAN 聚类算法](./dbscan-clustering.md)
- [多传感器融合框架](../fusion/multi-sensor-fusion.md)
