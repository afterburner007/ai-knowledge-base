# 云端数据标定质检方案，相机与激光/相机与相机

# 已实施且有效的方案：

## 图像、点云分割 + 匹配后处理 + 后端优化

### 图像分割：oneformer/sam3

> [!TIP]
> sam3 可以指定关键词分割自己目标对象，且都是实例分割；oneformer 不能指定分割类型，且杆子、建筑物等都不是实例分割

![](static/VvogbwJedoj1rsxbAORc7gBan6f.png)
![](static/CZUUbFlxeob5FzxrraEcuQiHngR.png)

### 点云分割：ptv3

![](static/WCuabzD9dofHzGxs1kscdT50n2f.png)

### 匹配

距离 +IOU+ 覆盖率等

### 后端 ceres 约束

#### 重投影（即尽可能将点在投至分割的图像中）

- 根据图像分割生成 DT 图
- 将点云投影至图中根据 DT 图插值计算出距离
- 最小化距离和

![](static/O6ZOb46mfoY6Wsx2mYocCMVUnZe.png)

![](static/Hww5br2oWoqJ1JxrvakcmhqYnlo.png)

#### 形状（KL 散度）

- 先将激光分割的点云拟合凸包
- 将点云生成的图像与图像分割的图像按像素点进行 KL 计算
- 最小化 KL 计算的值

![](static/IX2mb19yyoPqI8xenLvcxbBunaf.png)

图像的分割 mask 像素点认为是 P（x）；点云生成的图像 mask 像素点认为是 Q（x）

![](static/Yn6kbtYsUoAKSTxOGjjccMMEn4e.png)

#### 边缘

- 使用传统 cv 算法提取图像轮廓
- 基于图像轮廓生成 DT 图
- 使用传统 cv 算法提取点云轮廓点集
- 使得点到图像轮廓的距离最小

![](static/MyDab6odMoXiHWx3AitcKczAnGg.png)

#### 角度（杆子、立柱）

- 将图像的杆子/立柱进行直线拟合
- 使得点云到直线的距离最小

#### roll 角约束

## 模型提取对应的特征点 + 后端优化（侧视与环视）

- 采用 superPoint+lightGlur 进行特征点提取、匹配

1. 特征点对过滤

   1. 对于一个完整的静态 clip，对所有帧进行一次 superpoint+superglue 得到所有帧的特征点对
   2. 所有帧的所有特征点对组成一个四维样本，对这些样本进行聚类
   3. 对于每个聚类，考虑其类内样本数 >15，则认为该聚类是一个鲁棒的特征点对，对其坐标求均值得到该鲁棒的特征点对
2. 给定一组鲁棒的特征点对，完成相对旋转估计

   1. 根据已知平移，构造双向对极误差作为代价函数

   $$
   theta_{\text{sym}} = \arcsin\left( \frac{|\mathbf{p}'^\top E \mathbf{p}|}{\|E \mathbf{p}\|} \right) 
                   + \arcsin\left( \frac{|\mathbf{p}'^\top E \mathbf{p}|}{\|E^\top \mathbf{p}'\|} \right)
   $$

   1. 使用非线性优化和核函数降低异常点影响，得到估计的旋转矩阵

![](static/Y6TpbLxcooZrQUxJjljcBwxUnAg.png)
