# PVLane 模型推理与后处理算法原理详解

> 文档版本: v1.0
> 最后更新: 2026-03-06
> 目标受众: 算法工程师

---

## **目录**

- [1. 系统概述](#1-%E7%B3%BB%E7%BB%9F%E6%A6%82%E8%BF%B0)
- [2. 模型推理流程](#2-%E6%A8%A1%E5%9E%8B%E6%8E%A8%E7%90%86%E6%B5%81%E7%A8%8B)
- [3. 后处理算法详解](#3-%E5%90%8E%E5%A4%84%E7%90%86%E7%AE%97%E6%B3%95%E8%AF%A6%E8%A7%A3)
- [4. 车道线匹配算法](#4-%E8%BD%A6%E9%81%93%E7%BA%BF%E5%8C%B9%E9%85%8D%E7%AE%97%E6%B3%95)
- [5. 数据结构设计](#5-%E6%95%B0%E6%8D%AE%E7%BB%93%E6%9E%84%E8%AE%BE%E8%AE%A1)
- [6. 参数配置与调优](#6-%E5%8F%82%E6%95%B0%E9%85%8D%E7%BD%AE%E4%B8%8E%E8%B0%83%E4%BC%98)
- [7. 关键代码实现](#7-%E5%85%B3%E9%94%AE%E4%BB%A3%E7%A0%81%E5%AE%9E%E7%8E%B0)
- [8. 附录](#8-%E9%99%84%E5%BD%95)

---

## **1. 系统概述**

### **1.1 项目背景**

PVLaneFunction 是一个基于深度学习的车道线检测与后处理系统，支持多种相机类型（前视、侧视、鱼眼），实现从原始图像到车道线轮廓的完整处理流程。

### **1.2 系统架构总览**

```
┌─────────────────────────────────────────────────────────────────┐
│                        PVLane系统架构                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  原始图像     │      │  相机标定参数  │      │  配置文件     │
│  (RGB/BGR)   │      │  (内参/外参)  │      │  (阈值/参数)  │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       └─────────────────────┴─────────────────────┘
                             │
                ┌────────────▼────────────┐
                │   数据加载与预处理        │
                │  - 图像归一化            │
                │  - 裁剪与缩放            │
                └────────────┬────────────┘
                             │
                ┌────────────▼────────────┐
                │   ONNX模型推理           │
                │  - Mono/Side/Fisheye    │
                │  - 批处理优化            │
                └────────────┬────────────┘
                             │
                ┌────────────▼────────────┐
                │   Mask后处理             │
                │  - RLE编码              │
                │  - 连通性分析            │
                └────────────┬────────────┘
                             │
                ┌────────────▼────────────┐
                │   轮廓提取               │
                │  - RLE扫描              │
                │  - 轮廓合并/过滤/稀疏化   │
                └────────────┬────────────┘
                             │
                ┌────────────▼────────────┐
                │   坐标转换               │
                │  - 图像→相机→VCS        │
                │  - 鱼眼去畸变            │
                └────────────┬────────────┘
                             │
                ┌────────────▼────────────┐
                │   车道线匹配（可选）      │
                │  - 跨相机匹配            │
                │  - 匈牙利算法            │
                └────────────┬────────────┘
                             │
                ┌────────────▼────────────┐
                │   结果输出               │
                │  - JSON格式             │
                │  - 可视化结果            │
                └─────────────────────────┘
```

### **1.3 技术栈**

<table>
<tr>
<td>组件<br/></td><td>技术选型<br/></td><td>说明<br/></td></tr>
<tr>
<td>推理引擎<br/></td><td>ONNX Runtime<br/></td><td>跨平台、高性能推理<br/></td></tr>
<tr>
<td>图像处理<br/></td><td>OpenCV<br/></td><td>图像变换、鱼眼校正<br/></td></tr>
<tr>
<td>编程语言<br/></td><td>Python + C++<br/></td><td>Python推理，C++后处理<br/></td></tr>
<tr>
<td>数据格式<br/></td><td>JSON<br/></td><td>标定参数、输出结果<br/></td></tr>
</table>

### **1.4 关键文件路径**

```
pvlane_function/
├── scripts/pvlane/
│   └── pvlane_onnx_infer.py          # Python推理入口
├── src/pvlane/
│   ├── pvlane_data_loader.cpp        # 数据加载与处理
│   └── find_contour.cpp              # 轮廓提取实现
├── include/pvlane/
│   ├── pvlane_data_loader.h
│   ├── find_contour.h
│   └── hobot-adas/
│       ├── modules/lane/common/base/
│       │   └── rle_scan.h            # RLE扫描算法
│       └── utils/
│           ├── camera/camera.h       # 相机模型
│           └── rle/
│               └── rle_connectivity_analysis.h  # RLE连通性分析
└── main.cpp                          # 主程序入口
```

---

## **2. 模型推理流程**

### **2.1 ONNX 推理引擎**

**文件位置:** `scripts/pvlane/pvlane_onnx_infer.py`

**核心类:** `ONNXInferenceEngine`

```python
class ONNXInferenceEngine:
    """单例模式管理ONNX推理会话"""

    _instances = {}  # 按模型路径管理多个实例

    def __init__(self, onnx_path, batch_size=48):
        # 创建ONNX会话
        self.session = ort.InferenceSession(onnx_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
```

**特点:**

- 单例模式，避免重复加载模型
- 支持动态批处理（batch_size=48）
- GPU 加速推理

### **2.2 输入预处理**

#### **2.2.1 图像归一化**

**CustomNormalize 类实现:**

```python
class CustomNormalize:
    """自定义归一化，符合训练时的预处理"""

    mean = [123.675, 116.28, 103.53]   # ImageNet均值
    std = [58.395, 57.12, 57.375]      # ImageNet标准差

    def __call__(self, img):
        img = np.array(img, dtype=np.float32)
        img = (img - self.mean) / self.std
        return img
```

**数学公式:**

$$
x_{normalized} = \frac{x - \mu}{\sigma}
$$

其中:

- $x$: 原始像素值 (0-255)
- $\mu$: 均值向量 $[123.675, 116.28, 103.53]$
- $\sigma$: 标准差向量 $[58.395, 57.12, 57.375]$

#### **2.2.2 图像裁剪（CropTransform）**

用于 rear 和 side 相机，去除无效区域：

```python
class CropTransform:
    """图像裁剪，用于side/rear相机"""

    def __init__(self, crop_offset_y):
        self.crop_offset_y = crop_offset_y

    def __call__(self, img):
        # 裁剪掉顶部无效区域
        return img[int(self.crop_offset_y):, :, :]
```

**裁剪参数:**

- rear 相机: `crop_offset_y = 120 × 0.5037 ≈ 60像素`
- side 相机: `crop_offset_y = 120 × 0.5037 ≈ 60像素`

### **2.3 模型输入输出规格**

#### **2.3.1 输入尺寸配置**

<table>
<tr>
<td>模型类型<br/></td><td>输入尺寸 (H×W)<br/></td><td>使用相机<br/></td></tr>
<tr>
<td>Mono<br/></td><td>544 × 960<br/></td><td>front_wide, front_narrow, rear<br/></td></tr>
<tr>
<td>Side<br/></td><td>544 × 960<br/></td><td>left_front, right_front, left_back, right_back<br/></td></tr>
<tr>
<td>Fisheye<br/></td><td>640 × 960<br/></td><td>surround_front, surround_left, surround_right, surround_rear<br/></td></tr>
</table>

#### **2.3.2 输出格式**

**模型输出:** 语义分割 Mask

- **数据类型:** float32
- **形状:** `[batch_size, height, width]`
- **值范围:** 0-5 (Mono) 或 0-3 (Side)
- **含义:** 每个像素的类别标签

### **2.4 标签映射表**

#### **Mono 相机标签**

```python
MONO_LABEL_DICT = {
    0: "background",      # 背景
    1: "single_line",     # 单实线
    2: "curb",           # 路沿
    3: "double_line",    # 双黄线
    4: "wide_line",      # 宽线（导流线等）
    5: "slow_line"       # 减速线
}
```

#### **Side 相机标签**

```python
SIDE_LABEL_DICT = {
    0: "background",      # 背景
    1: "single_line",     # 单实线
    2: "wide_line",       # 宽线
    3: "double_line"      # 双黄线
}
```

### **2.5 多相机适配策略**

```
┌─────────────────────────────────────────────────────────┐
│               相机类型判断与处理流程                      │
└─────────────────────────────────────────────────────────┘

输入图像
    │
    ├─► 判断相机类型
    │      │
    │      ├─► front_wide/front_narrow
    │      │      └─► Mono模型 (960×544)
    │      │           └─► 无裁剪
    │      │
    │      ├─► rear
    │      │      └─► Mono模型 (960×544)
    │      │           └─► 垂直裁剪60像素
    │      │
    │      ├─► left_front/right_front/left_back/right_back
    │      │      └─► Side模型 (960×544)
    │      │           └─► 垂直裁剪60像素
    │      │
    │      └─► surround_* (鱼眼)
    │             └─► Fisheye模型 (960×640)
    │                  └─► 无裁剪
    │
    └─► 统一归一化处理
         └─► 批量推理
```

---

## **3. 后处理算法详解**

### **3.1 RLE 编码与连通性分析**

#### **3.1.1 RLE 编码原理**

**RLE (Run-Length Encoding)** 是一种简单的无损压缩算法，用于表示连续相同值的序列。

**定义:**

对于一维序列 $S = [s_1, s_2, ..., s_n]$，RLE 将其编码为：

$$
RLE(S) = [(v_1, l_1), (v_2, l_2), ..., (v_k, l_k)]
$$

其中:

- $v_i$: 第 i 段的值
- $l_i$: 第 i 段的长度（连续相同值的数量）
- $k$: 段的数量

**二维图像的 RLE 编码:**

对于图像 $I \in \mathbb{R}^{H \times W}$，按行进行 RLE 编码：

```
原始图像:
Row 0: [0, 0, 1, 1, 1, 2, 2]
Row 1: [0, 0, 0, 1, 1, 2, 2]

RLE编码:
Row 0: [(0,2), (1,3), (2,2)]
Row 1: [(0,3), (1,2), (2,2)]
```

**优势:**

- 压缩率高（对于稀疏 mask）
- 快速连通性分析
- 内存占用小

#### **3.1.2 RLE 数据结构**

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

#### **3.1.3 8 邻域连通性算法**

**连通性定义:**

两个像素 $p_1(x_1, y_1)$ 和 $p_2(x_2, y_2)$ 是 8 邻域连通的，当且仅当：

$$
|x_1 - x_2| \leq 1 \quad \text{且} \quad |y_1 - y_2| \leq 1
$$

且它们具有相同的标签值。

**算法流程:**

```
算法: RLE连通性分析
输入: RLE编码的图像
输出: 连通区域列表

1. 初始化:
   - 创建RLE段列表
   - 为每个RLE段分配唯一ID

2. 区域生长:
   for 每一行 y:
       for 每个RLE段 r in 行 y:
           检查上一行(y-1)的所有RLE段:
               if 存在8邻域重叠 且 标签相同:
                   合并区域ID

3. 区域合并:
   - 使用并查集(Union-Find)数据结构
   - 合并具有相同根节点的区域

4. 区域过滤:
   - 过滤面积 < 阈值 的区域

5. 输出连通区域
```

**8 邻域重叠判断:**

两个 RLE 段 $r_1 = [xstart_1, xend_1]$ 和 $r_2 = [xstart_2, xend_2]$ 在 8 邻域内重叠的条件：

$$
\max(xstart_1 - 1, 0) \leq xend_2 + 1 \quad \text{且} \quad \max(xstart_2 - 1, 0) \leq xend_1 + 1
$$

**代码实现:**

```cpp
int RLEConnectivityAnalysis(ConnectRegion *&regions,
                           int start_y = 0,
                           UniteLabelMap *label_map = nullptr,
                           bool enable_horizon_merge = false) {
    // 1. 创建RLE链表
    RLEList *rle_head = CreateRLEList(mask_data, height, width);

    // 2. 区域生长
    for (int y = 1; y < height; y++) {
        RLEList *curr = rle_rows[y];
        RLEList *prev = rle_rows[y-1];

        while (curr && prev) {
            // 检查8邻域连通性
            if (IsConnected(curr, prev) && curr->label == prev->label) {
                UnionRegions(curr->region_id, prev->region_id);
            }
            // 移动指针
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

#### **3.1.4 连通区域数据结构**

```cpp
struct ConnectRegion {
    cv::Rect boundbox;          // 外接矩形
    int nArea;                  // 像素数量（面积）
    RLEList *RLEhead;           // 首个RLE段
    RLEList *RLEtail;           // 最后RLE段
    RLELine *linePtr;           // 行指针数组
    ConnectRegion *pre;         // 前驱区域（链表）
    ConnectRegion *next;        // 后继区域（链表）
};
```

### **3.2 轮廓提取**

#### **3.2.1 RLE 扫描算法**

根据相机方向，采用不同的扫描策略：

**扫描模式:**

```
┌──────────────────────────────────────────────────┐
│  Front/Back相机: 垂直扫描 (VERTICAL)              │
│  Left/Right相机: 水平扫描 (HORIZONTAL)            │
└──────────────────────────────────────────────────┘

垂直扫描（前视相机）:
┌─────────────┐
│ ↓  ↓  ↓  ↓ │  从上到下扫描
│ ↓  ↓  ↓  ↓ │  适用于纵向车道线
│ ↓  ↓  ↓  ↓ │
└─────────────┘

水平扫描（侧视相机）:
┌─────────────┐
│ →  →  →  → │  从左到右扫描
│ →  →  →  → │  适用于横向车道线
│ →  →  →  → │
└─────────────┘
```

#### **3.2.2 垂直扫描算法 (RLEScanEx)**

**核心思想:**

对每个连通区域，按垂直方向（列）扫描，提取轮廓点。

**算法流程:**

```
算法: RLEScanEx (垂直扫描)
输入: 连通区域 region
输出: 轮廓点集 contours

1. 获取区域边界框 (x_min, x_max, y_min, y_max)

2. for x = x_min to x_max:
       初始化该列的RLE段列表

       for 每个RLE段 in region:
           if x in [xstart, xend]:
               添加到该列的RLE段列表

       if 该列有RLE段:
           提取轮廓点:
               - 计算RLE段的中心点 (x, y_center)
               - 填充坐标信息:
                   * img_raw: 原始图像坐标
                   * img: 变换后图像坐标
                   * ground: 地面坐标
               - 添加到轮廓

3. 轮廓后处理:
       - 轮廓合并 (ContourMerge)
       - 轮廓过滤 (ContourFilter)
       - 轮廓稀疏化 (ContourSparse)

4. 返回 contours
```

**坐标计算:**

对于 RLE 段 $r = [xstart, xend]$ 在行 $y$:

```
中心点:
    x_center = (xstart + xend) / 2
    y_center = y

原始图像坐标:
    img_raw = (x_center / scale_x + offset_x,
               y_center / scale_y + offset_y)

地面坐标:
    ground = Camera.ImageToGround(img_raw)
```

#### **3.2.3 水平扫描算法 (RLEScanNonFront)**

**核心思想:**

对侧视相机（left/right），按水平方向（行）扫描。

**算法流程:**

```
算法: RLEScanNonFront (水平扫描)
输入: 连通区域 region
输出: 轮廓点集 contours

1. 遍历region的所有RLE段（按行组织）

2. for 每个 RLE段 r:
       计算轮廓点:
           x_center = (r.xstart + r.xend) / 2
           y = r.y

       填充坐标信息（同垂直扫描）

3. 轮廓后处理（同垂直扫描）

4. 返回 contours
```

#### **3.2.4 双线轮廓提取**

对于 `double_line` 标签，需要提取两条线：

```cpp
void ExtractDoubleContour(RLEList *rle, Contour &contour) {
    // 计算RLE段宽度
    int width = rle->xend - rle->xstart + 1;

    // 双线判断阈值
    int double_line_threshold = 15;  // 像素

    if (width > double_line_threshold) {
        // 提取左线
        int left_x = rle->xstart + width * 0.25;
        AddContourPoint(left_x, rle->y, contour.left_line);

        // 提取右线
        int right_x = rle->xstart + width * 0.75;
        AddContourPoint(right_x, rle->y, contour.right_line);
    } else {
        // 单线处理
        int center_x = (rle->xstart + rle->xend) / 2;
        AddContourPoint(center_x, rle->y, contour);
    }
}
```

#### **3.2.5 轮廓合并 (ContourMerge)**

**目的:** 合并距离过近的轮廓点，减少冗余。

**算法:**

```cpp
void ContourMerge(std::vector<BasicInfoPts> &pts, float merge_threshold) {
    std::vector<BasicInfoPts> merged;
    merged.push_back(pts[0]);

    for (size_t i = 1; i < pts.size(); i++) {
        float dist = Distance(merged.back().pt, pts[i].pt);

        if (dist < merge_threshold) {
            // 合并点：取平均
            merged.back().pt.x = (merged.back().pt.x + pts[i].pt.x) / 2;
            merged.back().pt.y = (merged.back().pt.y + pts[i].pt.y) / 2;
        } else {
            merged.push_back(pts[i]);
        }
    }

    pts = merged;
}
```

#### **3.2.6 轮廓过滤 (ContourFilter)**

**过滤条件:**

```cpp
bool ContourFilter(const Contour &contour, FilterParams params) {
    // 1. 宽度过滤
    if (contour.width < params.min_width || contour.width > params.max_width) {
        return false;  // 过滤
    }

    // 2. VCS距离过滤
    for (const auto &pt : contour.basic_pts) {
        if (std::abs(pt.pt.x) > params.vcs_threshold ||
            std::abs(pt.pt.y) > params.vcs_threshold) {
            return false;  // 超出范围
        }
    }

    // 3. 点数过滤
    if (contour.basic_pts.size() < params.min_points) {
        return false;  // 点数太少
    }

    return true;  // 保留
}
```

**默认阈值:**

```cpp
FilterParams default_params = {
    .min_width = 40 * (image_height / 720.0),  // 宽度阈值
    .vcs_threshold = 6.0,                      // VCS距离阈值（米）
    .min_points = 5                             // 最小点数
};
```

#### **3.2.7 轮廓稀疏化 (ContourSparse)**

**目的:** 减少轮廓点数量，保留关键点。

**算法: Douglas-Peucker 简化版**

```cpp
void ContourSparse(std::vector<BasicInfoPts> &pts, float sparse_threshold) {
    if (pts.size() <= 2) return;

    std::vector<BasicInfoPts> sparse;
    sparse.push_back(pts.front());

    for (size_t i = 1; i < pts.size() - 1; i++) {
        // 计算到前一个保留点的距离
        float dist = Distance(sparse.back().pt, pts[i].pt);

        if (dist > sparse_threshold) {
            sparse.push_back(pts[i]);
        }
    }

    sparse.push_back(pts.back());
    pts = sparse;
}
```

**稀疏化阈值:**

```cpp
float sparse_threshold = 0.5 * (image_height / 1080.0);
sparse_threshold = std::clamp(sparse_threshold, 0.5f, 1.0f);
```

### **3.3 坐标转换系统**

#### **3.3.1 坐标系定义**

系统支持多种坐标系：

```
┌─────────────────────────────────────────────────────────┐
│                     坐标系定义                           │
└─────────────────────────────────────────────────────────┘

1. 图像坐标系 (Image)
   - 原点: 左上角
   - X轴向右, Y轴向下
   - 单位: 像素

2. 相机坐标系 (Camera)
   - 原点: 相机光心
   - X轴向右, Y轴向下, Z轴向前
   - 单位: 米

3. 车辆坐标系 (VCS - Vehicle Coordinate System)
   - 原点: 车辆中心（后轴中心）
   - X轴向前, Y轴向左, Z轴向上
   - 单位: 米

4. 地面坐标系 (Ground)
   - VCS在地面的投影
   - Z = 0
   - X轴向前, Y轴向左
```

**坐标系变换图:**

```
Image Space              Camera Space           VCS Ground
    ┌─────────────┐          ┌─────────────┐       ┌─────────────┐
    │  (u,v)      │          │  (xc,yc,zc) │       │  (xv,yv,0)  │
    │  像素坐标    │  ──────► │  相机坐标    │ ───► │  车辆坐标    │
    │             │  K^-1    │             │  T    │             │
    └─────────────┘          └─────────────┘       └─────────────┘
         │                         │                      │
         │  鱼眼去畸变               │  外参变换             │
         │                         │                      │
         ▼                         ▼                      ▼
    归一化坐标               3D空间坐标              地面投影
```

#### **3.3.2 相机内参模型**

**针孔相机模型:**

$$
\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} =
\frac{1}{Z_c} \mathbf{K} \begin{bmatrix} X_c \\ Y_c \\ Z_c \end{bmatrix}
$$

其中内参矩阵 $\mathbf{K}$:

$$
\mathbf{K} = \begin{bmatrix}
f_x & 0 & c_x \\
0 & f_y & c_y \\
0 & 0 & 1
\end{bmatrix}
$$

- $f_x, f_y$: 焦距（像素单位）
- $c_x, c_y$: 主点坐标

**逆变换（图像到相机）:**

$$
\begin{bmatrix} X_c/Z_c \\ Y_c/Z_c \\ 1 \end{bmatrix} =
\mathbf{K}^{-1} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}
$$

#### **3.3.3 鱼眼相机投影模型**

**等距投影模型 (Equidistant Projection)**

鱼眼相机采用 4 参数畸变模型：

$$
\theta_d = \theta(1 + k_1\theta^2 + k_2\theta^4 + k_3\theta^6 + k_4\theta^8)
$$

其中:

- $\theta = \arctan(r)$: 入射角
- $r = \sqrt{x^2 + y^2}$: 归一化半径
- $k_1, k_2, k_3, k_4$: 畸变系数

**投影公式:**

```
归一化坐标 → 鱼眼投影:

输入: (x, y) - 归一化相机坐标
输出: (u, v) - 畸变图像坐标

步骤:
1. r = sqrt(x² + y²)
2. θ = atan(r)
3. θ_d = θ * (1 + k1*θ² + k2*θ⁴ + k3*θ⁶ + k4*θ⁸)
4. scale = θ_d / r  (if r > 0, else 1.0)
5. x_d = x * scale
6. y_d = y * scale
7. u = fx * x_d + cx
8. v = fy * y_d + cy
```

**去畸变（OpenCV 实现）:**

```cpp
void UndistortFisheye(const cv::Point2f &distorted,
                      cv::Point2f &undistorted,
                      const cv::Mat &K,
                      const cv::Mat &D) {
    // distorted: 畸变图像坐标
    // K: 内参矩阵
    // D: 畸变系数 [k1, k2, k3, k4]

    std::vector<cv::Point2f> src = {distorted};
    std::vector<cv::Point2f> dst;

    // OpenCV鱼眼去畸变
    cv::fisheye::undistortPoints(src, dst, K, D);

    undistorted = dst[0];
}
```

#### **3.3.4 相机外参变换**

**外参矩阵:**

外参矩阵 $\mathbf{T}_{cam}^{vcs}$ 是一个 4×4 的齐次变换矩阵：

$$
\mathbf{T}_{cam}^{vcs} = \begin{bmatrix}
\mathbf{R} & \mathbf{t} \\
\mathbf{0}^T & 1
\end{bmatrix} =
\begin{bmatrix}
r_{11} & r_{12} & r_{13} & t_x \\
r_{21} & r_{22} & r_{23} & t_y \\
r_{31} & r_{32} & r_{33} & t_z \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

- $\mathbf{R}$: 3×3 旋转矩阵
- $\mathbf{t}$: 3×1 平移向量

**坐标变换:**

从相机坐标系到车辆坐标系：

$$
\begin{bmatrix} X_{vcs} \\ Y_{vcs} \\ Z_{vcs} \\ 1 \end{bmatrix} =
\mathbf{T}_{cam}^{vcs} \begin{bmatrix} X_{cam} \\ Y_{cam} \\ Z_{cam} \\ 1 \end{bmatrix}
$$

#### **3.3.5 射线投射到地面算法**

**核心思想:**

给定图像上的一个点，找到它在地面（Z=0）上的投影。

**算法流程:**

```
算法: ImageToGround
输入: 图像点 (u, v), 相机参数
输出: 地面坐标 (X_vcs, Y_vcs)

1. 图像坐标 → 归一化相机坐标:
   ┌           ┐⁻¹  ┌   ┐   ┌    ┐
   │ u         │    │ 1 │   │ x_n│
   │ v    = K  │    │ 1 │ = │ y_n│
   │ 1         │    │ 1 │   │ 1  │
   └           ┘    ┘   ┘   └    ┘

2. 鱼眼去畸变（如果是鱼眼相机）:
   (x_n, y_n) → (x_undist, y_undist)

3. 构建射线方向（相机坐标系）:
   d_cam = [x_undist, y_undist, 1]^T

4. 转换到VCS坐标系:
   d_vcs = R * d_cam  (R是外参的旋转部分)
   cam_pos_vcs = t    (t是外参的平移部分)

5. 射线与地面求交（Z_vcs = 0）:
   射线方程: P = cam_pos + s * d_vcs

   求解 s 使得 Z_vcs = 0:
   cam_pos.z + s * d_vcs.z = 0
   => s = -cam_pos.z / d_vcs.z

6. 计算地面交点:
   X_vcs = cam_pos.x + s * d_vcs.x
   Y_vcs = cam_pos.y + s * d_vcs.y

7. 返回 (X_vcs, Y_vcs)
```

**数学推导:**

射线参数方程：

$$
\mathbf{P}(s) = \mathbf{P}_{cam} + s \cdot \mathbf{d}_{vcs}
$$

其中:

- $\mathbf{P}_{cam} = [t_x, t_y, t_z]^T$: 相机在 VCS 中的位置
- $\mathbf{d}_{vcs} = \mathbf{R} \cdot [x_n, y_n, 1]^T$: 射线方向（VCS）
- $s$: 参数

地面约束（$Z_{vcs} = 0$）:

$$
t_z + s \cdot d_{vcs,z} = 0
$$

求解 $s$:

$$
s = -\frac{t_z}{d_{vcs,z}}
$$

代入得到地面坐标:

$$
\begin{cases}
X_{vcs} = t_x + s \cdot d_{vcs,x} \\
Y_{vcs} = t_y + s \cdot d_{vcs,y}
\end{cases}
$$

**代码实现:**

```cpp
cv::Point2f Camera::cvtImageToGround(const cv::Point2f &pt) const {
    // 1. 图像坐标 → 归一化坐标
    float x_n = (pt.x - cx_) / fx_;
    float y_n = (pt.y - cy_) / fy_;

    // 2. 鱼眼去畸变
    if (is_fisheye_) {
        cv::Point2f undistorted;
        UndistortFisheye(cv::Point2f(x_n, y_n), undistorted, K_, D_);
        x_n = undistorted.x;
        y_n = undistorted.y;
    }

    // 3. 构建射线方向
    cv::Vec3f d_cam(x_n, y_n, 1.0f);

    // 4. 转换到VCS
    cv::Vec3f d_vcs = R_ * d_cam;  // R_: 3x3旋转矩阵
    cv::Vec3f cam_pos(t_x_, t_y_, t_z_);  // 相机位置

    // 5. 射线投射到地面
    float s = -cam_pos[2] / d_vcs[2];

    // 6. 计算地面坐标
    float X_vcs = cam_pos[0] + s * d_vcs[0];
    float Y_vcs = cam_pos[1] + s * d_vcs[1];

    return cv::Point2f(X_vcs, Y_vcs);
}
```

#### **3.3.6 完整坐标转换流程**

**图像 → VCS 地面坐标:**

```cpp
std::vector<cv::Point2f> TransformPointsFromImageToVehicleCoordinate(
    const std::vector<cv::Point2f> &img_pts,
    const CameraParams &camera_params) {

    std::vector<cv::Point2f> vcs_pts;

    // 准备内参矩阵
    cv::Mat K = (cv::Mat_<double>(3, 3) <<
        camera_params.fx, 0, camera_params.cx,
        0, camera_params.fy, camera_params.cy,
        0, 0, 1);

    // 准备畸变系数
    cv::Mat D = (cv::Mat_<double>(4, 1) <<
        camera_params.k1, camera_params.k2,
        camera_params.k3, camera_params.k4);

    // 准备外参矩阵
    cv::Mat T_cam_to_vcs = camera_params.extrinsics;  // 4x4

    // 提取旋转和平移
    cv::Mat R = T_cam_to_vcs(cv::Rect(0, 0, 3, 3));
    cv::Mat t = T_cam_to_vcs(cv::Rect(3, 0, 1, 3));

    // 转换每个点
    for (const auto &pt : img_pts) {
        // 1. 鱼眼去畸变
        std::vector<cv::Point2f> src = {pt};
        std::vector<cv::Point2f> undistorted;
        cv::fisheye::undistortPoints(src, undistorted, K, D);

        // 2. 归一化坐标
        cv::Vec3f d_cam(undistorted[0].x, undistorted[0].y, 1.0f);

        // 3. 转换到VCS
        cv::Vec3f d_vcs = R * d_cam;
        cv::Vec3f cam_pos(t.at<double>(0), t.at<double>(1), t.at<double>(2));

        // 4. 射线投射
        float s = -cam_pos[2] / d_vcs[2];
        float X_vcs = cam_pos[0] + s * d_vcs[0];
        float Y_vcs = cam_pos[1] + s * d_vcs[1];

        vcs_pts.emplace_back(X_vcs, Y_vcs);
    }

    return vcs_pts;
}
```

---

## **4. 车道线匹配算法**

### **4.1 跨相机共视关系**

**共视相机对定义:**

```cpp
// 前视与侧视
front_wide ↔ {left_front, right_front}

// 后视与侧视
rear ↔ {left_back, right_back}
```

**共视区域示意:**

```
Front Wide Camera
              ▲
             /|\
            / | \
           /  |  \
          /   |   \
         /    |    \
    Left ◄────┼────► Right
   Front     车辆    Front
            中心
         \    |    /
          \   |   /
           \  |  /
            \ | /
             \|/
              ▼
        Rear Camera
```

### **4.2 匹配条件**

**三个匹配维度:**

1. **距离匹配度**

$$
D_{dist} = \exp\left(-\frac{\|p_1 - p_2\|^2}{2\sigma_d^2}\right)
$$

其中:

- $p_1, p_2$: 两条车道线的端点
- $\sigma_d$: 距离标准差（0.5m）

2. **角度匹配度**

$$
D_{angle} = \exp\left(-\frac{(\theta_1 - \theta_2)^2}{2\sigma_\theta^2}\right)
$$

其中:

- $\theta_1, \theta_2$: 两条车道线的方向角
- $\sigma_\theta$: 角度标准差（约 11.5°）

3. **重叠度匹配度**

$$
D_{overlap} = \frac{|R_1 \cap R_2|}{|R_1 \cup R_2|}
$$

其中:

- $R_1, R_2$: 两条车道线在共视区域的投影范围

**综合评分:**

$$
Score = 0.5 \cdot D_{dist} + 0.3 \cdot D_{angle} + 0.2 \cdot D_{overlap}
$$

### **4.3 匈牙利算法**

**目的:** 找到最优的一对一匹配方案。

**算法步骤:**

```
算法: Hungarian Matching
输入: 代价矩阵 cost_matrix[m×n]
输出: 最优匹配 matching

1. 构建代价矩阵:
   cost[i][j] = 1 - Score(contour_i, contour_j)

2. 调用匈牙利算法:
   matching = HungarianAlgorithm(cost)

3. 过滤低质量匹配:
   for (i, j) in matching:
       if cost[i][j] > threshold:
           移除该匹配

4. 返回 matching
```

**代码实现:**

```cpp
std::vector<std::pair<int, int>> MatchLaneContours(
    const std::vector<Contour> &contours_cam1,
    const std::vector<Contour> &contours_cam2) {

    // 1. 构建代价矩阵
    int m = contours_cam1.size();
    int n = contours_cam2.size();
    cv::Mat cost_matrix(m, n, CV_32F);

    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            float score = ComputeMatchingScore(contours_cam1[i],
                                               contours_cam2[j]);
            cost_matrix.at<float>(i, j) = 1.0f - score;
        }
    }

    // 2. 匈牙利算法
    std::vector<int> assignment;
    cv::Mat cost = cost_matrix.clone();
    HungarianAlgorithm::Solve(cost, assignment);

    // 3. 过滤匹配
    std::vector<std::pair<int, int>> matches;
    for (int i = 0; i < m; i++) {
        int j = assignment[i];
        if (j >= 0 && cost_matrix.at<float>(i, j) < 0.5) {
            matches.emplace_back(i, j);
        }
    }

    return matches;
}
```

---

## **5. 数据结构设计**

### **5.1 轮廓点结构 (BasicInfoPts)**

```cpp
struct BasicInfoPts {
    Point2DF pt;              // 使用坐标（VCS或Local）
    cv::Point2f pt_rle;       // RLE图像坐标
    cv::Point2f pt_oriimg;    // 原始图像坐标
    cv::Point2f pt_img;       // 去畸变图像坐标
    cv::Point2f dir;          // 方向向量
    uint64_t label;           // 统计标签
    uint64_t parsing_label;   // 解析标签（原始类别）
    float conf;               // 置信度
    int8_t score;             // 单通道得分
};
```

**字段说明:**

<table>
<tr>
<td>字段<br/></td><td>类型<br/></td><td>说明<br/></td><td>示例<br/></td></tr>
<tr>
<td>pt<br/></td><td>Point2DF<br/></td><td>最终使用坐标（米）<br/></td><td>(5.2, -1.5)<br/></td></tr>
<tr>
<td>pt_rle<br/></td><td>cv::Point2f<br/></td><td>RLE扫描得到的坐标（像素）<br/></td><td>(480, 270)<br/></td></tr>
<tr>
<td>pt_oriimg<br/></td><td>cv::Point2f<br/></td><td>原始图像坐标（像素）<br/></td><td>(1920, 540)<br/></td></tr>
<tr>
<td>pt_img<br/></td><td>cv::Point2f<br/></td><td>去畸变后坐标（像素）<br/></td><td>(1905, 538)<br/></td></tr>
<tr>
<td>dir<br/></td><td>cv::Point2f<br/></td><td>车道线方向向量<br/></td><td>(0.99, 0.15)<br/></td></tr>
<tr>
<td>label<br/></td><td>uint64_t<br/></td><td>统计后的标签<br/></td><td>3 (double_line)<br/></td></tr>
<tr>
<td>parsing_label<br/></td><td>uint64_t<br/></td><td>原始预测标签<br/></td><td>3<br/></td></tr>
<tr>
<td>conf<br/></td><td>float<br/></td><td>置信度<br/></td><td>0.95<br/></td></tr>
<tr>
<td>score<br/></td><td>int8_t<br/></td><td>单通道得分<br/></td><td>127<br/></td></tr>
</table>

### **5.2 轮廓结构 (Contour)**

```cpp
class Contour {
private:
    float dis_;               // 距离（到车辆中心的距离）
    float width_;             // 宽度（像素）
    uint64_t label_;          // 统计标签
    int sample_coordinate_;   // 采样坐标系
    int type_;                // 轮廓类型
    int region_idx_;          // 连通区域索引

    std::vector<BasicInfoPts> basic_pts_;  // 基础点集
    std::vector<LaneSegInfo> lane_segs_;   // 车道线段

public:
    // Getters
    const std::vector<BasicInfoPts>& GetBasicPts() const { return basic_pts_; }
    float GetDistance() const { return dis_; }
    float GetWidth() const { return width_; }
    uint64_t GetLabel() const { return label_; }

    // Setters
    void SetDistance(float dis) { dis_ = dis; }
    void SetWidth(float width) { width_ = width; }

    // Methods
    void AddPoint(const BasicInfoPts &pt);
    void MergeContour(const Contour &other);
    void FilterPoints(float threshold);
    void SparsePoints(float threshold);
};
```

### **5.3 连通区域结构 (ConnectRegion)**

```cpp
struct ConnectRegion {
    cv::Rect boundbox;         // 外接矩形 [x, y, width, height]
    int nArea;                 // 像素数量（面积）
    RLEList *RLEhead;          // 首个RLE段
    RLEList *RLEtail;          // 最后RLE段
    RLELine *linePtr;          // 行指针数组
    ConnectRegion *pre;        // 前驱区域
    ConnectRegion *next;       // 后继区域
};
```

### **5.4 RLE 信息结构 (RLEInfo)**

```cpp
struct RLEInfo {
    uint64_t label;            // 标签
    int y;                     // 行号
    int xstart, xend;          // 起止列

    cv::Point2f img_raw_st;    // 原始图像起点
    cv::Point2f img_raw_ed;    // 原始图像终点
    cv::Point2f img_raw_c;     // 原始图像中心

    cv::Point2f img_st;        // 变换后起点
    cv::Point2f img_ed;        // 变换后终点
    cv::Point2f img_c;         // 变换后中心

    cv::Point2f ground_st;     // 地面起点
    cv::Point2f ground_ed;     // 地面终点
    cv::Point2f ground_c;      // 地面中心
};
```

### **5.5 相机参数结构 (CameraParams)**

```cpp
struct CameraParams {
    // 内参
    float fx, fy;              // 焦距
    float cx, cy;              // 主点

    // 畸变系数（鱼眼）
    float k1, k2, k3, k4;

    // 外参
    cv::Mat extrinsics;        // 4×4变换矩阵

    // 图像尺寸
    int width, height;

    // 相机类型
    CameraType type;           // MONO, SIDE, FISHEYE
};
```

---

## **6. 参数配置与调优**

### **6.1 模型输入尺寸配置**

<table>
<tr>
<td>模型类型<br/></td><td>输入尺寸 (H×W)<br/></td><td>原始图像尺寸<br/></td><td>Scale<br/></td><td>Crop Offset<br/></td></tr>
<tr>
<td>Mono<br/></td><td>544×960<br/></td><td>3840×2160<br/></td><td>0.25<br/></td><td>(0, 0)<br/></td></tr>
<tr>
<td>Mono (rear)<br/></td><td>544×960<br/></td><td>1920×1200<br/></td><td>0.5<br/></td><td>(0, 60)<br/></td></tr>
<tr>
<td>Side<br/></td><td>544×960<br/></td><td>1920×1200<br/></td><td>0.5<br/></td><td>(0, 60)<br/></td></tr>
<tr>
<td>Fisheye<br/></td><td>640×960<br/></td><td>1920×1300<br/></td><td>0.2<br/></td><td>(0, 0)<br/></td></tr>
</table>

### **6.2 图像处理参数**

```cpp
// 归一化参数（ImageNet）
const std::vector<float> MEAN = {123.675, 116.28, 103.53};
const std::vector<float> STD = {58.395, 57.12, 57.375};

// 裁剪参数
const float CROP_OFFSET_RATIO = 0.5037;  // rear/side相机

// 缩放参数
const std::map<std::string, float> SCALE_MAP = {
    {"front_wide", 0.25},
    {"rear", 0.5},
    {"side", 0.5},
    {"fisheye", 0.2}
};
```

### **6.3 后处理阈值**

#### **6.3.1 RLE 连通性分析**

```cpp
// 区域最小面积（像素）
const int MIN_AREA_FAR = 10;    // 远处区域
const int MIN_AREA_NEAR = 8;    // 近处区域

// 行号阈值（区分远/近）
const int FAR_NEAR_THRESHOLD = image_height / 2;
```

#### **6.3.2 轮廓过滤**

```cpp
// 宽度过滤
float min_width = 40 * (image_height / 720.0);
float max_width = 200 * (image_height / 720.0);

// VCS距离阈值（米）
const float VCS_THRESHOLD = 6.0;

// 最小点数
const int MIN_CONTOUR_POINTS = 5;
```

#### **6.3.3 轮廓稀疏化**

```cpp
// 稀疏化阈值（像素）
float sparse_threshold = 0.5 * (image_height / 1080.0);
sparse_threshold = std::clamp(sparse_threshold, 0.5f, 1.0f);
```

#### **6.3.4 双线检测**

```cpp
// 双线宽度阈值（像素）
const int DOUBLE_LINE_WIDTH_THRESHOLD = 15;
```

### **6.4 车道线匹配参数**

```cpp
// 匹配距离阈值（米）
const float MATCH_DISTANCE_THRESHOLD = 0.5;

// 匹配角度阈值（弧度）
const float MATCH_ANGLE_THRESHOLD_RAD = 20.0 * M_PI / 180.0;

// 匹配评分阈值
const float MATCH_SCORE_THRESHOLD = 0.5;

// 评分权重
const float WEIGHT_DISTANCE = 0.5;
const float WEIGHT_ANGLE = 0.3;
const float WEIGHT_OVERLAP = 0.2;
```

### **6.5 性能优化建议**

#### **6.5.1 推理优化**

```python
# 1. 批处理
batch_size = 48  # 根据GPU内存调整

# 2. GPU加速
providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

# 3. 模型优化
# 使用ONNX Optimizer进行图优化
```

#### **6.5.2 后处理优化**

```cpp
// 1. RLE编码并行化
#pragma omp parallel for
for (int y = 0; y < height; y++) {
    EncodeRowRLE(mask_data + y * width, width, rle_rows[y]);
}

// 2. 轮廓提取并行化
#pragma omp parallel for
for (int i = 0; i < num_regions; i++) {
    ExtractContour(regions[i], contours[i]);
}

// 3. 坐标转换批量处理
std::vector<cv::Point2f> vcs_pts = TransformPointsBatch(img_pts, camera_params);
```

#### **6.5.3 内存优化**

```cpp
// 1. 预分配内存
contours.reserve(num_regions);

// 2. 避免不必要的拷贝
const auto& pts = contour.GetBasicPts();  // 使用引用

// 3. 及时释放
delete[] rle_head;
```

### **6.6 调优指南**

#### **6.6.1 远处车道线丢失**

**症状:** 远处车道线检测不完整

**解决方案:**

```cpp
// 降低最小面积阈值
MIN_AREA_FAR = 6;  // 从10降到6

// 放宽宽度过滤
min_width = 30 * (image_height / 720.0);  // 从40降到30
```

#### **6.6.2 噪声过多**

**症状:** 检测到虚假车道线

**解决方案:**

```cpp
// 提高最小面积阈值
MIN_AREA_FAR = 15;  // 从10提高到15
MIN_AREA_NEAR = 12; // 从8提高到12

// 提高最小点数
MIN_CONTOUR_POINTS = 8;  // 从5提高到8

// 增加VCS距离约束
VCS_THRESHOLD = 5.0;  // 从6.0降到5.0
```

#### **6.6.3 车道线断裂**

**症状:** 连续车道线被分成多段

**解决方案:**

```cpp
// 启用水平合并
enable_horizon_merge = true;

// 降低轮廓合并阈值
merge_threshold = 2.0;  // 从5.0降到2.0
```

---

## **7. 关键代码实现**

### **7.1 核心函数签名**

#### **7.1.1 数据加载**

```cpp
class PVLaneDataLoader {
public:
    // 加载相机标定参数
    bool LoadCameraCalibrations(const std::string &calib_dir);

    // 处理Mask数据
    bool ProcessMaskData(const float *mask_data,
                        int mask_h,
                        int mask_w,
                        int camera_idx,
                        std::vector<Contour> &contours);

    // 保存结果到JSON
    bool SaveContoursToJson(const std::vector<Contour> &contours,
                           const std::string &output_path);
};
```

#### **7.1.2 轮廓提取**

```cpp
class ParsingSampling {
public:
    // 主处理函数
    bool Process(const float *mask_data,
                int mask_h,
                int mask_w,
                int camera_idx,
                const std::string &camera_name,
                std::vector<Contour> &contours);

private:
    // 设置图像变换参数
    void SetImageTransformParams(float scale_x, float scale_y,
                                float offset_x, float offset_y);

    // 初始化相机
    void InitializeCamera(const CameraParams &params);
};
```

#### **7.1.3 RLE 扫描**

```cpp
class RLEScanner {
public:
    // 垂直扫描（前/后视相机）
    void RLEScanEx(ConnectRegion *region,
                   std::vector<Contour> &contours,
                   int scan_direction);

    // 水平扫描（侧视相机）
    void RLEScanNonFront(ConnectRegion *region,
                        std::vector<Contour> &contours);

    // 轮廓合并
    void ContourMerge(std::vector<BasicInfoPts> &pts, float threshold);

    // 轮廓过滤
    bool ContourFilter(const Contour &contour, const FilterParams &params);

    // 轮廓稀疏化
    void ContourSparse(std::vector<BasicInfoPts> &pts, float threshold);
};
```

#### **7.1.4 坐标转换**

```cpp
class Camera {
public:
    // 图像坐标 → 地面坐标
    cv::Point2f cvtImageToGround(const cv::Point2f &pt) const;

    // 地面坐标 → 图像坐标
    cv::Point2f cvtGroundToImage(const cv::Point2f &pt) const;

    // 图像坐标 → VCS地面
    cv::Point2f CvtImageToVcsGnd(const cv::Point2f &pt) const;

    // VCS地面 → 图像坐标
    cv::Point2f CvtVcsGndToImage(const cv::Point2f &pt) const;

private:
    // 鱼眼去畸变
    void UndistortFisheye(const cv::Point2f &distorted,
                         cv::Point2f &undistorted) const;
};
```

### **7.2 算法复杂度分析**

<table>
<tr>
<td>算法<br/></td><td>时间复杂度<br/></td><td>空间复杂度<br/></td><td>说明<br/></td></tr>
<tr>
<td>RLE编码<br/></td><td>O(H×W)<br/></td><td>O(H×W)<br/></td><td>遍历所有像素<br/></td></tr>
<tr>
<td>RLE连通性分析<br/></td><td>O(H×W×α(n))<br/></td><td>O(H×W)<br/></td><td>α(n)为并查集的逆Ackermann函数<br/></td></tr>
<tr>
<td>轮廓提取<br/></td><td>O(N_regions × N_rle)<br/></td><td>O(N_contours × N_pts)<br/></td><td>N_rle为每个区域的RLE段数<br/></td></tr>
<tr>
<td>坐标转换<br/></td><td>O(N_pts)<br/></td><td>O(1)<br/></td><td>每个点独立计算<br/></td></tr>
<tr>
<td>车道线匹配<br/></td><td>O(N_1 × N_2)<br/></td><td>O(N_1 × N_2)<br/></td><td>匈牙利算法<br/></td></tr>
</table>

### **7.3 典型调用流程**

```cpp
int main() {
    // 1. 初始化数据加载器
    PVLaneDataLoader loader;
    loader.LoadCameraCalibrations("/path/to/calib");

    // 2. 加载Mask数据（假设已经推理得到）
    float *mask_data = LoadMaskFromNpy("/path/to/mask.npy");
    int mask_h = 544, mask_w = 960;

    // 3. 处理每个相机
    for (int cam_idx = 0; cam_idx < num_cameras; cam_idx++) {
        std::vector<Contour> contours;

        // 提取轮廓
        loader.ProcessMaskData(mask_data, mask_h, mask_w, cam_idx, contours);

        // 保存结果
        std::string output_path = "/path/to/output_" + std::to_string(cam_idx) + ".json";
        loader.SaveContoursToJson(contours, output_path);
    }

    // 4. 跨相机匹配（可选）
    if (enable_matching) {
        std::vector<Contour> contours_cam1 = LoadContours("/path/to/output_0.json");
        std::vector<Contour> contours_cam2 = LoadContours("/path/to/output_1.json");

        auto matches = MatchLaneContours(contours_cam1, contours_cam2);

        // 使用匹配结果...
    }

    return 0;
}
```

---

## **8. 附录**

### **8.1 文件路径索引**

<table>
<tr>
<td>功能模块<br/></td><td>头文件<br/></td><td>实现文件<br/></td></tr>
<tr>
<td>主入口<br/></td><td>-<br/></td><td>`main.cpp`<br/></td></tr>
<tr>
<td>数据加载器<br/></td><td>`include/pvlane/pvlane_data_loader.h`<br/></td><td>`src/pvlane/pvlane_data_loader.cpp`<br/></td></tr>
<tr>
<td>轮廓提取<br/></td><td>`include/pvlane/find_contour.h`<br/></td><td>`src/pvlane/find_contour.cpp`<br/></td></tr>
<tr>
<td>RLE扫描<br/></td><td>`include/pvlane/hobot-adas/modules/lane/common/base/rle_scan.h`<br/></td><td>`src/pvlane/hobot-adas/modules/lane/common/base/rle_scan.cpp`<br/></td></tr>
<tr>
<td>相机模型<br/></td><td>`include/pvlane/hobot-adas/utils/camera/camera.h`<br/></td><td>`src/pvlane/hobot-adas/utils/camera/camera.cpp`<br/></td></tr>
<tr>
<td>RLE连通性<br/></td><td>`include/pvlane/hobot-adas/utils/rle/rle_connectivity_analysis.h`<br/></td><td>`src/pvlane/hobot-adas/utils/rle/rle_connectivity_analysis.cpp`<br/></td></tr>
<tr>
<td>数据结构<br/></td><td>`include/pvlane/hobot-adas/modules/lane/common/msg/contour_msg.h`<br/></td><td>`src/pvlane/hobot-adas/modules/lane/common/msg/contour_msg.cpp`<br/></td></tr>
<tr>
<td>Python推理<br/></td><td>-<br/></td><td>`scripts/pvlane/pvlane_onnx_infer.py`<br/></td></tr>
</table>

### **8.2 标签映射表**

#### **Mono 相机**

<table>
<tr>
<td>标签值<br/></td><td>英文名称<br/></td><td>中文名称<br/></td><td>说明<br/></td></tr>
<tr>
<td>0<br/></td><td>background<br/></td><td>背景<br/></td><td>非车道线区域<br/></td></tr>
<tr>
<td>1<br/></td><td>single_line<br/></td><td>单实线<br/></td><td>白色/黄色单实线<br/></td></tr>
<tr>
<td>2<br/></td><td>curb<br/></td><td>路沿<br/></td><td>道路边缘<br/></td></tr>
<tr>
<td>3<br/></td><td>double_line<br/></td><td>双黄线<br/></td><td>双黄实线<br/></td></tr>
<tr>
<td>4<br/></td><td>wide_line<br/></td><td>宽线<br/></td><td>导流线、斑马线等<br/></td></tr>
<tr>
<td>5<br/></td><td>slow_line<br/></td><td>减速线<br/></td><td>减速提示线<br/></td></tr>
</table>

#### **Side 相机**

<table>
<tr>
<td>标签值<br/></td><td>英文名称<br/></td><td>中文名称<br/></td><td>说明<br/></td></tr>
<tr>
<td>0<br/></td><td>background<br/></td><td>背景<br/></td><td>非车道线区域<br/></td></tr>
<tr>
<td>1<br/></td><td>single_line<br/></td><td>单实线<br/></td><td>白色/黄色单实线<br/></td></tr>
<tr>
<td>2<br/></td><td>wide_line<br/></td><td>宽线<br/></td><td>导流线、斑马线等<br/></td></tr>
<tr>
<td>3<br/></td><td>double_line<br/></td><td>双黄线<br/></td><td>双黄实线<br/></td></tr>
</table>

### **8.3 常见问题与解决方案**

#### **Q1: 推理速度慢**

**原因:**

- GPU 未正确启用
- 批处理大小过小
- 模型未优化

**解决方案:**

```python
# 1. 确认GPU可用
import torch
print(torch.cuda.is_available())

# 2. 增加批处理大小
batch_size = 64  # 根据GPU内存调整

# 3. 使用ONNX优化器
import onnxoptimizer
optimized_model = onnxoptimizer.optimize(original_model)
```

#### **Q2: 轮廓提取失败**

**原因:**

- Mask 数据格式错误
- 连通区域面积过小
- 过滤参数过严

**解决方案:**

```cpp
// 1. 检查Mask数据
assert(mask_data != nullptr);
assert(mask_h > 0 && mask_w > 0);

// 2. 调整面积阈值
MIN_AREA_FAR = 5;   // 降低阈值

// 3. 放宽过滤参数
FilterParams params;
params.min_width = 20;  // 降低最小宽度
```

#### **Q3: 坐标转换不准确**

**原因:**

- 标定参数错误
- 相机类型不匹配
- 地面假设不成立

**解决方案:**

```cpp
// 1. 验证标定参数
ValidateCameraParams(camera_params);

// 2. 确认相机类型
if (camera_name.find("surround") != std::string::npos) {
    // 使用鱼眼模型
    UseFisheyeModel();
} else {
    // 使用针孔模型
    UsePinholeModel();
}

// 3. 检查地面高度
float ground_height = EstimateGroundHeight();
if (std::abs(ground_height) > 0.1) {
    // 调整地面平面
    AdjustGroundPlane(ground_height);
}
```

#### **Q4: 跨相机匹配错误**

**原因:**

- 时间戳不同步
- 共视区域计算错误
- 匹配阈值不合理

**解决方案:**

```cpp
// 1. 同步时间戳
if (std::abs(timestamp_cam1 - timestamp_cam2) > 0.1) {
    // 时间戳差异过大，跳过匹配
    return;
}

// 2. 重新计算共视区域
UpdateCoViewRegions();

// 3. 调整匹配阈值
MATCH_DISTANCE_THRESHOLD = 0.8;  // 放宽距离阈值
MATCH_SCORE_THRESHOLD = 0.4;     // 降低评分阈值
```

### **8.4 参考资料**

1. **ONNX Runtime 文档**

   https://onnxruntime.ai/docs/
2. **OpenCV 鱼眼相机模型**

   [https://docs.opencv.org/4.x/db/d58/group__calib3d__fisheye.html](https://docs.opencv.org/4.x/db/d58/group__calib3d__fisheye.html)
3. **RLE 编码**

   [https://en.wikipedia.org/wiki/Run-length_encoding](https://en.wikipedia.org/wiki/Run-length_encoding)
4. **匈牙利算法**

   Kuhn, H. W. (1955). "The Hungarian method for the assignment problem"
5. **车道线检测综述**

   Ye, J., et al. (2020). "A Review of Lane Detection Methods"

---

## **文档修订历史**

<table>
<tr>
<td>版本<br/></td><td>日期<br/></td><td>作者<br/></td><td>修订内容<br/></td></tr>
<tr>
<td>v1.0<br/></td><td>2026-03-06<br/></td><td>Claude<br/></td><td>初始版本，完整记录pvlane算法原理<br/></td></tr>
</table>

---

**文档结束**

如有疑问或需要补充，请联系算法团队。
