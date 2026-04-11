---
title: "粒子滤波 (PF)"
category: tracking
tags:
  - 粒子滤波
  - 蒙特卡洛方法
  - 马氏距离
  - 重采样
  - 行人跟踪
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/fusion/fusion-presentation.md
  - raw/debug_tools/project-knowledge-points.md
---

# 粒子滤波 (Particle Filter, PF)

## 概述

粒子滤波是一种基于蒙特卡洛采样的贝叶斯滤波方法，通过一组带权重的随机样本（粒子）来近似后验概率分布。相比 KF 和 EKF，PF 能够处理任意非线性非高斯系统，适用于多模态分布和复杂运动模型。

## 核心算法

### 粒子表示

每个粒子 $i$ 表示为 $(\mathbf{x}^{(i)}, w^{(i)})$，其中：
- $\mathbf{x}^{(i)}$：粒子的状态
- $w^{(i)}$：粒子的权重，满足 $\sum_i w^{(i)} = 1$

### 算法步骤

1. **预测**：根据运动模型对每个粒子进行状态传播
2. **权重更新**：根据观测似然更新每个粒子的权重
3. **重采样**：根据权重对粒子进行重采样，避免粒子退化

## 权重采样

使用均匀分布进行随机索引采样：

```cpp
std::uniform_real_distribution<double> distribution(0.0, 1.0);
double index = distribution(generator_) * num_particles_;
```

## 马氏距离 (Mahalanobis Distance)

马氏距离用于衡量观测值与粒子状态之间的匹配程度，考虑了各维度的相关性和尺度差异。

### 定义

$$
D_M(\mathbf{x}) = \sqrt{(\mathbf{x} - \boldsymbol{\mu})^T \boldsymbol{\Sigma}^{-1} (\mathbf{x} - \boldsymbol{\mu})}
$$

### 协方差矩阵计算

$$
\boldsymbol{\Sigma} = \frac{1}{N-1} \sum_{i=1}^{N} (\mathbf{x}_i - \boldsymbol{\mu})(\mathbf{x}_i - \boldsymbol{\mu})^T
$$

### 奇异矩阵处理

当无法求协方差逆矩阵时（奇异矩阵）：
- **样本不足**：粒子数过少导致协方差矩阵秩不足
- **共线分布**：所有粒子分布在一条直线上

**解决方案**：当有效粒子数小于 3 时，将协方差矩阵设为单位矩阵，此时马氏距离退化为欧式距离。

## 轮盘赌重采样 (Roulette Wheel Resampling)

```cpp
void ParticleFilter::resample() {
    std::vector<Particle> new_particles;
    std::uniform_real_distribution<double> distribution(0.0, 1.0);

    double index = distribution(generator_) * num_particles_;
    double beta = 0.0;
    double mw = 0.0; // 最大权重

    for (auto& particle : particles_) {
        if (particle.weight > mw) mw = particle.weight;
    }

    for (int i = 0; i < num_particles_; ++i) {
        beta += distribution(generator_) * 2.0 * mw;
        while (particles_[index].weight < beta) {
            beta -= particles_[index].weight;
            index = fmod(index + 1, num_particles_);
        }
        new_particles.push_back(particles_[index]);
    }

    particles_ = new_particles;
}
```

## 粒子退化与 ESS

### 有效样本数 (ESS)

$$
ESS = \frac{1}{\sum_{i=1}^{N} w_i^2}
$$

ESS 越小说明粒子退化越严重，此时需要触发重采样。当 ESS 低于阈值时，说明少数粒子占据了大部分权重，大量粒子对后验估计几乎没有贡献。

## 应用场景

- **行人跟踪**：在 Freespace 障碍物边界跟踪中，针对行人目标采用粒子滤波进行状态估计，能够有效处理行人的非线性和不可预测运动
- **多假设跟踪**：粒子天然支持多模态分布，适用于存在多个可能状态的场景
- **强非线性系统**：当运动模型或观测模型存在强非线性时，EKF 的一阶近似误差过大，PF 是更好的选择

## 优缺点

**优点**：
- 能处理任意非线性非高斯系统
- 天然支持多模态分布
- 实现相对简单

**缺点**：
- 计算量大，粒子数需求高
- 高维空间中存在维度灾难
- 粒子退化问题需要频繁重采样

## 相关页面

- [卡尔曼滤波 (KF)](./kalman-filter.md)
- [扩展卡尔曼滤波 (EKF)](./extended-kalman-filter.md)
- [DBSCAN 聚类算法](./dbscan-clustering.md)
- [多传感器融合框架](../fusion/multi-sensor-fusion.md)
