# Fusion分享

Created: January 10, 2024 5:46 PM
Updated: March 28, 2026 8:56 PM

# 一、COSTMAP

## i.框架结构：

![Untitled](Untitled.png)

## ii.基础原理：

1. 贝叶斯理论
    
    $$
    P(A|B) = \frac{P(B|A)P(A)}{P(B)}
    
    $$
    
2. 马尔可夫（离散时间的马尔可夫链）
    
    下一时刻的状态只与当前时刻的状态有关
    
3. 基础推理过程
    1. grid占有概率：
        
        $$
        odd(s)=\frac{p(s=1)}{p(s=0)}
        $$
        
    2. 当有测量量时刻的概率：
        
        $$
        odd(s|z)=\frac{p(s=1|z)}{p(s=0|z}
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
        
4. 示意图：

![Untitled](Untitled%201.png)

![Untitled](Untitled%202.png)

## iii.实现效果：

### iv.方案优缺点：

优点：

- 各个传感器可以方便的接入，只需要调整先验概率即可
- 不需要对传感器的输入进行过多的处理，可以直接输入

缺点：

- 计算量较高
- 未考虑车辆的位姿概率模型（apa中此问题不明显）

### v.后续改进：

    加入激光数据解决远距离感知不准确与悬空障碍物的问题。视频：

# 二、车位信息：

## i. 计算B、C点模块：

### 1.   **垂直车位：**

![Untitled](Untitled%203.png)

2. 水平车位

![Untitled](Untitled%204.png)

## ii. endpose调整模块

### 1.水平车位

1. Calculate curb position step 0:
    
    ![Untitled](Untitled%205.png)
    
2. Calculate curb position step 1:
    
    ![Untitled](Untitled%206.png)
    
3. Calculate curb position step 2:
    
    ![Untitled](Untitled%207.png)
    
4. Calculate curb position step 3:
    
    ![Untitled](Untitled%208.png)
    
5. Calculate curb position step 4:
    
    ![Untitled](Untitled%209.png)
    
6. Calculate endpose position

![Untitled](Untitled%2010.png)

1. video：

![PixPin_2024-01-11_14-01-50.gif](PixPin_2024-01-11_14-01-50.gif)

### 2.**垂直车位**

![Untitled](Untitled%2011.png)

# 三、单帧矢量化：

![Untitled](Untitled%2012.png)