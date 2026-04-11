---
title: "在线道路标定算法"
category: calibration
tags: [online-calibration, lane-line, vanishing-point, ceres, extrinsic, self-calibration]
created: 2026-04-09
updated: 2026-04-09
sources: ["raw/avm_calib/online-road-calibration.md"]
---

# 在线道路标定算法

在线道路标定是一种基于场景特征的自标定方法，利用车辆行驶过程中的车道线特征自动标定相机外参。该方法无需专用标定场地和靶标，可在正常驾驶条件下完成标定。

## 1. 核心思想

```
自然场景特征 (车道线) → 几何约束 → 外参求解
```

### 1.1 基本假设

1. 车道线在 3D 空间中是平行的
2. 车道宽度是恒定的（通常 3.5m）
3. 地面是平面
4. 车辆行驶在平坦路面上

### 1.2 坐标系定义

| 坐标系 | 符号 | 原点 | 轴方向 |
|--------|------|------|--------|
| 车身坐标系 | $b$ | 车辆后轴中心 | X 前, Y 左, Z 上 |
| 相机坐标系 | $c$ | 相机光心 | X 右, Y 下, Z 前 |
| 旋转中间坐标系 | $r$ | -- | 用于优化的中间表示 |

变换关系：

$$\mathbf{P}_{body} = \mathbf{R}_{bc} \cdot \mathbf{P}_{camera} + \mathbf{t}_{bc}$$

## 2. 灭点（Vanishing Point）理论

### 2.1 基本原理

**灭点定义**：空间中一组平行线在图像平面上的投影交点。

```
3D 空间平行线
════════════════════> 行驶方向
   ═══════════════════════>
        ═══════════════════════>

投影到图像平面
         ╲    ╱
          ╲  ╱
           ╲╱
            × ← 灭点
```

### 2.2 灭点与相机姿态的关系

对于方向向量为 $\mathbf{d} = [d_x, d_y, d_z]^T$ 的平行线族，其灭点位置为：

$$\mathbf{v} = \mathbf{K} \cdot \mathbf{R} \cdot \mathbf{d}$$

其中 $\mathbf{K}$ 为相机内参矩阵，$\mathbf{R}$ 为世界坐标系到相机坐标系的旋转矩阵。

反求旋转矩阵：

$$\mathbf{R}^T \cdot \mathbf{K}^{-1} \cdot \mathbf{v} \propto \mathbf{d}_{ideal}$$

即：

$$\mathbf{R} \cdot \mathbf{d}_{ideal} \propto \mathbf{K}^{-1} \cdot \mathbf{v}$$

### 2.3 两直线交点计算

给定两条直线的齐次表示 $\mathbf{l}_1$ 和 $\mathbf{l}_2$，其交点为：

$$\mathbf{v} = \mathbf{l}_1 \times \mathbf{l}_2$$

直线由车道线端点 $(x_1, y_1), (x_2, y_2)$ 确定：

$$\mathbf{l} = [y_1 - y_2,\; x_2 - x_1,\; x_1 y_2 - x_2 y_1]^T$$

### 2.4 RANSAC 灭点估计

由于车道线检测存在噪声和异常值，使用 RANSAC 进行鲁棒灭点估计：

```
for iter = 1 to max_iterations:
    1. 随机选择两条车道线
    2. 计算交点 v = l_i × l_j
    3. 计算内点数量（距离 < threshold）
    4. 更新最优解
最小二乘精化最优灭点
```

精化阶段使用高斯-牛顿法最小化所有直线到灭点的距离平方和：

$$\min_{\mathbf{v}} \sum_i \text{dist}(\mathbf{v}, \mathbf{l}_i)^2$$

## 3. 外参初始化

### 3.1 2DOF 旋转初始化（roll + pitch）

适用于主相机（前、后鱼眼），基于车道线灭点初始化：

```cpp
// 1. 将灭点转换到归一化平面
v_norm = K⁻¹ · vanish_point_in_cam
v_norm.normalize()

// 2. 计算旋转角
pitch = asin(-v_norm[2])
roll  = atan2(v_norm[0], v_norm[2])

// 3. 构建旋转矩阵
Q_rc = Quaternion(AngleAxis(pitch, Y) * AngleAxis(roll, X))
```

几何解释：通过旋转使灭点方向 $\mathbf{v}$ 对齐到理想方向 $[0, 1, 0]^T$（车辆行驶方向）。

### 3.2 3DOF 旋转初始化（roll + pitch + yaw）

增加停止线灭点来初始化 yaw 角：

$$\mathbf{Q}_{rc} = \text{Quaternion}\left(\mathbf{R}_z(yaw) \cdot \mathbf{R}_y(pitch) \cdot \mathbf{R}_x(roll)\right)$$

### 3.3 平移向量初始化

基于车道宽度的约束求解相机高度 $h$ 和横向偏移 $t_x$：

对于地面上的点 $\mathbf{P} = [X, Y, 0]^T$，其投影为：

$$u = f_x \cdot \frac{X_c}{Z_c} + c_x, \quad v = f_y \cdot \frac{Y_c}{Z_c} + c_y$$

对于左右车道线上相同 $Z$ 坐标的点：

$$\Delta u = u_{right} - u_{left} = f_x \cdot \frac{W}{Z_c}$$

利用有限远处的测量可反求相机高度。

## 4. Ceres 非线性优化

### 4.1 优化问题形式化

**优化变量**：

$$\mathbf{x} = [\mathbf{Q}_1, \mathbf{Q}_2, \mathbf{Q}_3, \mathbf{Q}_4, \mathbf{t}_1, \mathbf{t}_2, \mathbf{t}_3, \mathbf{t}_4]$$

其中 $\mathbf{Q}_i \in SO(3)$ 为第 $i$ 个相机的旋转（四元数表示），$\mathbf{t}_i \in \mathbb{R}^3$ 为平移。

**目标函数**：

$$\min_{\mathbf{x}} \; f(\mathbf{x}) = \sum_i w_i \cdot r_i(\mathbf{x})^2$$

### 4.2 残差因子

#### LinesParallelFactor（车道线平行因子）

**几何约束**：同一车道的左右车道线在 3D 空间平行。

车道线变换到车身坐标系：

$$\mathbf{l}_b = \mathbf{R}^T \cdot \mathbf{l}_c$$

残差定义为上下边界处车道线间距的差值：

$$r_{parallel} = (y_{upper}^{(1)} - y_{upper}^{(2)}) - (y_{lower}^{(1)} - y_{lower}^{(2)})$$

#### LanesEqualWidthFactor（车道等宽因子）

**几何约束**：车道宽度恒定。

$$r_{width} = w_{upper} - w_{lower}$$

#### LineCoaxisFactor（共轴因子）

**几何约束**：同一车道的车道线在同一地面上。

地面平面方程：$\mathbf{n}^T \cdot \mathbf{P} + d = 0$

$$r_{coaxis} = |\mathbf{n}^T \cdot \mathbf{P} + d|^2$$

#### EndPointsCoinFactor（端点重合因子）

**几何约束**：相邻相机重叠区域的车道线端点应该重合。

$$r_{coin} = \|\mathbf{P}_{side} - \mathbf{P}_{front\_rear}\|^2$$

### 4.3 分阶段优化策略

```
Phase 1: 2DOF 优化（主相机）
├── 优化变量: Q_rc (仅 roll, pitch)
├── 固定变量: t_br, yaw
├── 残差因子: LinesParallel, Coaxis
└── 目标: 快速获得合理的旋转初值

Phase 2: 3DOF 优化（主相机）
├── 优化变量: Q_rc (roll, pitch, yaw)
├── 固定变量: t_br
├── 残差因子: Parallel + EqualWidth
└── 目标: 完善旋转估计

Phase 3: 6DOF 优化（全相机联合）
├── 优化变量: Q_rc + t_br（所有相机）
├── 残差因子: 全部因子 + EndPointsCoin
└── 目标: 全局最优解
```

### 4.4 Ceres Solver 配置

```cpp
ceres::Problem problem;
ceres::LossFunction* loss = new ceres::HuberLoss(1.0);

ceres::Solver::Options options;
options.linear_solver_type = ceres::SPARSE_SCHUR;
options.trust_region_strategy_type = ceres::LEVENBERG_MARQUARDT;
options.max_num_iterations = 100;

ceres::Solver::Summary summary;
ceres::Solve(options, &problem, &summary);
```

## 5. 坐标变换

### 5.1 齐次坐标变换

$$\mathbf{P}_{body} = \mathbf{T}_{bc} \cdot \mathbf{P}_{camera}, \quad \mathbf{T}_{bc} = \begin{bmatrix} \mathbf{R}_{bc} & \mathbf{t}_{bc} \\ \mathbf{0} & 1 \end{bmatrix}$$

### 5.2 直线变换

点在直线上的约束：$\mathbf{l}^T \cdot \mathbf{p} = 0$

若点的变换为 $\mathbf{p}' = \mathbf{H} \cdot \mathbf{p}$，则直线的变换为：

$$\mathbf{l}' = \mathbf{H}^{-T} \cdot \mathbf{l}$$

## 相关页面

- [[fish-eye-camera-model|Kannala-Brandt 鱼眼相机模型]] -- 在线标定依赖的鱼眼相机内参模型
- [[bev-projection|BEV 鸟瞰图投影变换]] -- 将鱼眼图像投影到鸟瞰平面以辅助车道线检测
- [[epipolar-geometry|对极几何推导]] -- 多相机系统间的几何约束关系
