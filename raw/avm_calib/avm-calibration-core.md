# AVM 标定系统核心算法原理 副本

**版本**: 1.0 **生成日期**: 2026-03-19 **文档类型**: 核心算法原理文档

---

## 目录

**第一部分 基础理论**

1. [鱼眼相机模型](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#1-%E9%B1%BC%E7%9C%BC%E7%9B%B8%E6%9C%BA%E6%A8%A1%E5%9E%8B)

**第二部分 核心算法** 2. [角点检测层](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#2-%E8%A7%92%E7%82%B9%E6%A3%80%E6%B5%8B%E5%B1%82)

- 2.1 [两级检测架构](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#21-%E4%B8%A4%E7%BA%A7%E6%A3%80%E6%B5%8B%E6%9E%B6%E6%9E%84)
- 2.2 [BEV 投影变换](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#22-bev-%E6%8A%95%E5%BD%B1%E5%8F%98%E6%8D%A2)
- 2.3 [BEV 角点检测](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#23-bev-%E8%A7%92%E7%82%B9%E6%A3%80%E6%B5%8B)

  - 2.3.1 [四象限卷积核设计](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#231-%E5%9B%9B%E8%B1%A1%E9%99%90%E5%8D%B7%E7%A7%AF%E6%A0%B8%E8%AE%BE%E8%AE%A1)
  - 2.3.2 [角点响应计算](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#232-%E8%A7%92%E7%82%B9%E5%93%8D%E5%BA%94%E8%AE%A1%E7%AE%97)
  - 2.3.3 [角点类型判断](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#233-%E8%A7%92%E7%82%B9%E7%B1%BB%E5%9E%8B%E5%88%A4%E6%96%AD)
  - 2.3.4 [非极大值抑制原理](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#234-%E9%9D%9E%E6%9E%81%E5%A4%A7%E5%80%BC%E6%8A%91%E5%88%B6%E5%8E%9F%E7%90%86)
  - 2.3.5 [亚像素优化](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#235-%E4%BA%9A%E5%83%8F%E7%B4%A0%E4%BC%98%E5%8C%96)
  - 2.3.6 [亚像素优化的数学推导](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#236-%E4%BA%9A%E5%83%8F%E7%B4%A0%E4%BC%98%E5%8C%96%E7%9A%84%E6%95%B0%E5%AD%A6%E6%8E%A8%E5%AF%BC%E5%8E%9F%E7%90%86)
- 2.4 [鱼眼图像角点检测](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#24-%E9%B1%BC%E7%9C%BC%E5%9B%BE%E5%83%8F%E8%A7%92%E7%82%B9%E6%A3%80%E6%B5%8B)

  - 2.4.1 [ROI 区域检测策略](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#241-roi-%E5%8C%BA%E5%9F%9F%E6%A3%80%E6%B5%8B%E7%AD%96%E7%95%A5)
  - 2.4.2 [高斯滤波预处理](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#242-%E9%AB%98%E6%96%AF%E6%BB%A4%E6%B3%A2%E9%A2%84%E5%A4%84%E7%90%86)
  - 2.4.3 [威斯滤波角点增强](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#243-%E5%A8%81%E6%96%AF%E6%BB%A4%E6%B3%A2%E8%A7%92%E7%82%B9%E5%A2%9E%E5%BC%BA)
  - 2.4.4 [非极大值抑制](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#244-%E9%9D%9E%E6%9E%81%E5%A4%A7%E5%80%BC%E6%8A%91%E5%88%B6)
  - 2.4.5 [亚像素优化](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#245-%E4%BA%9A%E5%83%8F%E7%B4%A0%E4%BC%98%E5%8C%96)
  - 2.4.6 [鞍点验证](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#246-%E9%9E%8D%E7%82%B9%E9%AA%8C%E8%AF%81)
  - 2.4.7 [消失点计算 R 矩阵](#247-消失点计算 r 矩阵)
- 2.5 [完整检测流程](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#25-%E5%AE%8C%E6%95%B4%E6%A3%80%E6%B5%8B%E6%B5%81%E7%A8%8B)
- 2.6 [棋盘格组织算法](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#26-%E6%A3%8B%E7%9B%98%E6%A0%BC%E7%BB%84%E7%BB%87%E7%AE%97%E6%B3%95)

1. [标定算法流程](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#3-%E6%A0%87%E5%AE%9A%E7%AE%97%E6%B3%95%E6%B5%81%E7%A8%8B)

**第三部分 应用输出** 4. [LUT 生成与图像拼接](https://vscode-remote+ssh-002dremote-002bdby-005fcalib-005fv5.vscode-resource.vscode-cdn.net/mnt/workspace/dlc-zhijiaquanjingpocheziyan-AVM_Calib-master/docs/architecture/avm-calib-core-algorithms.md#4-lut-%E7%94%9F%E6%88%90%E4%B8%8E%E5%9B%BE%E5%83%8F%E6%8B%BC%E6%8E%A5)

---

# 第一部分 基础理论

## 鱼眼相机模型

本系统采用 **Kannala-Brandt (KB) 鱼眼相机模型**，适用于 180°+ 超大视场角的鱼眼相机。

![](static/C9VYbD0EgoMieexRx7ocGbTinbd.png)

### 1.1 KB 投影模型

**从 3D 点到 2D 图像点的投影公式**：

θ=arctan⁡(rf)rd=f⋅(θ+k2θ2+k3θ3+k4θ4+k5θ5)u=cu+xr⋅rdv=cv+yr⋅rd_θrduv_=arctan(_fr_)=_f_⋅(_θ_+_k_2_θ_2+_k_3_θ_3+_k_4_θ_4+_k_5_θ_5)=_cu_+_rx_⋅_rd_=_cv_+_ry_⋅_rd_

**参数说明**：

### 1.2 坐标变换

**世界坐标系 → 相机坐标系**：

Pcam=R⋅Pworld+t**P**_cam_=**R**⋅**P**_world_+**t**

**旋转矩阵构造**（欧拉角 Rx,Ry,Rz_Rx_,_Ry_,_Rz_）：

R=Rz(Rz)⋅Ry(Ry)⋅Rx(Rx)**R**=**R**_z_(_Rz_)⋅**R**_y_(_Ry_)⋅**R**_x_(_Rx_)

---

# 第二部分 核心算法

## 角点检测层

角点检测是 AVM 标定系统的首要环节，检测精度直接决定外参标定准确性。

**技术指标**：

### 2.1 两级检测架构

**技术挑战**：鱼眼 180°+ FOV 导致严重径向畸变，棋盘格在图像边缘严重变形，直接检测困难。

**解决方案**：采用 BEV→ 鱼眼两级检测架构，包含主流程和回退流程。

```
主流程：鱼眼图像 → BEV 投影 → BEV 角点检测 → 反投影 → 鱼眼亚像素优化
              ↑                                                      │
              │                                                      │
              └────────────── 成功 ──────────────────────────────────┘

回退流程：当 BEV 检测失败时
鱼眼图像 → ROI 内鱼眼直接检测 → 消失点计算 R → 重新 BEV 投影 → BEV 检测 → 反投影 → 亚像素优化
```

**完整流程（含回退）**：

```
┌─────────────────────────────────────────────────────────────────┐
                              │                    鱼眼图像 (原始输入)                           │
                              │                   1920×1080 严重畸变                             │
                              └─────────────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
                              ┌─────────────────────────────────────────────────────────────────┐
                              │   第一步：投影变换 (fisheye → BEV)                               │
                              │   使用初始外参，强制相机位于 BEV 平面正上方                         │
                              └─────────────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
                              ┌─────────────────────────────────────────────────────────────────┐
                              │                    BEV 图像 (中间产物)                           │
                              │                    512×512 规则网格                              │
                              └─────────────────────────────────────────────────────────────────┘
                                                          │
                    ┌─────────────────────────────────────┴─────────────────────────────────────┐
                    │                                                                           │
                    ▼                                                                           ▼
    ┌───────────────────────────────────┐                                     ┌───────────────────────────────────┐
    │  主流程：BEV 角点检测成功           │                                     │  回退流程：BEV 角点检测失败         │
    │  (初始外参准确)                   │                                     │  (初始外参偏差大)                 │
    ├───────────────────────────────────┤                                     ├───────────────────────────────────┤
    │ • Find_Corner_BEV::findCorners() │                                     │ • 定义 ROI(中心 50%×55% 区域)        │
    │ • 四象限卷积 + 响应计算            │                                     │ • Find_Corner_Fisheye::findCorners()│
    │ • NMS + 棋盘格组织                │                                     │ • 高斯滤波 + 威斯滤波              │
    │ • 检测到正确数量角点              │                                     │ • NMS + 亚像素优化 + 鞍点验证      │
    └───────────────────────────────────┘                                     │ • 棋盘格组织                       │
                    │                                                         │ • 检测到 ROI 内角点                 │
                    │                                                         └───────────────────────────────────┘
                    │                                                                           │
                    │                                                                           ▼
                    │                                                         ┌───────────────────────────────────┐
                    │                                                         │  消失点计算 R 矩阵                  │
                    │                                                         │ • 去畸变 → 归一化坐标             │
                    │                                                         │ • 拟合行/列平行线                 │
                    │                                                         │ • 计算消失点 VP_x, VP_y           │
                    │                                                         │ • 构建精确旋转矩阵 R              │
                    │                                                         └───────────────────────────────────┘
                    │                                                                           │
                    │                                                                           ▼
                    │                                                         ┌───────────────────────────────────┐
                    │                                                         │  重新 BEV 投影（使用精确 R）         │
                    │                                                         │ • fisheyeImage2BEV(...)          │
                    │                                                         └───────────────────────────────────┘
                    │                                                                           │
                    │                                                                           ▼
                    │                                                         ┌───────────────────────────────────┐
                    │                                                         │  再次 BEV 角点检测                   │
                    │                                                         │ • Find_Corner_BEV::findCorners() │
                    │                                                         │ • 验证数量 + 后处理               │
                    │                                                         └───────────────────────────────────┘
                    │                                                                           │
                    └─────────────────────────────────────┬─────────────────────────────────────┘
                                                          │
                                                          ▼
                              ┌─────────────────────────────────────────────────────────────────┐
                              │   第二步：反投影 (BEV → 鱼眼)                                    │
                              │   Coord_Transform::BEVPoints2Fisheye()                         │
                              │   将 BEV 角点坐标映射回鱼眼图像                                   │
                              └─────────────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
                              ┌─────────────────────────────────────────────────────────────────┐
                              │   第三步：鱼眼亚像素优化                                         │
                              │   Get_SubPixel_Corner::getSubpixelbyLinefit()                  │
                              │   在鱼眼图像上直接优化，达到 0.01 像素精度                         │
                              └─────────────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
                                          最终输出：鱼眼图像上的亚像素角点
```

**模块职责**：

### 2.2 BEV 投影变换

**目的**：将鱼眼图像投影到鸟瞰图（BEV）平面，消除畸变影响。

**投影公式**：

PBEV=1m⋅(Ryaw⋅[xwyw]+[txty])**P**_BEV_=_m_1⋅(**R**_yaw_⋅[_xwyw_]+[_txty_])

其中 m=0.01_m_=0.01 米/像素（BEV 分辨率）。

**代码实现**：

```cpp
_// 1. 计算相机姿态（强制相机位于 BEV 平面正上方）_
cv::Mat rMatrix, camPos, tVecNew;
cv::Rodrigues(rVec, rMatrix);
camPos = -rMatrix.t() * tVec;
camPos.at<float>(0,0) = 0;   _// 强制 X=0_
camPos.at<float>(1,0) = 0.;  _// 强制 Y=0// 2. 仅保留 yaw 角_
cv::Mat YPRAngle;
Coord_Transform::rVec2YPRAngle(rVec, YPRAngle);
YPRAngle.at<float>(0,0) = 0;  _// pitch = 0_
Coord_Transform::YPRAngle2RMatrix(YPRAngle, rMatrix);
tVecNew = -rMatrix * camPos;

_// 3. 投影到 BEV_
Coord_Transform::fisheyeImage2BEV(
    imgFisheyeGray, imgBEVGray,
    rMatrix, tVecNew,
    intrinsic, distortion,
    BEVROI_pixel, meterPerPixel);
```

### 2.3 BEV 角点检测（主流程）

**核心流程**：

```
BEV 图像 (归一化)
    │
    ▼
┌─────────────────────┐
│ 1. 四象限卷积        │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 2. 角点响应计算      │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 3. 非极大值抑制      │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 4. 角点类型判断      │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 5. 亚像素优化        │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 6. 棋盘格组织        │
└─────────────────────┘
    │
    ▼
输出：棋盘格角点 (列主序)
```

#### 2.3.1 四象限卷积核设计

**目的**：检测棋盘格特有的黑白交替图案。

**核心思想**：棋盘格角点的典型特征是四个象限呈现黑白交替分布，对角象限颜色相同。

```
BEV 图像

     ┌─────────┬─────────┐
     │  黑色   │  白色   │
     │ (C1)    │ (C2)    │
     │ 左上    │ 右上    │
     ├─────────┼─────────┤  ← 角点中心
     │  白色   │  黑色   │
     │ (C3)    │ (C4)    │
     │ 左下    │ 右下    │
     └─────────┴─────────┘

特征：C1 ≈ C4 (对角同黑)，C2 ≈ C3 (对角同白)
```

**卷积核可视化**（11×11 核）：

```
kernal1 (左上象限):       kernal2 (右上象限):
  1 1 1 . . . . . . . .     . . . . . 1 1 1 . .
  1 1 1 . . . . . . . .     . . . . . 1 1 1 . .
  1 1 1 . . . . . . . .     . . . . . 1 1 1 . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .

kernal3 (左下象限):       kernal4 (右下象限):
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  . . . . . . . . . . .     . . . . . . . . . . .
  1 1 1 . . . . . . . .     . . . . . 1 1 1 . .
  1 1 1 . . . . . . . .     . . . . . 1 1 1 . .
  1 1 1 . . . . . . . .     . . . . . 1 1 1 . .
```

**中心区域设为 0 的原因**：角点中心可能模糊或不清晰，使用外围区域更鲁棒。

#### 2.3.2 角点响应计算

**双响应图设计**：

```cpp
_// 四象限卷积_
cv::filter2D(imgBEVNorm, conv1, -1, m_kernal1);
cv::filter2D(imgBEVNorm, conv2, -1, m_kernal2);
cv::filter2D(imgBEVNorm, conv3, -1, m_kernal3);
cv::filter2D(imgBEVNorm, conv4, -1, m_kernal4);

_// 响应图 1：对角象限和的差值_
convResult1.forEach<float>([&](float& pixel, const int* pos) {
    pixel = MAX((C1+C4) - (C2+C3), (C2+C3) - (C1+C4));
});

_// 响应图 2：对边角最小 - 最大差异_
convResult2.forEach<float>([&](float& pixel, const int* pos) {
    pixel = MAX(MIN(C1,C4) - MAX(C2,C3), MIN(C2,C3) - MAX(C1,C4));
});
```

**响应图 1 公式**：

R1=∣(C1+C4)−(C2+C3)∣_R_1=∣(_C_1+_C_4)−(_C_2+_C_3)∣

- 物理意义：检测对角象限的灰度差异
- 棋盘格角点：对角同色，差值最大

**响应图 2 公式**：

R2=max⁡(min⁡(C1,C4)−max⁡(C2,C3), min⁡(C2,C3)−max⁡(C1,C4))_R_2=max(min(_C_1,_C_4)−max(_C_2,_C_3), min(_C_2,_C_3)−max(_C_1,_C_4))

- 物理意义：验证对角一致性，排除非对称图案干扰

#### 2.3.3 角点类型判断

**双响应图联合判断**：

cornerType={SADDLE_POINTif R2/R1>0.25EDGE_POINTif R2/R1≤0.25cornerType={SADDLE_POINTEDGE_POINTif _R_2/_R_1>0.25if _R_2/_R_1≤0.25

**为什么使用比值**：

**比值优势**：

1. 尺度不变性：不受图像整体亮度影响
2. 对比度不变性：不受棋盘格黑白对比度影响
3. 鲁棒性：自动适应不同距离的棋盘格

#### 2.3.4 非极大值抑制原理

**目的**：从角点响应图中提取局部最大值点，抑制非极大值响应，从而精确定位角点位置。

**网格化 NMS 算法**：

```cpp
void Basic_Image_Process::nonMaxSuppression(cv::Mat& img,
    int width, float threshold, int height, std::vector<cv::Point2f>& localMax){
    int imgWidth = img.cols;
    int imgHeight = img.rows;
    float* data = img.ptr<float>(0);

    _// 网格化处理（支持并行）_int nWidth = imgWidth / width;
    int nHeight = imgHeight / height;

    for (int i = 0; i < nHeight; i++)
        for (int j = 0; j < nWidth; j++) {
            cv::Rect roi(j * width, i * height, width, height);
            cv::Mat subMatrix = img(roi);
            double minValue, maxValue;
            cv::minMaxLoc(subMatrix, &minValue, &maxValue);

            _// 在网格内找最大值_for (int y = 0; y < height; y++)
                for (int x = 0; x < width; x++) {
                    int index = (i * height + y) * imgWidth + j * width + x;
                    if (data[index] == maxValue && maxValue > threshold) {
                        localMax.push_back(cv::Point2f(j*width+x, i*height+y));
                    }
                }
        }
}
```

**参数设置**：

**算法流程**：

```
输入：角点响应图
    │
    ▼
┌─────────────────────────────────┐
│ 1. 网格化划分                    │
│    - 将图像划分为 11×11 的网格      │
│    - 每个网格独立处理，支持并行   │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. 网格内找最大值                │
│    - cv::minMaxLoc()             │
│    - 获取网格内最大响应值        │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. 阈值筛选                      │
│    - maxValue > threshold        │
│    - threshold = max × 0.1       │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 4. 输出局部极大值点              │
│    - 保存网格内最大响应点坐标    │
└─────────────────────────────────┘
    │
    ▼
输出：候选角点集合
```

**为什么使用网格化 NMS**：

**网格大小的影响**：

- **网格过小**（如 5×5）：角点密度高，可能检测到多个相邻响应
- **网格过大**（如 20×20）：可能遗漏相邻角点，尤其是密集棋盘格
- **网格 11×11**：适合棋盘格角点间距，平衡检测精度和效率

#### 2.3.5 亚像素优化

**目的**：将整数像素位置的角点优化到亚像素精度（±0.01 像素）。

**方法**：线性拟合（沿边缘方向拟合两条直线，交点即为亚像素角点）。

**线性拟合公式**：

沿两条边缘方向分别拟合直线：

y=k1x+b1_y_=_k_1_x_+_b_1

y=k2x+b2_y_=_k_2_x_+_b_2

交点即为亚像素角点：

x∗=b1−b2k2−k1,y∗=k1x∗+b1_x_∗=_k_2−_k_1_b_1−_b_2,_y_∗=_k_1_x_∗+_b_1

**代码实现**：

```cpp
bool Get_SubPixel_Corner::getSubpixelbyLinefit(cv::Mat img,
    std::vector<cv::Point2f>& corners, bool removeOutLiner, int r){
    for (每个角点) {
        _// 1. 提取角点邻域图像块_getImagePatch(img, ui, vi, r, img_sub);

        _// 2. 计算梯度_getImageGradient(img_sub, img_weight, img_angle, img_du, img_dv);

        _// 3. 提取主边缘方向_
        v = orientation2MainEdgesCrossImageCenter(img_weight, img_angle);

        _// 4. 沿边缘方向采样点// 5. 拟合两条直线_
        cv::fitLine(points1, line1_para, cv::DIST_L2, 0, 0.01, 0.01);
        cv::fitLine(points2, line2_para, cv::DIST_L2, 0, 0.01, 0.01);

        _// 6. 计算交点_
        k1 = line1_para[1] / line1_para[0];
        k2 = line2_para[1] / line2_para[0];
        newX = (b1 - b2) / (k2 - k1);
        newY = k1 * newX + b1;

        corner = cv::Point2f(newX, newY);
    }
}
```

#### 2.3.6 亚像素优化的数学推导原理

**二元二次多项式拟合法**：

**假设**：角点邻域内的灰度分布可以用二元二次曲面拟合：

f(x,y)=k0x2+k1y2+k2xy+k3x+k4y+k5_f_(_x_,_y_)=_k_0_x_2+_k_1_y_2+_k_2_xy_+_k_3_x_+_k_4_y_+_k_5

**最小二乘解**：

设邻域内有 n_n_ 个像素点 (xi,yi)(_xi_,_yi_)，对应灰度值为 Ii_Ii_，构建超定方程组：

Ak=b**Ak**=**b**

其中：

A=[x12y12x1y1x1y11x22y22x2y2x2y21⋮⋮⋮⋮⋮⋮xn2yn2xnynxnyn1],k=[k0k1k2k3k4k5],b=[I1I2⋮In]**A**=_x_12_x_22⋮_xn_2_y_12_y_22⋮_yn_2_x_1_y_1_x_2_y_2⋮_xnynx_1_x_2⋮_xny_1_y_2⋮_yn_11⋮1,**k**=_k_0_k_1_k_2_k_3_k_4_k_5,**b**=_I_1_I_2⋮_In_

最小二乘解为：

k=(ATA)−1ATb**k**=(**A**_T_**A**)−1**A**_T_**b**

**鞍点计算**：

二元二次函数的极值点满足：

∂f∂x=2k0x+k2y+k3=0∂_x_∂_f_=2_k_0_x_+_k_2_y_+_k_3=0

∂f∂y=2k1y+k2x+k4=0∂_y_∂_f_=2_k_1_y_+_k_2_x_+_k_4=0

联立解得：

Δx=k2k4−2k1k34k0k1−k22,Δy=k2k3−2k0k44k0k1−k22Δ_x_=4_k_0_k_1−_k_22_k_2_k_4−2_k_1_k_3,Δ_y_=4_k_0_k_1−_k_22_k_2_k_3−2_k_0_k_4

**鞍点条件**：4k0k1−k22<04_k_0_k_1−_k_22<0

当满足鞍点条件时，该点为棋盘格角点（一个方向凸起，垂直方向凹陷）。

**线性拟合法（本系统采用）**：

**步骤 1：提取边缘方向**

计算角点邻域的梯度：

∇I=[GxGy]=[∂I∂x∂I∂y]∇_I_=[_GxGy_]=[∂_x_∂_I_∂_y_∂_I_]

梯度幅值和方向：

∣∇I∣=Gx2+Gy2,θ=arctan⁡(GyGx)∣∇_I_∣=_Gx_2+_Gy_2,_θ_=arctan(_GxGy_)

**步骤 2：沿边缘方向采样**

棋盘格角点有两条相互垂直的边缘，沿两条边缘方向分别采样点集 {(x1i,y1i)}{(_x_1_i_,_y_1_i_)} 和 {(x2i,y2i)}{(_x_2_i_,_y_2_i_)}。

**步骤 3：拟合直线**

使用 `cv::fitLine` 拟合两条直线（最小二乘法）：

直线 1：y=k1x+b1_y_=_k_1_x_+_b_1 直线 2：y=k2x+b2_y_=_k_2_x_+_b_2

**步骤 4：计算交点**

联立两直线方程：

k1x+b1=k2x+b2_k_1_x_+_b_1=_k_2_x_+_b_2

解得：

x∗=b1−b2k2−k1,y∗=k1x∗+b1_x_∗=_k_2−_k_1_b_1−_b_2,_y_∗=_k_1_x_∗+_b_1

**精度分析**：

**影响精度的因素**：

1. **图像噪声**：高斯滤波可抑制噪声
2. **邻域大小**：通常取 7×7 或 11×11
3. **边缘质量**：棋盘格对比度越高，精度越好
4. **梯度计算**：Sobel 算子或更精确的梯度估计

### 2.4 鱼眼图像角点检测（回退流程）

**适用场景**：当初始外参偏差较大时，BEV 投影无法正确消除畸变，棋盘格在 BEV 图像上仍然变形，导致角点检测失败。

**回退策略**：在鱼眼图像上直接检测角点，通过消失点计算精确的旋转矩阵，然后重新进行 BEV 投影。

#### 2.4.1 ROI 区域检测策略

**目的**：鱼眼图像中心区域畸变相对较小，优先在中心区域检测角点，提高检测成功率并减少计算量。

**鱼眼畸变分布特性**：

- **中心区域**：畸变较小，棋盘格形状保持较好
- **边缘区域**：径向畸变严重，棋盘格拉伸变形

**ROI 定义**：

```cpp
cv::Rect ROIfisheye(
    imgFisheyeGray.cols/4,      _// x = 中心 1/4 处_
    imgFisheyeGray.rows/4,      _// y = 中心 1/4 处_
    imgFisheyeGray.cols/2,      _// 宽度 = 图像一半_
    imgFisheyeGray.rows*11/20   _// 高度 = 图像约 55%_
);
```

**ROI 可视化**：

```
┌─────────────────────────────────────────┐
│                                         │
│              鱼眼图像全景                │
│           (1920×1080 典型分辨率)          │
│                                         │
│    ┌─────────────────────────────┐      │
│    │                             │      │
│    │      ROI 检测区域             │      │
│    │    (中心 50% 宽度 × 55% 高度)    │      │
│    │                             │      │
│    │    畸变较小，棋盘格清晰       │      │
│    │                             │      │
│    └─────────────────────────────┘      │
│                                         │
└─────────────────────────────────────────┘
```

**ROI 参数影响**：

#### 2.4.2 高斯滤波预处理

**目的**：抑制图像噪声，平滑棋盘格边缘，为后续威斯滤波提供更稳定的输入。

**高斯滤波公式**：

G(x,y)=12πσ2e−x2+y22σ2_G_(_x_,_y_)=2_πσ_21_e_−2_σ_2_x_2+_y_2

**代码实现**：

```cpp
cv::GaussianBlur(imgFisheyeNorm, imgFisheyeGauss, cv::Size(9, 9), 2, 0);
```

**参数设置**：

**高斯滤波效果**：

```
原始图像 → 高斯滤波后
    │              │
    │  噪声         │  平滑
    │  锐利边缘    │  柔和边缘
    │  高频分量    │  低频分量
```

#### 2.4.3 威斯滤波角点增强

**目的**：增强棋盘格角点的响应，抑制噪声和边缘干扰。

**核心思想**：利用 Hessian 矩阵的特征值关系构建角点响应函数。棋盘格角点在两个垂直方向上具有相反的曲率符号（鞍点特性）。

**Hessian 矩阵**：

H=[LxxLxyLyxLyy]**H**=[_LxxLyxLxyLyy_]

**9×9 邻域模板可视化**：

```
输入像素邻域 (9×9):
 v11 v12 v13 v14 v15 v16 v17 v18 v19
 v21 v22 v23 v24 v25 v26 v27 v28 v29
 v31 v32 v33 v34 v35 v36 v37 v38 v39
 v41 v42 v43 v44 v45 v46 v47 v48 v49
 v51 v52 v53 v54 v55 v56 v57 v58 v59  ← 中心点
 v61 v62 v63 v64 v65 v66 v67 v68 v69
 v71 v72 v73 v74 v75 v76 v77 v78 v79
 v81 v82 v83 v84 v85 v86 v87 v88 v89
 v91 v92 v93 v94 v95 v96 v97 v98 v99

Hessian 矩阵计算采样点:
 • Lxx 采样：v51, v52, v58, v59 (x 方向两侧)
 • Lyy 采样：v15, v25, v85, v95 (y 方向两侧)
 • Lxy 采样：v37, v28, v73, v82 (反对角线方向)
 • Lyx 采样：v33, v22, v88, v77 (主对角线方向)
```

**二阶导数计算**：

Lxx=(v51+v52+v58+v59)−4⋅v55(x 方向曲率)Lyy=(−v15−v25−v85−v95)+4⋅v55(y 方向曲率)Lxy=(v37+v28+v73+v82)−4⋅v55(交叉导数 1)Lyx=(−v33−v22−v88−v77)+4⋅v55(交叉导数 2)_LxxLyyLxyLyx_=(_v_51+_v_52+_v_58+_v_59)−4⋅_v_55(x 方向曲率)=(−_v_15−_v_25−_v_85−_v_95)+4⋅_v_55(y 方向曲率)=(_v_37+_v_28+_v_73+_v_82)−4⋅_v_55(交叉导数 1)=(−_v_33−_v_22−_v_88−_v_77)+4⋅_v_55(交叉导数 2)

**角点响应公式**：

R=Lxy⋅Lyx+Lxx⋅Lyy_R_=_Lxy_⋅_Lyx_+_Lxx_⋅_Lyy_

**代码实现**：

```cpp
void Find_Corner_Fisheye::wsFilter(cv::Mat& img_in, cv::Mat& img_out){
    const int rows = img_in.rows;
    const int cols = img_in.cols;
    img_out = cv::Mat::zeros(rows, cols, CV_32F);

    for (int i = 4; i < rows - 4; ++i) {
        for (int c = 4; c < cols - 4; ++c) {
            _// 读取 9×9 邻域关键位置像素值_float v55 = in[0];
            float v51 = in[-4], v52 = in[-3], v58 = in[3], v59 = in[4];
            float v15 = in[-stride*4], v25 = in[-stride*3];
            float v85 = in[stride*3], v95 = in[stride*4];
            float v37 = in[2-stride*2], v28 = in[3-stride*3];
            float v73 = in[stride*2-2], v82 = in[stride*3-3];
            float v33 = in[-stride*2-2], v22 = in[-stride*3-3];
            float v88 = in[stride*3+3], v77 = in[stride*2+2];

            _// 计算 Hessian 矩阵元素_float Lxx = (v51 + v52 + v58 + v59 - 4 * v55);
            float Lyy = (-v15 - v25 - v85 - v95 + 4 * v55);
            float Lxy = (v37 + v28 + v73 + v82 - 4 * v55);
            float Lyx = (-v33 - v22 - v88 - v77 + 4 * v55);

            _// 角点响应_
            *out = Lxy * Lyx + Lxx * Lyy;

            in++; out++;
        }
        in += 8; out += 8;
    }
}
```

**角点响应分析**：

**为什么使用 **LxyLyx+LxxLyy_LxyLyx_+_LxxLyy_** 而不是 **det⁡(H)det(**H**)：

标准 Hessian 行列式为 det⁡(H)=LxxLyy−Lxy2det(**H**)=_LxxLyy_−_Lxy_2，但本系统采用 LxyLyx+LxxLyy_LxyLyx_+_LxxLyy_：

1. **考虑交叉项符号**：Lxy_Lxy_ 和 Lyx_Lyx_ 分别采样不同方向，乘积保留符号信息
2. **鞍点增强**：棋盘格角点在两个垂直方向曲率相反，LxxLyy<0_LxxLyy_<0 产生大响应
3. **经验验证**：在棋盘格数据集上验证，该公式产生更高的信噪比

#### 2.4.4 非极大值抑制 (NMS)

**目的**：从威斯滤波响应图中提取局部最大值点，抑制非极大值响应，从而精确定位角点位置，同时获得稀疏的候选角点集合。

**网格化 NMS 算法**：

```cpp
void Basic_Image_Process::nonMaxSuppression(cv::Mat& img,
    int width, float threshold, int height, std::vector<cv::Point2f>& localMax){
    int imgWidth = img.cols;
    int imgHeight = img.rows;
    const float* img_ptr = img.ptr<float>(0);

    _// 网格化处理（支持并行）_int nWidth = imgWidth / width;
    int nHeight = imgHeight / height;

    for (int i = 0; i < nHeight; i++)
        for (int j = 0; j < nWidth; j++) {
            cv::Rect roi(j * width, i * height, width, height);
            cv::Mat subMatrix = img(roi);
            double minValue, maxValue;
            cv::minMaxLoc(subMatrix, &minValue, &maxValue);

            _// 在网格内找最大值_for (int y = 0; y < height; y++)
                for (int x = 0; x < width; x++) {
                    int index = (i * height + y) * imgWidth + j * width + x;
                    if (img_ptr[index] == maxValue && maxValue > threshold) {
                        localMax.push_back(cv::Point2f(j*width+x, i*height+y));
                    }
                }
        }
}
```

**参数设置**：

**算法流程**：

```
输入：威斯滤波响应图
    │
    ▼
┌─────────────────────────────────┐
│ 1. 网格化划分                    │
│    - 将图像划分为 11×11 的网格      │
│    - 每个网格独立处理，支持并行   │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. 网格内找最大值                │
│    - cv::minMaxLoc()             │
│    - 获取网格内最大响应值        │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. 阈值筛选                      │
│    - maxValue > threshold        │
│    - threshold = max × 0.1       │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 4. 输出局部极大值点              │
│    - 保存网格内最大响应点坐标    │
└─────────────────────────────────┘
    │
    ▼
输出：候选角点集合
```

**为什么使用网格化 NMS**：

**网格大小的影响**：

- **网格过小**（如 5×5）：角点密度高，可能检测到多个相邻响应
- **网格过大**（如 20×20）：可能遗漏相邻角点，尤其是密集棋盘格
- **网格 11×11**：适合棋盘格角点间距，平衡检测精度和效率

#### 2.4.5 亚像素优化

**目的**：将整数像素位置的角点优化到亚像素精度（±0.01 像素）。

**方法**：线性拟合（沿边缘方向拟合两条直线，交点即为亚像素角点）。

**算法流程**：

```
输入：整数像素角点位置
    │
    ▼
┌─────────────────────────────────┐
│ 1. 提取角点邻域图像块            │
│    - 半径 r = 11 的方形邻域        │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. 计算梯度                      │
│    - Sobel 算子计算 du, dv        │
│    - 计算梯度幅值和方向          │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. 提取主边缘方向                │
│    - 方向直方图 + 均值漂移       │
│    - 找到两个主边缘方向 v1, v2   │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 4. 沿边缘方向采样点              │
│    - 根据方向垂直距离筛选点      │
│    - 要求至少 4 个点               │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 5. 拟合两条直线                  │
│    - cv::fitLine(..., DIST_L2)   │
│    - 最小二乘法拟合              │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 6. 计算交点                      │
│    - 联立两直线方程              │
│    - 得到亚像素角点位置          │
└─────────────────────────────────┘
    │
    ▼
输出：亚像素精度的角点坐标
```

**线性拟合公式**：

沿两条边缘方向分别拟合直线：

y=k1x+b1_y_=_k_1_x_+_b_1

y=k2x+b2_y_=_k_2_x_+_b_2

交点即为亚像素角点：

x∗=b1−b2k2−k1,y∗=k2b1−k1b2k2−k1_x_∗=_k_2−_k_1_b_1−_b_2,_y_∗=_k_2−_k_1_k_2_b_1−_k_1_b_2

**代码实现**：

```cpp
bool Get_SubPixel_Corner::getOneSubpixelbyLinefit(cv::Mat img_src, cv::Point2f& corner, int r, float d_threshold){
    int imgWidth = img_src.cols;
    int imgHeight = img_src.rows;
    float ui = corner.x;
    float vi = corner.y;

    _// 1. 提取角点邻域图像块_
    cv::Mat img_sub, img_du, img_dv, img_weight, img_angle;
    BasicImageProcess.getImagePatch(img_src, ui, vi, r, img_sub);

    _// 2. 计算梯度_
    BasicImageProcess.getImageGradient(img_sub, img_weight, img_angle, img_du, img_dv);

    _// 3. 提取主边缘方向_auto v = BasicImageProcess.orientation2MainEdgesCrossImageCenter(img_weight, img_angle);
    if (v.size() != 2) return false;

    _// 4. 沿边缘方向采样点_
    std::vector<cv::Point2f> points1, points2;
    for (每个像素) {
        _// 计算到两条边缘方向的垂直距离_float d1 = sqrt(w_u * w_u + v_u * v_u);
        float d2 = sqrt(w_u * w_u + v_u * v_u);

        _// 筛选距离小于阈值的点_if (d1 < d_threshold && abs(o_du_norm * v[0][0] + o_dv_norm * v[0][1]) < 0.1)
            points1.push_back(cv::Point2f(...));
        if (d2 < d_threshold && abs(o_du_norm * v[1][0] + o_dv_norm * v[1][1]) < 0.1)
            points2.push_back(cv::Point2f(...));
    }

    _// 5. 拟合两条直线_
    cv::fitLine(points1, line1_para, cv::DIST_L2, 0, 0.01, 0.01);
    cv::fitLine(points2, line2_para, cv::DIST_L2, 0, 0.01, 0.01);

    _// 6. 计算交点_float k1 = line1_para[1] / line1_para[0];
    float b1 = line1_para[3] - k1 * line1_para[2];
    float k2 = line2_para[1] / line2_para[0];
    float b2 = line2_para[3] - k2 * line2_para[2];

    float newX = (b1 - b2) / (k2 - k1);
    float newY = (k2 * b1 - k1 * b2) / (k2 - k1);
    corner = cv::Point2f(newX, newY);
}
```

**参数设置**：

**精度分析**：

**影响精度的因素**：

1. **图像噪声**：高斯滤波可抑制噪声
2. **邻域大小**：通常取 7×7 或 11×11
3. **边缘质量**：棋盘格对比度越高，精度越好
4. **梯度计算**：Sobel 算子或更精确的梯度估计

#### 2.4.7 消失点计算 R 矩阵

**目的**：从鱼眼图像检测到的角点中计算相机精确的旋转矩阵。

**消失点（Vanishing Point）**：空间中平行线在图像平面上的交点。

**计算流程**：

```
┌─────────────────────────────────────────────────────────────────┐
│  输入：鱼眼 ROI 图像上检测到的角点集合                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. 拟合两组平行线                                                │
│     - 棋盘格行方向平行线组                                         │
│     - 棋盘格列方向平行线组                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 计算消失点 V1, V2                                             │
│     - V1 = 行方向平行线交点                                       │
│     - V2 = 列方向平行线交点                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 归一化消失点方向                                              │
│     - v1 = K⁻¹ · V1                                              │
│     - v2 = K⁻¹ · V2                                              │
│     (K 为相机内参矩阵)                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 正交化构建旋转矩阵                                            │
│     - r1 = v1 / ||v1||    (行方向)                                │
│     - r2 = v2 / ||v2||    (列方向)                                │
│     - r3 = r1 × r2        (光轴方向)                              │
│     - R = [r1, r2, r3]                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              输出：精确的旋转矩阵 R
```

**代码实现**：

```cpp
bool Coord_Transform::getRMatrixbyVP(
    std::vector<std::vector<cv::Point2f>> imgPoints,  _// 棋盘格角点 (行主序)_
    cv::Mat& rMatrix,          _// 输出旋转矩阵_const cv::Mat& intrinsic,  _// 相机内参_const cv::Mat& distortion) _// 相机畸变_{
    _// 1. 去畸变：鱼眼坐标 → 归一化平面坐标_
    std::vector<std::vector<cv::Point2f>> undistPoints;
    for (每行角点) {
        fisheyePoints2NormUndist(rowPoints, undistRow, intrinsic, distortion);
        undistPoints.push_back(undistRow);
    }

    _// 2. 拟合两组平行线（行方向和列方向）_
    std::vector<cv::Vec4f> linesH;  _// 行方向平行线_for (每行角点) {
        cv::Vec4f linePara;
        cv::fitLine(rowPoints, linePara, cv::DIST_L2, 0, 0.01, 0.01);
        linesH.push_back(linePara);
    }

    std::vector<cv::Vec4f> linesL;  _// 列方向平行线_for (每列角点) {
        cv::Vec4f linePara;
        cv::fitLine(colPoints, linePara, cv::DIST_L2, 0, 0.01, 0.01);
        linesL.push_back(linePara);
    }

    _// 3. 计算消失点（直线交点）_
    std::vector<cv::Point3f> VPs_x, VPs_y;
    for (每对行线) {
        _// 计算两直线交点 (x, y)// 平行线：交点在无穷远 (z=0)// 相交线：x = (b1-b2)/(k2-k1), y = (k2*b1-k1*b2)/(k2-k1)_
        VPs_y.push_back({x, y, z});
    }
    for (每对列线) {
        VPs_x.push_back({x, y, z});
    }

    _// 4. 平均消失点位置_
    cv::Point3f VP_x = average(VPs_x);
    cv::Point3f VP_y = average(VPs_y);

    _// 5. 归一化并构建旋转矩阵_
    cv::Vec3f col1 = VP_x / cv::norm(VP_x);  _// x 轴方向_
    cv::Vec3f col2 = VP_y / cv::norm(VP_y);  _// y 轴方向_
    cv::Vec3f col3 = col1.cross(col2);       _// z 轴方向（叉乘保证正交）_

    cv::hconcat(col1, col2, col3, rMatrix);
    return true;
}
```

**数学原理**：

**消失点计算**：设消失点 V=(uv,vv)_V_=(_uv_,_vv_)，则其对应的空间方向向量为：

v=K−1⋅[uvvv1]**v**=**K**−1⋅_uvvv_1

**直线拟合**：使用 `cv::fitLine` 拟合每条线的参数 (vx,vy,x0,y0)(_vx_,_vy_,_x_0,_y_0)，其中：

- (vx,vy)(_vx_,_vy_) 是直线的方向向量
- (x0,y0)(_x_0,_y_0) 是直线上的一点

**直线交点计算**：对于两条直线 y=k1x+b1_y_=_k_1_x_+_b_1 和 y=k2x+b2_y_=_k_2_x_+_b_2：

- 平行（∣k1−k2∣<0.01∣_k_1−_k_2∣<0.01）：交点在无穷远，方向向量为 (vx,vy,0)(_vx_,_vy_,0)
- 相交：交点坐标 x=b1−b2k2−k1_x_=_k_2−_k_1_b_1−_b_2，y=k2b1−k1b2k2−k1_y_=_k_2−_k_1_k_2_b_1−_k_1_b_2

**旋转矩阵构造**：

R=[r1r2r3]**R**=[**r**1**r**2**r**3]

其中：

- r1=vx/∣∣vx∣∣**r**1=**v**_x_/∣∣**v**_x_∣∣（列方向，x 轴）
- r2=vy/∣∣vy∣∣**r**2=**v**_y_/∣∣**v**_y_∣∣（行方向，y 轴）
- r3=r1×r2**r**3=**r**1×**r**2（光轴方向，z 轴，叉乘保证正交）

#### 2.4.6 鞍点验证

**目的**：验证检测到的角点是否为棋盘格特有的鞍点（Saddle Point），排除 T 型边缘、角点等非棋盘格特征。

**核心思想**：棋盘格角点的典型特征是四个象限呈现黑白交替分布，对角象限颜色相同。

**四象限模板构建**：

基于角点检测时计算的两个主边缘方向 v1_v_1 和 v2_v_2，将角点邻域划分为四个象限：

```
角点邻域
              │
      象限 1   │   象限 2
    (左上)    │    (右上)
              │
    ──────────┼──────────  v1 方向
              │
      象限 3   │   象限 4
    (左下)    │    (右下)
              │
              v2 方向
```

**算法流程**：

```
输入：角点位置 + 两个主边缘方向 v1, v2
    │
    ▼
┌─────────────────────────────────┐
│ 1. 构建四象限模板                │
│    - 基于 v1, v2 划分四个象限     │
│    - 每个象限赋予权重 1           │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. 计算各象限平均灰度            │
│    - score1 = 象限 1 平均灰度      │
│    - score2 = 象限 2 平均灰度      │
│    - score3 = 象限 3 平均灰度      │
│    - score4 = 象限 4 平均灰度      │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. 计算对角差异                  │
│    - diff13 = |score1 - score3| │
│    - diff24 = |score2 - score4| │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 4. 计算全局一致性度量            │
│    - diffAll = max(min(s1,s3)   │
│                    -max(s2,s4), │
│                    min(s2,s4)   │
│                    -max(s1,s3)) │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 5. 判断是否为鞍点               │
│    - diffAll/diff13 > threshold │
│    - diffAll/diff24 > threshold │
└─────────────────────────────────┘
    │
    ▼
输出：SADDLE_POINT 或 UNKNOW_POINT
```

**代码实现**：

```cpp
bool Find_Corner_Fisheye::pickSaddlePoints(cv::Mat imgFisheyeNorm,
    CORNERS& corners, int radius, float threshold){
    cv::parallel_for_(cv::Range(0, cornerSize),
        [&](const cv::Range& range) -> void {
        for (int i = range.start; i < range.end; i++) {
            float u = corners.p[i].x;
            float v = corners.p[i].y;

            _// 1. 提取角点邻域图像块_
            cv::Mat img_sub, kernal1, kernal2, kernal3, kernal4;
            BasicImageProcess.getImagePatch(imgFisheyeNorm, u, v, radius, img_sub);

            _// 2. 构建四象限模板（基于角点方向 v1, v2）_
            kernal1 = cv::Mat::zeros(radius*2+1, radius*2+1, CV_32FC1);
            kernal2 = cv::Mat::zeros(radius*2+1, radius*2+1, CV_32FC1);
            kernal3 = cv::Mat::zeros(radius*2+1, radius*2+1, CV_32FC1);
            kernal4 = cv::Mat::zeros(radius*2+1, radius*2+1, CV_32FC1);

            for (int ii = 0; ii < radius*2+1; ++ii) {
                for (int jj = 0; jj < radius*2+1; jj++) {
                    cv::Vec2f v3(jj - radius, ii - radius);
                    cv::Vec2f v1 = corners.v1[i];
                    cv::Vec2f v2 = corners.v2[i];

                    _// 判断像素点属于哪个象限_float isBetweenVecs = (v3[0]*v2[1] - v3[1]*v2[0]) *
                                          (v3[0]*v1[1] - v3[1]*v1[0]);
                    if (isBetweenVecs < -0.1) {
                        if (v3[0]*v1[0] + v3[1]*v1[1] > 0)
                            ptr1[jj] = 1;  _// 象限 1_else
                            ptr3[jj] = 1;  _// 象限 3_
                    } else if (isBetweenVecs > 0.1) {
                        if (v3[0]*v2[0] + v3[1]*v2[1] > 0)
                            ptr2[jj] = 1;  _// 象限 2_else
                            ptr4[jj] = 1;  _// 象限 4_
                    }
                }
            }

            _// 3. 计算各象限平均灰度_float score1 = img_sub.dot(kernal1) / cv::sum(kernal1)[0];
            float score2 = img_sub.dot(kernal2) / cv::sum(kernal2)[0];
            float score3 = img_sub.dot(kernal3) / cv::sum(kernal3)[0];
            float score4 = img_sub.dot(kernal4) / cv::sum(kernal4)[0];

            _// 4. 计算对角差异和全局一致性_float diff13 = fabs(score1 - score3);
            float diff24 = fabs(score2 - score4);
            float diffAll = MAX(MIN(score1,score3) - MAX(score2,score4),
                                MIN(score2,score4) - MAX(score1,score3));

            _// 5. 判断是否为鞍点_if (diffAll/diff13 > threshold && diffAll/diff24 > threshold)
                corners.type[i] = SADDLE_POINT;
            else
                corners.type[i] = UNKNOW_POINT;
        }
    });

    _// 6. 剔除非鞍点_for (int i = 0; i < corners.p.size();) {
        if (corners.type[i] != SADDLE_POINT) {
            corners.p.erase(corners.p.begin() + i);
            corners.type.erase(corners.type.begin() + i);
            corners.v1.erase(corners.v1.begin() + i);
            corners.v2.erase(corners.v2.begin() + i);
        } else
            i++;
    }
}
```

**判断条件**：

diff13=∣score1−score3∣diff24=∣score2−score4∣diffAll=max⁡(min⁡(s1,s3)−max⁡(s2,s4),  min⁡(s2,s4)−max⁡(s1,s3))cornerType={SADDLE_POINTif diffAlldiff13>t∧diffAlldiff24>tUNKNOW_POINTotherwisediff13diff24diffAllcornerType=∣score1−score3∣=∣score2−score4∣=max(min(s1,s3)−max(s2,s4),  min(s2,s4)−max(s1,s3))={SADDLE_POINTUNKNOW_POINTif diff13diffAll>_t_∧diff24diffAll>_t_otherwise

**参数设置**：

**验证效果分析**：

**为什么使用比值而不是绝对差值**：

1. **尺度不变性**：不受图像整体亮度影响
2. **对比度不变性**：不受棋盘格黑白对比度影响
3. **鲁棒性**：自动适应不同光照条件下的棋盘格

### 2.5 完整检测流程

**主流程 + 回退流程**：

```
┌────────────────────────────────────────────────────────────────┐
│ Fisheye_Corner_Detect::findAllCorners() 主入口                │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 1. 图像预处理                                                   │
│    - 转为灰度图 (BGR/RGBA → GRAY)                               │
│    - 归一化到 0-1                                                │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 2. BEV 投影（使用初始外参）                                      │
│    - 强制相机位于 BEV 平面正上方 (X=0, Y=0)                        │
│    - 仅保留 yaw 角 (pitch=0)                                     │
│    - fisheyeImage2BEV(...)                                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 3. BEV 角点检测                                                  │
│    - Find_Corner_BEV::findCorners()                             │
│    - 四象限卷积 → 响应计算 → NMS → 棋盘格组织                   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ 验证角点数量       │
                    │ cornersBEV.p.size │
                    └───────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
     ┌─────────────────┐            ┌─────────────────┐
     │ 成功：数量匹配   │            │ 失败：数量不匹配 │
     │ (BEV 检测成功)    │            │ (BEV 检测失败)    │
     └─────────────────┘            └─────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────┐        ┌─────────────────────────────────┐
│ 4a. 反投影到鱼眼图像     │        │ 4b. 回退流程：鱼眼 ROI 内检测      │
│     BEVPoints2Fisheye   │        │     - 定义 ROI(中心 50%×55% 区域)   │
└─────────────────────────┘        │     - 高斯滤波 (9×9, σ=2)          │
              │                    │     - 威斯滤波增强角点             │
              │                    │     - NMS 提取候选点                │
              │                    │     - 线性拟合亚像素优化           │
              │                    │     - 鞍点验证 pickSaddlePoints    │
              │                    │     - 棋盘格组织                   │
              │                    └─────────────────────────────────┘
              │                                         │
              │                                         ▼
              │                    ┌─────────────────────────────────┐
              │                    │ 5b. 消失点计算 R 矩阵              │
              │                    │     getRMatrixbyVP(...)          │
              │                    │     - 去畸变 → 归一化坐标         │
              │                    │     - 拟合行/列平行线             │
              │                    │     - 计算消失点 VP_x, VP_y      │
              │                    │     - 构建旋转矩阵 R              │
              │                    └─────────────────────────────────┘
              │                                         │
              │                                         ▼
              │                    ┌─────────────────────────────────┐
              │                    │ 6b. 重新 BEV 投影（使用精确 R）     │
              │                    │     fisheyeImage2BEV(...)        │
              │                    └─────────────────────────────────┘
              │                                         │
              │                                         ▼
              │                    ┌─────────────────────────────────┐
              │                    │ 7b. 再次 BEV 角点检测               │
              │                    │     Find_Corner_BEV::findCorners │
              │                    └─────────────────────────────────┘
              │                                         │
              │                   ┌──────────────────────┴──────────┘
              │                   │
              │                   ▼
              │         ┌───────────────────┐
              │         │ 验证角点数量      │
              │         │ - 成功：继续       │
              │         │ - 多余<7：剔除     │
              │         │ - 仍失败：返回 false│
              │         └───────────────────┘
              │                   │
              │                   ▼
              └──────►┌─────────────────────────┐
                      │ 8. 反投影到鱼眼图像     │
                      │    BEVPoints2Fisheye    │
                      └─────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ 9. 亚像素优化                                                   │
│    - Get_SubPixel_Corner::getSubpixelbyLinefit()               │
│    - 投影尺度缩放                                              │
│    - 沿边缘方向线性拟合                                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              最终输出：鱼眼图像上的亚像素角点
```

**代码流程**：

```cpp
bool Fisheye_Corner_Detect::findAllCorners(
    cv::Mat imgFisheyeBGR,       _// 输入鱼眼图像_
    cv::Mat rVec, cv::Mat tVec,  _// 初始外参_
    cv::Mat intrinsic, cv::Mat distortion,
    std::vector<cv::Point2f>& corners,  _// 输出角点_
    cv::Vec4f BEVROI,
    cv::Mat& debugImg,
    std::pair<cv::Mat, cv::Mat>& rVectVecOut,  _// 输出的精确外参_int cornerNum){
    _// ========== 1. 图像预处理 ==========_
    cv::Mat imgFisheyeGray;
    if (imgFisheyeBGR.type() == CV_8UC3)
        cv::cvtColor(imgFisheyeBGR, imgFisheyeGray, cv::COLOR_BGR2GRAY);
    else if (imgFisheyeBGR.type() == CV_8UC4)
        cv::cvtColor(imgFisheyeBGR, imgFisheyeGray, cv::COLOR_RGBA2GRAY);

    _// ========== 2. BEV 投影（使用初始外参）==========// 强制相机位于 BEV 平面正上方_
    cv::Mat rMatrix, camPos, tVecNew;
    cv::Rodrigues(rVec, rMatrix);
    camPos = -rMatrix.t() * tVec;
    camPos.at<float>(0,0) = 0;   _// 强制 X=0_
    camPos.at<float>(1,0) = 0.;  _// 强制 Y=0// 仅保留 yaw 角_
    cv::Mat YPRAngle;
    Coord_Transform::rVec2YPRAngle(rVec, YPRAngle);
    YPRAngle.at<float>(0,0) = 0;  _// pitch = 0_
    Coord_Transform::YPRAngle2RMatrix(YPRAngle, rMatrix);
    tVecNew = -rMatrix * camPos;

    _// 投影到 BEV_
    Coord_Transform::fisheyeImage2BEV(imgFisheyeGray, imgBEVGray,
        rMatrix, tVecNew, intrinsic, distortion, BEVROI_pixel, meterPerPixel);

    _// ========== 3. BEV 角点检测 ==========_Find_Corner_BEV FindCornerBEV(...);
    FindCornerBEV.findCorners(imgBEVGrayNorm, cornersBEV);

    _// ========== 4. 验证角点数量 ==========_if (cornersBEV.p.size() == cornerNum) {
        _// ===== 主流程成功：反投影 + 亚像素优化 =====_
        Coord_Transform::BEVPoints2Fisheye(cornersBEV.p, cornersFisheye.p, ...);
        GetSubPixelCorner.getSubpixelbyLinefit(imgFisheyeGray, cornersFisheye.p, ...);
        corners = std::move(cornersFisheye.p);
        return true;
    }

    _// ========== 5. 回退流程：鱼眼 ROI 内检测 ==========_cv::Rect ROIfisheye(
        imgFisheyeGray.cols/4,      _// x = 中心 1/4 处_
        imgFisheyeGray.rows/4,      _// y = 中心 1/4 处_
        imgFisheyeGray.cols/2,      _// 宽度 = 图像一半_
        imgFisheyeGray.rows*11/20   _// 高度 = 图像约 55%_
    );
    cv::Mat imgFisheyeGrayROI = imgFisheyeGray(ROIfisheye).clone();

    _// 鱼眼图像角点检测_
    Find_Corner_Fisheye FindCornerFisheye;
    FindCornerFisheye.findCorners(imgFisheyeGrayROI, cornersFisheyeROI);
    for (auto& p : cornersFisheyeROI)
        p += cv::Point2f(ROIfisheye.x, ROIfisheye.y);  _// 坐标还原// ========== 6. 消失点计算精确 R 矩阵 ==========_
    Coord_Transform::getRMatrixbyVP(cornersFisheyeROI, rMatrix, intrinsic, distortion);

    _// ========== 7. 重新 BEV 投影（使用精确 R）==========_
    tVecNew = -rMatrix * camPos;
    rVectVecOut = std::make_pair(rMatrix, tVecNew);
    Coord_Transform::fisheyeImage2BEV(imgFisheyeGray, imgBEVGray,
        rMatrix, tVecNew, intrinsic, distortion, BEVROI_pixel, meterPerPixel);

    _// ========== 8. 再次 BEV 角点检测 ==========_
    FindCornerBEV.findCorners(imgBEVGrayNorm, cornersBEV);

    _// ========== 9. 验证并后处理 ==========_if (cornersBEV.p.size() > 3 && cornersBEV.p.size() <= cornerNum) {
        _// 成功：反投影 + 亚像素优化_
        Coord_Transform::BEVPoints2Fisheye(cornersBEV.p, cornersFisheye.p, ...);
        GetSubPixelCorner.getSubpixelbyLinefit(imgFisheyeGray, cornersFisheye.p, ...);
        corners = std::move(cornersFisheye.p);
        return true;
    }
    else if (cornersBEV.p.size() > cornerNum && cornersBEV.p.size() - cornerNum < 7) {
        _// 角点数量多余但少于 7 个：按 Y 坐标排序剔除多余的_
        std::sort(cornersBEV.p.begin(), cornersBEV.p.end(),
            [](cv::Point2f a, cv::Point2f b) { return a.y < b.y; });
        _// 剔除多余的角点..._
        Coord_Transform::BEVPoints2Fisheye(cornersBEV.p, cornersFisheye.p, ...);
        GetSubPixelCorner.getSubpixelbyLinefit(imgFisheyeGray, cornersFisheye.p, ...);
        corners = std::move(cornersFisheye.p);
        return true;
    }

    return false;  _// 检测失败_
}
```

### 2.6 棋盘格组织算法

**目的**：从离散的角点集合中组织成规则的棋盘格结构。

#### 2.6.1 十字初始化

从中心角点出发，找到上下左右四个相邻角点，形成 3×3 十字。

**方向一致性检查**：

∣∣2dir−vc−vi∣∣<0.2∣∣2**dir**−**v**_c_−**v**_i_∣∣<0.2

#### 2.6.2 能量函数

衡量棋盘格假设的质量：

E=λ⋅(∣∣v0+v1−2d1∣∣+∣∣v1+v2−2d2∣∣)+∣d1−d2∣min⁡(d1,d2)_E_=_λ_⋅(∣∣**v**0+**v**1−2**d**1∣∣+∣∣**v**1+**v**2−2**d**2∣∣)+min(_d_1,_d_2)∣_d_1−_d_2∣

**接受条件**：E<15_E_<15

#### 2.6.3 棋盘格生长

基于已有棋盘格，预测并扩展下一行/列。

---

## 标定算法流程

### 3.1 PnP 求解原理

**PnP 问题**：通过 n 个 3D 点及其对应的 2D 图像点求解相机位姿。

**重投影误差**：

E=∑i=1n∥pi−π(R,t,K,D,Pi)∥2_E_=_i_=1∑_n_∥**p**_i_−_π_(**R**,**t**,**K**,**D**,**P**_i_)∥2

**优化目标**：

(R∗,t∗)=arg⁡min⁡R,tE(**R**∗,**t**∗)=arg**R**,**t**min_E_

**求解方法**：

1. **DLT (Direct Linear Transform)**：初始值估计
2. **高斯 - 牛顿迭代**：非线性优化

**迭代公式**：

J=∂π∂[R∣t]Δx=−(JTJ)−1JTexk+1=xk+Δx**J**Δ**xx**_k_+1=∂[**R**∣**t**]∂_π_=−(**J**_T_**J**)−1**J**_T_**e**=**x**_k_+Δ**x**

### 3.2 完整标定流程

```
[开始]
  │
  ▼
┌─────────────────────────────────┐
│ 1. 初始化                        │
│    - 加载配置文件                │
│    - 初始化参数单例              │
│    - 加载相机内参                │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 2. 场景识别                      │
│    - 识别标靶类型 (棋盘格/菱形)    │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 3. 角点检测 (4 路相机并行)        │
│    - BEV 检测（主流程）           │
│    - 鱼眼检测（回退流程）         │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 4. PnP 求解 (4 路相机)            │
│    - DLT 初始估计                 │
│    - 高斯 - 牛顿迭代优化          │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 5. 联合优化 (可选)               │
│    - 光束平差 (Bundle Adjustment)│
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 6. 误差验证                      │
│    - 重投影误差 < 阈值？          │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 7. 结果保存                      │
│    - 外参保存 (YAML)             │
│    - 误差报告生成                │
└─────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────┐
│ 8. LUT 生成                       │
└─────────────────────────────────┘
  │
  ▼
[结束]
```

---

# 第三部分 应用输出

## LUT 生成与图像拼接

### 4.1 LUT 生成原理

**LUT（Look-Up Table）**：建立目标图像像素与源图像像素之间的映射关系。

**数据结构**：

```cpp
struct vert_tex_coord {
    float u;      _// 源图像 u 坐标_float v;      _// 源图像 v 坐标_float alpha;  _// 融合权重_
};

struct vert_index {
    unsigned char camera_id;  _// 相机 ID_
};
```

### 4.2 2D BEV 生成流程

```
1. 定义 BEV 视图参数
   - 视图宽度：车辆宽度 + 两侧扩展
   - 视图高度：车辆长度 + 前后扩展
   - 分辨率：像素/米 (ppm)

2. 生成 BEV 网格
   - 在 BEV 平面生成均匀网格点

3. 坐标变换
   - 世界点 → 车体系 → 相机系

4. 相机投影
   - 3D 相机系 → 2D 图像系
   - 应用鱼眼畸变模型

5. 融合权重计算
   - 基于距离拼接线的距离

6. LUT 序列化保存
```

### 4.3 单视图

![](static/AONlbhuWmoxDyMxnLBzcXNKZnpc.png)

![](static/UWeUbZSM1oyPpDx4o4kcwm6Cn3g.png)

### 4.4 多波段融合算法

**目的**：在相机重叠区域实现平滑过渡。

**流程**：

1. 构建高斯 - 拉普拉斯金字塔
2. 计算融合权重
3. 金字塔各层加权融合
4. 重构最终图像

**融合权重公式**：

wi(d)={1d<dstitchdblend−(d−dstitch)dblenddstitch≤d<dstitch+dblend0d≥dstitch+dblend_wi_(_d_)=⎩⎨⎧1_dblenddblend_−(_d_−_dstitch_)0_d_<_dstitchdstitch_≤_d_<_dstitch_+_dblendd_≥_dstitch_+_dblend_

### 4.5 支持视图模式

---

**文档结束**
