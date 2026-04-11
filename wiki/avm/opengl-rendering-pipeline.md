---
title: "OpenGL 渲染管线"
category: avm
tags: [OpenGL, 渲染管线, VBO, VAO, Shader, Framebuffer, AVM]
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/avm_render/avm-rendering-notes.md
---

# OpenGL 渲染管线

本文档详述 AVM（Around View Monitor）系统中 OpenGL 渲染管线的完整流程，涵盖从顶点数据到帧缓冲输出的各阶段原理与实现。

## 1. 完整渲染管线

OpenGL 渲染管线是一条将 3D 顶点数据转换为 2D 像素图像的流水线：

```
顶点数据 -> 顶点着色器 -> 图元装配 -> 裁剪 -> 光栅化 -> 片段着色器 -> 深度/模板测试 -> 混合 -> 帧缓冲
```

### 各阶段详解

| 阶段 | 说明 |
|------|------|
| **1. VBO（顶点缓冲对象）** | 存储顶点数据（位置、法线、UV、颜色等），驻留 GPU 内存 |
| **2. VAO（顶点数组对象）** | 记录 VBO 的格式和属性状态，方便快速切换渲染目标 |
| **3. 顶点着色器** | 处理每个顶点，执行坐标变换（局部空间 -> 世界空间 -> 视图空间 -> 裁剪空间） |
| **4. 图元装配** | 将顶点组装成点、线、三角形等图元 |
| **5. 裁剪 (Clipping)** | 剔除视锥体外的图元，提升渲染效率 |
| **6. 光栅化 (Rasterization)** | 将三角形图元转换为像素片段 (Fragment) |
| **7. 片段着色器** | 计算每个片段的最终颜色（纹理采样、光照计算） |
| **8. 深度测试** | 通过深度缓冲判断片段是否被遮挡 |
| **9. 模板测试** | 控制哪些像素区域可以被绘制 |
| **10. 混合 (Blending)** | 处理透明效果，与帧缓冲中已有颜色混合 |
| **11. 帧缓冲** | 输出最终图像到屏幕或纹理 |

## 2. 核心对象与初始化

### 2.1 VBO / VAO 初始化

```cpp
// 创建并绑定 VAO
glGenVertexArrays(1, &VAO);
glBindVertexArray(VAO);

// 创建并绑定 VBO
glGenBuffers(1, &VBO);
glBindBuffer(GL_ARRAY_BUFFER, VBO);
glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);

// 设置顶点属性指针
// location=0: 位置 (vec3)
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, (void*)0);
glEnableVertexAttribArray(0);

// location=1: 法线 (vec3)
glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, (void*)12);
glEnableVertexAttribArray(1);

// location=2: UV 坐标 (vec2)
glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, (void*)24);
glEnableVertexAttribArray(2);

// 解绑 VAO
glBindVertexArray(0);
```

### 2.2 骨骼动画顶点属性

对于带骨骼动画的模型，需额外传入骨骼索引和权重：

```cpp
struct SkinVertex {
    vec3 position;       // 位置
    vec3 normal;         // 法线
    vec2 uv;             // 纹理坐标
    ivec4 boneIndices;   // 最多 4 根影响骨骼的索引
    vec4 boneWeights;    // 对应权重（和为 1.0）
};

// location=3: 骨骼索引 (ivec4)
glVertexAttribPointer(3, 4, GL_INT, GL_FALSE, stride, (void*)32);
glEnableVertexAttribArray(3);

// location=4: 骨骼权重 (vec4)
glVertexAttribPointer(4, 4, GL_FLOAT, GL_FALSE, stride, (void*)48);
glEnableVertexAttribArray(4);
```

## 3. 着色器实现

### 3.1 顶点着色器（含蒙皮计算）

```glsl
#version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoords;
layout(location = 3) in ivec4 aBoneIndices;
layout(location = 4) in vec4 aBoneWeights;

uniform mat4 uBoneMatrices[MAX_BONES];  // 每帧更新的骨骼变换矩阵
uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

out vec3 FragPos;
out vec3 Normal;
out vec2 TexCoords;

void main() {
    // 计算蒙皮变换矩阵（加权混合多根骨骼的影响）
    mat4 skinTransform = mat4(0.0);
    skinTransform += aBoneWeights.x * uBoneMatrices[aBoneIndices.x];
    skinTransform += aBoneWeights.y * uBoneMatrices[aBoneIndices.y];
    skinTransform += aBoneWeights.z * uBoneMatrices[aBoneIndices.z];
    skinTransform += aBoneWeights.w * uBoneMatrices[aBoneIndices.w];

    // 应用蒙皮变换
    vec4 skinPos = skinTransform * vec4(aPos, 1.0);
    vec4 skinNormal = skinTransform * vec4(aNormal, 0.0);

    // MVP 变换
    FragPos = vec3(uModel * skinPos);
    Normal = mat3(transpose(inverse(uModel))) * vec3(skinNormal);
    TexCoords = aTexCoords;

    gl_Position = uProjection * uView * uModel * skinPos;
}
```

### 3.2 坐标变换链

顶点着色器中经历的坐标变换：

$$
\mathbf{p}_{clip} = \mathbf{M}_{projection} \cdot \mathbf{M}_{view} \cdot \mathbf{M}_{model} \cdot \mathbf{p}_{local}
$$

其中：

- $\mathbf{p}_{local}$：模型局部空间坐标
- $\mathbf{M}_{model}$：模型变换矩阵（平移、旋转、缩放）
- $\mathbf{M}_{view}$：视图变换矩阵（相机位置与朝向）
- $\mathbf{M}_{projection}$：投影变换矩阵（透视/正交投影）
- $\mathbf{p}_{clip}$：裁剪空间齐次坐标

## 4. 渲染循环

```cpp
// 每帧渲染
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

// 激活着色器程序
shader.use();

// 设置 MVP 矩阵
shader.setMat4("model", modelMatrix);
shader.setMat4("view", viewMatrix);
shader.setMat4("projection", projectionMatrix);

// 更新骨骼矩阵（如有骨骼动画）
float currentTime = GetCurrentTime();
skeleton.Update(currentTime);
shader.SetInt("uBoneCount", skeleton.GetBoneCount());
for (int i = 0; i < skeleton.GetBoneCount(); i++) {
    shader.SetMat4("uBoneMatrices[" + to_string(i) + "]",
                   skeleton.GetBoneMatrix(i));
}

// 绑定 VAO 并绘制
glBindVertexArray(VAO);
glDrawArrays(GL_TRIANGLES, 0, vertexCount);
```

## 5. 帧缓冲 (Framebuffer)

帧缓冲是 AVM 系统中的关键组件，用于离屏渲染和纹理输出：

1. **创建帧缓冲**：将渲染目标从默认窗口缓冲切换到自定义纹理
2. **渲染到纹理**：在帧缓冲中渲染 AVM 拼接图像
3. **后处理**：对渲染结果进行色调映射、模糊等后处理效果
4. **输出到屏幕**：将最终纹理通过全屏四边形绘制到窗口

```cpp
// 创建帧缓冲对象
glGenFramebuffers(1, &FBO);
glBindFramebuffer(GL_FRAMEBUFFER, FBO);

// 创建纹理附件
glGenTextures(1, &textureColorBuffer);
glBindTexture(GL_TEXTURE_2D, textureColorBuffer);
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, textureColorBuffer, 0);

// 检查帧缓冲完整性
if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
    // 处理错误
}
glBindFramebuffer(GL_FRAMEBUFFER, 0);
```

## 6. 深度测试与混合

### 6.1 深度测试

```cpp
glEnable(GL_DEPTH_TEST);
glDepthFunc(GL_LESS);  // 片段深度值小于缓冲值时才通过
```

### 6.2 混合（透明效果）

```cpp
glEnable(GL_BLEND);
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
```

## 相关页面

- [[gltf-and-skinning|glTF 2.0 格式与骨骼动画]] -- glTF 模型加载与骨骼动画实现
- [[avm-calibration-algorithms|AVM 标定系统核心算法]] -- 鱼眼相机模型与角点检测
- [[opengl-rendering-pipeline|OpenGL 渲染管线]] -- 本文档
