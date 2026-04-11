---
title: "PVLane 检测系统架构"
category: perception
tags:
  - lane-detection
  - onnx
  - semantic-segmentation
  - multi-camera
  - resnet
  - vargnet
  - cuda
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/lane_detection/pvlane-system-architecture.md
---

# PVLane 检测系统架构

## 一、系统概述

PVLane 是一个基于深度学习的车道线检测系统，支持多种相机视角（单目、侧视、鱼眼）的车道线语义分割。系统采用 ONNX 推理引擎，支持 CUDA 加速，具备高效的数据处理和可视化能力。

## 二、系统架构

```
+-------------------------------------------------------------------+
|                        PVLane 检测系统                              |
+-------------------------------------------------------------------+
|  +-------------+  +-------------+  +-------------+                |
|  | 单目相机     |  | 侧视相机     |  | 鱼眼相机     |                |
|  | (mono)      |  | (side)      |  | (fisheye)   |                |
|  +------+------+  +------+------+  +------+------++               |
|         |                |                |                       |
|         +----------------+----------------+                       |
|                          |                                        |
|         +----------------v----------------+                       |
|         |      数据预处理流水线             |                       |
|         |  - 几何变换 (裁剪/缩放)          |                       |
|         |  - 归一化 (Mean/Std)            |                       |
|         +----------------+----------------+                       |
|                          |                                        |
|         +----------------v----------------+                       |
|         |      ONNX 推理引擎               |                       |
|         |  - CUDA/CPU 执行 provider        |                       |
|         |  - 图优化 (ORT_ENABLE_ALL)       |                       |
|         |  - 单例模式 (懒加载)             |                       |
|         +----------------+----------------+                       |
|                          |                                        |
|         +----------------v----------------+                       |
|         |      后处理流水线               |                       |
|         |  - Mask 生成                   |                       |
|         |  - 可视化渲染                  |                       |
|         |  - 异步队列处理                |                       |
|         +----------------+----------------+                       |
|                          |                                        |
|         +----------------v----------------+                       |
|         |      输出模块                   |                       |
|         |  - mask/ (语义分割结果)         |                       |
|         |  - vis/  (可视化叠加图)         |                       |
|         |  - raw/  (Numpy 原始数据)       |                       |
|         +-------------------------------+                        |
+-------------------------------------------------------------------+
```

## 三、模型配置

### 3.1 模型文件清单

系统支持多种模型配置，每种模型提供 FP32 和 FP16 两种精度：

| 模型文件 | 类型 | 精度 | 用途 |
|----------|------|------|------|
| `V0911-7tasks-7V_pv_monolane_sim.onnx` | 单目 | FP32 | 单目前视车道线检测 |
| `V0911-7tasks-7V_pv_monolane_sim_fp16.onnx` | 单目 | FP16 | 单目前视车道线检测 (半精度) |
| `V0911-7tasks-7V_pv_sidelane_sim.onnx` | 侧视 | FP32 | 侧视车道线检测 |
| `V0911-7tasks-7V_pv_sidelane_sim_fp16.onnx` | 侧视 | FP16 | 侧视车道线检测 (半精度) |
| `mpl_pv_fisheye_vargnet_finetune_0229_iter100000_sim.onnx` | 鱼眼 | FP32 | 鱼眼相机车道线检测 |
| `mpl_pv_fisheye_vargnet_finetune_0229_iter100000_sim_fp16.onnx` | 鱼眼 | FP16 | 鱼眼车道线检测 (半精度) |
| `mono_20241205_v2.4.onnx` | 单目 | - | 单目模型 v2.4 |
| `side_20241205_v2.4.onnx` | 侧视 | - | 侧视模型 v2.4 |
| `pvlane_mono.onnx` | 单目 | - | 通用模型 |

### 3.2 三种模型对比

| 特性 | 单目模型 | 侧视模型 | 鱼眼模型 |
|------|----------|----------|----------|
| 输入尺寸 | 3x544x960 | 3x544x960 | 3x640x960 |
| 输出尺寸 | 272x480 | 272x480 | 640x960 |
| 下采样倍率 | 2x | 2x | 1x (原分辨率) |
| 总节点数 | 168 | 168 | 323 |
| Conv 数量 | 73 | 73 | 128 |
| Backbone | ResNet | ResNet | VarGNet |
| 类别数 | 6 | 4 | - |
| 模型大小 (约) | 50MB | 50MB | 100MB |

### 3.3 单目/侧视模型架构

**网络结构** (ResNet-Backbone + Lane Head)：

```
输入: [B, 3, 544, 960]
         |
         v
+-------------------------------------+
|        Image Backbone (ResNet)      |
|  - conv1: 7x7 卷积, stride=2        |
|  - layer1: Bottleneck x3  [64->256] |
|  - layer2: Bottleneck x4  [256->512]|
|  - layer3: Bottleneck x6  [512->1024]|
|  - layer4: Bottleneck x3  [1024->2048]|
+-------------------------------------+
         |
         v  多尺度特征 {P2, P3, P4}
+-------------------------------------+
|           Mono/Side Neck            |
|  - channel_transform: 1x1 卷积降维   |
|    * P2: 256 -> 64                  |
|    * P3: 512 -> 96                  |
|    * P4: 1024 -> 160                |
|  - 特征融合 + 上采样                 |
+-------------------------------------+
         |
         v
+-------------------------------------+
|          PV Lane Head               |
|  - seg_convs: 分割卷积层            |
|  - stride8: 8 倍上采样到原图 1/8      |
|  - output_convs: 1x1 卷积输出        |
+-------------------------------------+
         |
         v
输出: [B, 272, 480]  (输入 1/2 分辨率)
```

节点统计：

| 类型 | 数量 |
|------|------|
| 总节点数 | 168 |
| Conv | 73 |
| Relu | 61 |
| Add | 20 |
| ConvTranspose | 2 (上采样) |
| MaxPool | 1 |
| ArgMax | 1 |

### 3.4 鱼眼模型架构

**VarGNet (Variable Group Network)** 特点：

- **可变分组卷积**: 不同区域使用不同的卷积核组
- **大感受野**: 适应鱼眼镜头的径向畸变特性
- **多尺度融合**: 13 次 Resize 操作融合多尺度特征

**为什么鱼眼使用 VarGNet 而非 ResNet？**

| 相机类型 | 成像特点 | 对模型的影响 |
|----------|----------|--------------|
| 单目/侧视 | 透视投影，畸变小 | 标准卷积即可有效提取特征 |
| 鱼眼相机 | 球面投影，径向畸变大 | 需要大感受野适应非线性畸变 |

鱼眼相机的成像特点：
- **径向畸变**: 图像边缘的直线呈现弯曲
- **视野范围广**: 通常 >120 deg，甚至达到 180 deg
- **分辨率分布不均**: 中心区域分辨率高，边缘区域压缩严重

### 3.5 训练策略

基于模型命名 `V0911-7tasks-7V` 和 `finetune_0229_iter100000`：

| 训练要素 | 配置 |
|----------|------|
| 预训练 | ImageNet 预训练 ResNet |
| 微调迭代 | 100,000+ iterations |
| 多任务学习 | 7 tasks (可能包含深度、法向量等) |
| 多视角 | 7V (7 个视角联合训练) |
| 损失函数 | CrossEntropy + Dice Loss |
| 数据增强 | 随机裁剪、翻转、颜色抖动 |

## 四、标签字典

### 4.1 单目相机标签 (MONO_LABEL_DICT)

```python
{
    0: "background",    # 背景
    1: "single_line",   # 单实线
    2: "curb",          # 路沿
    3: "double_line",   # 双实线
    4: "wide_line",     # 宽线
    5: "slow_line"      # 减速带
}
```

### 4.2 侧视相机标签 (SIDE_LABEL_DICT)

```python
{
    0: "background",    # 背景
    1: "single_line",   # 单实线
    2: "wide_line",     # 宽线
    3: "double_line"    # 双实线
}
```

## 五、ONNX 推理引擎

推理引擎采用单例模式设计，确保模型只加载一次：

```python
class ONNXInferenceEngine:
    """单例模式确保模型只加载一次"""

    _session = None  # ONNX Session 单例
    _model_path = None

    @classmethod
    def get_session(cls, onnx_path):
        if cls._session is None or cls._model_path != onnx_path:
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            cls._session = ort.InferenceSession(
                onnx_path,
                sess_options=sess_options,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
        return cls._session
```

**关键特性:**
- **单例模式**: 避免重复加载模型
- **CUDA 加速**: 优先使用 GPU 推理
- **图优化**: `ORT_ENABLE_ALL` 级别优化

## 六、异步流水线

系统采用生产者-消费者模式，推理与后处理解耦：

```
+------------------------------------------------------------------+
|                        推理循环                                     |
|  +----------------------------------------------------------+    |
|  |  DataLoader (batch_size=32, num_workers=4)               |    |
|  |  -> ONNX 推理 -> preds [B, H, W]                         |    |
|  +-----------------------+----------------------------------+    |
|                          |                                       |
|                          v                                       |
|              +-------------------+                               |
|              |   result_queue    |  Queue(maxsize=8)            |
|              +---------+---------+                               |
|                        |                                         |
+------------------------+-----------------------------------------+
                         |
                         v
+------------------------------------------------------------------+
|                    后台处理线程                                     |
|  +----------------------------------------------------------+    |
|  |  post_process_worker                                     |    |
|  |  1. 保存 Mask -> mask/*.png                              |    |
|  |  2. 生成彩色遮罩 (COLOR_MAP 向量化染色)                  |    |
|  |  3. 尺寸对齐 (cv2.resize)                                |    |
|  |  4. 图像融合 -> vis/*.jpg (alpha=0.3)                    |    |
|  |  5. 保存原始数据 -> raw/*.npy (可选)                     |    |
|  +----------------------------------------------------------+    |
+------------------------------------------------------------------+
```

### 性能优化策略

| 优化项 | 实现方式 |
|--------|----------|
| 模型加载 | 单例模式，避免重复初始化 |
| 推理加速 | CUDA Execution Provider + 图优化 |
| 数据加载 | PyTorch DataLoader (多进程 num_workers=4) |
| 后处理 | 异步队列 + 后台线程 |
| 内存控制 | Queue 限制 maxsize |
| 向量化染色 | Numpy 索引操作代替循环 |

## 七、数据预处理

```
输入图像 (RGB)
     |
     v
+------------------------+
|  CropTransform (可选)   |  # 后视/左/右相机: 裁剪 (0,120,1920,1080)
+-----------+------------+
            |
            v
+------------------------+
|  Resize                |  # 缩放到目标尺寸
|  - mono: 960x544       |
|  - side: 960x544       |
|  - fisheye: 960x640    |
+-----------+------------+
            |
            v
+------------------------+
|  CustomNormalize       |  # 归一化 (camera_surround 除外)
|  Mean: [123.675, 116.28, 103.53]    |
|  Std:  [58.395, 57.12, 57.375]      |
+-----------+------------+
            |
            v
输出 Tensor [B, 3, H, W]
```

## 八、可视化颜色映射

```python
COLOR_MAP = np.array([
    [0, 0, 0],      # 0: background (黑色)
    [0, 128, 0],    # 1: single_line (绿色)
    [128, 128, 0],  # 2: curb (青色)
    [0, 0, 128],    # 3: double_line (红色)
    [128, 0, 128],  # 4: wide_line (品红)
    [0, 128, 128],  # 5: slow_line (黄色)
])
```

相机颜色映射：

| 相机名称 | 颜色 (BGR) |
|----------|------------|
| camera_front_wide | 红色 (0,0,255) |
| camera_front_narrow | 蓝色 (255,0,0) |
| camera_rear | 红色 (0,0,255) |
| camera_left_back | 蓝色 (255,0,0) |
| camera_left_front | 蓝色 (255,0,0) |
| camera_right_back | 绿色 (0,255,0) |
| camera_right_front | 绿色 (0,255,0) |

## 九、FP16 模型转换

系统提供 `convert_to_fp16.py` 脚本，用于将 FP32 模型转换为 FP16 半精度模型：

```bash
python convert_to_fp16.py --input_path models/model.onnx
```

**优势:**
- 减少模型体积约 50%
- 提升推理速度（尤其是 Tensor Core GPU）
- 保持精度基本不变

## 十、常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| Mask 与原图尺寸不匹配 | cv2.resize + INTER_NEAREST |
| 内存溢出 | Queue 限制 maxsize |
| 模型重复加载 | 单例模式 |
| 后处理阻塞推理 | 异步后台线程 |

## 十一、文件结构

```
pvlane_function/scripts/pvlane/
+-- pvlane_onnx_infer.py          # 核心推理脚本
+-- pvlane_result_save_image.py   # 可视化脚本
+-- convert_to_fp16.py            # FP16 转换脚本
+-- models/
    +-- V0911-7tasks-7V_pv_monolane_sim.onnx
    +-- V0911-7tasks-7V_pv_monolane_sim_fp16.onnx
    +-- V0911-7tasks-7V_pv_sidelane_sim.onnx
    +-- V0911-7tasks-7V_pv_sidelane_sim_fp16.onnx
    +-- mpl_pv_fisheye_vargnet_finetune_0229_iter100000_sim.onnx
    +-- mpl_pv_fisheye_vargnet_finetune_0229_iter100000_sim_fp16.onnx
    +-- mono_20241205_v2.4.onnx
    +-- side_20241205_v2.4.onnx
    +-- pvlane_mono.onnx
```

## 十二、总结

PVLane 检测系统是一个完整的工业级车道线检测方案，具备以下特点：

- **多相机支持**: 单目/侧视/鱼眼
- **高性能推理**: CUDA 加速 + 异步流水线
- **灵活部署**: FP32/FP16 双精度支持
- **完整输出**: Mask + 可视化 + 原始数据
- **可扩展架构**: 模块化设计，易于新增模型和相机类型

## 相关页面

- [PVLane 推理与后处理](./pvlane-inference-postprocess.md) - 模型推理、RLE 编码、连通性分析、轮廓提取与坐标转换的详细算法
- [SuperPoint + LightGlue 特征匹配](./superpoint-lightglue.md) - 基于深度学习的跨视角特征匹配与球面本质矩阵估计
- [云端标定质检方案](./cloud-calibration-qa.md) - 基于图像/点云分割与 Ceres 后端优化的标定质量检验
