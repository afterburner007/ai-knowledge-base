# AI 知识库索引

> 由 LLM 自动维护。每次 ingest 后更新此文件。

## 3D Gaussian Splatting

| 页面 | 摘要 | 更新日期 |
|------|------|----------|
| [3DGS-Calib 架构与算法](wiki/3dgs/3dgs-calib-architecture.md) | MLP 隐式表示的 3DGS 系统，HashGrid 编码，可微光栅化，在线联合标定 | 2026-04-11 |
| [HashGrid 编码原理](wiki/3dgs/hashgrid-encoding.md) | 多分辨率哈希网格编码的数学推导与配置参数 | 2026-04-11 |

## AVM 环视系统

| 页面 | 摘要 | 更新日期 |
|------|------|----------|
| [OpenGL 渲染管线](wiki/avm/opengl-rendering-pipeline.md) | 完整 OpenGL 渲染流程，VBO/VAO，着色器，帧缓冲 | 2026-04-11 |
| [glTF 2.0 格式与骨骼动画](wiki/avm/gltf-and-skinning.md) | glTF 优势对比，骨骼蒙皮动画实现，着色器代码 | 2026-04-11 |
| [AVM 标定系统核心算法](wiki/avm/avm-calibration-algorithms.md) | 鱼眼相机模型，BEV 投影，两级角点检测，LUT 生成 | 2026-04-11 |

## 相机标定

| 页面 | 摘要 | 更新日期 |
|------|------|----------|
| [Kannala-Brandt 鱼眼相机模型](wiki/calibration/fish-eye-camera-model.md) | KB 畸变模型，投影公式，坐标变换 | 2026-04-11 |
| [BEV 投影变换](wiki/calibration/bev-projection.md) | 鸟瞰图投影公式与分辨率设置 | 2026-04-11 |
| [在线道路标定算法](wiki/calibration/online-road-calibration.md) | 基于车道线灭点的在线外参标定 | 2026-04-11 |
| [对极几何推导](wiki/calibration/epipolar-geometry.md) | 本质矩阵、基础矩阵推导，BA 优化 | 2026-04-11 |

## 感知与检测

| 页面 | 摘要 | 更新日期 |
|------|------|----------|
| [PVLane 检测系统架构](wiki/perception/pvlane-system-architecture.md) | 多相机车道线检测系统，ONNX 推理，异步后处理 | 2026-04-11 |
| [PVLane 推理与后处理](wiki/perception/pvlane-inference-postprocess.md) | RLE 编码，连通性分析，轮廓提取，坐标转换 | 2026-04-11 |
| [云端标定质检方案](wiki/perception/cloud-calibration-qa.md) | 图像/点云分割匹配，Ceres 后端多约束优化 | 2026-04-11 |
| [SuperPoint + LightGlue 特征匹配](wiki/perception/superpoint-lightglue.md) | 特征提取，Transformer 匹配，球面本质矩阵估计 | 2026-04-11 |

## 跟踪与滤波

| 页面 | 摘要 | 更新日期 |
|------|------|----------|
| [卡尔曼滤波 (KF)](wiki/tracking/kalman-filter.md) | CV/CA 模型，预测与更新公式，应用场景 | 2026-04-11 |
| [扩展卡尔曼滤波 (EKF)](wiki/tracking/extended-kalman-filter.md) | CTRV 模型，雅可比矩阵，非线性状态估计 | 2026-04-11 |
| [粒子滤波 (PF)](wiki/tracking/particle-filter.md) | 权重采样，马氏距离，重采样策略 | 2026-04-11 |
| [DBSCAN 聚类算法](wiki/tracking/dbscan-clustering.md) | 密度聚类原理，FLANN 加速，应用场景 | 2026-04-11 |

## 传感器融合

| 页面 | 摘要 | 更新日期 |
|------|------|----------|
| [多传感器融合框架](wiki/fusion/multi-sensor-fusion.md) | 超声/视觉融合，车位信息提取，Endpose 调整 | 2026-04-11 |
| [Costmap 概率累加模型](wiki/fusion/costmap-probabilistic.md) | 贝叶斯推理，马尔可夫链，log-odds 更新 | 2026-04-11 |

## 嵌入式平台

| 页面 | 摘要 | 更新日期 |
|------|------|----------|
| [TDA4 OpenVX 优化](wiki/platform/tda4-openvx-optimization.md) | 计算图重构，DSP Kernel 卸载，DMA 与 Ping-Pong 缓存 | 2026-04-11 |

## 工具与优化

|------|------|----------|
| [Ceres 非线性优化](wiki/tools/ceres-optimization.md) | 车道线约束，重投影优化，代价函数设计 | 2026-04-11 |
| [匈牙利匹配算法](wiki/tools/hungarian-matching.md) | 跨相机车道线匹配，空间距离与方向相似性 | 2026-04-11 |
| [EMA 平滑算法](wiki/tools/ema-smoothing.md) | 指数移动平均公式，初始值修正，应用 | 2026-04-11 |
| [Douglas-Peucker 抽稀算法](wiki/tools/douglas-peucker.md) | 递归折线简化，点到直线距离，特征提取 | 2026-04-11 |
