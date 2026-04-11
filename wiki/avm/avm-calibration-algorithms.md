---
title: "AVM 标定系统核心算法"
category: avm
tags: [AVM, 标定, 鱼眼相机, Kannala-Brandt, BEV, 角点检测, LUT, PnP]
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/avm_calib/avm-calibration-core.md
  - raw/avm_calib/online-road-calibration.md
---

# AVM 标定系统核心算法

本文档详述 AVM（Around View Monitor）系统的核心标定算法，涵盖鱼眼相机模型、BEV 投影变换、两级角点检测、PnP 标定求解以及 LUT 生成。

## 1. 鱼眼相机模型

本系统采用 **Kannala-Brandt (KB) 鱼眼相机模型**，适用于 180 度以上超大视场角的鱼眼相机。

### 1.1 KB 投影模型

从 3D 点到 2D 图像点的投影过程：

$$
\begin{aligned}
\theta &= \arctan\left(\frac{r}{f}\right) \\
r_d &= f \cdot (\theta + k_2 \theta^2 + k_3 \theta^3 + k_4 \theta^4 + k_5 \theta^5) \\
u &= c_u + \frac{x}{r} \cdot r_d \\
v &= c_v + \frac{y}{r} \cdot r_d
\end{aligned}
$$

其中：

- $(x, y)$：归一化相机坐标系中的坐标
- $r = \sqrt{x^2 + y^2}$：归一化半径
- $\theta$：入射角
- $f$：焦距
- $k_2, k_3, k_4, k_5$：KB 畸变系数
- $(c_u, c_v)$：主点坐标
- $(u, v)$：最终像素坐标

### 1.2 坐标变换

**世界坐标系到相机坐标系**：

$$
\mathbf{P}_{cam} = \mathbf{R} \cdot \mathbf{P}_{world} + \mathbf{t}
$$

**旋转矩阵构造**（欧拉角 $R_x, R_y, R_z$）：

$$
\mathbf{R} = \mathbf{R}_z(R_z) \cdot \mathbf{R}_y(R_y) \cdot \mathbf{R}_x(R_x)
$$

## 2. BEV 投影变换

BEV（Bird's Eye View，鸟瞰图）投影将鱼眼图像映射到地面平面，消除透视畸变影响。

### 2.1 投影公式

$$
\mathbf{P}_{BEV} = \frac{1}{m} \cdot \left(\mathbf{R}_{yaw} \cdot \begin{bmatrix} x_w \\ y_w \end{bmatrix} + \begin{bmatrix} t_x \\ t_y \end{bmatrix}\right)
$$

其中 $m = 0.01$ 米/像素（BEV 分辨率）。

### 2.2 实现代码

```cpp
// 1. 计算相机姿态（强制相机位于 BEV 平面正上方）
cv::Mat rMatrix, camPos, tVecNew;
cv::Rodrigues(rVec, rMatrix);
camPos = -rMatrix.t() * tVec;
camPos.at<float>(0,0) = 0;   // 强制 X=0
camPos.at<float>(1,0) = 0.;  // 强制 Y=0

// 2. 仅保留 yaw 角
cv::Mat YPRAngle;
Coord_Transform::rVec2YPRAngle(rVec, YPRAngle);
YPRAngle.at<float>(0,0) = 0;  // pitch = 0
Coord_Transform::YPRAngle2RMatrix(YPRAngle, rMatrix);
tVecNew = -rMatrix * camPos;

// 3. 投影到 BEV
Coord_Transform::fisheyeImage2BEV(
    imgFisheyeGray, imgBEVGray,
    rMatrix, tVecNew,
    intrinsic, distortion,
    BEVROI_pixel, meterPerPixel);
```

## 3. 两级角点检测架构

鱼眼 180 度以上 FOV 导致严重径向畸变，棋盘格在图像边缘严重变形。系统采用 **BEV -> 鱼眼** 两级检测架构，包含主流程和回退流程。

### 3.1 完整检测流程

```
主流程：鱼眼图像 -> BEV 投影 -> BEV 角点检测 -> 反投影 -> 鱼眼亚像素优化
              ^                                                      |
              |                                                      |
              +---------------------- 成功 ---------------------------+

回退流程：当 BEV 检测失败时
鱼眼图像 -> ROI 内鱼眼直接检测 -> 消失点计算 R -> 重新 BEV 投影 -> BEV 检测 -> 反投影 -> 亚像素优化
```

### 3.2 BEV 角点检测（主流程）

#### 四象限卷积核设计

棋盘格角点的典型特征是四个象限呈现黑白交替分布，对角象限颜色相同：

```
BEV 图像

     +---------+---------+
     |  黑色   |  白色   |
     | (C1)    | (C2)    |
     | 左上    | 右上    |
     +---------+---------+  <-- 角点中心
     |  白色   |  黑色   |
     | (C3)    | (C4)    |
     | 左下    | 右下    |
     +---------+---------+

特征：C1 = C4 (对角同黑)，C2 = C3 (对角同白)
```

使用 11x11 卷积核，中心区域设为 0（角点中心可能模糊，使用外围区域更鲁棒）。

#### 角点响应计算

$$
\begin{aligned}
R_1 &= |(C_1 + C_4) - (C_2 + C_3)| \\
R_2 &= \max(\min(C_1, C_4) - \max(C_2, C_3), \quad \min(C_2, C_3) - \max(C_1, C_4))
\end{aligned}
$$

- $R_1$：检测对角象限的灰度差异，棋盘格角点处差值最大
- $R_2$：验证对角一致性，排除非对称图案干扰

#### 角点类型判断

$$
\text{cornerType} = \begin{cases}
\text{SADDLE\_POINT} & \text{if } R_2 / R_1 > 0.25 \\
\text{EDGE\_POINT} & \text{if } R_2 / R_1 \leq 0.25
\end{cases}
$$

使用比值而非绝对差值的优势：尺度不变性、对比度不变性、自动适应不同光照条件。

#### 非极大值抑制 (NMS)

采用网格化 NMS（11x11 网格），每个网格内寻找局部最大响应点：

```cpp
void Basic_Image_Process::nonMaxSuppression(cv::Mat& img,
    int width, float threshold, int height, std::vector<cv::Point2f>& localMax) {
    // 将图像划分为 width x height 的网格
    // 每个网格内使用 minMaxLoc 找最大值
    // 超过阈值的保留为候选角点
}
```

### 3.3 鱼眼图像角点检测（回退流程）

当初始外参偏差较大，BEV 投影无法正确消除畸变时触发。

#### ROI 区域策略

在鱼眼图像中心区域（50% 宽度 x 55% 高度）检测，该区域畸变相对较小：

```cpp
cv::Rect ROIfisheye(
    imgFisheyeGray.cols / 4,        // x = 中心 1/4 处
    imgFisheyeGray.rows / 4,        // y = 中心 1/4 处
    imgFisheyeGray.cols / 2,        // 宽度 = 图像一半
    imgFisheyeGray.rows * 11 / 20   // 高度 = 图像约 55%
);
```

#### 威斯滤波 (Wisconsin Filter)

利用 Hessian 矩阵构建角点响应函数，检测棋盘格鞍点特征：

$$
\mathbf{H} = \begin{bmatrix} L_{xx} & L_{xy} \\ L_{yx} & L_{yy} \end{bmatrix}
$$

二阶导数在 9x9 邻域中采样计算：

$$
\begin{aligned}
L_{xx} &= (v_{51} + v_{52} + v_{58} + v_{59}) - 4 \cdot v_{55} \\
L_{yy} &= (-v_{15} - v_{25} - v_{85} - v_{95}) + 4 \cdot v_{55} \\
L_{xy} &= (v_{37} + v_{28} + v_{73} + v_{82}) - 4 \cdot v_{55} \\
L_{yx} &= (-v_{33} - v_{22} - v_{88} - v_{77}) + 4 \cdot v_{55}
\end{aligned}
$$

角点响应公式：

$$
R = L_{xy} \cdot L_{yx} + L_{xx} \cdot L_{yy}
$$

该公式而非 $\det(\mathbf{H}) = L_{xx} L_{yy} - L_{xy}^2$ 的原因：考虑交叉项符号、鞍点增强（$L_{xx} L_{yy} < 0$ 产生大响应）、信噪比更高。

#### 鞍点验证

基于两个主边缘方向 $v_1, v_2$ 将邻域划分为四象限，验证黑白交替分布：

$$
\begin{aligned}
\text{diff}_{13} &= |\text{score}_1 - \text{score}_3| \\
\text{diff}_{24} &= |\text{score}_2 - \text{score}_4| \\
\text{diffAll} &= \max(\min(s_1, s_3) - \max(s_2, s_4), \quad \min(s_2, s_4) - \max(s_1, s_3))
\end{aligned}
$$

判定条件：

$$
\text{cornerType} = \begin{cases}
\text{SADDLE\_POINT} & \text{if } \frac{\text{diffAll}}{\text{diff}_{13}} > t \land \frac{\text{diffAll}}{\text{diff}_{24}} > t \\
\text{UNKNOW\_POINT} & \text{otherwise}
\end{cases}
$$

#### 消失点计算旋转矩阵

从鱼眼图像检测到的角点中拟合两组平行线，计算消失点构建精确旋转矩阵：

$$
\begin{aligned}
\mathbf{v}_x &= \mathbf{K}^{-1} \cdot \mathbf{V}_x \quad \text{(列方向消失点)} \\
\mathbf{v}_y &= \mathbf{K}^{-1} \cdot \mathbf{V}_y \quad \text{(行方向消失点)} \\
\mathbf{r}_1 &= \frac{\mathbf{v}_x}{\|\mathbf{v}_x\|} \quad \text{(x 轴方向)} \\
\mathbf{r}_2 &= \frac{\mathbf{v}_y}{\|\mathbf{v}_y\|} \quad \text{(y 轴方向)} \\
\mathbf{r}_3 &= \mathbf{r}_1 \times \mathbf{r}_2 \quad \text{(z 轴方向)} \\
\mathbf{R} &= [\mathbf{r}_1, \mathbf{r}_2, \mathbf{r}_3]
\end{aligned}
$$

### 3.4 亚像素优化

将整数像素位置的角点优化到亚像素精度（约 0.01 像素），采用线性拟合方法：

1. 提取角点邻域图像块（半径 r=11）
2. 计算 Sobel 梯度（幅值和方向）
3. 提取两条主边缘方向
4. 沿边缘方向采样点
5. 用 `cv::fitLine` 拟合两条直线
6. 计算两直线交点作为亚像素角点

交点公式：

$$
x^* = \frac{b_1 - b_2}{k_2 - k_1}, \quad y^* = \frac{k_2 b_1 - k_1 b_2}{k_2 - k_1}
$$

### 3.5 棋盘格组织算法

从离散角点集合组织成规则棋盘格结构：

1. **十字初始化**：从中心角点出发，找到上下左右四个相邻角点，形成 3x3 十字
2. **能量函数评估**：衡量棋盘格假设质量

$$
E = \lambda \cdot (\|\mathbf{v}_0 + \mathbf{v}_1 - 2\mathbf{d}_1\| + \|\mathbf{v}_1 + \mathbf{v}_2 - 2\mathbf{d}_2\|) + \frac{|d_1 - d_2|}{\min(d_1, d_2)}
$$

接受条件：$E < 15$

3. **棋盘格生长**：基于已有棋盘格，预测并扩展下一行/列

## 4. PnP 标定求解

### 4.1 PnP 原理

通过 n 个 3D 点及其对应的 2D 图像点求解相机位姿：

$$
E = \sum_{i=1}^{n} \|\mathbf{p}_i - \pi(\mathbf{R}, \mathbf{t}, \mathbf{K}, \mathbf{D}, \mathbf{P}_i)\|^2
$$

优化目标：

$$
(\mathbf{R}^*, \mathbf{t}^*) = \arg\min_{\mathbf{R}, \mathbf{t}} E
$$

### 4.2 求解方法

1. **DLT (Direct Linear Transform)**：初始值估计
2. **高斯-牛顿迭代**：非线性优化

迭代公式：

$$
\begin{aligned}
\mathbf{J} &= \frac{\partial \pi}{\partial [\mathbf{R}|\mathbf{t}]} \\
\Delta \mathbf{x} &= -(\mathbf{J}^T \mathbf{J})^{-1} \mathbf{J}^T \mathbf{e} \\
\mathbf{x}_{k+1} &= \mathbf{x}_k + \Delta \mathbf{x}
\end{aligned}
$$

### 4.3 完整标定流程

```
[开始]
  |
  v
+---------------------------+
| 1. 初始化                  |
|    - 加载配置文件           |
|    - 加载相机内参           |
+---------------------------+
  |
  v
+---------------------------+
| 2. 场景识别                |
|    - 识别标靶类型           |
+---------------------------+
  |
  v
+---------------------------+
| 3. 角点检测 (4路相机并行)   |
|    - BEV 检测（主流程）     |
|    - 鱼眼检测（回退流程）   |
+---------------------------+
  |
  v
+---------------------------+
| 4. PnP 求解 (4路相机)      |
|    - DLT 初始估计          |
|    - 高斯-牛顿迭代优化     |
+---------------------------+
  |
  v
+---------------------------+
| 5. 联合优化 (可选)          |
|    - 光束平差 (BA)         |
+---------------------------+
  |
  v
+---------------------------+
| 6. 误差验证                |
|    - 重投影误差 < 阈值？    |
+---------------------------+
  |
  v
+---------------------------+
| 7. 结果保存                |
|    - 外参保存 (YAML)       |
+---------------------------+
  |
  v
+---------------------------+
| 8. LUT 生成               |
+---------------------------+
  |
  v
[结束]
```

## 5. LUT 生成与图像拼接

### 5.1 LUT 原理

LUT（Look-Up Table）建立目标图像像素与源图像像素之间的映射关系。

数据结构：

```cpp
struct vert_tex_coord {
    float u;       // 源图像 u 坐标
    float v;       // 源图像 v 坐标
    float alpha;   // 融合权重
};

struct vert_index {
    unsigned char camera_id;  // 相机 ID
};
```

### 5.2 2D BEV 生成流程

1. **定义 BEV 视图参数**：视图宽度 = 车辆宽度 + 两侧扩展，视图高度 = 车辆长度 + 前后扩展，分辨率 = 像素/米 (ppm)
2. **生成 BEV 网格**：在 BEV 平面生成均匀网格点
3. **坐标变换**：世界点 -> 车体系 -> 相机系
4. **相机投影**：3D 相机系 -> 2D 图像系，应用鱼眼畸变模型
5. **融合权重计算**：基于距离拼接线的距离
6. **LUT 序列化保存**

### 5.3 多波段融合

在相机重叠区域实现平滑过渡：

1. 构建高斯-拉普拉斯金字塔
2. 计算融合权重
3. 金字塔各层加权融合
4. 重构最终图像

融合权重公式：

$$
w_i(d) = \begin{cases}
1 & d < d_{stitch} \\
\frac{d_{blend} - (d - d_{stitch})}{d_{blend}} & d_{stitch} \leq d < d_{stitch} + d_{blend} \\
0 & d \geq d_{stitch} + d_{blend}
\end{cases}
$$

## 相关页面

- [[opengl-rendering-pipeline|OpenGL 渲染管线]] -- AVM 图像的 OpenGL 渲染实现
- [[gltf-and-skinning|glTF 2.0 格式与骨骼动画]] -- glTF 模型加载与骨骼动画
- [[avm-calibration-algorithms|AVM 标定系统核心算法]] -- 本文档
