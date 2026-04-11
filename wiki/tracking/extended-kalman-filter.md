---
title: "扩展卡尔曼滤波 (EKF)"
category: tracking
tags:
  - 扩展卡尔曼滤波
  - CTRV模型
  - 非线性估计
  - 雅可比矩阵
  - 目标跟踪
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/fusion/fusion-presentation.md
  - raw/debug_tools/project-knowledge-points.md
---

# 扩展卡尔曼滤波 (Extended Kalman Filter, EKF)

## 概述

扩展卡尔曼滤波是卡尔曼滤波在非线性系统中的推广。通过对非线性函数进行一阶泰勒展开（线性化），将非线性系统近似为线性系统后再使用标准 KF 框架进行状态估计。

## CTRV 模型（Constant Turn Rate and Velocity）

### 状态向量

$$
\mathbf{X} = \begin{bmatrix}
x \\
y \\
v \\
\theta \\
\omega
\end{bmatrix}
$$

其中 $(x, y)$ 为位置，$v$ 为线速度，$\theta$ 为航向角，$\omega$ 为转弯率。

### 状态转移方程

$$
\mathbf{X}_{k+1} = \begin{bmatrix}
x_k + \frac{v_k}{\omega}\left[\sin(\omega \Delta t + \theta_k) - \sin(\theta_k)\right] \\
y_k + \frac{v_k}{\omega}\left[-\cos(\omega \Delta t + \theta_k) + \cos(\theta_k)\right] \\
v_k \\
\omega \Delta t + \theta_k \\
\omega
\end{bmatrix}
$$

### 推导过程

$$
\Delta x = \int v \cos(\theta_k + \omega (t - t_k)) \, dt
$$

令 $u = \theta_k + \omega (t - t_k)$，则 $du = \omega \, dt$，代入得：

$$
\Delta x = v \int \cos(u) \frac{1}{\omega} \, du = \frac{v}{\omega}[\sin(u)]_{t_k}^{t_{k+1}}
$$

$$
\Delta x = \frac{v}{\omega}\left[\sin(\theta_k + \omega \Delta t) - \sin(\theta_k)\right]
$$

同理可得：

$$
\Delta y = \frac{v}{\omega}\left[-\cos(\theta_k + \omega \Delta t) + \cos(\theta_k)\right]
$$

### 状态转移雅可比矩阵 $J_F$

$$
J_F = \begin{bmatrix}
1 & 0 & \frac{1}{\omega}\left[\sin(\omega \Delta t + \theta) - \sin(\theta)\right] & \frac{v}{\omega^2}\left[-\cos(\omega \Delta t + \theta) + \cos(\theta)\right] \\
0 & 1 & \frac{1}{\omega}\left[-\cos(\omega \Delta t + \theta) + \cos(\theta)\right] & \frac{v}{\omega^2}\left[\sin(\omega \Delta t + \theta) - \sin(\theta)\right] \\
0 & 0 & 1 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

## 毫米波雷达观测模型

### 观测向量

毫米波雷达的观测量为极坐标形式 $(\rho, \theta, \dot{\rho})$：

$$
\mathbf{z}_k = \begin{bmatrix}
\rho_k \\
\theta_k \\
\dot{\rho}_k
\end{bmatrix} = \begin{bmatrix}
\sqrt{x_k^2 + y_k^2} \\
\text{atan2}(y_k, x_k) \\
\frac{x_k v_{x,k} + y_k v_{y,k}}{\sqrt{x_k^2 + y_k^2}}
\end{bmatrix}
$$

### 观测雅可比矩阵 $J_H$

$$
J_H = \begin{bmatrix}
\frac{x_k}{\sqrt{x_k^2 + y_k^2}} & \frac{y_k}{\sqrt{x_k^2 + y_k^2}} & 0 & 0 & 0 \\
-\frac{y_k}{x_k^2 + y_k^2} & \frac{x_k}{x_k^2 + y_k^2} & 0 & 0 & 0 \\
\frac{y_k(v_{x,k}\cos\theta_k - v_{y,k}\sin\theta_k)}{(x_k^2 + y_k^2)^{3/2}} & -\frac{x_k(v_{x,k}\sin\theta_k + v_{y,k}\cos\theta_k)}{(x_k^2 + y_k^2)^{3/2}} & \frac{x_k\cos\theta_k + y_k\sin\theta_k}{\sqrt{x_k^2 + y_k^2}} & \frac{v_{x,k}\cos\theta_k + v_{y,k}\sin\theta_k}{\sqrt{x_k^2 + y_k^2}} & 0
\end{bmatrix}
$$

## EKF 算法流程

EKF 的核心步骤与标准 KF 相同，区别在于使用雅可比矩阵替代线性系统中的状态转移矩阵和观测矩阵：

1. **预测**：使用非线性状态转移函数 $f(\cdot)$ 计算先验状态，使用 $J_F$ 传播协方差
2. **更新**：使用非线性观测函数 $h(\cdot)$ 计算预测观测，使用 $J_H$ 计算卡尔曼增益

## 泰勒展开近似

EKF 使用一阶泰勒展开对非线性函数进行线性化：

$$
f(x) = f(x_0) + \frac{f'(x_0)}{1!}(x - x_0) + \frac{f''(x_0)}{2!}(x - x_0)^2 + \cdots
$$

EKF 仅保留一阶项，因此适用于弱非线性系统。

## 应用场景

- **车辆转弯轨迹跟踪**：CTRV 模型适用于泊车过程中车辆的曲线运动
- **毫米波雷达目标跟踪**：极坐标观测到笛卡尔状态的转换
- **运动学模型融合**：结合车辆前轮偏向角和运动学约束进行状态估计

## 相关页面

- [卡尔曼滤波 (KF)](./kalman-filter.md)
- [粒子滤波 (PF)](./particle-filter.md)
- [多传感器融合框架](../fusion/multi-sensor-fusion.md)
