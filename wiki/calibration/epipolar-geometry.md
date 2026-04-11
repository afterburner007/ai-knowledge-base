---
title: "对极几何推导"
category: calibration
tags: [epipolar-geometry, essential-matrix, fundamental-matrix, BA, multi-camera, constraint]
created: 2026-04-09
updated: 2026-04-09
sources: ["raw/calibration_geo/epipolar-geometry.md"]
---

# 对极几何推导

对极几何（Epipolar Geometry）描述了同一个空间点在两个相机视角下的成像几何关系。其核心是推导出本质矩阵（Essential Matrix）的约束方程，这是多相机系统外参标定和光束法平差（BA）的数学基础。

## 1. 坐标系与变量定义

假设空间中有一点 $P$，在两个相机坐标系下的坐标分别为 $\mathbf{P}_1$ 和 $\mathbf{P}_2$。

- **相机 1（左）**：光心为 $O_1$，作为参考坐标系
- **相机 2（右）**：光心为 $O_2$，相对于相机 1 的旋转为 $\mathbf{R}$，平移为 $\mathbf{t}$

**归一化平面坐标**：点 $P$ 在两个相机成像平面上的归一化坐标分别为 $\mathbf{x}_1$ 和 $\mathbf{x}_2$。

根据投影模型，空间点坐标与归一化坐标的关系为：

$$\mathbf{P}_1 = z_1 \mathbf{x}_1$$

$$\mathbf{P}_2 = z_2 \mathbf{x}_2$$

其中 $z_1, z_2$ 是点 $P$ 在各自坐标系下的深度值。

## 2. 空间几何约束

根据坐标变换，点 $P$ 在两个坐标系下的位置满足：

$$\mathbf{P}_2 = \mathbf{R} \mathbf{P}_1 + \mathbf{t}$$

将归一化坐标代入上式：

$$z_2 \mathbf{x}_2 = \mathbf{R} (z_1 \mathbf{x}_1) + \mathbf{t}$$

## 3. 代数推导步骤

推导的目标是消除深度因子 $z_1$ 和 $z_2$，得到一个仅包含观测值 $\mathbf{x}$ 和位姿 $\mathbf{R}, \mathbf{t}$ 的等式。

### 3.1 第一步：左叉乘 $\mathbf{t}$ 消除平移项

在等式两边同时左叉乘平移向量 $\mathbf{t}$。由于向量与自身叉乘为零（$\mathbf{t} \times \mathbf{t} = 0$）：

$$\mathbf{t} \times (z_2 \mathbf{x}_2) = \mathbf{t} \times (z_1 \mathbf{R} \mathbf{x}_1) + \mathbf{t} \times \mathbf{t}$$

$$z_2 (\mathbf{t} \times \mathbf{x}_2) = z_1 (\mathbf{t} \times \mathbf{R} \mathbf{x}_1)$$

引入反对称矩阵 $[\mathbf{t}]_{\times}$，将叉乘写作矩阵乘法形式：

$$z_2 [\mathbf{t}]_{\times} \mathbf{x}_2 = z_1 [\mathbf{t}]_{\times} \mathbf{R} \mathbf{x}_1$$

其中：

$$[\mathbf{t}]_{\times} = \begin{bmatrix} 0 & -t_z & t_y \\ t_z & 0 & -t_x \\ -t_y & t_x & 0 \end{bmatrix}$$

### 3.2 第二步：左点乘 $\mathbf{x}_2^T$ 消除左侧项

在等式两边同时左点乘 $\mathbf{x}_2^T$。由于向量 $\mathbf{t} \times \mathbf{x}_2$ 同时垂直于 $\mathbf{t}$ 和 $\mathbf{x}_2$，因此它与 $\mathbf{x}_2$ 的点积必定为 $0$：

$$\mathbf{x}_2^T \cdot (z_2 [\mathbf{t}]_{\times} \mathbf{x}_2) = \mathbf{x}_2^T \cdot (z_1 [\mathbf{t}]_{\times} \mathbf{R} \mathbf{x}_1)$$

$$0 = z_1 \mathbf{x}_2^T [\mathbf{t}]_{\times} \mathbf{R} \mathbf{x}_1$$

### 3.3 第三步：化简得到对极约束

由于深度 $z_1$ 是标量且通常不为 $0$，可以将其约去，得到最终的几何约束方程：

$$\mathbf{x}_2^T [\mathbf{t}]_{\times} \mathbf{R} \mathbf{x}_1 = 0$$

## 4. 本质矩阵（Essential Matrix）

定义中间的矩阵乘积为**本质矩阵** $\mathbf{E}$：

$$\mathbf{E} = [\mathbf{t}]_{\times} \mathbf{R}$$

则对极约束简化为：

$$\mathbf{x}_2^T \mathbf{E} \mathbf{x}_1 = 0$$

**几何意义**：该公式表示向量 $\mathbf{x}_2$、$\mathbf{t}$ 和 $\mathbf{R} \mathbf{x}_1$ 三者共面。这三个向量共同构成了对极平面（Epipolar Plane）。

### 4.1 本质矩阵的性质

- 秩为 2：$\text{rank}(\mathbf{E}) = 2$
- 两个非零奇异值相等，第三个为 0
- 尺度等价性：$\mathbf{E}$ 具有尺度模糊性（乘以任意非零常数不改变约束）
- 自由度为 5：旋转 3 个自由度 + 平移方向 2 个自由度（平移尺度不确定）

## 5. 基础矩阵（Fundamental Matrix）

如果考虑相机内参矩阵 $\mathbf{K}$，像素坐标 $\mathbf{u}$ 与归一化坐标 $\mathbf{x}$ 的关系为 $\mathbf{u} = \mathbf{K} \mathbf{x}$，即 $\mathbf{x} = \mathbf{K}^{-1} \mathbf{u}$。

代入对极约束：

$$(\mathbf{K}_2^{-1} \mathbf{u}_2)^T \mathbf{E} (\mathbf{K}_1^{-1} \mathbf{u}_1) = 0$$

$$\mathbf{u}_2^T (\mathbf{K}_2^{-T} \mathbf{E} \mathbf{K}_1^{-1}) \mathbf{u}_1 = 0$$

定义**基础矩阵** $\mathbf{F} = \mathbf{K}_2^{-T} \mathbf{E} \mathbf{K}_1^{-1}$，则有像素层面的约束：

$$\mathbf{u}_2^T \mathbf{F} \mathbf{u}_1 = 0$$

### 5.1 本质矩阵与基础矩阵的对比

| 性质 | 本质矩阵 $\mathbf{E}$ | 基础矩阵 $\mathbf{F}$ |
|------|----------------------|----------------------|
| 坐标空间 | 归一化坐标 | 像素坐标 |
| 依赖内参 | 否 | 是 |
| 自由度 | 5 | 7 |
| 秩 | 2 | 2 |
| 约束 | $\mathbf{x}_2^T \mathbf{E} \mathbf{x}_1 = 0$ | $\mathbf{u}_2^T \mathbf{F} \mathbf{u}_1 = 0$ |

## 6. BA（Bundle Adjustment）优化

### 6.1 目标函数

BA 同时优化相机位姿（Poses）和空间点坐标（Points）。假设有 $n$ 个相机位姿 $\boldsymbol{\xi}_i$ 和 $m$ 个 3D 点 $\mathbf{P}_j$，目标是最小化所有观测点的重投影误差：

$$\min_{\boldsymbol{\xi}, \mathbf{P}} \sum_{i=1}^{n} \sum_{j=1}^{m} \delta_{ij} \left\| \mathbf{u}_{ij} - h(\boldsymbol{\xi}_i, \mathbf{P}_j) \right\|^2$$

其中：

| 符号 | 含义 |
|------|------|
| $\mathbf{u}_{ij}$ | 第 $j$ 个点在第 $i$ 幅图像上的实际观测像素坐标 |
| $h(\boldsymbol{\xi}_i, \mathbf{P}_j)$ | 投影函数，利用位姿 $\boldsymbol{\xi}_i$ 和点 $\mathbf{P}_j$ 计算出的预测像素坐标 |
| $\delta_{ij}$ | 指示变量，如果第 $i$ 个相机能看到第 $j$ 个点则为 1，否则为 0 |

### 6.2 投影函数

对于鱼眼相机，投影函数 $h$ 包含 KB 畸变模型：

$$h(\boldsymbol{\xi}_i, \mathbf{P}_j) = \pi_{KB}(\mathbf{R}_i \mathbf{P}_j + \mathbf{t}_i)$$

其中 $\pi_{KB}$ 为 KB 模型的投影算子（参见 [[fish-eye-camera-model|Kannala-Brandt 鱼眼相机模型]]）。

### 6.3 优化方法

BA 是一个大规模非线性最小二乘问题，常用求解器包括：

- **Ceres Solver**：自动微分，支持 Levenberg-Marquardt 和 Trust Region 策略
- **g2o**：图优化框架，适合稀疏结构
- **SPARSE_SCHUR**：利用 Schur Complement 加速求解（针对 BA 问题的特殊稀疏结构）

### 6.4 与对极约束的关系

对极约束提供了多相机系统外参的**初始估计**，而 BA 在此基础上进行**联合精化**：

```
特征匹配 → 对极约束 (E/F 矩阵) → 初始外参估计 → BA 联合优化 → 精确外参
```

对于 AVM 系统（4 个鱼眼相机），对极几何约束可用于验证和优化相邻相机之间的外参关系。

## 相关页面

- [[fish-eye-camera-model|Kannala-Brandt 鱼眼相机模型]] -- BA 优化中使用的鱼眼相机投影模型
- [[bev-projection|BEV 鸟瞰图投影变换]] -- 基于精确外参的 BEV 投影
- [[online-road-calibration|在线道路标定算法]] -- 利用场景特征在线优化相机外参
