---
title: "EMA 平滑算法"
category: tools
tags:
  - EMA
  - 指数移动平均
  - 时序平滑
  - 传感器滤波
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/debug_tools/project-knowledge-points.md
  - raw/fusion/fusion-notes.md
---

# EMA 平滑算法

## 概述

指数移动平均（Exponential Moving Average, EMA）是一种加权平均滤波器，对近期数据赋予更高权重，对历史数据赋予指数衰减的权重。在自动驾驶系统中，广泛用于传感器检测结果的时序平滑，抑制检测抖动，提升系统稳定性。

## 数学公式

### 递推公式

$$
v_t = \beta v_{t-1} + (1 - \beta) \theta_t
$$

其中：
- $v_t$ 为第 $t$ 时刻的平滑值
- $\theta_t$ 为第 $t$ 时刻的观测值
- $\beta$ 为衰减系数（$0 < \beta < 1$），控制平滑程度

### 展开式

将递推公式展开，可看出 EMA 的加权平均本质：

$$
v_t = (1-\beta) \cdot (\theta_t + \beta \cdot \theta_{t-1} + \beta^2 \cdot \theta_{t-2} + \cdots + \beta^{t-1} \cdot \theta_1)
$$

各项权重呈指数衰减，$\beta$ 越大，历史数据的影响范围越广，平滑效果越强。

### 等效窗口大小

EMA 的等效窗口大小约为：

$$
N \approx \frac{1}{1 - \beta}
$$

| $\beta$ 值 | 等效窗口 | 适用场景 |
|------------|----------|----------|
| 0.5 | ~2 帧 | 快速响应，轻度平滑 |
| 0.9 | ~10 帧 | 中等平滑 |
| 0.95 | ~20 帧 | 强平滑，适用于稳定场景 |
| 0.99 | ~100 帧 | 极强平滑，响应迟缓 |

## 初始值修正

### 偏差问题

在初始阶段（$t$ 较小时），由于 $v_0 = 0$，EMA 估计值会偏向 0：

$$
v_1 = (1 - \beta) \theta_1 \quad \text{（仅为真实值的 $1-\beta$ 倍）}
$$

### 修正公式

对 $v_t$ 进行偏差修正：

$$
v_t^{\text{corrected}} = \frac{v_t}{1 - \beta^t}
$$

当 $t$ 较小时，修正因子 $\frac{1}{1 - \beta^t}$ 显著大于 1，补偿了初始偏差；当 $t$ 增大后，$\beta^t \to 0$，修正因子趋于 1，修正自然消退。

### 修正效果示意

```
t=1:  v_corrected = v_1 / (1 - β)     → 修正 1/(1-β) 倍
t=2:  v_corrected = v_2 / (1 - β²)    → 修正 1/(1-β²) 倍
...
t→∞: v_corrected → v_t               → 无需修正
```

## 应用场景

### 1. 视觉检测结果平滑

在车位检测、车道线检测等视觉算法中，单帧检测结果受光照、遮挡等因素影响存在抖动。EMA 可有效平滑检测位置、角度等连续变量。

### 2. 结合超声传感器动态修正

在泊车系统中，将视觉检测结果与超声传感器的 DE (Distance Estimation) / CE (Closest Edge) 值融合：

```
visual_detection → EMA 平滑 → 平滑后的视觉位置
                          ↓
ultrasonic DE/CE → 动态修正 → 最终轮挡/路沿位置
```

### 3. 多变量平滑

对向量型检测结果（如位置 $(x, y)$、角度 $\theta$）的每个分量独立应用 EMA：

$$
\mathbf{v}_t = \beta \mathbf{v}_{t-1} + (1 - \beta) \boldsymbol{\theta}_t
$$

## 与卡尔曼滤波的比较

| 特性 | EMA | 卡尔曼滤波 (KF) |
|------|-----|-----------------|
| **模型** | 无显式状态模型 | 显式状态转移模型 |
| **噪声建模** | 无，仅参数 $\beta$ | 过程噪声 $Q$ + 观测噪声 $R$ |
| **计算复杂度** | $O(1)$ 每帧 | $O(n^3)$（矩阵求逆） |
| **自适应能力** | 固定 $\beta$ | 协方差自适应 |
| **适用场景** | 快速平滑、轻量级 | 精确状态估计 |

## 代码示例

```cpp
class EMASmoother {
public:
    EMASmoother(double beta) : beta_(beta), v_(0.0), t_(0), initialized_(false) {}

    double update(double theta) {
        if (!initialized_) {
            v_ = theta;
            initialized_ = true;
            t_ = 1;
            return v_;
        }
        v_ = beta_ * v_ + (1.0 - beta_) * theta;
        t_++;
        // 偏差修正
        return v_ / (1.0 - std::pow(beta_, t_));
    }

private:
    double beta_;
    double v_;
    int t_;
    bool initialized_;
};
```

## 相关页面

- [Ceres 非线性优化](./ceres-optimization.md) — 优化结果的后处理平滑
- [匈牙利匹配算法](./hungarian-matching.md) — 匹配结果的时序一致性平滑
- [Douglas-Peucker 抽稀算法](./douglas-peucker.md) — 与 EMA 配合使用：先抽稀再平滑
- [TDA4 OpenVX 系统优化](../platform/tda4-openvx-optimization.md) — 在 DSP 上部署 EMA 滤波
