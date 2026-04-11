# 简历项目知识点汇总

> 生成日期：2026-04-09
> 基于简历：窦步源 - 标定算法工程师 (7 年 + 自动驾驶/融合算法/环视标定系统经验)

---

## 目录

### 第一部分：上海比亚迪有限公司 (2024.04 - 至今)
1. [AVM 影像渲染开发](#1-avm 影像渲染开发)
2. [AVM 影像标定功能开发](#2-avm 影像标定功能开发)
3. [标定云端质检功能开发](#3-标定云端质检功能开发)
4. [高精地图车道线与相机配准](#4-高精地图车道线与相机配准)
5. [3DGS-Calib 神经渲染与在线联合标定系统](#5-3dgs-calib 神经渲染与在线联合标定系统)

### 第二部分：华人运通控股有限公司 (2022.05 - 2024.02)
6. [多传感器融合车位关键信息提取](#6-多传感器融合车位关键信息提取)
7. [基于单帧 Freespace 的障碍物边界提取与跟踪](#7-基于单帧 freespace 的障碍物边界提取与跟踪)
8. [基于概率累计的多源融合 Costmap 构建](#8-基于概率累计的多源融合 costmap 构建)
9. [基于 Ti OpenVX 的系统性能深度优化](#9-基于 ti openvx 的系统性能深度优化)

### 第三部分：上海欧菲智能车联科技有限公司 (2018.07 - 2022.05)
10. [超声/毫米波车位检测 (SPLD) 与空间车位研发](#10-超声毫米波车位检测 spld 与空间车位研发)
11. [超声/毫米波紧急制动 (MEB) 功能开发](#11-超声毫米波紧急制动 meb 功能开发)
12. [实车调试程序与运动模型标定工具](#12-实车调试程序与运动模型标定工具)

---

## 第一部分：上海比亚迪有限公司 (2024.04 - 至今)

### 1. AVM 影像渲染开发

**时间**：2024.04 - 2025.01

**背景**：开发智能座舱 360 全景影像功能，提升车载视觉交互体验。

#### 知识点 1.1：OpenGL 渲染流程

**完整渲染管线**：
```
顶点数据 → 顶点着色器 → 图元装配 → 光栅化 → 片段着色器 → 测试/混合 → 帧缓冲
```

| 阶段 | 说明 |
|------|------|
| **VBO** | 顶点缓冲对象，存储顶点数据（位置、法线、UV、颜色等） |
| **VAO** | 顶点数组对象，记录 VBO 格式和状态 |
| **顶点着色器** | 处理每个顶点，执行坐标变换（局部→世界→视图→裁剪空间） |
| **图元装配** | 将顶点组装成点、线、三角形等图元 |
| **裁剪** | 剔除视锥体外的图元 |
| **光栅化** | 将图元转换为像素片段 (Fragment) |
| **片段着色器** | 计算每个片段的最终颜色（纹理采样、光照计算） |
| **深度测试** | 判断片段是否被遮挡 |
| **模板测试** | 控制哪些像素可以被绘制 |
| **混合** | 处理透明效果，与帧缓冲中已有颜色混合 |
| **帧缓冲** | 输出最终图像到屏幕或纹理 |

**关键代码结构**：
```cpp
// 初始化流程
glGenVertexArrays(1, &VAO);
glGenBuffers(1, &VBO);
glBindVertexArray(VAO);
glBindBuffer(GL_ARRAY_BUFFER, VBO);
glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
// 设置顶点属性
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, (void*)0);
glEnableVertexAttribArray(0);

// 渲染循环
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
shader.use();
shader.setMat4("model", modelMatrix);
shader.setMat4("view", viewMatrix);
shader.setMat4("projection", projectionMatrix);
glBindVertexArray(VAO);
glDrawArrays(GL_TRIANGLES, 0, vertexCount);
```

#### 知识点 1.2：glTF 格式优势

| 特性 | glTF 2.0 | FBX | OBJ |
|------|----------|-----|-----|
| **开放性** | 开放标准 (Khronos Group) | Autodesk 私有 | 开放但过时 |
| **PBR 材质** | ✅ 原生支持 (Metallic-Roughness) | ✅ 支持 | ❌ 不支持 |
| **动画支持** | ✅ 完整（节点/骨骼/变形） | ✅ 完整 | ❌ 无 |
| **加载速度** | ⚡ 极快（GPU 就绪格式） | 🐌 需大量解析转换 | 🐌 需解析计算法线 |
| **Web 友好** | ✅ "3D 领域的 JPEG" | ❌ 需转换 | ⚠️ 功能有限 |

**glTF 核心优势**：
1. **GPU 就绪格式**：数据结构与 GPU 内存布局一致，几乎零拷贝加载
2. **PBR 标准**：基于物理的渲染，Metallic-Roughness 工作流
3. **模块化设计**：Buffer/Accessor/Mesh/Material/Texture 分离
4. **扩展机制**：支持自定义扩展（如 KHR_lights_punctual）

#### 知识点 1.3：骨骼动画实现流程

| 术语 | 说明 |
|------|------|
| **骨骼 (Bone)** | 变换矩阵，定义关节位置和方向 |
| **蒙皮 (Skinning)** | 顶点绑定到骨骼，受骨骼影响 |
| **权重 (Weight)** | 顶点对每根骨骼的影响程度（通常最多 4 根） |
| **绑定姿势 (Bind Pose)** | 模型初始状态，骨骼的参考变换 |
| **逆绑定矩阵** | 将顶点从模型空间变换到骨骼空间 |

**实现流程**：
```
1. 加载骨骼层次结构 → 2. 计算逆绑定矩阵 → 3. 提取动画关键帧
       ↓
4. 每帧插值计算骨骼变换 → 5. 构建骨骼变换矩阵数组 → 6. 传入着色器
       ↓
7. 顶点着色器中进行蒙皮计算 → 8. 输出变换后顶点位置
```

**顶点着色器蒙皮计算**：
```glsl
#version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoords;
layout(location = 3) in ivec4 aBoneIndices;
layout(location = 4) in vec4 aBoneWeights;

uniform mat4 uBoneMatrices[MAX_BONES];

void main() {
    // 计算蒙皮变换矩阵
    mat4 skinTransform = mat4(0.0);
    skinTransform += aBoneWeights.x * uBoneMatrices[aBoneIndices.x];
    skinTransform += aBoneWeights.y * uBoneMatrices[aBoneIndices.y];
    skinTransform += aBoneWeights.z * uBoneMatrices[aBoneIndices.z];
    skinTransform += aBoneWeights.w * uBoneMatrices[aBoneIndices.w];

    // 应用蒙皮变换
    vec4 skinPos = skinTransform * vec4(aPos, 1.0);
    gl_Position = uProjection * uView * uModel * skinPos;
}
```

---

### 2. AVM 影像标定功能开发

**时间**：2024.04 - 2025.04

**背景**：研发座舱 360 影像的产线与在线标定算法，确保环视拼接精度。

#### 知识点 2.1：鱼眼相机模型 (Kannala-Brandt)

**从 3D 点到 2D 图像点的投影公式**：
$$
\begin{aligned}
\theta &= \arctan\left(\frac{r}{f}\right) \\
r_d &= f \cdot (\theta + k_2\theta^2 + k_3\theta^3 + k_4\theta^4 + k_5\theta^5) \\
u &= c_u + \frac{x}{r} \cdot r_d \\
v &= c_v + \frac{y}{r} \cdot r_d
\end{aligned}
$$

**坐标变换**：
$$
P_{cam} = R \cdot P_{world} + t
$$

#### 知识点 2.2：BEV 投影变换

**目的**：将鱼眼图像投影到鸟瞰图（BEV）平面，消除畸变影响。

**投影公式**：
$$
P_{BEV} = \frac{1}{m} \cdot \left(R_{yaw} \cdot \begin{bmatrix} x_w \\ y_w \end{bmatrix} + \begin{bmatrix} t_x \\ t_y \end{bmatrix}\right)
$$

其中 $m = 0.01$ 米/像素（BEV 分辨率）。

#### 知识点 2.3：两级角点检测架构

**技术挑战**：鱼眼 180°+ FOV 导致严重径向畸变，棋盘格在图像边缘严重变形。

**解决方案**：采用 BEV→鱼眼两级检测架构：

```
主流程：鱼眼图像 → BEV 投影 → BEV 角点检测 → 反投影 → 鱼眼亚像素优化

回退流程：当 BEV 检测失败时
鱼眼图像 → ROI 内鱼眼直接检测 → 消失点计算 R → 重新 BEV 投影 → BEV 检测
```

**BEV 角点检测 - 四象限卷积核设计**：
- 设计四个象限的卷积核，分别检测左上、右上、左下、右下角
- 通过卷积响应值判断角点位置和类型

**亚像素优化**：
- 在鱼眼图像上直接优化，达到 0.01 像素精度
- 采用最小二乘法拟合角点位置

#### 知识点 2.4：LUT 表生成

**LUT 类型**：
- 2D BEV LUT：用于生成 2D 鸟瞰图
- 3D BEV LUT：用于生成 3D 鸟瞰图
- 单视图/双视图 LUT：用于不同显示模式
- 画中画 LUT：用于 PIP 显示

**生成流程**：
```
角点检测 → 棋盘格组织 → 外参标定 → 生成映射表 → 保存 LUT
```

#### 知识点 2.5：在线道路标定算法

**核心思想**：
```
自然场景特征 (车道线) → 几何约束 → 外参求解
```

**基本假设**：
1. 车道线在 3D 空间中是平行的
2. 车道宽度是恒定的
3. 地面是平面
4. 车辆行驶在平坦路面上

**灭点 (Vanishing Point) 理论**：
- **灭点定义**：空间中一组平行线在图像平面上的投影交点
- **数学推导**：对于方向向量 $d = [dx, dy, dz]^T$ 的平行线族，其灭点位置为：
  $$v = K \cdot R \cdot d$$

**灭点计算算法**：
1. 两直线交点：$v = l_1 \times l_2$ (叉积)
2. RANSAC 灭点估计：随机采样 + 内点验证
3. 最小二乘精化：高斯 - 牛顿法优化

#### 知识点 2.6：车道线提取与优化

**车道线提取**：
- EDLine/Canny 边缘检测
- Hough 变换提取直线

**Ceres 非线性优化**：
- 车道线平行约束因子
- 车道线等宽约束因子
- 共轴优化因子

---

### 3. 标定云端质检功能开发

**时间**：2025.05 - 2026.02

**背景**：在自动化数据生产链路中，识别并修复存在投影偏差的传感器数据。

#### 知识点 3.1：图像分割模型

**OneFormer**：
- 通用图像分割模型，支持语义/实例/全景分割
- 适用于杆子、建筑物等语义分割任务

**SAM3 (Segment Anything Model 3)**：
- 可指定关键词分割目标对象
- 支持实例分割，交互式分割

#### 知识点 3.2：点云分割模型

**PTv3 (Point Transformer v3)**：
- 基于 Transformer 的 3D 点云分割
- 支持大规模场景点云语义分割

#### 知识点 3.3：匹配后处理

**匹配策略**：
- 距离约束：3D 空间距离阈值
- IOU 约束：2D 投影重叠率
- 覆盖率约束：分割区域覆盖比例

#### 知识点 3.4：Ceres 后端优化

**重投影约束**：
- 根据图像分割生成 DT (Distance Transform) 图
- 将点云投影至图中，根据 DT 图插值计算距离
- 最小化重投影距离和

**形状约束 (KL 散度)**：
- 将激光分割的点云拟合凸包
- 点云生成的图像与图像分割的图像按像素点进行 KL 计算
- 最小化 KL 散度值

$$
D_{KL}(P || Q) = \sum_x P(x) \log \frac{P(x)}{Q(x)}
$$

**边缘约束**：
- 使用传统 CV 算法提取图像轮廓
- 基于图像轮廓生成 DT 图
- 提取点云轮廓点集
- 最小化点到图像轮廓的距离

**角度约束 (杆子/立柱)**：
- 对图像的杆子/立柱进行直线拟合
- 最小化点云到直线的距离

#### 知识点 3.5：SuperPoint+LightGlue 特征匹配

**SuperPoint 特征提取**：
```
输入图像 → 共享编码器 (多层卷积) → 分支
                            ├→ 关键点检测头 (65 通道 → NMS → 关键点)
                            └→ 描述子头 (L2 归一化 → 采样)
```

**描述子特性**：
- 维度：256 维
- 归一化：L2 归一化
- 相似度度量：余弦相似度 (点积)

**LightGlue 匹配**：
- 基于 Transformer 的特征匹配网络
- 支持跨视角匹配 (侧视↔俯视)

**特征点对过滤**：
1. 对所有帧进行 SuperPoint+SuperGlue 得到所有特征点对
2. 对所有特征点对进行聚类
3. 类内样本数>15 的聚类认为是鲁棒特征点对

**外参估计**：
- 根据已知平移，构造双向对极误差作为代价函数
- 使用非线性优化和核函数降低异常点影响

---

### 4. 高精地图车道线与相机配准

**时间**：2025.12 - 2026.03

**背景**：解决数据生产过程中高精地图 (HD Map) 与真实图像中车道线不对齐的偏差问题。

#### 知识点 4.1：PVLane 车道线检测系统

**系统架构**：
```
原始图像 → 数据预处理 → ONNX 模型推理 → Mask 后处理 → 轮廓提取 → 坐标转换 → 输出
```

**模型配置**：

| 模型类型 | 输入尺寸 | 使用相机 | 标签数 |
|----------|----------|----------|--------|
| Mono | 544×960 | front_wide/front_narrow/rear | 6 |
| Side | 544×960 | left/right_front/back | 4 |
| Fisheye | 640×960 | surround_* | - |

**标签体系**：
```python
MONO_LABEL_DICT = {
    0: "background",      # 背景
    1: "single_line",     # 单实线
    2: "curb",            # 路沿
    3: "double_line",     # 双黄线
    4: "wide_line",       # 宽线
    5: "slow_line"        # 减速线
}
```

#### 知识点 4.2：RLE 编码与连通性分析

**RLE (Run-Length Encoding)**：
- 用于表示连续相同值的序列
- 一维序列编码：$RLE(S) = [(v_1, l_1), (v_2, l_2), ..., (v_k, l_k)]$

**连通性分析**：
- 基于 RLE 的连通区域提取
- 轮廓扫描与合并

#### 知识点 4.3：坐标转换

**坐标变换链**：
```
图像坐标 → 相机坐标 → VCS(车身坐标)
```

**鱼眼去畸变**：
- 基于 KB 模型的反向投影
- 基于查找表的快速去畸变

#### 知识点 4.4：车道线匹配算法

**匈牙利算法**：
- 跨相机车道线匹配
- 基于空间距离和方向相似性

#### 知识点 4.5：后端优化

**优化目标**：
- 重投影误差最小化
- 车道线连续性约束
- 车道宽度一致性约束

---

### 5. 3DGS-Calib 神经渲染与在线联合标定系统

**时间**：2026.01 - 2026.03

**背景**：复现 3DGS-Calib 论文方案，实现基于 3D Gaussian Splatting 的神经渲染系统与多相机在线外参联合标定。

#### 知识点 5.1：整体架构

```
点云 PCD → 归一化 → HashGrid 编码 → MLP 预测 → 参数激活 → 3DGS 光栅化 → 损失计算
```

**优势**：
- **参数效率高**：MLP 隐式表示场景，避免存储数百万独立高斯参数
- **泛化能力强**：学习到的特征可以泛化到未见视角
- **支持在线标定**：可联合优化相机外参，实现自标定功能

#### 知识点 5.2：HashGrid 编码

**数学表达**：

对于输入点 $x \in [0,1]^3$，HashGrid 编码过程：

**步骤 1：多分辨率网格采样**
$$
b_l = \lfloor b_0 \cdot \alpha^l \rfloor
$$
其中 $b_0 = 16$，$\alpha = 2.0$，$L = 16$ 层

**步骤 2：顶点坐标计算**
$$
v_{l,i} = \text{floor}(b_l \cdot x) + \delta_i
$$

**步骤 3：哈希映射**
$$
h_{l,i} = \left( \prod_{d=0}^{2} \pi_d \oplus v_{l,i,d} \right) \bmod T
$$
其中 $T = 2^{19}$

**步骤 4：特征插值**
$$
f_l(x) = \sum_{i=0}^{7} w_{l,i} \cdot E[h_{l,i}]
$$

**步骤 5：层级拼接**
$$
\text{Enc}_{\text{HashGrid}}(x) = f_0(x) \oplus f_1(x) \oplus \cdots \oplus f_{L-1}(x)
$$

最终输出维度：$16 \times 2 = 32$

**配置参数**：
```json
{
    "otype": "HashGrid",
    "n_levels": 16,
    "n_features_per_level": 2,
    "log2_hashmap_size": 19,
    "base_resolution": 16,
    "per_level_scale": 2.0
}
```

#### 知识点 5.3：MLP 参数预测器

**网络架构**：`32 → 64 → 64 → 11`

```json
{
    "otype": "FullyFusedMLP",
    "activation": "ReLU",
    "n_neurons": 64,
    "n_hidden_layers": 2
}
```

**输出参数分解**：
```
o = [c₀, c₁, c₂, α, s₀, s₁, s₂, q₀, q₁, q₂, q₃]
     └─────┬─────┘ └─┬─┘ └─────┬─────┘ └──────┬──────┘
       color      opacity    scale       rotation
```

| 参数 | 维度 | 物理意义 | 约束条件 |
|------|------|----------|----------|
| color | 3 | RGB 颜色 | [0, 1] |
| opacity | 1 | 不透明度 | [0, 1] |
| scale | 3 | 高斯球三轴半径 | (0, scale_size] |
| rotation | 4 | 旋转四元数 | 单位四元数 \|q\|=1 |

**参数激活函数**：
- `color = sigmoid(·)`
- `opacity = sigmoid(·)`
- `scale = sigmoid(·) × scale_size`
- `rotation = normalize(·)`

#### 知识点 5.4：3DGS 可微光栅化

**渲染流程**：
```
3D 高斯 → 2D 投影 → Alpha Blending → 渲染图像
```

**坐标变换**（世界→相机）：
$$
P_{cam} = V \times P_{world}
$$

**透视投影**（相机→归一化平面）：
$$
u_{norm} = x_{cam} / z_{cam} \\
v_{norm} = y_{cam} / z_{cam}
$$

**投影到像素平面**（内参变换）：
$$
u = f_x \cdot u_{norm} + c_x \\
v = f_y \cdot v_{norm} + c_y
$$

**Alpha Blending**（从前到后）：
$$
w_i = \alpha_i \cdot \exp\left(-\frac{1}{2}(u-\mu')^T \Sigma'^{-1} (u-\mu')\right)
$$
$$
C(u) = \sum c_i \cdot w_i \cdot \prod_{j<i}(1-w_j)
$$

#### 知识点 5.5：ROI 区域损失计算

**ROI 定义**（以相机前广为例）：
- $x_{min} = 0, x_{max} = W$
- $y_{min} = H/2, y_{max} = H \times 0.8$ (图像下半部)

**L1 重建损失**：
$$
L_{l1} = \text{mean}(|I_{roi} - I_{gt\_roi}|)
$$

**Scale 正则化损失**：
$$
L_{scale} = \text{mean}(||s_g||_1) \quad \text{for } g \in G_{roi}
$$

**总损失**：
$$
L = L_{l1} + \lambda_{scale} \times L_{scale}
$$
其中 $\lambda_{scale} = 0.001$

---

## 第二部分：华人运通控股有限公司 (2022.05 - 2024.02)

### 6. 多传感器融合车位关键信息提取

**时间**：2022.06 - 2022.12

**背景**：针对复杂泊车场景，融合超声与视觉信息提取高精度车位元数据（轮挡、路沿、角点）。

#### 知识点 6.1：EMA 平滑算法

**公式**：
$$
v_t = \beta v_{t-1} + (1 - \beta) \theta_t
$$

**展开式**：
$$
v_t = (1-\beta) \cdot (\theta_t + \beta \cdot \theta_{t-1} + \beta^2 \cdot \theta_{t-2} + \cdots + \beta^{t-1} \cdot \theta_1)
$$

**初始值修正**：
$$
v_t = \frac{v_t}{1 - \beta^t}
$$

**应用**：平滑视觉检测结果，结合超声 DE/CE 值动态修正轮挡与路沿位置。

#### 知识点 6.2：Costmap 融合

**融合策略**：
- 视觉入口角点与超声障碍物特征匹配
- 精准调整泊车最终位姿 (Endpose)

---

### 7. 基于单帧 Freespace 的障碍物边界提取与跟踪

**时间**：2022.12 - 2023.03

#### 知识点 7.1：DBSCAN 聚类算法

**算法流程**：
1. 定义 Eps (邻域半径) 与 MinPts (最小点数)
2. 依次访问所有的点，如果已被访问则跳过，否则查找半径为 Eps 内的所有点
   - 如果点数 < MinPts，认为是噪点
   - 如果点数 >= MinPts，认为是核心点
3. 依次访问邻域内的所有点，递归扩展，直到所有点都被遍历

**优化**：
- 使用 FLANN 最近邻搜索加速
- 使用 `std::unordered_set` 记录已访问点

#### 知识点 7.2：DP (Douglas-Peucker) 抽稀算法

**算法简介**：
1. 找出有序点集上离首末点连线最远的点
2. 如果此点距离直线的距离大于阈值，则递归处理这两部分
3. 否则删除中间所有点

**点到直线距离公式**：
$$
D = \frac{|Ax_0 + By_0 + C|}{\sqrt{A^2 + B^2}}
$$

**应用**：针对立柱与墙角提取 90° 折角特征。

#### 知识点 7.3：粒子滤波 (Particle Filter)

**权重采样**：
```cpp
std::uniform_real_distribution<double> distribution(0.0, 1.0);
double index = distribution(generator_) * num_particles_;
```

**马氏距离**：
$$
D_M(\mathbf{x}) = \sqrt{(\mathbf{x} - \boldsymbol{\mu})^T \boldsymbol{\Sigma}^{-1} (\mathbf{x} - \boldsymbol{\mu})}
$$

**协方差计算**：
$$
\Sigma = \frac{1}{N-1} \sum (\mathbf{x} - \boldsymbol{\mu})(\mathbf{x} - \boldsymbol{\mu})^T
$$

**应用场景**：针对行人采用粒子滤波 (PF) 跟踪。

#### 知识点 7.4：卡尔曼滤波 (KF)

**CV 模型 (匀速)**：
- 状态量：$\mathbf{x}(t) = (x, y, v_x, v_y)$
- 状态转移矩阵：
$$
A = \begin{bmatrix}
1 & 0 & t & 0 \\
0 & 1 & 0 & t \\
0 & 0 & 1 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

**CA 模型 (匀加速)**：
- 状态量：$\mathbf{x}(t) = (x, y, v_x, v_y, a_x, a_y)$
- 状态转移矩阵：
$$
A = \begin{bmatrix}
1 & 0 & \Delta t & 0 & \frac{1}{2}\Delta t^2 & 0 \\
0 & 1 & 0 & \Delta t & 0 & \frac{1}{2}\Delta t^2 \\
0 & 0 & 1 & 0 & \Delta t & 0 \\
0 & 0 & 0 & 1 & 0 & \Delta t \\
0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}
$$

**KF 公式**：
- 预测：
$$
\hat{x}_{k|k-1} = F_k \hat{x}_{k-1|k-1} + B_k u_k
$$
$$
P_{k|k-1} = F_k P_{k-1|k-1} F_k^T + Q_k
$$

- 更新：
$$
K_k = P_{k|k-1} H_k^T (H_k P_{k|k-1} H_k^T + R_k)^{-1}
$$
$$
\hat{x}_{k|k} = \hat{x}_{k|k-1} + K_k (z_k - H_k \hat{x}_{k|k-1})
$$
$$
P_{k|k} = (I - K_k H_k) P_{k|k-1}
$$

**应用场景**：针对立柱与墙角采用卡尔曼滤波 (KF) 进行状态估计。

#### 知识点 7.5：EKF (扩展卡尔曼滤波)

**CTRV 模型 (匀速转弯)**：
- 状态量：$\mathbf{X} = [x, y, v, \theta, \omega]^T$
- 状态转移方程：
$$
\mathbf{X} = \begin{bmatrix}
x_k + \frac{v_k}{\omega}[\sin(\omega \Delta t + \theta) - \sin(\theta)] \\
y_k + \frac{v_k}{\omega}[-\cos(\omega \Delta t + \theta) + \cos(\theta)] \\
v_k \\
\omega \Delta t + \theta \\
\omega
\end{bmatrix}
$$

**雅可比矩阵**：
$$
J_F = \begin{bmatrix}
1 & 0 & \frac{1}{\omega}[\sin(\omega \Delta t + \theta) - \sin(\theta)] & \frac{v}{\omega^2}[-\cos(\omega \Delta t + \theta) + \cos(\theta)] \\
0 & 1 & \frac{1}{\omega}[-\cos(\omega \Delta t + \theta) + \cos(\theta)] & \frac{v}{\omega^2}[\sin(\omega \Delta t + \theta) - \sin(\theta)] \\
0 & 0 & 1 & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

---

### 8. 基于概率累计的多源融合 Costmap 构建

**时间**：2023.03 - 2024.02

#### 知识点 8.1：概率累加模型

**融合策略**：
- 融合四路鱼眼相机点云与超声 Map 值
- 基于距离衰减的概率累加模型构建 Costmap

**置信度权重**：
- 设定异构传感器置信度权重
- 超声在障碍物占有与空闲概率判断上具备更高优先级

---

### 9. 基于 Ti OpenVX 的系统性能深度优化

**时间**：2022.09 - 2024.02

**背景**：针对 TDA4 平台计算资源受限问题，降低算法模块的 CPU 负载。

#### 知识点 9.1：OpenVX 框架

**核心概念**：
- **Graph**：计算图，描述算法流程
- **Node**：图中的计算节点
- **Kernel**：自定义核函数，在 DSP/C6x 上执行
- **Data Object**：数据对象，用于节点间数据传递

**优化策略**：
1. 基于 OpenVX 框架重构算法逻辑
2. 自定义核函数 (Kernel) 将 A72 核心的计算压力卸载至 DSP (C6x)
3. 应用 DMA 传输与 Ping-Pong 缓存机制优化数据搬运效率
4. 提升核函数并行执行性能

#### 知识点 9.2：DMA 与 Ping-Pong 缓存

**DMA 传输**：
- 直接内存访问，不占用 CPU 资源
- 异步数据传输，可与计算重叠

**Ping-Pong 缓存**：
- 双缓冲机制，一组缓冲用于输入，另一组用于输出
- 交替使用，实现流水线并行

---

## 第三部分：上海欧菲智能车联科技有限公司 (2018.07 - 2022.05)

### 10. 超声/毫米波车位检测 (SPLD) 与空间车位研发

**时间**：2019.08 - 2022.05

**背景**：开发基于多传感器融合的空间车位检测系统，解决无标线场景下的自动泊车难题。

#### 知识点 10.1：Costmap 构建

**Bresenham 算法**：
- 用于在栅格地图上绘制直线
- 基于多传感器数据建立高精度 Costmap（代价地图）

#### 知识点 10.2：车位检测算法

**双阶段算法**：
1. **巡库阶段**：搜索潜在车位区域
2. **跟踪阶段**：持续跟踪已检测车位

**关键步骤**：
- 车位角点检测、过滤、匹配
- 路沿检测
- 滑动窗口算法精确锁定泊车终止位置 (Endpose)

**成果指标**：
- 垂直车位：车宽 +0.8m
- 水平车位：车长 +1m
- 斜车位：车宽 +1.2m

---

### 11. 超声/毫米波紧急制动 (MEB) 功能开发

**时间**：2019.01 - 2021.12

**背景**：通过多雷达融合感知预防泊车过程中的碰撞风险，实现主动安全制动。

#### 知识点 11.1：数据融合

**数据源**：
- UPA/APA 定位点信息
- 毫米波雷达点云

**数据过滤算法**：
- 剔除杂点
- 基于车辆位姿、速度、前轮偏向角推算运动轨迹

#### 知识点 11.2：控制输出

**实时计算**：
- 障碍物距离计算
- 刹车量与扭矩控制信号输出

#### 知识点 11.3：骤变点辅助定位

**创新设计**：
- 建立三角定位点与侧面雷达定位点
- 骤变点辅助定位解决盲区问题

**成果**：95% 场景下自动刹停，制动平滑，驾驶体验优异。

---

### 12. 实车调试程序与运动模型标定工具

**时间**：2018.07 - 2019.02

#### 知识点 12.1：LCM 通信协议

**开发内容**：
- 基于 LCM 协议开发控制器与 PC 的通信链路
- 利用 Qt 构建实时可视化界面
- 支持数据本地存储与故障回溯

#### 知识点 12.2：坐标系转换

**IMU 与 RTK**：
- 采集经纬度并转 UTM 坐标系
- 拟合前轮偏向角与方向盘转角的非线性关系

---

## 附录：通用技能与工具

### A. 编程语言
- C/C++、Python

### B. 开发平台
- TI TDA2/TDA4
- OpenVX
- OpenGL
- ORIN

### C. 工具链
- Linux
- Git
- Ceres Solver (非线性优化)
- ONNX Runtime (模型推理)

### D. 算法库
- DBSCAN (聚类)
- 粒子滤波/卡尔曼滤波
- DP 算法 (抽稀)
- LUT 表生成
- 非线性优化
- 模型部署

### E. 传感器
- 超声/毫米波雷达
- 鱼眼摄像头
- LiDAR
- IMU
- RTK

### F. 专利与认证
- RHCSA、RHCE
- 10 篇专利

---

> 本文档根据简历项目经历整理，涵盖所有核心知识点与技术细节。
