---
title: "PVLane 推理与后处理"
category: perception
tags:
  - lane-detection
  - rle-encoding
  - connectivity-analysis
  - contour-extraction
  - coordinate-transform
  - hungarian-matching
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/lane_detection/pvlane-inference-postprocess.md
---

# PVLane 推理与后处理

## 一、系统概述

PVLane 后处理模块是车道线检测系统的核心组件，负责将模型输出的语义分割 Mask 转换为结构化的车道线轮廓数据。处理流程包含 RLE 编码、连通性分析、轮廓提取、坐标转换和跨相机匹配等关键步骤。

### 1.1 处理流水线

```
+--------------+      +--------------+      +--------------+
|  原始图像     |      |  相机标定参数  |      |  配置文件     |
|  (RGB/BGR)   |      |  (内参/外参)  |      |  (阈值/参数)  |
+------+-------+      +------+-------+      +------+-------+
       |                     |                     |
       +---------------------+---------------------+
                             |
                +------------v------------+
                |   数据加载与预处理        |
                |  - 图像归一化            |
                |  - 裁剪与缩放            |
                +------------+------------+
                             |
                +------------v------------+
                |   ONNX模型推理           |
                |  - Mono/Side/Fisheye    |
                |  - 批处理优化            |
                +------------+------------+
                             |
                +------------v------------+
                |   Mask后处理             |
                |  - RLE编码              |
                |  - 连通性分析            |
                +------------+------------+
                             |
                +------------v------------+
                |   轮廓提取               |
                |  - RLE扫描              |
                |  - 轮廓合并/过滤/稀疏化   |
                +------------+------------+
                             |
                +------------v------------+
                |   坐标转换               |
                |  - 图像->相机->VCS      |
                |  - 鱼眼去畸变            |
                +------------+------------+
                             |
                +------------v------------+
                |   车道线匹配（可选）      |
                |  - 跨相机匹配            |
                |  - 匈牙利算法            |
                +------------+------------+
                             |
                +------------v------------+
                |   结果输出               |
                |  - JSON格式             |
                |  - 可视化结果            |
                +-------------------------+
```

## 二、模型推理

### 2.1 输入预处理

**图像归一化** 使用 ImageNet 统计量：

$$
x_{\text{normalized}} = \frac{x - \mu}{\sigma}
$$

其中 $\mu = [123.675, 116.28, 103.53]$，$\sigma = [58.395, 57.12, 57.375]$。

**输入尺寸配置：**

| 模型类型 | 输入尺寸 (H x W) | 使用相机 |
|----------|------------------|----------|
| Mono | 544 x 960 | front_wide, front_narrow, rear |
| Side | 544 x 960 | left_front, right_front, left_back, right_back |
| Fisheye | 640 x 960 | surround_front, surround_left, surround_right, surround_rear |

## 三、RLE 编码与连通性分析

### 3.1 RLE 编码原理

**RLE (Run-Length Encoding)** 是一种简单的无损压缩算法，用于表示连续相同值的序列。

对于一维序列 $S = [s_1, s_2, \ldots, s_n]$，RLE 将其编码为：

$$
\text{RLE}(S) = [(v_1, l_1), (v_2, l_2), \ldots, (v_k, l_k)]
$$

其中 $v_i$ 为第 $i$ 段的值，$l_i$ 为第 $i$ 段的长度（连续相同值的数量）。

**二维图像的 RLE 编码**按行进行：

```
原始图像:
Row 0: [0, 0, 1, 1, 1, 2, 2]
Row 1: [0, 0, 0, 1, 1, 2, 2]

RLE编码:
Row 0: [(0,2), (1,3), (2,2)]
Row 1: [(0,3), (1,2), (2,2)]
```

**优势：** 压缩率高（对于稀疏 mask）、快速连通性分析、内存占用小。

### 3.2 RLE 数据结构

```cpp
struct RLEList {
    uint64_t label;        // 像素标签
    int y;                 // 行号
    int xstart;            // 起始列
    int xend;              // 结束列
    RLEList *next;         // 下一个RLE段

    // 坐标信息（填充后）
    cv::Point2f img_raw_st, img_raw_ed, img_raw_c;  // 原始图像坐标
    cv::Point2f img_st, img_ed, img_c;              // 变换后图像坐标
    cv::Point2f ground_st, ground_ed, ground_c;     // 地面坐标
};
```

### 3.3 8 邻域连通性分析

两个像素 $p_1(x_1, y_1)$ 和 $p_2(x_2, y_2)$ 是 8 邻域连通的，当且仅当：

$$
|x_1 - x_2| \leq 1 \quad \text{且} \quad |y_1 - y_2| \leq 1
$$

且它们具有相同的标签值。

**8 邻域重叠判断：** 两个 RLE 段 $r_1 = [\text{xstart}_1, \text{xend}_1]$ 和 $r_2 = [\text{xstart}_2, \text{xend}_2]$ 在 8 邻域内重叠的条件：

$$
\max(\text{xstart}_1 - 1, 0) \leq \text{xend}_2 + 1 \quad \text{且} \quad \max(\text{xstart}_2 - 1, 0) \leq \text{xend}_1 + 1
$$

**算法流程：**

1. **初始化**: 创建 RLE 段列表，为每个 RLE 段分配唯一 ID
2. **区域生长**: 遍历每一行，检查上一行中 8 邻域重叠且标签相同的 RLE 段，合并区域 ID
3. **区域合并**: 使用并查集 (Union-Find) 数据结构合并具有相同根节点的区域
4. **区域过滤**: 过滤面积小于阈值的区域
5. **输出连通区域**

```cpp
int RLEConnectivityAnalysis(ConnectRegion *&regions,
                           int start_y = 0,
                           UniteLabelMap *label_map = nullptr,
                           bool enable_horizon_merge = false) {
    // 1. 创建RLE链表
    RLEList *rle_head = CreateRLEList(mask_data, height, width);
    // 2. 区域生长 (逐行检查 8 邻域连通)
    for (int y = 1; y < height; y++) {
        RLEList *curr = rle_rows[y];
        RLEList *prev = rle_rows[y-1];
        while (curr && prev) {
            if (IsConnected(curr, prev) && curr->label == prev->label) {
                UnionRegions(curr->region_id, prev->region_id);
            }
            if (curr->xend < prev->xend) curr = curr->next;
            else prev = prev->next;
        }
    }
    // 3. 构建连通区域
    regions = BuildConnectedRegions(rle_head);
    // 4. 过滤小区域
    FilterSmallRegions(regions, min_area_threshold);
    return num_regions;
}
```

**连通区域数据结构：**

```cpp
struct ConnectRegion {
    cv::Rect boundbox;          // 外接矩形
    int nArea;                  // 像素数量（面积）
    RLEList *RLEhead;           // 首个RLE段
    RLEList *RLEtail;           // 最后RLE段
    RLELine *linePtr;           // 行指针数组
    ConnectRegion *pre;         // 前驱区域
    ConnectRegion *next;        // 后继区域
};
```

## 四、轮廓提取

### 4.1 扫描策略

根据相机方向采用不同的扫描策略：

- **前视/后视相机**: 垂直扫描 (VERTICAL) -- 适用于纵向车道线
- **左视/右视相机**: 水平扫描 (HORIZONTAL) -- 适用于横向车道线

```
垂直扫描（前视相机）:          水平扫描（侧视相机）:
+-----------+                 +-----------+
| v  v  v  v|                 | >  >  >  >|
| v  v  v  v|                 | >  >  >  >|
| v  v  v  v|                 | >  >  >  >|
+-----------+                 +-----------+
```

### 4.2 垂直扫描算法 (RLEScanEx)

对每个连通区域，按垂直方向（列）扫描，提取轮廓点：

1. 获取区域边界框 $(x_{\min}, x_{\max}, y_{\min}, y_{\max})$
2. 对每列 $x$，收集该列中所有 RLE 段
3. 提取轮廓点：计算 RLE 段的中心点 $(x, y_{\text{center}})$，填充原始图像坐标、变换后坐标和地面坐标

对于 RLE 段 $r = [\text{xstart}, \text{xend}]$ 在行 $y$：

$$
x_{\text{center}} = \frac{\text{xstart} + \text{xend}}{2}, \quad y_{\text{center}} = y
$$

### 4.3 双线轮廓提取

对于 `double_line` 标签，需要提取两条线：

```cpp
void ExtractDoubleContour(RLEList *rle, Contour &contour) {
    int width = rle->xend - rle->xstart + 1;
    int double_line_threshold = 15;  // 像素

    if (width > double_line_threshold) {
        // 提取左线 (25% 位置)
        int left_x = rle->xstart + width * 0.25;
        AddContourPoint(left_x, rle->y, contour.left_line);
        // 提取右线 (75% 位置)
        int right_x = rle->xstart + width * 0.75;
        AddContourPoint(right_x, rle->y, contour.right_line);
    } else {
        // 单线处理: 取中心
        int center_x = (rle->xstart + rle->xend) / 2;
        AddContourPoint(center_x, rle->y, contour);
    }
}
```

### 4.4 轮廓后处理

**轮廓合并 (ContourMerge):** 合并距离过近的轮廓点，减少冗余：

```cpp
void ContourMerge(std::vector<BasicInfoPts> &pts, float merge_threshold) {
    std::vector<BasicInfoPts> merged;
    merged.push_back(pts[0]);
    for (size_t i = 1; i < pts.size(); i++) {
        float dist = Distance(merged.back().pt, pts[i].pt);
        if (dist < merge_threshold) {
            merged.back().pt.x = (merged.back().pt.x + pts[i].pt.x) / 2;
            merged.back().pt.y = (merged.back().pt.y + pts[i].pt.y) / 2;
        } else {
            merged.push_back(pts[i]);
        }
    }
    pts = merged;
}
```

**轮廓过滤 (ContourFilter):** 过滤条件包括：

| 条件 | 默认值 | 说明 |
|------|--------|------|
| 最小宽度 | $40 \times (H/720)$ 像素 | 宽度阈值 |
| VCS 距离 | 6.0 米 | 超出范围过滤 |
| 最小点数 | 5 | 点数太少过滤 |

**轮廓稀疏化 (ContourSparse):** 采用 Douglas-Peucker 简化版算法，减少轮廓点数量并保留关键点：

```cpp
float sparse_threshold = 0.5 * (image_height / 1080.0);
sparse_threshold = std::clamp(sparse_threshold, 0.5f, 1.0f);
```

## 五、坐标转换系统

### 5.1 坐标系定义

| 坐标系 | 原点 | X 轴 | Y 轴 | Z 轴 | 单位 |
|--------|------|------|------|------|------|
| 图像 (Image) | 左上角 | 向右 | 向下 | - | 像素 |
| 相机 (Camera) | 光心 | 向右 | 向下 | 向前 | 米 |
| 车辆 (VCS) | 后轴中心 | 向前 | 向左 | 向上 | 米 |
| 地面 (Ground) | VCS 投影 | 向前 | 向左 | Z=0 | 米 |

### 5.2 相机内参模型

**针孔相机模型：**

$$
\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} =
\frac{1}{Z_c} \mathbf{K} \begin{bmatrix} X_c \\ Y_c \\ Z_c \end{bmatrix}
$$

其中内参矩阵：

$$
\mathbf{K} = \begin{bmatrix}
f_x & 0 & c_x \\
0 & f_y & c_y \\
0 & 0 & 1
\end{bmatrix}
$$

### 5.3 鱼眼相机投影模型

鱼眼相机采用 4 参数等距投影畸变模型：

$$
\theta_d = \theta(1 + k_1\theta^2 + k_2\theta^4 + k_3\theta^6 + k_4\theta^8)
$$

其中 $\theta = \arctan(r)$ 为入射角，$r = \sqrt{x^2 + y^2}$ 为归一化半径。

**投影步骤：**

1. $r = \sqrt{x^2 + y^2}$
2. $\theta = \arctan(r)$
3. $\theta_d = \theta(1 + k_1\theta^2 + k_2\theta^4 + k_3\theta^6 + k_4\theta^8)$
4. $\text{scale} = \theta_d / r$（若 $r > 0$，否则 1.0）
5. $x_d = x \cdot \text{scale}, \; y_d = y \cdot \text{scale}$
6. $u = f_x \cdot x_d + c_x, \; v = f_y \cdot y_d + c_y$

### 5.4 外参变换

外参矩阵 $\mathbf{T}_{\text{cam}}^{\text{vcs}}$ 为 4x4 齐次变换矩阵：

$$
\mathbf{T}_{\text{cam}}^{\text{vcs}} = \begin{bmatrix}
\mathbf{R} & \mathbf{t} \\
\mathbf{0}^T & 1
\end{bmatrix}
$$

坐标变换：

$$
\begin{bmatrix} X_{\text{vcs}} \\ Y_{\text{vcs}} \\ Z_{\text{vcs}} \\ 1 \end{bmatrix} =
\mathbf{T}_{\text{cam}}^{\text{vcs}} \begin{bmatrix} X_{\text{cam}} \\ Y_{\text{cam}} \\ Z_{\text{cam}} \\ 1 \end{bmatrix}
$$

### 5.5 射线投射到地面

给定图像点，找到其在地面 ($Z=0$) 上的投影：

1. **图像坐标 -> 归一化相机坐标**: $\mathbf{x}_n = \mathbf{K}^{-1} [u, v, 1]^T$
2. **鱼眼去畸变** (如适用)
3. **构建射线方向**: $\mathbf{d}_{\text{cam}} = [x_n, y_n, 1]^T$
4. **转换到 VCS**: $\mathbf{d}_{\text{vcs}} = \mathbf{R} \cdot \mathbf{d}_{\text{cam}}$

射线参数方程：

$$
\mathbf{P}(s) = \mathbf{P}_{\text{cam}} + s \cdot \mathbf{d}_{\text{vcs}}
$$

地面约束 ($Z_{\text{vcs}} = 0$)：

$$
t_z + s \cdot d_{\text{vcs},z} = 0 \quad \Rightarrow \quad s = -\frac{t_z}{d_{\text{vcs},z}}
$$

地面坐标：

$$
\begin{cases}
X_{\text{vcs}} = t_x + s \cdot d_{\text{vcs},x} \\
Y_{\text{vcs}} = t_y + s \cdot d_{\text{vcs},y}
\end{cases}
$$

## 六、车道线匹配算法

### 6.1 跨相机共视关系

```
front_wide <-> {left_front, right_front}
rear       <-> {left_back,  right_back}
```

### 6.2 匹配评分

三个匹配维度：

**距离匹配度：**

$$
D_{\text{dist}} = \exp\left(-\frac{\|p_1 - p_2\|^2}{2\sigma_d^2}\right)
$$

其中 $\sigma_d = 0.5$ 米。

**角度匹配度：**

$$
D_{\text{angle}} = \exp\left(-\frac{(\theta_1 - \theta_2)^2}{2\sigma_\theta^2}\right)
$$

其中 $\sigma_\theta \approx 11.5^\circ$。

**重叠度匹配度：**

$$
D_{\text{overlap}} = \frac{|R_1 \cap R_2|}{|R_1 \cup R_2|}
$$

**综合评分：**

$$
\text{Score} = 0.5 \cdot D_{\text{dist}} + 0.3 \cdot D_{\text{angle}} + 0.2 \cdot D_{\text{overlap}}
$$

### 6.3 匈牙利算法

采用匈牙利算法找到最优的一对一匹配方案：

1. 构建代价矩阵：$\text{cost}[i][j] = 1 - \text{Score}(\text{contour}_i, \text{contour}_j)$
2. 调用匈牙利算法求解最优分配
3. 过滤低质量匹配（cost > threshold 的配对移除）

## 七、数据结构

### 7.1 轮廓点结构 (BasicInfoPts)

| 字段 | 类型 | 说明 |
|------|------|------|
| pt | Point2DF | 最终使用坐标（米） |
| pt_rle | cv::Point2f | RLE 扫描得到的坐标（像素） |
| pt_oriimg | cv::Point2f | 原始图像坐标（像素） |
| pt_img | cv::Point2f | 去畸变后坐标（像素） |
| dir | cv::Point2f | 车道线方向向量 |
| label | uint64_t | 统计后的标签 |
| parsing_label | uint64_t | 原始预测标签 |
| conf | float | 置信度 |

### 7.2 相机参数结构 (CameraParams)

| 字段 | 类型 | 说明 |
|------|------|------|
| fx, fy | float | 焦距 |
| cx, cy | float | 主点 |
| k1-k4 | float | 鱼眼畸变系数 |
| extrinsics | cv::Mat | 4x4 变换矩阵 |
| width, height | int | 图像尺寸 |
| type | CameraType | MONO / SIDE / FISHEYE |

## 相关页面

- [PVLane 检测系统架构](./pvlane-system-architecture.md) - 系统整体架构、模型配置、标签字典和 ONNX 推理引擎
- [SuperPoint + LightGlue 特征匹配](./superpoint-lightglue.md) - 基于深度学习的跨视角特征匹配与球面本质矩阵估计
- [云端标定质检方案](./cloud-calibration-qa.md) - 基于图像/点云分割与 Ceres 后端优化的标定质量检验
