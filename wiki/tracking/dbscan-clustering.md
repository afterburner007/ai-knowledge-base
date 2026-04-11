---
title: "DBSCAN 聚类算法"
category: tracking
tags:
  - DBSCAN
  - 密度聚类
  - FLANN
  - 点云处理
  - Freespace
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/fusion/fusion-presentation.md
  - raw/debug_tools/project-knowledge-points.md
---

# DBSCAN 聚类算法

## 概述

DBSCAN（Density-Based Spatial Clustering of Applications with Noise）是一种基于密度的空间聚类算法，能够发现任意形状的簇并自动识别噪声点。在泊车感知系统中，用于 Freespace 边界点云的聚类分割。

## 核心概念

- **Eps（邻域半径）**：定义点的邻域范围
- **MinPts（最小点数）**：核心点所需的最少邻域点数
- **核心点**：Eps 邻域内包含至少 MinPts 个点的点
- **边界点**：在某个核心点的邻域内但不是核心点的点
- **噪声点**：既不是核心点也不是边界点的点

## 算法流程

1. 定义参数 `Eps`（邻域半径）与 `MinPts`（最小点数）
2. 依次遍历所有点：
   - 如果点已被访问则跳过
   - 否则查找半径为 `Eps` 内的所有邻域点
     - 如果邻域点数 `< MinPts`，标记为噪声点
     - 如果邻域点数 `>= MinPts`，标记为核心点
3. 从核心点出发，递归访问其邻域内的所有点，不断扩展簇
4. 重复步骤 2-3 直到所有点都被遍历

```
初始化：所有点标记为未访问
for each 未访问的点 p:
    查询 Eps 邻域内的邻居集合 N(p)
    if |N(p)| < MinPts:
        标记 p 为噪声
    else:
        创建新簇 C
        将 p 加入 C
        对 N(p) 中每个点 q:
            if q 未被访问:
                标记 q 为已访问
                查询 N(q)
                if |N(q)| >= MinPts:
                    将 N(q) 合并到 N(p) 中
            if q 不属于任何簇:
                将 q 加入 C
```

## 性能优化

### FLANN 加速

使用 **FLANN**（Fast Library for Approximate Nearest Neighbors）进行最近邻搜索加速，替代暴力搜索：
- 构建 KD-Tree 或随机 KD-Tree 索引
- 近似最近邻搜索，在精度可接受范围内大幅提升查询速度
- 特别适合大规模点云数据的 Eps 邻域查询

### 已访问集合优化

使用 `std::unordered_set` 记录已访问点，实现 O(1) 时间复杂度的访问状态查询，替代线性扫描。

## 应用场景

- **Freespace 边界聚类**：对单帧 Freespace 提取的障碍物边界点进行聚类，分离不同的障碍物轮廓
- **立柱与墙角提取**：聚类后结合 DP 抽稀算法提取 90 度折角特征，用于车位角点检测
- **点云分割**：在基于鱼眼相机点云的 Costmap 构建前，对点云进行预处理聚类

## 相关页面

- [卡尔曼滤波 (KF)](./kalman-filter.md)
- [粒子滤波 (PF)](./particle-filter.md)
- [多传感器融合框架](../fusion/multi-sensor-fusion.md)
- [Costmap 概率累加模型](../fusion/costmap-probabilistic.md)
