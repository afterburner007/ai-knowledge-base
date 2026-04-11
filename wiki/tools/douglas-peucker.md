---
title: "Douglas-Peucker 抽稀算法"
category: tools
tags:
  - Douglas-Peucker
  - 折线简化
  - 点抽稀
  - 轮廓提取
  - 递归算法
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/debug_tools/project-knowledge-points.md
  - raw/fusion/fusion-notes.md
---

# Douglas-Peucker 抽稀算法

## 概述

Douglas-Peucker 算法（又称 Ramer-Douglas-Peucker 算法）是一种经典的**递归折线简化算法**，通过迭代地移除距离折线首末连线最近的中间点，在保持折线形状特征的同时大幅减少点数。在自动驾驶中，常用于点云轮廓简化、障碍物边界抽稀、90 度折角特征提取等场景。

## 算法原理

### 核心思想

```
给定有序点集 P = [p_1, p_2, ..., p_n] 和距离阈值 ε:

1. 连接首点 p_1 和末点 p_n 形成直线
2. 计算所有中间点到该直线的距离
3. 找到最大距离 d_max 及其对应点 p_max
4. 如果 d_max > ε:
   - 递归处理 [p_1, ..., p_max]
   - 递归处理 [p_max, ..., p_n]
5. 否则:
   - 移除所有中间点，只保留 p_1 和 p_n
```

### 算法流程图

```
         [A ───────────────────────────────────── B]
                  ↑ 最远点 C (d_max > ε)
                  │
        [A ─────── C]         [C ──────────────── B]
            ↑ 递归               ↑ 递归
            处理                  处理
```

## 点到直线距离计算

### 一般式

对于直线 $Ax + By + C = 0$ 和点 $(x_0, y_0)$，点到直线的距离为：

$$
D = \frac{|Ax_0 + By_0 + C|}{\sqrt{A^2 + B^2}}
$$

### 两点式（常用）

对于由点 $A(x_1, y_1)$ 和 $B(x_2, y_2)$ 定义的直线，点 $P(x_0, y_0)$ 到该直线的距离为：

$$
D = \frac{|(y_2 - y_1)x_0 - (x_2 - x_1)y_0 + x_2 y_1 - y_2 x_1|}{\sqrt{(y_2 - y_1)^2 + (x_2 - x_1)^2}}
$$

### 向量叉积形式（三维扩展）

对于三维空间中的点 $P$ 和由 $A$、$B$ 定义的直线：

$$
D = \frac{\|(\mathbf{B} - \mathbf{A}) \times (\mathbf{A} - \mathbf{P})\|}{\|\mathbf{B} - \mathbf{A}\|}
$$

## 递归实现

```cpp
void DouglasPeucker(
    const std::vector<Point2D>& points,
    double epsilon,
    std::vector<Point2D>& result
) {
    if (points.size() <= 2) {
        result = points;
        return;
    }

    // 找到最远点
    double max_dist = 0;
    size_t max_idx = 0;
    for (size_t i = 1; i < points.size() - 1; i++) {
        double d = PointToLineDistance(points[i], points[0], points.back());
        if (d > max_dist) {
            max_dist = d;
            max_idx = i;
        }
    }

    if (max_dist > epsilon) {
        // 递归处理左右两部分
        std::vector<Point2D> left(points.begin(), points.begin() + max_idx + 1);
        std::vector<Point2D> right(points.begin() + max_idx, points.end());

        std::vector<Point2D> left_result, right_result;
        DouglasPeucker(left, epsilon, left_result);
        DouglasPeucker(right, epsilon, right_result);

        // 合并（去掉右半部分的首点，避免重复）
        result = left_result;
        result.insert(result.end(), right_result.begin() + 1, right_result.end());
    } else {
        // 所有中间点距离足够小，只保留端点
        result = {points.front(), points.back()};
    }
}
```

## 应用场景

### 1. 障碍物边界提取与跟踪

在基于单帧 Freespace 的障碍物边界提取中，DBSCAN 聚类得到的点云轮廓包含大量冗余点。DP 算法将轮廓简化为关键特征点：

```
Freespace 边界点集 → DP 抽稀 → 关键轮廓点
    ↓
90° 折角特征提取（立柱、墙角）
```

### 2. 90 度折角特征检测

对于立柱与墙角，DP 抽稀后保留的转折点恰好对应 90 度折角特征：

```
原始密集点集:  ········┐···············
DP 抽稀后:     A────────┴──────────────B
                          ↑
                      关键折角点
```

### 3. 车道线简化

在高精地图车道线匹配前，使用 DP 算法减少车道线点数，降低后续匈牙利匹配和 Ceres 优化的计算量：

```
原始车道线 (100+ 点) → DP 抽稀 (ε = 0.05m) → 关键车道线 (5~10 点)
    ↓
减少匹配/优化计算量 10~20 倍
```

## 阈值选择

| $\epsilon$ 值 | 简化程度 | 适用场景 |
|---------------|----------|----------|
| 0.01 m | 轻度简化，保留细节 | 高精度建模 |
| 0.05 m | 中度简化 | 车道线匹配 |
| 0.1 m | 较强简化 | 障碍物轮廓 |
| 0.5 m | 极度简化 | 快速预览 |

## 算法复杂度

- **最坏情况**：$O(n^2)$（每次递归只分割出一个点）
- **平均情况**：$O(n \log n)$
- **优化版本**：使用预先计算的点到直线距离表可达到 $O(n)$

## 相关页面

- [Ceres 非线性优化](./ceres-optimization.md) — 抽稀后减少优化计算量
- [匈牙利匹配算法](./hungarian-matching.md) — 抽稀后加速匹配过程
- [EMA 平滑算法](./ema-smoothing.md) — 抽稀与平滑配合：先简化再平滑
- [TDA4 OpenVX 系统优化](../platform/tda4-openvx-optimization.md) — 在 DSP 上部署 DP 算法加速
