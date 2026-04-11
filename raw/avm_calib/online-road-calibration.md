# 相机在线道路标定算法原理 (camera_online_calib)

## **1. 概述**

相机在线道路标定是一种基于场景特征的自标定方法，利用车辆行驶过程中的车道线特征自动标定相机外参。该方法无需专用标定场地和靶标，可在正常驾驶条件下完成标定。

### **1.1 核心思想**

```
自然场景特征 (车道线) → 几何约束 → 外参求解
```

**基本假设**：

1. 车道线在 3D 空间中是平行的
2. 车道宽度是恒定的
3. 地面是平面
4. 车辆行驶在平坦路面上

### **1.2 数学基础**

**坐标系定义**：

- `b`: 车身坐标系 (Body frame) - 原点在车辆后轴中心
- `c`: 相机坐标系 (Camera frame) - 原点在相机光心
- `r`: 旋转坐标系 (Rotation frame) - 用于优化的中间坐标系

**变换关系**：

```
P_body = R_bc * P_camera + t_bc

其中:
- R_bc ∈ SO(3): 相机到车身的旋转矩阵
- t_bc ∈ ℝ³: 相机到车身的平移向量
```

## **2. 灭点 (Vanishing Point) 理论**

### **2.1 基本原理**

**灭点定义**: 空间中一组平行线在图像平面上的投影交点。

```
┌─────────────────────────────────────────────────────────────┐
│                    灭点几何示意图                            │
│                                                             │
│         3D 空间平行线                                        │
│    ════════════════════════> 行驶方向                        │
│         ════════════════════════>                           │
│              ════════════════════════>                      │
│                                                             │
│                    投影到图像平面                            │
│                          ╲    ╱                             │
│                           ╲  ╱                              │
│                            ╲╱                               │
│                             × ← 灭点                        │
│                          ╱  ╲                               │
│                         ╱    ╲                              │
└─────────────────────────────────────────────────────────────┘
```

### **2.2 灭点与相机姿态的关系**

**数学推导**：

对于方向向量为 `d = [dx, dy, dz]ᵀ` 的平行线族，其灭点位置为：

```
v = K * R * d

其中:
- v: 灭点在像素坐标系中的齐次坐标
- K: 相机内参矩阵
- R: 世界坐标系到相机坐标系的旋转矩阵
```

**反求旋转矩阵**：

已知灭点 `v` 和理想灭点方向 `d_ideal`，可以求解旋转矩阵：

```
Rᵀ * K⁻¹ * v ∝ d_ideal

即: R * d_ideal ∝ K⁻¹ * v
```

### **2.3 灭点计算算法**

#### **2.3.1 两直线交点**

给定两条直线的齐次表示 `l₁` 和 `l₂`，其交点为：

```
v = l₁ × l₂  (叉积)
```

**直线表示**：

```
l: ax + by + c = 0  ←→  l = [a, b, c]ᵀ

车道线端点 (x₁, y₁), (x₂, y₂) 确定的直线:
l = [y₁-y₂, x₂-x₁, x₁*y₂ - x₂*y₁]ᵀ
```

#### **2.3.2 RANSAC 灭点估计**

```cpp
// 算法流程
bool compute_vanish_point_ransac(
    const std::vector<Lane_t>& parallel_lanes,
    Eigen::Vector3f& vanish_point,
    std::vector<size_t>& inliers) {

    int best_inlier_count = 0;
    Eigen::Vector3f best_vanish_point;

    for (int iter = 0; iter < max_iterations; iter++) {
        // 1. 随机选择两条车道线
        auto lane_i = parallel_lanes[rand() % n];
        auto lane_j = parallel_lanes[rand() % n];

        // 2. 计算交点
        Eigen::Vector3f v = line_i.cross(line_j);
        v /= v[2];  // 归一化

        // 3. 计算内点数量
        int inlier_count = 0;
        for (const auto& lane : parallel_lanes) {
            float dist = point_line_distance(v, lane);
            if (dist < threshold) {
                inlier_count++;
            }
        }

        // 4. 更新最优解
        if (inlier_count > best_inlier_count) {
            best_inlier_count = inlier_count;
            best_vanish_point = v;
        }
    }

    // 5. 最小二乘精化
    vanish_point = refine_vanish_point_lsq(best_vanish_point, inliers);

    return best_inlier_count > min_inliers;
}
```

#### **2.3.3 最小二乘精化**

```cpp
// 目标：最小化所有直线到灭点的距离平方和
// min Σᵢ dist(v, lᵢ)²

// 使用高斯 - 牛顿法求解
void refine_vanish_point_lsq(
    const Eigen::Vector3f& initial_guess,
    const std::vector<size_t>& inliers) {

    Eigen::Vector3f v = initial_guess;

    for (int iter = 0; iter < max_iter; iter++) {
        // 构建雅可比矩阵
        Matrix3d J = Matrix3d::Zero();
        Vector3d b = Vector3d::Zero();

        for (size_t i : inliers) {
            const auto& l = lines[i];
            // 距离函数：d = (a*vx + b*vy + c) / sqrt(a² + b²)
            // 雅可比：∂d/∂v = [a, b, 0] / sqrt(a² + b²)
            ...
        }

        // 高斯 - 牛顿更新
        Vector3d delta = (J.transpose() * J).inverse() * J.transpose() * b;
        v += delta;

        if (delta.norm() < tolerance) break;
    }

    return v;
}
```

## **3. 外参初始化**

### **3.1 旋转矩阵初始化**

#### **3.1.1 2DOF 旋转初始化**

**适用场景**: 主相机 (前、后鱼眼) 基于车道线灭点初始化 roll 和 pitch。

```cpp
// 从灭点计算 2DOF 旋转
bool compute_2dof_rotation_by_lane_marker_vanish_point(
    const Eigen::Vector3f& ideal_point_in_bird,   // 理想灭点 [0, 1, 0]ᵀ
    Eigen::Vector3f& vanish_point_in_cam,         // 相机坐标系灭点
    Eigen::Quaternionf& Q_r_c) {                  // 输出旋转

    // 理想灭点在鸟瞰图中是无穷远点 (0, 1, 0)
    // 对应车辆行驶方向

    // 1. 将灭点转换到归一化平面
    Eigen::Vector3f v_norm = K⁻¹ * vanish_point_in_cam;
    v_norm.normalize();

    // 2. 计算旋转角
    // 目标：将 v_norm 旋转到 [0, 1, 0]ᵀ
    float pitch = asin(-v_norm[2]);
    float roll = atan2(v_norm[0], v_norm[2]);

    // 3. 构建旋转矩阵
    Q_r_c = Quaternionf(AngleAxisf(pitch, Vector3f::UnitY()) *
                        AngleAxisf(roll, Vector3f::UnitX()));

    return true;
}
```

**几何解释**：

```
相机坐标系下的灭点方向 v = [vx, vy, vz]ᵀ

通过旋转使 v 对齐到理想方向 [0, 1, 0]ᵀ:

1. 绕 X 轴旋转 roll 角：使 v 落入 Y-Z 平面
   roll = atan2(vx, vz)

2. 绕 Y 轴旋转 pitch 角：使 v 对齐 Y 轴
   pitch = asin(-vy / |v|)
```

#### **3.1.2 3DOF 旋转初始化**

**适用场景**: 需要初始化 yaw 角的场景。

```cpp
// 使用停止线灭点初始化 yaw
bool compute_main_3dof_rotation_by_stop_line_vanish_point(
    const Eigen::Vector3f& stop_lines_vanish_point,    // 停止线灭点
    const Eigen::Vector3f& lane_marker_vanish_point,   // 车道线灭点
    Eigen::Quaternionf& Q_r_c) {

    // 1. 从车道线灭点计算 roll 和 pitch (同 2DOF)
    float roll, pitch;
    compute_2dof_rotation(..., roll, pitch);

    // 2. 从停止线灭点计算 yaw
    // 停止线与车道线垂直，其灭点方向为 [-1, 0, 0]ᵀ 或 [1, 0, 0]ᵀ
    float yaw = compute_yaw_from_stop_line_vanish_point(
        stop_lines_vanish_point, lane_marker_vanish_point);

    // 3. 组合旋转
    Q_r_c = Quaternionf(
        AngleAxisf(yaw, Vector3f::UnitZ()) *
        AngleAxisf(pitch, Vector3f::UnitY()) *
        AngleAxisf(roll, Vector3f::UnitX()));

    return true;
}
```

### **3.2 平移向量初始化**

**基于车道宽度的约束**：

```
已知：
- 标准车道宽度 W (通常 3.5m)
- 左右车道线在图像中的位置

求解：
- 相机高度 h
- 横向偏移 t_x
```

**推导过程**：

```
对于地面上的点 P = [X, Y, 0]ᵀ (地面坐标系)，其在图像中的投影为：

u = fx * (X_c / Z_c) + cx
v = fy * (Y_c / Z_c) + cy

其中 [X_c, Y_c, Z_c]ᵀ = R * P + t

对于左右车道线上的对应点 (相同的 Z 坐标)：
X_left = X₀
X_right = X₀ + W

在图像中的水平距离：
Δu = u_right - u_left = fx * (W / Z_c)

当 Z_c → ∞ (灭点附近):
Δu → 0

利用有限远处的测量：
h = (fx * W * Y_c) / (Δu * Z_c²)
```

## **4. 非线性优化**

### **4.1 优化问题形式化**

**优化变量**：

```
x = [Q₁, Q₂, Q₃, Q₄, t₁, t₂, t₃, t₄]

其中:
- Q_i ∈ SO(3): 第 i 个相机的旋转 (四元数表示，4 个参数)
- t_i ∈ ℝ³: 第 i 个相机的平移 (3 个参数)
```

**目标函数**：

```
minimize: f(x) = Σᵢ wᵢ * rᵢ(x)²

其中:
- rᵢ(x): 第 i 个残差项
- wᵢ: 对应权重
```

### **4.2 残差因子详解**

#### **4.2.1 LinesParallelFactor (车道线平行因子)**

**几何约束**: 同一车道的左右车道线在 3D 空间平行。

**数学表达**：

```
给定两条车道线在相机坐标系下的表示:
l₁_c = [a₁, b₁, c₁]ᵀ
l₂_c = [a₂, b₂, c₂]ᵀ

变换到车身坐标系:
l_b = Rᵀ * l_c  (直线变换)

平行条件:
l₁_b × l₂_b = 0

残差定义:
r_parallel = |(l₁_b × l₂_b)|²
```

**Ceres 实现**：

```cpp
template <typename T>
bool operator()(const T* const rotation_r_c, T* residual) const {
    // 旋转组合: R_bc = R_br * R_rc
    const Eigen::Quaternion<T> R_r_c(rotation_r_c);
    const Eigen::Quaternion<T> R_bc = rotation_b_r_ * R_r_c;

    // 变换车道线到车身坐标系
    Eigen::Matrix<T, 3, 1> line_in_body_1 = R_bc * line_in_cam_1_;
    Eigen::Matrix<T, 3, 1> line_in_body_2 = R_bc * line_in_cam_2_;

    // 计算与参考边界的交点
    Eigen::Matrix<T, 3, 1> upper_1, lower_1, upper_2, lower_2;
    GeneratePointInNormalizedPlane(line_in_body_1, upper_line_in_body_, upper_1);
    GeneratePointInNormalizedPlane(line_in_body_1, lower_line_in_body_, lower_1);
    GeneratePointInNormalizedPlane(line_in_body_2, upper_line_in_body_, upper_2);
    GeneratePointInNormalizedPlane(line_in_body_2, lower_line_in_body_, lower_2);

    // 平行残差：上下交点 Y 坐标差应该相等
    residual[0] = (upper_1.y() - upper_2.y()) - (lower_1.y() - lower_2.y());
    residual[0] *= scaling_factor_;

    return true;
}
```

#### **4.2.2 LanesEqualWidthFactor (车道线等宽因子)**

**几何约束**: 车道宽度恒定。

**数学表达**：

```
对于左右车道线:
width_left = distance(L_left, origin)
width_right = distance(L_right, origin)

等宽条件:
width_left - width_right = 0

残差定义:
r_width = |width_left - width_right|²
```

**Ceres 实现**：

```cpp
template <typename T>
bool operator()(const T* const rotation_r_c, T* residual) const {
    // 变换车道线到车身坐标系
    auto left_line_body = transform_line(left_line_cam_, R_r_c, ...);
    auto right_line_body = transform_line(right_line_cam_, R_r_c, ...);

    // 计算在上下边界处的宽度
    T width_upper = compute_line_distance(left_line_body, right_line_body, upper_y);
    T width_lower = compute_line_distance(left_line_body, right_line_body, lower_y);

    // 等宽残差
    residual[0] = width_upper - width_lower;
    residual[0] *= scaling_factor_;

    return true;
}
```

#### **4.2.3 LineCoaxisFactor (共轴因子)**

**几何约束**: 同一车道的车道线在同一平面上。

**数学表达**：

```
地面平面方程: nᵀ * P + d = 0

对于车道线上的点 P:
nᵀ * P + d = 0

残差定义:
r_coaxis = |nᵀ * P + d|²
```

#### **4.2.4 EndPointsCoinFactor (端点重合因子)**

**几何约束**: 相邻相机重叠区域的车道线端点应该重合。

**数学表达**：

```
对于侧视相机和前后视相机的重叠区域:
P_side = P_front_rear

残差定义:
r_coin = |P_side - P_front_rear|²
```

### **4.3 优化求解**

#### **4.3.1 Ceres Solver 配置**

```cpp
ceres::Problem problem;
ceres::LossFunction* loss_function = new ceres::HuberLoss(1.0);

// 添加残差项
for (const auto& observation : observations) {
    // LinesParallelFactor
    problem.AddResidualBlock(
        LinesParallelFactor::CreateAutoDiffCostFunction(
            weight_parallel, line1, line2, ...),
        loss_function,
        Qrc_arr);  // 优化变量

    // LanesEqualWidthFactor
    problem.AddResidualBlock(
        LanesEqualWidthFactor::CreateAutoDiffCostFunction(
            width_weight, left_lane, right_lane, ...),
        loss_function,
        Qrc_arr);

    // LineCoaxisFactor
    problem.AddResidualBlock(
        LineCoaxisFactor::CreateAutoDiffCostFunction(
            coaxis_weight, line, ...),
        loss_function,
        Qrc_arr);
}

// 求解器配置
ceres::Solver::Options options;
options.linear_solver_type = ceres::SPARSE_SCHUR;
options.trust_region_strategy_type = ceres::LEVENBERG_MARQUARDT;
options.max_num_iterations = 100;
options.minimizer_progress_to_stdout = false;

ceres::Solver::Summary summary;
ceres::Solve(options, &problem, &summary);
```

#### **4.3.2 分阶段优化策略**

```
Phase 1: 2DOF 优化 (主相机)
┌────────────────────────────────────────┐
│ 优化变量: Q_r_c (仅 roll, pitch)       │
│ 固定变量: t_b_r, yaw                   │
│ 残差因子: LinesParallel, Coaxis        │
│ 目标: 快速获得合理的旋转初值           │
└────────────────────────────────────────┘
                    ↓
Phase 2: 3DOF 优化 (主相机)
┌────────────────────────────────────────┐
│ 优化变量: Q_r_c (roll, pitch, yaw)     │
│ 固定变量: t_b_r                        │
│ 残差因子: Parallel + EqualWidth        │
│ 目标: 完善旋转估计                     │
└────────────────────────────────────────┘
                    ↓
Phase 3: 6DOF 优化 (全相机联合)
┌────────────────────────────────────────┐
│ 优化变量: Q_r_c + t_b_r (所有相机)     │
│ 残差因子: 全部因子 + EndPointsCoin     │
│ 目标: 全局最优解                       │
└────────────────────────────────────────┘
```

## **5. 坐标变换**

### **5.1 坐标系定义**

```
车身坐标系 (Body Frame):
  - 原点：车辆后轴中心
  - X 轴：指向前方
  - Y 轴：指向左侧
  - Z 轴：指向上方

相机坐标系 (Camera Frame):
  - 原点：相机光心
  - X 轴：指向右侧
  - Y 轴：指向下方
  - Z 轴：指向前方 (光轴方向)

图像坐标系 (Image Frame):
  - 原点：图像左上角
  - u 轴：指向右侧
  - v 轴：指向下方

地面坐标系 (Ground Frame):
  - 原点：车辆后轴中心在地面的投影
  - X 轴：指向前方
  - Y 轴：指向左侧
  - Z 轴：指向上方 (与车身坐标系相同)
```

### **5.2 变换公式**

**齐次坐标变换**：

```
P_body = T_bc * P_camera

其中 T_bc = [R_bc | t_bc]
              [ 0  |  1  ]
```

**旋转向量与四元数**：

```cpp
// 旋转向量 → 旋转矩阵
R = exp(ω × ) = I + sin(θ)*[u]× + (1-cos(θ))*[u]×²

// 旋转矩阵 → 四元数
q = [cos(θ/2), u*sin(θ/2)]

// 四元数 → 旋转矩阵
R = (1-2q₂²-2q₃²)  (2q₁q₂-2q₀q₃)  (2q₁q₃+2q₀q₂)
    (2q₁q₂+2q₀q₃)  (1-2q₁²-2q₃²)  (2q₂q₃-2q₀q₁)
    (2q₁q₃-2q₀q₂)  (2q₂q₃+2q₀q₁)  (1-2q₁²-2q₂²)
```

### **5.3 直线变换**

**点在直线上的约束**：

```
lᵀ * p = 0

其中 l = [a, b, c]ᵀ 是直线的齐次表示，p = [x, y, 1]ᵀ是点
```

**直线变换公式**：

```
已知点的变换: p' = H * p

则直线的变换: l' = H⁻ᵀ * l

证明:
lᵀ * p = 0
lᵀ * (H⁻¹ * p') = 0
(lᵀ * H⁻¹) * p' = 0
(H⁻ᵀ * l)ᵀ * p' = 0

因此: l' = H⁻ᵀ * l
```

**应用到相机 - 车身变换**：

```cpp
Eigen::Vector3d transform_line(
    const Eigen::Vector3d& line_in_cam,
    const Eigen::Quaterniond& R_bc,
    const Eigen::Vector3d& t_bc) {

    // 构造变换矩阵
    Eigen::Matrix3d H;
    H.block<2, 2>(0, 0) = R_bc.topLeftCorner<2, 2>();
    H.block<2, 1>(0, 2) = t_bc.head<2>();
    H.row(2) << 0, 0, 1;

    // 直线变换
    Eigen::Vector3d line_in_body = H.inverse().transpose() * line_in_cam;
    line_in_body /= line_in_body[2];  // 归一化

    return line_in_body;
}
```

## **6. 逆透视变换 (IPM)**

### **6.1 基本原理**

**IPM 定义**: 将透视图像变换为鸟瞰图，使得平行线在变换后保持平行。

```
原始图像 (透视)                    IPM 图像 (鸟瞰)
┌─────────────────┐              ┌─────────────────┐
│    ╲       ╱    │              │    │       │    │
│     ╲     ╱     │              │    │       │    │
│      ╲   ╱      │    IPM  ──>  │    │       │    │
│       ╲ ╱       │              │    │       │    │
│        ×        │              │    │       │    │
│       ╱ ╲       │              │    │       │    │
│      ╱   ╱      │              │    │       │    │
└─────────────────┘              └─────────────────┘
```

### **6.2 IPM 变换矩阵**

**单应性矩阵推导**：

```
假设地面平面方程: nᵀ * P + d = 0

对于地面上的点 P，有:
nᵀ * P = -d

相机投影:
p = K * [R | t] * P

将 P 分解为地面上的点:
P = [X, Y, 0, 1]ᵀ (地面坐标系)

则投影可以写为:
p = K * (R_ground * P_ground + t)
  = K * (R_ground(:, 0:2) * [X, Y]ᵀ + t)

定义单应性矩阵:
H = K * [R_ground(:, 0:2) | t]

则:
p = H * [X, Y, 1]ᵀ

反变换:
[X, Y, 1]ᵀ = H⁻¹ * p
```

**IPM 实现**：

```cpp
void init_inverse_project_mat(cv::Mat& inverse_project_map) const {
    // 1. 计算 IPM 单应性矩阵
    Eigen::Matrix3d H = calculate_ipm_homography();

    // 2. 生成查找表
    inverse_project_map.create(height, width, CV_32FC2);

    for (int v = 0; v < height; v++) {
        for (int u = 0; u < width; u++) {
            // 像素坐标齐次化
            Eigen::Vector3d p_img = {u, v, 1};

            // 反投影到地面
            Eigen::Vector3d p_ground = H.inverse() * p_img;
            p_ground /= p_ground[2];

            // 存储映射关系
            inverse_project_map.at<cv::Point2f>(v, u) =
                cv::Point2f(p_ground[0], p_ground[1]);
        }
    }
}
```

### **6.3 ROI 分区**

**分区策略**：

```
┌─────────────────────────────────────────────────────────────┐
│                    鸟瞰图 ROI 分区                            │
│                                                             │
│    LEFT_ZONE        FRONT_ZONE        RIGHT_ZONE           │
│   (左侧区域)        (前侧区域)         (右侧区域)            │
│                                                             │
│                                                             │
│                    REAR_ZONE                                │
│                    (后侧区域)                               │
│                                                             │
│                    WHOLE_ZONE                               │
│                    (完整区域)                               │
└─────────────────────────────────────────────────────────────┘
```

**分区参数**：

```cpp
struct BirdGenerationParam {
    // 距离范围
    double front_distance_min = 0.5;   // 前侧最小距离 (m)
    double front_distance_max = 15.0;  // 前侧最大距离 (m)
    double side_distance_min = 0.5;    // 侧面最小距离 (m)
    double side_distance_max = 8.0;    // 侧面最大距离 (m)

    // 分辨率
    double resolution = 0.05;  // 5cm/pixel

    // ROI 定义
    struct ROI {
        double x_min, x_max, y_min, y_max;
    };
    std::map<RoiZone, ROI> roi_zones;
};
```

## **7. 数据同步与采样**

### **7.1 时间同步**

**问题**: 相机和轮速传感器时间戳不同步。

**解决方案**: 硬件时间同步 + 软件插值。

```cpp
// 线性插值获取同步的车速
VehicleSpeedData interpolate_velocity(
    const double timestamp,
    const std::map<double, VehicleSpeedData>& speed_data) {

    auto it = speed_data.upper_bound(timestamp);
    if (it == speed_data.begin() || it == speed_data.end()) {
        return VehicleSpeedData{timestamp, 0, 0};
    }

    auto prev = std::prev(it);
    double alpha = (timestamp - prev->first) / (it->first - prev->first);

    VehicleSpeedData result;
    result.timestamp = timestamp;
    result.linear_vel = (1 - alpha) * prev->second.linear_vel +
                        alpha * it->second.linear_vel;
    result.angular_vel = (1 - alpha) * prev->second.angular_vel +
                         alpha * it->second.angular_vel;

    return result;
}
```

### **7.2 距离积分**

**行驶距离计算**：

```cpp
double calculate_travel_distance(
    const VehicleSpeedData& start_speed,
    const VehicleSpeedData& end_speed,
    double time_delta) {

    // 梯形积分
    double avg_speed = (start_speed.linear_vel + end_speed.linear_vel) / 2;
    return avg_speed * time_delta;
}
```

### **7.3 自适应采样**

**采样策略**：

```cpp
// 基于行驶距离的自适应采样
bool should_sample(
    const double current_timestamp,
    const double last_sample_timestamp,
    const VehicleSpeedData& current_speed,
    const double sampling_distance_threshold = 2.0) {  // 2 米采样一次

    double distance = calculate_travel_distance(
        last_speed_, current_speed,
        current_timestamp - last_sample_timestamp);

    return distance >= sampling_distance_threshold;
}
```

## **8. 质量控制**

### **8.1 数据质量检查**

**车速检查**：

```
有效条件:
- 线速度: 5 km/h < v < 50 km/h
- 角速度: |ω| < 15°/s

无效条件:
- 车辆静止 (v < 5 km/h): 特征不足
- 车速过快 (v > 50 km/h): 运动模糊
- 急转弯 (|ω| > 15°/s): 地面假设失效
```

**特征质量检查**：

```
有效条件:
- 每个 ROI 区域内车道线数量 >= 2
- 车道线长度 >= 3m
- 车道线拟合优度 R² > 0.9

无效条件:
- 车道线太少: 约束不足
- 车道线太短: 灭点计算不准确
- 拟合质量差: 可能是噪声
```

### **8.2 标定结果验证**

**超差检查**：

```cpp
bool check_calibration_result(
    const CalibResult& result,
    const CalibResult& reference) {

    // 旋转角度检查
    Eigen::Vector3f ypr_diff = quat_to_ypr(result.Q_b_c) -
                               quat_to_ypr(reference.Q_b_c);

    if (ypr_diff.cwiseAbs().maxCoeff() > max_angle_diff) {
        return false;
    }

    // 平移检查
    double translation_diff = (result.t_b_c - reference.t_b_c).norm();

    if (translation_diff > max_translation_diff) {
        return false;
    }

    return true;
}
```

**IPM 拼接验证**：

```
验证方法:
1. 检查相邻相机重叠区域的车道线连续性
2. 检查拼接缝处的灰度一致性
3. 检查整体鸟瞰图的几何畸变

评分标准:
- 连续性得分: 车道线断开程度
- 一致性得分: 拼接缝处灰度差异
- 几何得分: 直线是否保持直线
```

### **8.3 稳定性检查**

**多次采样一致性**：

```cpp
// 计算多次标定结果的标准差
Eigen::Vector3f compute_rotation_std(
    const std::vector<Eigen::Quaternionf>& rotations) {

    std::vector<Eigen::Vector3f> yprs;
    for (const auto& q : rotations) {
        yprs.push_back(quat_to_ypr(q));
    }

    Eigen::Vector3f mean = compute_mean(yprs);
    Eigen::Vector3f std = compute_std(yprs, mean);

    return std;
}

// 稳定性判断
bool is_stable(const Eigen::Vector3f& std) {
    return std.maxCoeff() < stability_threshold;  // 如 0.5°
}
```

## **9. 误差分析**

### **9.1 误差来源**

```
┌─────────────────────────────────────────────────────────────┐
│                      误差来源分析                            │
├─────────────────────────┬───────────────────────────────────┤
│ 传感器误差              │ 相机内参误差                      │
│                         │ 轮速计误差                        │
│                         │ 时间同步误差                      │
├─────────────────────────┼───────────────────────────────────┤
│ 算法误差                │ 特征检测误差                      │
│                         │ 灭点计算误差                      │
│                         │ 优化局部最优                      │
├─────────────────────────┼───────────────────────────────────┤
│ 环境误差                │ 地面不平整                        │
│                         │ 车道线磨损                        │
│                         │ 光照变化                          │
└─────────────────────────┴───────────────────────────────────┘
```

### **9.2 误差传播分析**

**内参误差对外参的影响**：

```
Δx_ext = J * Δx_int

其中 J 是雅可比矩阵:
J = ∂(外参) / ∂(内参)

通过实验标定:
- fx 误差 1% → 外参角度误差约 0.1°
- cx 误差 10px → 外参角度误差约 0.2°
```

**灭点误差对旋转的影响**：

```
给定灭点误差 Δv，旋转误差为:

ΔR ≈ [v]× * Δv / |v|²

其中 [v]×是叉积矩阵
```

### **9.3 不确定性估计**

```cpp
// 使用协方差矩阵估计不确定性
Eigen::Matrix6d estimate_covariance(
    const ceres::Problem& problem,
    const std::vector<double*>& parameter_blocks) {

    Eigen::SparseMatrix<double> J;
    problem.Jacobian(&J);

    // 协方差 = (JᵀJ)⁻¹
    Eigen::SparseMatrix<double> H = J.transpose() * J;
    Eigen::SimplicialLDLT<Eigen::SparseMatrix<double>> solver;
    solver.compute(H);

    Eigen::Matrix6d cov = solver.solve(Eigen::Matrix6d::Identity());

    return cov;
}

// 从协方差提取标准差
Eigen::Vector6d std_dev = cov.diagonal().cwiseSqrt();
```

## **10. 性能优化**

### **10.1 计算加速**

**LUT 查找表优化**：

```cpp
// 预计算畸变校正映射
void init_undistort_map(cv::Mat& map1, cv::Mat& map2) const {
    // 离线计算每个像素的映射关系
    // 运行时直接使用 cv::remap
    cv::initUndistortRectifyMap(
        K_, dist_coeffs_, cv::Mat(), K_,
        image_size_, CV_32FC2, map1, map2);
}

// IPM 查找表
void init_ipm_lut(std::vector<cv::Point2f>& lut) const {
    // 预计算 IPM 映射
    for (int v = 0; v < height; v++) {
        for (int u = 0; u < width; u++) {
            lut[v * width + u] = inverse_project(u, v);
        }
    }
}
```

**批量处理优化**：

```cpp
// 使用 Eigen 向量化批量处理车道线
void transform_lines_batch(
    const std::vector<Eigen::Vector3d>& lines_in_cam,
    const Eigen::Quaterniond& R_bc,
    const Eigen::Vector3d& t_bc,
    std::vector<Eigen::Vector3d>& lines_in_body) {

    // 构造变换矩阵
    Eigen::Matrix<double, 3, Eigen::Dynamic> lines_cam(3, lines_in_cam.size());
    for (size_t i = 0; i < lines_in_cam.size(); i++) {
        lines_cam.col(i) = lines_in_cam[i];
    }

    // 批量变换
    Eigen::Matrix3d H_inv_T = compute_line_transform_matrix(R_bc, t_bc).inverse().transpose();
    Eigen::Matrix<double, 3, Eigen::Dynamic> lines_body = H_inv_T * lines_cam;

    // 转换回 vector
    lines_in_body.resize(lines_in_cam.size());
    for (size_t i = 0; i < lines_in_cam.size(); i++) {
        lines_in_body[i] = lines_body.col(i);
    }
}
```

### **10.2 内存优化**

**对象池模式**：

```cpp
template<typename T>
class ObjectPool {
public:
    T* acquire() {
        if (pool_.empty()) {
            return new T();
        }
        T* obj = pool_.back();
        pool_.pop_back();
        return obj;
    }

    void release(T* obj) {
        obj->reset();  // 重置状态
        pool_.push_back(obj);
    }

private:
    std::vector<T*> pool_;
};

// 使用对象池管理 Frame 对象
ObjectPool<Frame> frame_pool;

void process_image(const cv::Mat& image) {
    Frame* frame = frame_pool.acquire();
    // ... 处理 ...
    frame_pool.release(frame);
}
```

### **10.3 并行化**

**线程池任务分发**：

```cpp
// 多相机并行处理
std::vector<std::future<bool>> futures;
for (CameraID cam_id : calib_cam_ids_) {
    futures.push_back(thread_pool_->enqueue([=]() {
        return bird_lane_detector_->run(image, frame);
    }));
}

// 等待所有任务完成
for (auto& future : futures) {
    future.get();
}
```

## **11. 总结**

### **11.1 算法流程总结**

```
┌─────────────────────────────────────────────────────────────┐
│                  在线标定完整流程                            │
├─────────────────────────────────────────────────────────────┤
│ 1. 系统初始化                                                │
│    - 加载配置参数                                            │
│    - 初始化相机模型                                          │
│    - 创建调度器和检测器                                      │
├─────────────────────────────────────────────────────────────┤
│ 2. 数据采集与同步                                            │
│    - 图像回调 → 畸变校正 → IPM → 车道线检测                 │
│    - 轮速回调 → 速度积分 → 距离计算                         │
│    - 时间同步 → 数据配对                                    │
├─────────────────────────────────────────────────────────────┤
│ 3. 特征处理与采样                                            │
│    - 特征质量检查                                            │
│    - 自适应采样 (基于距离)                                   │
│    - 特征组织与存储                                          │
├─────────────────────────────────────────────────────────────┤
│ 4. 外参初始化                                                │
│    - 灭点计算 (RANSAC)                                       │
│    - 2DOF/3DOF旋转初始化                                    │
│    - 平移初始化                                              │
├─────────────────────────────────────────────────────────────┤
│ 5. 非线性优化                                                │
│    - 构建优化问题 (Ceres)                                    │
│    - 添加残差因子                                            │
│    - 分阶段优化 (2DOF → 3DOF → 6DOF)                        │
├─────────────────────────────────────────────────────────────┤
│ 6. 结果验证与输出                                            │
│    - 候选解筛选                                              │
│    - 超差检查                                                │
│    - IPM 拼接验证                                           │
│    - 输出标定结果                                            │
└─────────────────────────────────────────────────────────────┘
```

### **11.2 关键创新点**

1. **基于灭点的闭式解**: 无需迭代即可获取合理的初值
2. **多因子联合优化**: 综合利用平行、等宽、共轴等多种几何约束
3. **分阶段优化策略**: 从简到繁，避免局部最优
4. **自适应采样**: 基于行驶距离，保证数据多样性
5. **质量控制系统**: 多层验证，确保结果可靠

### **11.3 局限性与改进方向**

**局限性**:

- 依赖清晰的车道线
- 需要平坦路面假设
- 对车速范围有要求

**改进方向**:

- 增加其他特征源 (如停止线、路沿)
- 引入 IMU 数据辅助
- 深度学习特征检测
- 在线质量监控与自修复

---

# **相机在线道路标定系统 (camera_online_calib) 架构设计**

## **1. 系统概述**

### **1.1 模块简介**

`camera_online_calib` 模块是车辆传感器在线标定系统的核心组件，负责在车辆行驶过程中自动标定四路鱼眼相机的外参。该系统基于车道线特征进行自标定，无需专用标定场地和靶标。

**核心功能**：

- 基于车道线的相机外参自动标定
- 支持四路鱼眼相机 (前、后、左、右) 联合优化
- 支持环视 (AVM) 和广角相机标定
- 实时数据同步与特征提取
- 自适应采样与质量控制

### **1.2 应用场景**

```
┌─────────────────────────────────────────────────────────────┐
│                    车辆行驶场景                              │
│                                                             │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│   │ 前鱼眼  │    │ 后鱼眼  │    │ 左/右鱼眼│               │
│   └────┬────┘    └────┬────┘    └────┬────┘               │
│        │              │              │                     │
│        └──────────────┼──────────────┘                     │
│                       ▼                                    │
│            ┌─────────────────────┐                         │
│            │  OnlineCalibScheduler │                       │
│            │  - 数据同步          │                        │
│            │  - 特征提取          │                        │
│            │  - 外参优化          │                        │
│            └─────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### **1.3 系统输入输出**

**输入**：

- 四路鱼眼相机图像
- 车辆轮速信号 (线速度、角速度)
- 相机内参参数 (EOL 标定结果)
- 初始外参 (EOL 标定结果)

**输出**：

- 相机外参标定结果 (旋转 + 平移)
- 标定状态与进度
- 质量评估指标
- 更新的标定文件

## **2. 系统架构**

### **2.1 分层架构**

```
┌────────────────────────────────────────────────────────────┐
│                    接口层 (Interface)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ OnlineCalibrator                                      │  │
│  │ - start()/stop()/clear()                              │  │
│  │ - image_callback()/wheel_speed_callback()             │  │
│  │ - fetch_calib_state()/update_calib_result()           │  │
│  └──────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│                   调度层 (Scheduler)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ OnlineCalibScheduler                                  │  │
│  │ - 数据同步 (sync_sensors)                             │  │
│  │ - 采样调度 (udpate_next_sample_stamp)                 │  │
│  │ - 任务分发 (thread_pool)                              │  │
│  │ - 状态管理 (drive_state_jump)                         │  │
│  └──────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│                   算法层 (Algorithm)                        │
│  ┌────────────────────┐  ┌────────────────────────────┐   │
│  │   Frontend (前端)  │  │      Backend (后端)        │   │
│  │ ┌────────────────┐ │  │ ┌────────────────────────┐ │   │
│  │ │BirdLaneDetector│ │  │ │ VPExtrinsicCalib       │ │   │
│  │ │- 图像畸变校正  │ │  │ │- 外参初始化            │ │   │
│  │ │- IPM 变换       │ │  │ │- 灭点计算              │ │   │
│  │ │- 车道线检测    │ │  │ │- 外参优化              │ │   │
│  │ │- 特征组织      │ │  │ │- 结果验证              │ │   │
│  │ └────────────────┘ │  │ └────────────────────────┘ │   │
│  └────────────────────┘  └────────────────────────────┘   │
├────────────────────────────────────────────────────────────┤
│                   基础层 (Infrastructure)                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │ ThreadPool │ │ SteadyTimer│ │ EventLoop  │ │  Log    │ │
│  └────────────┘ └────────────┘ └────────────┘ └─────────┘ │
└────────────────────────────────────────────────────────────┘
```

### **2.2 核心类图**

```
┌─────────────────────────────────────────────────────────────────┐
│                     OnlineCalibrator                            │
│─────────────────────────────────────────────────────────────────│
│ - calib_scheduler_: std::shared_ptr<OnlineCalibScheduler>       │
│─────────────────────────────────────────────────────────────────│
│ + start()                                                       │
│ + stop()                                                        │
│ + image_callback()                                              │
│ + wheel_speed_callback()                                        │
│ + fetch_calib_state()                                           │
│ + update_calib_result()                                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ 组合
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  OnlineCalibScheduler                           │
│─────────────────────────────────────────────────────────────────│
│ - config_path_: std::string                                     │
│ - car_ptr_: CarPtr                                              │
│ - calib_cam_ids_: std::set<CameraID>                            │
│ - bird_lane_detector_: std::unique_ptr<BirdLaneDetector>        │
│ - vp_extrinsic_calib_: std::unique_ptr<ExtrinsicCalibInterface> │
│ - thread_pool_lane_detection_: ThreadPool                       │
│ - thread_pool_optimization_: ThreadPool                         │
│ - sync_thread_: std::thread                                     │
│─────────────────────────────────────────────────────────────────│
│ + start() / stop() / clear()                                    │
│ + image_callback() / vehicle_speed_callback()                   │
│ + fetch_calib_result()                                          │
│ - sync_sensors()                                                │
│ - run_optimization()                                            │
│ - check_calibration_result()                                    │
└───────┬──────────────────────────────────┬──────────────────────┘
        │ 使用                             │ 使用
        ▼                                  ▼
┌──────────────────┐            ┌────────────────────────────────┐
│ BirdLaneDetector │            │      VPExtrinsicCalib          │
│──────────────────│            │────────────────────────────────│
│ - options_       │            │ - frames_splitter_options_     │
│ - car_ptr_       │            │ - closed_form_options_         │
│──────────────────│            │ - optimization_problem_options_│
│ + init()         │            │ - ruler_lines_                 │
│ + run()          │            │ - raw_car_ptr_                 │
│ - run_impl()     │            │────────────────────────────────│
│ - detect_lanes() │            │ + reset()                      │
│ - generate_bird()│            │ + run_once()                   │
└──────────────────┘            │ - init_extrinsic()             │
                                │ - init_main_extrinsic()        │
                                │ - init_side_extrinsic()        │
                                │ - optimize_extrinsic()         │
                                └────────────────────────────────┘
```

## **3. 核心模块设计**

### **3.1 接口层：OnlineCalibrator**

**职责**: 对外提供统一的标定接口，隐藏内部实现细节。

**核心方法**：

```cpp
class OnlineCalibrator {
public:
    // 生命周期管理
    bool start(const CameraIDOut &calib_camera_id,
               const std::string &camera_param_path,
               const std::string &avm_config_path,
               const std::string &online_calib_config_path);
    bool stop();
    bool clear();

    // 数据输入
    bool image_callback(const CameraIDOut &camera_id,
                        const double timestamp,
                        const std::string color_type,
                        const cv::Mat &image);
    bool wheel_speed_callback(const double timestamp,
                              const double left_wheelspeed,
                              const double right_wheelspeed,
                              const double yaw);

    // 状态获取
    bool fetch_calib_state(CalibrationStateOut &calib_state_out,
                           ErrorCodeOut &error_code_out,
                           float &calib_progress);

    // 结果更新
    bool update_calib_result(const std::string &input_calib_result_path,
                             const std::string &output_calib_result_path);
};
```

### **3.2 调度层：OnlineCalibScheduler**

**职责**: 数据同步、任务调度、状态管理。

#### **3.2.1 数据流**

```
图像数据 ──┬──> image_callback() ──> lane_feature_frame_ (队列)
           │
轮速数据 ──┴──> vehicle_speed_callback() ──> vechile_speed_data_ (Map)
                                        │
                                        ▼
                              sync_sensors() 线程
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
        add_sync_job()                            maybe_finish_sample()
        数据同步任务                                采样完成检查
                    │                                       │
                    ▼                                       ▼
        run_optimization()                      check_calibration_result()
        外参优化                                  结果验证
```

#### **3.2.2 关键数据结构**

```cpp
// 车速数据结构
struct VehicleSpeedData {
    double timestamp;
    double linear_vel;   // 线速度 (m/s)
    double angular_vel;  // 角速度 (rad/s)
};

// 帧数据结构
struct Frame {
    CameraID cam_id;
    double timestamp;
    cv::Mat raw_image;
    cv::Mat bird_image;
    std::map<LaneSide, LaneFeature> lane_features;  // 车道线特征
};

// 观测数据结构
struct Observation {
    CameraID cam_id;
    double timestamp;
    VehicleSpeedData vehicle_speed;
    std::map<LaneSide, std::vector<Lane_t>> lanes;  // 车道线数据
};
```

#### **3.2.3 采样调度策略**

```cpp
// 基于行驶距离的自适应采样
void update_next_sample_stamp(const CameraID camera_id,
                               const double timestamp,
                               const float linear_vel) {
    // 计算行驶距离
    double distance = linear_vel * (timestamp - last_sample_timestamp);

    // 距离阈值判断
    if (distance >= sampling_distance_threshold) {
        trigger_sampling();
        next_sample_timestamp = timestamp + sampling_interval;
    }
}
```

### **3.3 前端：BirdLaneDetector**

**职责**: 从原始图像中提取车道线特征，生成鸟瞰图。

#### **3.3.1 处理流程**

```
原始图像 ──> 畸变校正 ──> IPM 变换 ──> 鸟瞰图 ──> 车道线检测 ──> 特征组织
     │              │            │           │            │
     │              │            │           │            ▼
     │              │            │           │      LaneFeature
     │              │            │           ▼
     │              │            │    ┌──────────────┐
     │              │            │    │ EDLineDetector│
     │              │            │    │ CannyHough    │
     │              │            ▼    └──────────────┘
     │              │      ┌─────────────┐
     │              ▼      │  BirdMap    │
     │          ┌───────── │  - LUT 表   │
     ▼          │          │  - 重映射   │
┌───────────┐   │          └─────────────┘
│ 相机模型  │   │
│ - 去畸变  │   │
└───────────┘   │
                ▼
         ┌──────────────┐
         │ MapGenerator │
         │ - IPM 参数   │
         │ - ROI 分区   │
         └──────────────┘
```

#### **3.3.2 核心接口**

```cpp
class BirdLaneDetector : public MapGenerator, public LaneDetector {
public:
    // 初始化
    bool init(const std::set<CameraID>& calib_cam_ids);

    // 执行检测
    bool run(const cv::Mat& raw_image,
             Frame* frame,
             cv::Mat* whole_bird_image) const;

    // 可视化绘制
    void draw(const Frame& frame,
              const Eigen::Isometry3f& new_Tbc,
              cv::Mat& whole_bird_image) const;

private:
    const calibration::common::LaneFrontendParam options_;
    const calibration::common::CarPtr car_ptr_;
};
```

#### **3.3.3 IPM (逆透视变换)**

```cpp
// IPM 变换矩阵计算
H_ipm = K * R * K⁻¹

其中:
- K: 相机内参矩阵
- R: 旋转矩阵 (将地平面变换为平行于图像平面)
- K⁻¹: 内参矩阵的逆

// 查找表生成
void init_inverse_project_mat(cv::Mat& inverse_project_map) const {
    // 预计算每个像素点对应的地面坐标
    for (int v = 0; v < height; v++) {
        for (int u = 0; u < width; u++) {
            // 反投影到地面
            cv::Point2f ground_pt = inverse_project_ground(u, v);
            inverse_project_map.at<cv::Point2f>(v, u) = ground_pt;
        }
    }
}
```

### **3.4 后端：VPExtrinsicCalib**

**职责**: 基于灭点理论进行外参初始化和优化。

#### **3.4.1 算法流程**

```
┌─────────────────────────────────────────────────────────────┐
│                    VPExtrinsicCalib                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  输入：BatchObservations (批量观测数据)                     │
│         ↓                                                    │
│  ┌────────────────┐                                        │
│  │ 1. reset()     │ 初始化优化变量                          │
│  └───────┬────────┘                                        │
│          ↓                                                  │
│  ┌────────────────┐                                        │
│  │ 2. init_       │ 外参初始化 (闭式解)                     │
│  │    extrinsic() │   - 灭点计算 (RANSAC)                   │
│  └───────┬────────┘   - 旋转初始化 (2DOF/3DOF)              │
│          ↓            - 平移初始化                          │
│  ┌────────────────┐                                        │
│  │ 3. optimize_   │ 非线性优化 (Ceres)                     │
│  │    extrinsic() │   - 添加残差因子                       │
│  └───────┬────────┘   - 求解优化问题                       │
│          ↓                                                  │
│  输出：CalibResult (标定结果)                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### **3.4.2 灭点计算**

```cpp
// 基于 RANSAC 的灭点计算
static bool compute_vanish_point_ransac(
    const std::vector<Lane_t>& parallel_lanes,  // 平行车道线
    Eigen::Vector3f& vanish_point,               // 输出灭点
    std::vector<size_t>& inliers,                // 内点索引
    const float max_distance_meters,             // 最大距离阈值
    const float max_condition_num);              // 最大条件数

// 算法步骤:
// 1. 随机选择两条车道线计算交点
// 2. 计算其他车道线到交点的距离
// 3. 统计内点数量
// 4. 迭代获取最优灭点
// 5. 使用最小二乘法精化
```

#### **3.4.3 外参初始化**

```cpp
// 2DOF 旋转初始化 (基于车道线灭点)
static bool compute_2dof_rotation_by_lane_marker_vanish_point(
    const Eigen::Vector3f& ideal_point_in_bird,    // 理想灭点 (鸟瞰图)
    Eigen::Vector3f& vanish_point_in_cam,          // 相机坐标系灭点
    Eigen::Quaternionf& Q_r_c);                    // 输出旋转

// 3DOF 旋转初始化 (基于停止线灭点)
static bool compute_main_3dof_rotation_by_stop_line_vanish_point(
    const Eigen::Vector3f& stop_lines_vanish_point,
    const Eigen::Vector3f& lane_marker_vanish_point,
    Eigen::Quaternionf& Q_r_c);
```

## **4. 优化问题建模**

### **4.1 优化变量**

```cpp
// 优化变量定义
struct Extrinsic {
    std::map<CameraID, Eigen::Quaternionf> Q_r_c;  // 旋转 (四元数)
    std::map<CameraID, Eigen::Vector3f> t_b_r;     // 平移

    // 常量 (固定值)
    std::map<CameraID, Eigen::Quaterniond> Q_b_r_const;
    std::map<CameraID, Eigen::Vector3d> t_b_r_const;
};
```

### **4.2 优化因子 (Factor)**

#### **4.2.1 因子类型**

```
┌────────────────────────────────────────────────────────────┐
│                    优化因子类型                             │
├────────────────────┬───────────────────────────────────────┤
│ LinesParallelFactor│ 车道线平行因子                         │
│                    │ 约束：同一车道的左右车道线平行          │
├────────────────────┼───────────────────────────────────────┤
│ LanesEqualWidth    │ 车道线等宽因子                         │
│ Factor             │ 约束：车道宽度恒定                     │
├────────────────────┼───────────────────────────────────────┤
│ LineCoaxisFactor   │ 共轴因子                               │
│                    │ 约束：车道线在同一平面上                │
├────────────────────┼───────────────────────────────────────┤
│ EndPointsCoin      │ 端点重合因子                           │
│ Factor             │ 约束：相邻相机重叠区域车道线端点重合    │
└────────────────────┴───────────────────────────────────────┘
```

#### **4.2.2 因子数学表达**

**LinesParallelFactor (车道线平行因子)**:

```cpp
template <typename T>
bool operator()(const T* const rotation_r_c, T* residual) const {
    // 将相机坐标系下的车道线变换到车身坐标系
    auto line_in_body_1 = TransformLine2(line_in_cam_1_, R_r_c, ...);
    auto line_in_body_2 = TransformLine2(line_in_cam_2_, R_r_c, ...);

    // 计算上下边界交点的 Y 坐标差
    residual[0] = (upper_intersection_1.y() - upper_intersection_2.y()) -
                  (lower_intersection_1.y() - lower_intersection_2.y());

    return true;
}

// 理想情况下 residual[0] = 0 (平行)
```

**LanesEqualWidthFactor (车道线等宽因子)**:

```cpp
// 约束：左右车道线宽度相等
residual = width_left - width_right
```

**LineCoaxisFactor (共轴因子)**:

```cpp
// 约束：车道线在同一个平面上
residual = distance(line, plane)
```

### **4.3 优化问题构建**

```cpp
// 优化问题构建流程
ceres::Problem problem;
ceres::LossFunction* loss_function = new ceres::HuberLoss(1.0);

// 添加残差因子
for (const auto& [cam_id, lanes] : observations) {
    // 1. 共轴因子
    for (const auto& line : lines) {
        problem.AddResidualBlock(
            LineCoaxisFactor::CreateAutoDiffCostFunction(
                weight_coaxis, line, ...),
            loss_function,
            Qrc_arr);  // 优化变量
    }

    // 2. 平行因子
    for (size_t i = 0; i < lines.size(); i++) {
        for (size_t j = i + 1; j < lines.size(); j++) {
            problem.AddResidualBlock(
                LinesParallelFactor::CreateAutoDiffCostFunction(
                    weight_parallel, lines[i], lines[j], ...),
                loss_function,
                Qrc_arr);
        }
    }

    // 3. 等宽因子
    for (const auto& left_lane : left_lanes) {
        for (const auto& right_lane : right_lanes) {
            problem.AddResidualBlock(
                LanesEqualWidthFactor::CreateAutoDiffCostFunction(
                    width_weight, left_lane, right_lane, ...),
                loss_function,
                Qrc_arr);
        }
    }
}

// 求解
ceres::Solver::Options options;
options.max_num_iterations = 100;
options.linear_solver_type = ceres::SPARSE_SCHUR;
ceres::Solve(options, &problem, &summary);
```

### **4.4 优化策略**

#### **4.4.1 分阶段优化**

```
Stage 1: 2DOF 优化 (主相机)
  - 优化变量：rotation (roll, pitch)
  - 固定：translation, yaw

Stage 2: 3DOF 优化 (主相机)
  - 优化变量：rotation (roll, pitch, yaw)
  - 固定：translation

Stage 3: 6DOF 优化 (全相机联合)
  - 优化变量：rotation + translation
  - 所有相机联合优化
```

#### **4.4.2 优化配置**

```cpp
struct OptimizationProblemOptions {
    // 权重配置
    double line_coaxis_weight = 1.0;
    double lines_parallel_weight = 1.0;
    double lanes_equal_width_weight = 0.1;
    double end_points_coin_weight = 1.0;

    // 求解器配置
    int max_num_iterations = 100;
    double function_tolerance = 1e-6;
    double parameter_tolerance = 1e-8;

    // 优化阶段配置
    bool optimize_rotation = true;
    bool optimize_translation = false;
};
```

## **5. 数据流与状态机**

### **5.1 标定状态机**

```
┌─────────────────────────────────────────────────────────────┐
│                   标定状态流转图                             │
│                                                             │
│     ┌──────┐   start()   ┌──────────────┐                  │
│     │ IDLE │ ──────────> │ DATA_RECORDING │                │
│     └──────┘            └───────┬──────┘                  │
│        ▲                        │                          │
│        │             采集足够数据│                          │
│        │                        ▼                          │
│     ┌──────┐  失败/停止  ┌──────────────┐                  │
│     │FAILED│ <───────── │ LANE_DETECTION │                 │
│     └──────┘            └───────┬──────┘                  │
│        ▲                        │                          │
│        │              特征提取完成│                          │
│        │                        ▼                          │
│     ┌──────┐  失败/停止  ┌─────────────────┐               │
│     │PAUSED│ <───────── │ EXTRINSIC_CALIBRATION│            │
│     └──────┘            └────────┬────────┘               │
│                                  │                          │
│                        标定成功验证通过│                       │
│                                  ▼                          │
│                          ┌──────────────┐                  │
│                          │    FINISH    │                  │
│                          └──────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### **5.2 数据同步流程**

```cpp
void sync_sensors() {
    while (is_running_) {
        // 等待新数据
        std::unique_lock<std::mutex> lock(sync_mutex_);
        condition_sync_.wait(lock);

        // 处理同步任务队列
        while (!sync_job_queue_.empty()) {
            auto job = sync_job_queue_.front();
            sync_job_queue_.pop_front();
            job();  // 执行任务
        }

        // 检查是否可以完成采样
        maybe_finish_sample();
    }
}

void add_sync_job(bool notice, const std::function<void()>& job) {
    {
        std::lock_guard<std::mutex> lock(sync_mutex_);
        sync_job_queue_.push_back(job);
    }
    if (notice) {
        condition_sync_.notify_one();
    }
}
```

## **6. 质量控制与验证**

### **6.1 数据质量检查**

```cpp
// 车速检查
bool check_vehicle_speed(const VehicleSpeedData& speed) {
    // 速度阈值检查
    if (speed.linear_vel > max_speed_threshold ||
        speed.linear_vel < min_speed_threshold) {
        return false;
    }

    // 角速度检查
    if (std::abs(speed.angular_vel) > max_yaw_rate_threshold) {
        return false;
    }

    return true;
}

// 特征质量检查
bool check_lane_quality(const LaneFeature& feature) {
    // 车道线数量检查
    if (feature.lanes.size() < min_lane_count) {
        return false;
    }

    // 车道线长度检查
    for (const auto& lane : feature.lanes) {
        if (lane.length() < min_lane_length) {
            return false;
        }
    }

    return true;
}
```

### **6.2 标定结果验证**

```cpp
ErrorCode check_calibration_result() {
    // 1. 候选解筛选
    calculate_optimal_result(filter_threshold);

    // 2. 与参考外参对比
    for (const auto& [cam_id, result] : calib_results_) {
        double rotation_diff = calculate_angle_diff(
            result.Q_b_c, ref_extrinsic_[cam_id].rotation());
        double translation_diff = (result.t_b_c -
            ref_extrinsic_[cam_id].translation()).norm();

        if (rotation_diff > max_rotation_diff ||
            translation_diff > max_translation_diff) {
            return ErrorCode::ALG_CALIB_RESULT_VERIFY_FAILED;
        }
    }

    // 3. IPM 拼接验证
    if (!verify_ipm_stitching()) {
        return ErrorCode::ALG_CALIB_RESULT_VERIFY_FAILED;
    }

    return ErrorCode::NO_ERROR;
}
```

### **6.3 错误码定义**

```cpp
enum class ErrorCode {
    NO_ERROR = 0,

    // 系统相关
    SYS_ERROR = 1000,
    SYS_LOGIC_ERROR = 1001,
    SYS_NO_CAMERA_CONFIG_FOUND = 1002,
    SYS_CALIB_CFG_PARSE_FAILED = 1003,
    SYS_CALIBRATOR_TIMEOUT = 1004,

    // 传感器相关
    SENSOR_NO_CAMERA_DATA = 2001,
    SENSOR_NO_WHEEL_SPEED_DATA = 2002,

    // 用户相关
    USER_TRIGGER_ID_INVALID = 3001,
    USER_VEHICLE_OVER_SPEED = 3002,
    USER_VEHICLE_STATIC_TOO_LONG = 3003,
    USER_CALIB_DATASET_LESS = 3004,
    USER_CALIBRATION_CANCELED = 3005,

    // 算法相关
    ALG_FRONTEND_FEATURE_LESS = 4001,
    ALG_BACKEND_SOLVE_FAILED = 4002,
    ALG_CALIB_RESULT_VERIFY_FAILED = 4003
};
```

## **7. 配置系统**

### **7.1 配置参数层次**

```
OnlineCalibrationConfig
├── frontend_param (前端参数)
│   ├── bird_generation_param (鸟瞰图生成参数)
│   │   ├── ipm_resolution
│   │   ├── ipm_distance_range
│   │   └── roi_zones
│   └── lane_detection_param (车道线检测参数)
│       ├── edge_threshold
│       ├── line_min_length
│       └── merge_distance
├── backend_param (后端参数)
│   ├── frames_splitter_options (帧分割选项)
│   ├── closed_form_solution_options (闭式解选项)
│   └── optimization_problem_options (优化问题选项)
└── scheduler_param (调度器参数)
    ├── sampling_distance_threshold
    ├── max_calibration_time
    └── speed_thresholds
```

### **7.2 关键配置项**

```protobuf
// Proto 配置示例
message OnlineCalibrationConfig {
    // 前端配置
    LaneFrontendParam frontend_param = 1;

    // 后端配置
    CalibBackendParam backend_param = 2;

    // 调度器配置
    SchedulerParam scheduler_param = 3;

    // 质量阈值
    QualityThresholds quality_thresholds = 4;
}

message OptimizationProblemOptions {
    // 因子权重
    double line_coaxis_weight = 1;
    double lines_parallel_weight = 2;
    double lanes_equal_width_weight = 3;
    double end_points_coin_weight = 4;

    // 优化配置
    bool optimize_rotation = 5;
    bool optimize_translation = 6;
    int32 max_iterations = 7;
}
```

## **8. 性能与资源**

### **8.1 性能指标**

<table>
<tr>
<td>指标<br/></td><td>目标值<br/></td><td>说明<br/></td></tr>
<tr>
<td>单帧处理时间<br/></td><td>< 50ms<br/></td><td>包含 IPM+ 车道线检测<br/></td></tr>
<tr>
<td>优化求解时间<br/></td><td>< 5s<br/></td><td>完整 6DOF 优化<br/></td></tr>
<tr>
<td>内存占用<br/></td><td>< 500MB<br/></td><td>峰值内存<br/></td></tr>
<tr>
<td>标定总时间<br/></td><td>< 5min<br/></td><td>正常行驶条件<br/></td></tr>
</table>

### **8.2 线程模型**

```
Main Thread (接口线程)
  │
  ├── image_callback() → 图像数据入队
  └── wheel_speed_callback() → 车速数据入队

Sync Thread (数据同步线程)
  │
  ├── sync_sensors() → 数据同步
  ├── add_sync_job() → 任务分发
  └── maybe_finish_sample() → 采样检查

Lane Detection Thread Pool (车道线检测线程池)
  │
  └── BirdLaneDetector::run() → 特征提取

Optimization Thread Pool (优化线程池)
  │
  └── run_optimization() → 外参优化
```

### **8.3 资源管理**

```cpp
// 线程池管理
std::unique_ptr<ThreadPool> thread_pool_lane_detection_;
std::unique_ptr<ThreadPool> thread_pool_optimization_;

// 数据队列管理
std::map<CameraID, FrameQueue> lane_feature_frame_;
std::map<double, VehicleSpeedData> vechile_speed_data_;

// 内存优化
// - 使用对象池复用 Frame 对象
// - 图像数据零拷贝传递
// - LUT 表预计算共享
```

## **9. 扩展点**

### **9.1 新增前端检测器**

```cpp
// 继承 LaneDetector 接口
class CustomLaneDetector : public LaneDetector {
public:
    bool detect(const cv::Mat& bird_image,
                std::map<LaneSide, LaneFeature>& features) override {
        // 自定义车道线检测逻辑
        return true;
    }
};
```

### **9.2 新增优化因子**

```cpp
// 自定义 Ceres Factor
class CustomFactor {
public:
    static ceres::CostFunction* CreateAutoDiffCostFunction(
        const double weight,
        const Eigen::Vector3d& observation) {
        return new ceres::AutoDiffCostFunction<
            CustomFactor, 1, 4>(new CustomFactor(weight, observation));
    }

    template <typename T>
    bool operator()(const T* const rotation_r_c, T* residual) const {
        // 自定义残差计算
        residual[0] = ...;
        return true;
    }
};
```

### **9.3 新增标定模式**

```cpp
// 扩展 CalibrationType
enum class CalibrationType {
    UNKNOWN = 0,
    AVM = 1,      // 环视标定
    WIDES = 2,    // 广角相机标定
    ALL = 3,      // 全相机标定
    CUSTOM = 4    // 自定义标定模式
};
```

## **10. 调试与可视化**

### **10.1 日志系统**

```cpp
// 日志级别
MLOG(ONLINE_CALIB, INFO) << "标定流程启动";
MLOG(ONLINE_CALIB, WARNING) << "车速超过阈值";
MLOG(ONLINE_CALIB, ERROR) << "优化求解失败";

// 性能统计
MLOG(ONLINE_CALIB, PERF) << "单帧处理时间："
                         << timer.elapsed_ms() << "ms";
```

### **10.2 可视化工具**

```cpp
class Visualization {
public:
    // 绘制车道线特征
    void draw_lane_features(const Frame& frame, cv::Mat& image);

    // 绘制 IPM 拼接结果
    void draw_ipm_stitching(const std::vector<cv::Mat>& ipm_images,
                            cv::Mat& output);

    // 绘制标定结果对比
    void draw_calibration_result(const CalibResult& result,
                                 const CalibResult& reference,
                                 cv::Mat& output);
};
```

### **10.3 调试数据记录**

```cpp
// 录制配置
struct DebugConfig {
    bool save_raw_images = true;
    bool save_bird_images = true;
    bool save_lane_features = true;
    bool save_optimization_log = true;
    std::string output_directory = "/tmp/online_calib_debug";
};
```
