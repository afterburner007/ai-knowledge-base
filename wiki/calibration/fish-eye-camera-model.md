---
title: "Kannala-Brandt 鱼眼相机模型"
category: calibration
tags: [fisheye, camera-model, KB-model, distortion, intrinsic, AVM]
created: 2026-04-09
updated: 2026-04-09
sources: ["raw/avm_calib/avm-calibration-core.md"]
---

# Kannala-Brandt 鱼眼相机模型

本页面详细介绍 Kannala-Brandt (KB) 鱼眼相机模型，该模型适用于 180 度以上超大视场角的鱼眼相机，是 AVM（全景环视）标定系统的核心基础。

## 1. KB 投影模型

### 1.1 从 3D 点到 2D 图像点的投影

KB 模型使用入射角 $\theta$ 的非线性多项式来描述径向畸变，投影公式如下：

$$\theta = \arctan\left(\frac{r}{f}\right)$$

$$r_d = f \cdot \left(\theta + k_2 \theta^2 + k_3 \theta^3 + k_4 \theta^4 + k_5 \theta^5\right)$$

$$u = c_u + \frac{x}{r} \cdot r_d$$

$$v = c_v + \frac{y}{r} \cdot r_d$$

其中：

| 参数 | 含义 |
|------|------|
| $f$ | 等效焦距 |
| $k_2, k_3, k_4, k_5$ | 径向畸变系数（KB 多项式） |
| $c_u, c_v$ | 主点坐标（光心） |
| $r = \sqrt{x^2 + y^2}$ | 入射点在归一化平面上到光心的距离 |
| $x, y$ | 归一化平面坐标 |
| $u, v$ | 像素坐标 |
| $r_d$ | 畸变后的径向距离 |

### 1.2 与针孔模型的区别

针孔相机模型的投影为 $r_d = f \cdot \theta$（线性关系），而 KB 模型引入了关于 $\theta$ 的多项式畸变项，能够更精确地描述鱼眼镜头在超大视场下的非线性投影特性。

## 2. 坐标变换

### 2.1 世界坐标系到相机坐标系

$$\mathbf{P}_{cam} = \mathbf{R} \cdot \mathbf{P}_{world} + \mathbf{t}$$

其中 $\mathbf{R} \in SO(3)$ 为旋转矩阵，$\mathbf{t} \in \mathbb{R}^3$ 为平移向量。

### 2.2 旋转矩阵构造

旋转矩阵由欧拉角 $(R_x, R_y, R_z)$ 按 ZYX 顺序构造：

$$\mathbf{R} = \mathbf{R}_z(R_z) \cdot \mathbf{R}_y(R_y) \cdot \mathbf{R}_x(R_x)$$

### 2.3 坐标变换完整链路

```
世界坐标 P_world
       │
       ▼  [R | t]  外参变换
相机坐标 P_cam = R · P_world + t
       │
       ▼  归一化
归一化坐标 [x, y] = [X_cam / Z_cam, Y_cam / Z_cam]
       │
       ▼  KB 畸变模型
畸变径向距离 r_d = f · (θ + k₂θ² + k₃θ³ + k₄θ⁴ + k₅θ⁵)
       │
       ▼  内参投影
像素坐标 [u, v] = [c_u + x/r · r_d, c_v + y/r · r_d]
```

## 3. KB 畸变模型详解

### 3.1 入射角计算

对于相机坐标系中的点 $\mathbf{P}_{cam} = [X, Y, Z]^T$，入射角为：

$$\theta = \arctan\left(\frac{\sqrt{X^2 + Y^2}}{Z}\right)$$

### 3.2 畸变多项式

KB 模型的畸变函数为奇次多项式：

$$d(\theta) = k_1 \theta + k_2 \theta^2 + k_3 \theta^3 + k_4 \theta^4 + k_5 \theta^5$$

其中 $k_1 = 1$（等价于焦距 $f$），因此：

$$r_d = f \cdot d(\theta)$$

### 3.3 反向投影（像素坐标到 3D 方向）

给定像素坐标 $(u, v)$，反求 3D 射线方向：

1. 计算归一化畸变坐标：

$$x_d = \frac{u - c_u}{f}, \quad y_d = \frac{v - c_v}{f}$$

2. 计算畸变径向距离：

$$r_d = \sqrt{x_d^2 + y_d^2}$$

3. 通过牛顿迭代法求解 $\theta$，使得 $d(\theta) = r_d$

4. 得到归一化方向向量：

$$\mathbf{v} = \left[\frac{x_d}{r_d} \sin\theta,\; \frac{y_d}{r_d} \sin\theta,\; \cos\theta\right]^T$$

## 4. 参数标定

KB 模型的待标定参数包括：

- **内参**：$f, c_u, c_v$
- **畸变系数**：$k_2, k_3, k_4, k_5$
- **外参**（多相机系统）：每个相机的 $\mathbf{R}_i, \mathbf{t}_i$

标定通常通过棋盘格标定板进行，利用角点检测得到 2D-3D 对应关系，然后通过非线性优化（如 Ceres Solver）最小化重投影误差。

## 5. 应用场景

- **AVM 全景环视系统**：四个鱼眼相机的统一建模
- **BEV 投影变换**：基于 KB 模型将鱼眼图像投影到鸟瞰平面
- **角点检测**：两级检测架构（BEV + 鱼眼回退）的基础
- **LUT 查找表生成**：用于实时鱼眼图像去畸变和拼接

## 相关页面

- [[bev-projection|BEV 鸟瞰图投影变换]] -- 基于 KB 模型将鱼眼图像投影到鸟瞰平面
- [[online-road-calibration|在线道路标定算法]] -- 利用鱼眼相机进行在线外参标定
- [[epipolar-geometry|对极几何推导]] -- 多相机系统间的几何约束关系
