# 对极几何推导过程 (Epipolar Geometry Derivation)

对极几何描述了同一个空间点在两个相机视角下的成像几何关系。其核心是推导出本质矩阵 (Essential Matrix) 的约束方程。

## 1. 坐标系与变量定义

假设空间中有一点 $P$，在两个相机坐标系下的坐标分别为 $\mathbf{P}_1$ 和 $\mathbf{P}_2$。

- **相机 1 (左)**：光心为 $O_1$，作为参考坐标系。
- **相机 2 (右)**：光心为 $O_2$，相对于相机 1 的旋转为 $R$，平移为 $t$。

**归一化平面坐标**：点 $P$ 在两个相机成像平面上的归一化坐标分别为 $\mathbf{x}_1$ 和 $\mathbf{x}_2$。

根据投影模型，空间点坐标与归一化坐标的关系为：

$$\mathbf{P}_1 = z_1 \mathbf{x}_1$$
$$\mathbf{P}_2 = z_2 \mathbf{x}_2$$

其中 $z_1, z_2$ 是点 $P$ 在各自坐标系下的深度值。

## 2. 空间几何约束

根据坐标变换，点 $P$ 在两个坐标系下的位置满足：

$$\mathbf{P}_2 = R \mathbf{P}_1 + t$$

将归一化坐标代入上式：

$$z_2 \mathbf{x}_2 = R (z_1 \mathbf{x}_1) + t$$

## 3. 代数推导步骤

推导的目标是消除深度因子 $z_1$ 和 $z_2$，得到一个仅包含观测值 $\mathbf{x}$ 和位姿 $R, t$ 的等式。

### 第一步：左叉乘 $t$ 消除平移项

在等式两边同时左叉乘平移向量 $t$。由于向量与自身叉乘为零（$t \times t = 0$）：

$$t \times (z_2 \mathbf{x}_2) = t \times (z_1 R \mathbf{x}_1) + t \times t$$

$$z_2 (t \times \mathbf{x}_2) = z_1 (t \times R \mathbf{x}_1)$$

引入反对称矩阵 $[t]_{\times}$，将叉乘写作矩阵乘法形式：

$$z_2 [t]_{\times} \mathbf{x}_2 = z_1 [t]_{\times} R \mathbf{x}_1$$

### 第二步：左点乘 $\mathbf{x}_2^T$ 消除左侧项

在等式两边同时左点乘 $\mathbf{x}_2^T$。由于向量 $t \times \mathbf{x}_2$ 同时垂直于 $t$ 和 $\mathbf{x}_2$，因此它与 $\mathbf{x}_2$ 的点积必定为 $0$：

$$\mathbf{x}_2^T \cdot (z_2 [t]_{\times} \mathbf{x}_2) = \mathbf{x}_2^T \cdot (z_1 [t]_{\times} R \mathbf{x}_1)$$

$$0 = z_1 \mathbf{x}_2^T [t]_{\times} R \mathbf{x}_1$$

### 第三步：化简得到对极约束

由于深度 $z_1$ 是标量且通常不为 $0$，可以将其约去，得到最终的几何约束方程：

$$\mathbf{x}_2^T [t]_{\times} R \mathbf{x}_1 = 0$$

## 4. 结论：本质矩阵 (Essential Matrix)

我们定义中间的矩阵乘积为本质矩阵 $E$：

$$E = [t]_{\times} R$$

则对极约束简化为：

$$\mathbf{x}_2^T E \mathbf{x}_1 = 0$$

**几何意义**：该公式表示向量 $\mathbf{x}_2$、$t$ 和 $R \mathbf{x}_1$ 三者共面。这三个向量共同构成了对极平面 (Epipolar Plane)。

## 5. 补充：基础矩阵 (Fundamental Matrix)

如果考虑相机内参矩阵 $K$，像素坐标 $\mathbf{u}$ 与归一化坐标 $\mathbf{x}$ 的关系为 $\mathbf{u} = K \mathbf{x}$，即 $\mathbf{x} = K^{-1} \mathbf{u}$。

代入上式：

$$(K_2^{-1} \mathbf{u}_2)^T E (K_1^{-1} \mathbf{u}_1) = 0$$

$$\mathbf{u}_2^T (K_2^{-T} E K_1^{-1}) \mathbf{u}_1 = 0$$

定义 **基础矩阵** $F = K_2^{-T} E K_1^{-1}$，则有像素层面的约束：

$$\mathbf{u}_2^T F \mathbf{u}_1 = 0$$

## 6. 补充：BA优化的代价函数

目标函数 (Cost Function)BA 同时优化相机位姿（Poses）和空间点坐标（Points）。假设有 $n$ 个相机位姿 $\xi_i$ 和 $m$ 个 3D 点 $\mathbf{P}_j$，目标是最小化所有观测点的重投影误差：$$\min_{\xi, \mathbf{P}} \sum_{i=1}^{n} \sum_{j=1}^{m} \delta_{ij} \| \mathbf{u}_{ij} - h(\xi_i, \mathbf{P}_j) \|^2$$$\mathbf{u}_{ij}$：第 $j$ 个点在第 $i$ 幅图像上的实际观测像素坐标。$h(\xi_i, \mathbf{P}_j)$：投影函数，利用位姿 $\xi_i$ 和点 $\mathbf{P}_j$ 计算出的预测像素坐标。$\delta_{ij}$：指示变量，如果第 $i$ 个相机能看到第 $j$ 个点则为 1，否则为 0。