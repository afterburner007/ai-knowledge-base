---
title: "glTF 2.0 格式与骨骼动画"
category: avm
tags: [glTF, FBX, OBJ, 骨骼动画, 蒙皮, PBR, AVM]
created: 2026-04-09
updated: 2026-04-09
sources:
  - raw/avm_render/avm-rendering-notes.md
---

# glTF 2.0 格式与骨骼动画

本文档介绍 glTF 2.0 3D 模型格式的核心概念，对比 FBX、OBJ 等格式，并详述骨骼动画的完整工作流程。

## 1. 3D 格式对比

### glTF 2.0 vs FBX vs OBJ

| 特性 | glTF 2.0 | FBX | OBJ |
|------|----------|-----|-----|
| **开放性** | 开放标准 (Khronos Group) | Autodesk 私有 | 开放但过时 |
| **文件结构** | JSON + Binary (.glb) 或分离式 | 二进制私有格式 | 文本 + 单独 MTL |
| **PBR 材质** | 原生支持 (Metallic-Roughness) | 支持 | 不支持 |
| **动画支持** | 完整（节点/骨骼/变形） | 完整 | 无 |
| **纹理嵌入** | 可嵌入 Base64 或 Binary | 支持 | 需外部文件 |
| **加载速度** | 极快（GPU 就绪格式） | 需大量解析转换 | 需解析计算法线 |
| **文件大小** | 小（二进制 GLB 更紧凑） | 中等 | 大（文本格式） |
| **场景图** | 完整层级结构 | 完整 | 扁平结构 |
| **压缩支持** | Draco 几何压缩、KTX2 纹理 | 不支持 | 不支持 |
| **跨平台兼容** | Web/移动/桌面原生支持 | 需 SDK | 简单但功能有限 |
| **Web 友好** | "3D 领域的 JPEG" | 需转换 | 功能有限 |

### glTF 核心优势

1. **GPU 就绪格式**：数据结构与 GPU 内存布局一致，几乎零拷贝加载
2. **PBR 标准**：基于物理的渲染，Metallic-Roughness 工作流
3. **模块化设计**：Buffer / Accessor / Mesh / Material / Texture 分离
4. **扩展机制**：支持自定义扩展（如 `KHR_lights_punctual`、`KHR_materials_clearcoat`）

## 2. glTF 2.0 文件结构

```
glTF (.gltf + .bin + textures/)
|-- .gltf (JSON)          - 场景描述、节点层次、材质参数
|-- .bin (Binary)         - 顶点、索引、动画数据
+-- textures/             - 图片纹理

GLB (.glb)                - 单文件二进制打包
|-- Header (12 bytes)
|-- JSON Chunk
+-- Binary Chunk
```

### 核心概念

| 概念 | 说明 |
|------|------|
| **Buffer** | 原始二进制数据块 |
| **Accessor** | 描述 Buffer 中数据的类型、数量、步长 |
| **Mesh** | 包含一个或多个 Primitive（图元），引用 Accessor 获取顶点数据 |
| **Node** | 场景图中的节点，包含变换矩阵，引用 Mesh |
| **Scene** | 根节点集合，定义渲染层次结构 |
| **Animation** | 关键帧动画，包含采样器（插值方式）和通道（目标属性） |
| **Skin** | 蒙皮信息，包含逆绑定矩阵和骨骼节点索引 |

## 3. 骨骼动画基础概念

| 术语 | 说明 |
|------|------|
| **骨骼 (Bone)** | 变换矩阵，定义关节位置和方向 |
| **蒙皮 (Skinning)** | 顶点绑定到骨骼，受骨骼影响而产生形变 |
| **权重 (Weight)** | 顶点对每根骨骼的影响程度（通常最多 4 根骨骼） |
| **绑定姿势 (Bind Pose)** | 模型初始状态，骨骼的参考变换 |
| **逆绑定矩阵 (Inverse Bind Matrix)** | 将顶点从模型空间变换到骨骼空间，公式为 $\mathbf{M}_{IBM} = \mathbf{M}_{bind}^{-1}$ |

## 4. 骨骼动画工作流程

```
1. 加载骨骼层次结构 -> 2. 计算逆绑定矩阵 -> 3. 提取动画关键帧
                              |
                              v
4. 每帧插值计算骨骼变换 -> 5. 构建骨骼变换矩阵数组 -> 6. 传入着色器
                              |
                              v
7. 顶点着色器中进行蒙皮计算 -> 8. 输出变换后顶点位置
```

### 4.1 骨骼层次结构

骨骼以树状层级组织，子骨骼继承父骨骼的变换：

```
Root
|-- Spine
|   |-- Head
|   +-- Arm_L
|       |-- ForeArm_L
|       +-- Hand_L
+-- Leg_L
    +-- Foot_L
```

### 4.2 顶点蒙皮数据结构

```cpp
struct SkinVertex {
    vec3 position;
    vec3 normal;
    vec2 uv;
    ivec4 boneIndices;    // 最多 4 根影响骨骼的索引
    vec4 boneWeights;     // 对应权重（和为 1.0）
};
```

### 4.3 关键帧插值

在 CPU 端对动画关键帧进行插值计算，位置使用线性插值，旋转使用球面线性插值 (SLERP)：

```cpp
mat4 InterpolateTransform(float animationTime,
                          const vector<KeyPosition>& positions) {
    // 找到当前帧和下一帧
    int index = FindKeyIndex(positions, animationTime);
    int nextIndex = (index + 1) % positions.size();

    float deltaTime = positions[nextIndex].timeStamp - positions[index].timeStamp;
    float factor = (animationTime - positions[index].timeStamp) / deltaTime;

    // 线性插值位置，球面插值旋转
    vec3 pos = mix(positions[index].position,
                   positions[nextIndex].position, factor);
    quat rot = slerp(positions[index].rotation,
                     positions[nextIndex].rotation, factor);

    return translate(mat4(1.0f), pos) * mat4_cast(rot);
}
```

### 4.4 骨骼变换矩阵递归计算

从根骨骼开始递归计算每根骨骼的最终变换矩阵：

```cpp
void Skeleton::CalculateBoneTransform(const Bone* bone, mat4 parentTransform) {
    // 全局变换 = 父节点变换 * 当前骨骼局部变换
    mat4 globalTransform = parentTransform * bone->mLocalTransform;

    // 最终骨骼矩阵 = 逆绑定矩阵 * 全局变换
    if (bone->mBoneIndex != -1) {
        mFinalBoneMatrices[bone->mBoneIndex] =
            bone->mInverseBindMatrix * globalTransform;
    }

    // 递归处理子骨骼
    for (const auto& child : bone->mChildren) {
        CalculateBoneTransform(child, globalTransform);
    }
}
```

最终骨骼矩阵的数学表达为：

$$
\mathbf{M}_{final} = \mathbf{M}_{IBM} \cdot \mathbf{M}_{global} = \mathbf{M}_{bind}^{-1} \cdot \prod_{i=0}^{n} \mathbf{M}_{local}^{(i)}
$$

### 4.5 着色器蒙皮计算

在顶点着色器中，使用线性混合蒙皮 (Linear Blend Skinning, LBS)：

$$
\mathbf{p}_{skinned} = \left( \sum_{i=1}^{4} w_i \cdot \mathbf{M}_{final}^{(i)} \right) \cdot \mathbf{p}_{local}
$$

其中 $w_i$ 为第 $i$ 根骨骼的权重，$\mathbf{M}_{final}^{(i)}$ 为第 $i$ 根骨骼的最终变换矩阵。

对应的 GLSL 实现参见 [[opengl-rendering-pipeline|OpenGL 渲染管线]] 中的顶点着色器代码。

### 4.6 渲染循环集成

```cpp
// 每帧更新骨骼并上传到 GPU
float currentTime = GetCurrentTime();
skeleton.Update(currentTime);  // 更新骨骼变换
shader.SetInt("uBoneCount", skeleton.GetBoneCount());
for (int i = 0; i < skeleton.GetBoneCount(); i++) {
    shader.SetMat4("uBoneMatrices[" + to_string(i) + "]",
                   skeleton.GetBoneMatrix(i));
}
model.Draw(shader);
```

## 相关页面

- [[opengl-rendering-pipeline|OpenGL 渲染管线]] -- VBO/VAO、着色器、帧缓冲的完整渲染流程
- [[avm-calibration-algorithms|AVM 标定系统核心算法]] -- 鱼眼相机模型与角点检测
- [[gltf-and-skinning|glTF 2.0 格式与骨骼动画]] -- 本文档
