---
title: "匈牙利匹配算法"
category: tools
tags:
  - 匈牙利算法
  - 二分图匹配
  - 车道线匹配
  - 跨相机匹配
  - 空间距离
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/debug_tools/project-knowledge-points.md
  - raw/fusion/fusion-notes.md
---

# 匈牙利匹配算法

## 概述

匈牙利算法（Hungarian Algorithm），又称 Kuhn-Munkres 算法，是解决**指派问题**（Assignment Problem）的经典算法。在自动驾驶的跨相机车道线匹配、多目标跟踪等场景中，匈牙利算法用于在两组检测目标之间找到最优的一一匹配关系。

## 算法原理

### 问题定义

给定一个 $n \times n$ 的代价矩阵 $C$，其中 $C_{ij}$ 表示将第 $i$ 个元素分配给第 $j$ 个元素的代价，求解一个排列 $\sigma$，使得总代价最小：

$$
\min_{\sigma} \sum_{i=1}^{n} C_{i, \sigma(i)}
$$

### 算法步骤

```
1. 行归约：每行减去该行最小值
   ↓
2. 列归约：每列减去该列最小值
   ↓
3. 用最少的水平/垂直线覆盖所有零元素
   ↓
4. 如果线的数量 = n，则找到最优匹配，算法结束
   ↓
5. 否则，找到未被覆盖的最小元素，未覆盖行减去该值，覆盖列加上该值
   ↓
6. 回到步骤 3
```

### 时间复杂度

- 原始实现：$O(n^4)$
- 改进实现（如 Jonker-Volgenant 算法）：$O(n^3)$

## 跨相机车道线匹配

### 应用场景

在高精地图车道线与相机配准、多相机环视融合中，需要将不同相机视角下检测到的车道线段进行匹配，以确定哪些线段属于同一条物理车道线。

### 代价矩阵构建

#### 1. 空间距离代价

对于两条车道线段 $L_a$ 和 $L_b$，计算它们之间的空间距离：

$$
D_{\text{spatial}}(L_a, L_b) = \min_{p_a \in L_a, p_b \in L_b} \|p_a - p_b\|
$$

实际实现中，可采样车道线上的关键点，计算点到线段的最短距离：

$$
d(p, \overline{AB}) = \frac{|(B - A) \times (A - p)|}{\|B - A\|}
$$

#### 2. 方向相似性代价

计算两条车道线的方向夹角余弦值：

$$
D_{\text{direction}}(L_a, L_b) = 1 - |\cos \theta| = 1 - \frac{|\mathbf{d}_a \cdot \mathbf{d}_b|}{\|\mathbf{d}_a\| \cdot \|\mathbf{d}_b\|}
$$

其中 $\mathbf{d}_a$ 和 $\mathbf{d}_b$ 分别为两条车道线的方向向量。

#### 3. 综合代价

将空间距离和方向相似性加权组合：

$$
C_{ij} = \alpha \cdot \frac{D_{\text{spatial}}(L_i, L_j)}{D_{\text{max}}} + \beta \cdot D_{\text{direction}}(L_i, L_j)
$$

其中 $\alpha + \beta = 1$，$D_{\text{max}}$ 为归一化因子。

### 代价矩阵示例

假设有 3 条前视相机检测的车道线和 3 条侧视相机检测的车道线：

$$
C = \begin{bmatrix}
0.12 & 0.85 & 0.90 \\
0.78 & 0.15 & 0.82 \\
0.92 & 0.88 & 0.10
\end{bmatrix}
$$

最小代价匹配为：$(L_1 \rightarrow R_1), (L_2 \rightarrow R_2), (L_3 \rightarrow R_3)$。

## 非方阵处理

当两组车道线数量不等时（$m \neq n$），通过添加虚拟行/列（填充无穷大代价值）将代价矩阵扩展为方阵。

## 在系统中的位置

```
多相机检测
    ↓
车道线提取 → 特征描述
    ↓
代价矩阵构建（空间距离 + 方向相似性）
    ↓
匈牙利匹配 → 匹配结果
    ↓
Ceres 优化（精化外参）
```

## 相关页面

- [Ceres 非线性优化](./ceres-optimization.md) — 匹配后的外参精化优化
- [Douglas-Peucker 抽稀算法](./douglas-peucker.md) — 车道线简化减少匹配计算量
- [EMA 平滑算法](./ema-smoothing.md) — 匹配结果的时序平滑
