# 面试知识点终结

Created: January 3, 2024 1:59 PM
Updated: March 28, 2026 5:31 PM

# 1.**KF**

1. CV

   1. 模型：

      $$
      \vec{x}(t)=(x, y, v_x, v_y)
      $$
   2. 状态转移函数

      $$
      \vec{x}(t + \Delta t) = 
      \begin{pmatrix}
      x(t) + v_x \cdot \Delta t \\
      y(t) + v_y \cdot \Delta t \\
      v_x \\
      v_y
      \end{pmatrix}
      $$
   3. 状态转移矩阵

   $$
   A = \begin{bmatrix}1 & 0 & t & 0 \\0 & 1 & 0 & t \\0 & 0 & 1 & 0 \\0 & 0 & 0 & 1\end{bmatrix}
   $$
2. CA

   1. 模型：

      $$
      \vec{x}(t)=(x, y, v_x, v_y,a_x,a_y)^T
      $$
   2. 状态转移函数

      $$
      \vec{x}(t + \Delta t) = \begin{pmatrix}x(t) + v_x \cdot \Delta t + \frac{1}{2} \cdot a_x \cdot \Delta t^2 \\y(t) + v_y \cdot \Delta t + \frac{1}{2} \cdot a_y \cdot \Delta t^2 \\v_x + \Delta t \cdot a_x \\v_y + \Delta t \cdot a_y \\a_x \\a_y\end{pmatrix}
      $$
   3. 状态转移矩阵

      $$
      A = \begin{bmatrix}1 & 0 & \Delta t & 0 & \frac{1}{2}\Delta t^2 & 0 \\0 & 1 & 0 & \Delta t & 0 & \frac{1}{2}\Delta t^2 \\0 & 0 & 1 & 0 & \Delta t & 0 \\0 & 0 & 0 & 1 & 0 & \Delta t \\0 & 0 & 0 & 0 & 1 & 0 \\0 & 0 & 0 & 0 & 0 & 1 \\\end{bmatrix}
      $$
3. KF公式：

   1. 预测

      $$
      \hat{x}_{k|k-1} = F_k \hat{x}_{k-1|k-1} + B_k u_k \\
      P_{k|k-1} = F_k P_{k-1|k-1} F_k^T + Q_k
      $$
   2. 更新

      $$
      K_k = P_{k|k-1} H_k^T (H_k P_{k|k-1} H_k^T + R_k)^{-1} \\
      \hat{x}_{k|k} = \hat{x}_{k|k-1} + K_k (z_k - H_k \hat{x}_{k|k-1}) \\
      P_{k|k} = (I - K_k H_k) P_{k|k-1}
      $$
4. Q与R的设定

   1. Q:
      1. CA模型中Q是四维矩阵，且方差即为每一维度的方差，只有相连关系的维度协方差才有值，否则为0
      2. CV模型中Q是六维矩阵。
   2. R：R取决于观测值，如果只能观测到（x,y），那么R即为二维，且只有方差

# 2.**EKF**

1. CTRV

   1. 状态量：

      $$
      \mathbf{X} = \begin{bmatrix}x \\y \\v \\\theta \\\omega\end{bmatrix}
      $$
   2. 状态转移方程：

      $$
      \mathbf{X} =\begin{bmatrix}
      x_k + \frac{v_k}{\omega}\left[\sin(\omega \Delta t + \theta) - \sin(\theta)\right] \\
      y_k + \frac{v_k}{\omega}\left[-\cos(\omega \Delta t + \theta) + \cos(\theta)\right] \\
      v_k \\
      \omega \Delta t + \theta \\
      \omega
      \end{bmatrix}
      $$
   3. 推算过程：

      $$
      \Delta{x}=\int v\cos(\theta_k + \omega (t_k - t_{k+1}))d_t ① \\
      令u = \theta_k + \omega (t - t_k)\\
      du = \omega dt,带入①\\
      \Delta{x}=v\int \cos(u)\frac{1}{w}d_u\\
      \Delta{x}=v[\frac{1}{w}sin(u)]
      _{t_k}^{t_{k+1}}\\
      \Delta{x}=\frac{v}{w}[sin(\theta_k + \omega (t_{k+1} - t_k)-sin(\theta_k + \omega (t_{k} - t_k)]\\
      \Delta{x}=\frac{v}{w}[sin(\theta_k + \omega \Delta{t})-sin(\theta_k)]
      \\
      同理得：\\
      \Delta{y}=\frac{v}{w}[-cos(\theta_k + \omega \Delta{t})+cos(\theta_k)]
      $$
   4. 雅可比矩阵：

      $$
      J_F = \begin{bmatrix}1 & 0 & \frac{1}{\omega} \left[ \sin(\omega \Delta t + \theta) - \sin(\theta) \right] & \frac{v}{\omega^2} \left[ -\cos(\omega \Delta t + \theta) + \cos(\theta) \right] \\0 & 1 & \frac{1}{\omega} \left[ -\cos(\omega \Delta t + \theta) + \cos(\theta) \right] & \frac{v}{\omega^2} \left[ \sin(\omega \Delta t + \theta) - \sin(\theta) \right] \\0 & 0 & 1 & 0 \\0 & 0 & 0 & 1 \\\end{bmatrix}
      $$
2. CTRA:
3. 毫米波的观测矩阵：

   1. 观测矩阵：

      $$
      \mathbf{z}_k = \begin{bmatrix}\rho_k \\\theta_k \\\dot{\rho}_k\end{bmatrix}=\begin{bmatrix}\sqrt{x_k^2 + y_k^2} \\\text{atan2}(y_k, x_k) \\\frac{x_k v_{x,k} + y_k v_{y,k}}{\sqrt{x_k^2 + y_k^2}}\end{bmatrix}=\begin{bmatrix}\sqrt{x_k^2 + y_k^2} \\\text{atan2}(y_k, x_k) \\\frac{x_k v_{x,k}\cos \theta_k + y_k v_{y,k}\sin \theta_k}{\sqrt{x_k^2 + y_k^2}}\end{bmatrix}
      $$
   2. 雅可比矩阵:

   $$
   J_H = \begin{bmatrix}\frac{x_k}{\sqrt{x_k^2 + y_k^2}} & \frac{y_k}{\sqrt{x_k^2 + y_k^2}} & 0 & 0 & 0 \\-\frac{y_k}{x_k^2 + y_k^2} & \frac{x_k}{x_k^2 + y_k^2} & 0 & 0 & 0 \\\frac{y_k(v_{x,k}\cos \theta_k - v_{y,k}\sin \theta_k)}{(x_k^2 + y_k^2)^{\frac{3}{2}}} & -\frac{x_k(v_{x,k}\sin \theta_k + v_{y,k}\cos \theta_k)}{(x_k^2 + y_k^2)^{\frac{3}{2}}} & \frac{x_k \cos \theta_k + y_k \sin \theta_k}{\sqrt{x_k^2 + y_k^2}} & \frac{v_{x,k}\cos \theta_k + v_{y,k}\sin \theta_k}{\sqrt{x_k^2 + y_k^2}} & 0\end{bmatrix}
   $$
4. 泰勒展开公式：

$$
f(x) = f(x_0) + \frac{f'(x_0)}{1!}(x - x_0) + \frac{f''(x_0)}{2!}(x - x_0)^2 + \frac{f'''(x_0)}{3!}(x - x_0)^3 + \ldots + \frac{f^{(n)}(x_0)}{n!}(x - x_0)^n + R_n(x)
$$

# 3.**EMA**

1. 公式：

   $$
   v_t = \beta v_{t-1} + (1 - \beta) \theta_t
   $$
2. 展开

   $$
   v_t=(1-\beta)*(\theta_t+\beta*\theta_{t-1}+\beta^2*\theta_{t-2}......+\beta^{t-1}*\theta_1)
   $$
3. 初始值修正：

   $$
   v_t=\frac{v_t}{1-\beta^t}
   $$

# 4.DBSCAN

1. 算法流程：
   1. 定义Eps 与minPts
   2. 依次访问所有的点，如果被访问过则跳过，否则查找半径为Eps内的所有点
      1. 如果点小于minPts，则认为是噪点
      2. 如果点大于minPts，则认为是核心点
   3. 依次访问半径内的所有点，做ii的操作，知道所有的点都被遍历
2. 可以用flann的最近邻搜索与std::unordered_set来优化

# 5.DP

1. 算法简介：

   1. 找出有序点集上离首末点连线最远的点
   2. 如果此点距离直线的距离大于阈值，则递归这两部分
2. 计算点到直线的距离：(一般式)

   $$
   D=\frac{|Ax_0+By_0+C|}{\sqrt{A^2+B^2}}
   $$

# 6.粒子滤波

1. 权重采样

   1. std::uniform_real_distribution `<float>`
2. 马氏距离

   1. 公式：

      $$
      D_M(\mathbf{x}) = \sqrt{(\mathbf{x} - \boldsymbol{\mu})^T \boldsymbol{\Sigma}^{-1} (\mathbf{x} - \boldsymbol{\mu})}
      $$
   2. 协方差

      $$
      \Sigma=\frac{1}{N-1}*\Sigma(x-\boldsymbol{\mu})*(x-\boldsymbol{\mu})^{T}
      $$
   3. 协方差的逆求不出来的情况：（奇异矩阵）

      1. 样本不足
      2. 所有点都在一条线上
   4. 点小于3则将协方差矩阵设为单位阵，即欧式距离
3. 轮盘赌重采样

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
4. 粒子退化+

   1. ESS：

      $$
      ESS=\frac{1}{\Sigma_1^N{w_i}^2}
      $$

# 7.costmap

1. 贝叶斯理论

   $$
   P(A|B) = \frac{P(B|A)P(A)}{P(B)}
   $$
2. 马尔可夫（离散时间的马尔可夫链）

   1. 下一时刻的状态只与当前时刻的状态有关
3. 基础推理过程

   1. grid占有概率：

      $$
      odd(s)=\frac{p(s=1)}{p(s=0)}
      $$
   2. 当有测量量时刻的概率：

      $$
      odd(s|z)=\frac{p(s=1|z)}{p(s=0|z)}
      $$
   3. 贝叶斯展开

      $$
      \text{Odds}(s|z) = \frac{p(s=1|z)}{p(s=0|z)} = \frac{p(s=1)p(z|s=1)/p(z)}{p(s=0)p(z|s=0)/p(z)} = \frac{p(z|s=1)}{p(z|s=0)} \times \text{Odds}(s)
      $$
   4. 两边取对数（概率等于0或1会有异常）：

      $$
      \log \text{Odds}(s|z) = \log \frac{p(z|s=1)}{p(z|s=0)} + \log \text{Odds}(s)
      $$
   5. 初始grid概率：

      $$
      odd(s)=\frac{p(s=1)}{p(s=0)}=\frac{0.5}{0.5}=0
      $$

# 8. 匈牙利匹配:
