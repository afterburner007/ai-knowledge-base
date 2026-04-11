---
title: "BEV 鸟瞰图投影变换"
category: calibration
tags: [BEV, projection, fisheye, AVM, homography, transformation]
created: 2026-04-09
updated: 2026-04-09
sources: ["raw/avm_calib/avm-calibration-core.md"]
---

# BEV 鸟瞰图投影变换

BEV（Bird's Eye View，鸟瞰图）投影变换是将鱼眼相机图像投影到地面平面（鸟瞰平面）的过程，是 AVM 标定系统中角点检测的核心前置步骤。

## 1. 投影原理

### 1.1 投影公式

BEV 投影将世界坐标系中的地面点 $(x_w, y_w)$ 映射到 BEV 图像的像素坐标 $(u_{BEV}, v_{BEV})$：

$$\mathbf{P}_{BEV} = \frac{1}{m} \cdot \left(\mathbf{R}_{yaw} \cdot \begin{bmatrix} x_w \\ y_w \end{bmatrix} + \begin{bmatrix} t_x \\ t_y \end{bmatrix}\right)$$

其中：

| 参数 | 含义 |
|------|------|
| $m$ | BEV 分辨率（米/像素），通常 $m = 0.01$ |
| $\mathbf{R}_{yaw}$ | 仅保留 yaw 角的 2D 旋转矩阵 |
| $t_x, t_y$ | 相机在地面平面上的横向平移 |

### 1.2 完整投影链路

BEV 投影的完整链路为：

```
BEV 像素坐标 (u_BEV, v_BEV)
       │
       ▼  分辨率换算
地面坐标 (x_w, y_w, 0)   ← 假设地面为 Z=0 平面
       │
       ▼  外参变换 [R | t]
相机坐标 P_cam = R · P_world + t
       │
       ▼  KB 模型投影 (鱼眼)
鱼眼像素坐标 (u, v)
```

反向投影（BEV 到鱼眼）的过程即为：对 BEV 图像中的每个像素，计算其对应的地面 3D 点，再通过鱼眼相机模型投影到鱼眼图像上采样像素值。

## 2. 相机姿态强制约束

在 AVM 标定的 BEV 投影中，需要对相机姿态进行特殊处理：

### 2.1 强制相机位于 BEV 平面正上方

```cpp
// 1. 计算相机光心位置
cv::Mat rMatrix, camPos, tVecNew;
cv::Rodrigues(rVec, rMatrix);
camPos = -rMatrix.t() * tVec;
camPos.at<float>(0,0) = 0;   // 强制 X = 0
camPos.at<float>(1,0) = 0;   // 强制 Y = 0

// 2. 仅保留 yaw 角，将 pitch 和 roll 归零
cv::Mat YPRAngle;
Coord_Transform::rVec2YPRAngle(rVec, YPRAngle);
YPRAngle.at<float>(0,0) = 0;  // pitch = 0
Coord_Transform::YPRAngle2RMatrix(YPRAngle, rMatrix);
tVecNew = -rMatrix * camPos;

// 3. 执行 BEV 投影
Coord_Transform::fisheyeImage2BEV(
    imgFisheyeGray, imgBEVGray,
    rMatrix, tVecNew,
    intrinsic, distortion,
    BEVROI_pixel, meterPerPixel);
```

这样处理的目的是将鱼眼图像投影到一个虚拟的水平鸟瞰平面上，使得棋盘格在 BEV 图像上呈现规则的网格形态，便于角点检测。

## 3. BEV 分辨率设置

### 3.1 分辨率参数

| 参数 | 典型值 | 说明 |
|------|--------|------|
| `meterPerPixel` | 0.01 m/pixel | BEV 图像每像素代表的实际距离 |
| `BEVROI_pixel` | 512 × 512 | BEV 图像尺寸 |

### 3.2 分辨率对检测的影响

- **高分辨率**（$m$ 较小）：BEV 图像更大，角点定位更精确，但计算量增加
- **低分辨率**（$m$ 较大）：BEV 图像更小，计算更快，但可能丢失细节

通常选择 $m = 0.01$（1 cm/pixel），512 × 512 的 BEV 图像可覆盖约 5m × 5m 的地面区域。

## 4. 两级检测架构中的 BEV 投影

BEV 投影是 AVM 标定两级检测架构的核心环节：

```
主流程：鱼眼图像 → BEV 投影 → BEV 角点检测 → 反投影 → 鱼眼亚像素优化

回退流程（当 BEV 检测失败时）：
鱼眼图像 → ROI 内鱼眼直接检测 → 消失点计算 R → 重新 BEV 投影 → BEV 检测 → 反投影 → 亚像素优化
```

### 4.1 主流程

当初始外参较准确时，BEV 投影能有效消除鱼眼畸变，棋盘格在 BEV 图像上呈现规则的正交网格，此时使用四象限卷积核进行角点检测效果最佳。

### 4.2 回退流程

当初始外参偏差较大时，BEV 投影后的棋盘格仍然变形。此时需要：

1. 在鱼眼图像中心 ROI 区域（中心 50% 宽度 × 55% 高度）直接检测角点
2. 通过消失点（Vanishing Point）计算精确的旋转矩阵 $R$
3. 使用精确的 $R$ 重新进行 BEV 投影
4. 在修正后的 BEV 图像上再次进行角点检测

## 5. 反投影（BEV 到鱼眼）

BEV 角点检测完成后，需要将检测到的角点反投影回鱼眼图像进行亚像素优化：

$$\text{Coord\_Transform::BEVPoints2Fisheye()}$$

反投影链路：

```
BEV 角点 (u_BEV, v_BEV)
       │
       ▼  分辨率 + 外参逆变换
地面 3D 点 P_world = [x_w, y_w, 0]^T
       │
       ▼  相机外参
相机坐标 P_cam = R · P_world + t
       │
       ▼  KB 模型正向投影
鱼眼像素坐标 (u, v)
```

## 相关页面

- [[fish-eye-camera-model|Kannala-Brandt 鱼眼相机模型]] -- BEV 投影依赖的鱼眼相机畸变模型
- [[online-road-calibration|在线道路标定算法]] -- 利用 BEV 投影进行在线道路标定
- [[epipolar-geometry|对极几何推导]] -- 多相机系统间的几何约束，可用于外参验证
