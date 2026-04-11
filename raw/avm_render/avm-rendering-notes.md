# AVM 影像渲染开发 - 知识点

## 项目背景
开发智能座舱 360 全景影像功能，提升车载视觉交互体验。

---

## 1. OpenGL 渲染流程

### 完整渲染管线

```
顶点数据 → 顶点着色器 → 图元装配 → 光栅化 → 片段着色器 → 测试/混合 → 帧缓冲
```

### 详细步骤

| 阶段 | 说明 |
|------|------|
| **1. 顶点缓冲对象 (VBO)** | 存储顶点数据（位置、法线、UV、颜色等） |
| **2. 顶点数组对象 (VAO)** | 记录 VBO 格式和状态，方便切换 |
| **3. 顶点着色器 (Vertex Shader)** | 处理每个顶点，执行坐标变换（局部→世界→视图→裁剪空间） |
| **4. 图元装配** | 将顶点组装成点、线、三角形等图元 |
| **5. 裁剪 (Clipping)** | 剔除视锥体外的图元 |
| **6. 光栅化 (Rasterization)** | 将图元转换为像素片段 (Fragment) |
| **7. 片段着色器 (Fragment Shader)** | 计算每个片段的最终颜色（纹理采样、光照计算） |
| **8. 深度测试 (Depth Test)** | 判断片段是否被遮挡 |
| **9. 模板测试 (Stencil Test)** | 控制哪些像素可以被绘制 |
| **10. 混合 (Blending)** | 处理透明效果，与帧缓冲中已有颜色混合 |
| **11. 帧缓冲 (Framebuffer)** | 输出最终图像到屏幕或纹理 |

### 关键代码结构

```cpp
// 初始化流程
glGenVertexArrays(1, &VAO);
glGenBuffers(1, &VBO);
glBindVertexArray(VAO);
glBindBuffer(GL_ARRAY_BUFFER, VBO);
glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
// 设置顶点属性
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, (void*)0);
glEnableVertexAttribArray(0);

// 渲染循环
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
shader.use();
shader.setMat4("model", modelMatrix);
shader.setMat4("view", viewMatrix);
shader.setMat4("projection", projectionMatrix);
glBindVertexArray(VAO);
glDrawArrays(GL_TRIANGLES, 0, vertexCount);
```

---

## 2. glTF 相比其他 3D 格式（FBX、OBJ）的优势

### 格式对比表

| 特性 | glTF 2.0 | FBX | OBJ |
|------|----------|-----|-----|
| **开放性** | 开放标准 (Khronos Group) | Autodesk 私有 | 开放但过时 |
| **文件结构** | JSON + Binary (.glb) 或分离式 | 二进制私有格式 | 文本 + 单独 MTL |
| **PBR 材质** | ✅ 原生支持 (Metallic-Roughness) | ✅ 支持 | ❌ 不支持 |
| **动画支持** | ✅ 完整（节点/骨骼/变形） | ✅ 完整 | ❌ 无 |
| **纹理嵌入** | ✅ 可嵌入 Base64 或 Binary | ✅ 支持 | ❌ 需外部文件 |
| **加载速度** | ⚡ 极快（GPU 就绪格式） | 🐌 需大量解析转换 | 🐌 需解析计算法线 |
| **文件大小** | 小（二进制 GLB 更紧凑） | 中等 | 大（文本格式） |
| **场景图** | ✅ 完整层级结构 | ✅ 完整 | ❌ 扁平结构 |
| **压缩支持** | ✅ Draco 几何压缩、KTX2 纹理 | ❌ | ❌ |
| **跨平台兼容** | ✅ Web/移动/桌面原生支持 | ⚠️ 需 SDK | ✅ 简单但功能有限 |
| **Web 友好** | ✅ "3D 领域的 JPEG" | ❌ 需转换 | ⚠️ 功能有限 |

### glTF 核心优势

1. **GPU 就绪格式**：数据结构与 GPU 内存布局一致，几乎零拷贝加载
2. **PBR 标准**：基于物理的渲染，Metallic-Roughness 工作流
3. **模块化设计**：Buffer/Accessor/Mesh/Material/Texture 分离
4. **扩展机制**：支持自定义扩展（如 KHR_lights_punctual、KHR_materials_clearcoat）

### glTF 2.0 文件结构

```
glTF (.gltf + .bin + textures/)
├── .gltf (JSON)          - 场景描述、节点层次、材质参数
├── .bin (Binary)         - 顶点、索引、动画数据
└── textures/             - 图片纹理

GLB (.glb)                - 单文件二进制打包
├── Header (12 bytes)
├── JSON Chunk
└── Binary Chunk
```

---

## 3. 骨骼动画实现流程

### 基本概念

| 术语 | 说明 |
|------|------|
| **骨骼 (Bone)** | 变换矩阵，定义关节位置和方向 |
| **蒙皮 (Skinning)** | 顶点绑定到骨骼，受骨骼影响 |
| **权重 (Weight)** | 顶点对每根骨骼的影响程度（通常最多 4 根） |
| **骨骼权重** | 顶点和骨骼的关联程度 |
| **绑定姿势 (Bind Pose)** | 模型初始状态，骨骼的参考变换 |
| **逆绑定矩阵 (Inverse Bind Matrix)** | 将顶点从模型空间变换到骨骼空间 |

### 实现流程

```
1. 加载骨骼层次结构 → 2. 计算逆绑定矩阵 → 3. 提取动画关键帧
       ↓
4. 每帧插值计算骨骼变换 → 5. 构建骨骼变换矩阵数组 → 6. 传入着色器
       ↓
7. 顶点着色器中进行蒙皮计算 → 8. 输出变换后顶点位置
```

### 详细步骤

#### 步骤 1：骨骼层次结构
```
Root
├── Spine
│   ├── Head
│   └── Arm_L
│       ├── ForeArm_L
│       └── Hand_L
└── Leg_L
    └── Foot_L
```

#### 步骤 2：顶点蒙皮数据
每个顶点存储：
```cpp
struct SkinVertex {
    vec3 position;
    vec3 normal;
    vec2 uv;
    ivec4 boneIndices;    // 最多 4 根影响骨骼的索引
    vec4 boneWeights;     // 对应权重（和为 1.0）
};
```

#### 步骤 3：顶点着色器蒙皮计算
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
    // 计算蒙皮变换矩阵
    mat4 skinTransform = mat4(0.0);
    skinTransform += aBoneWeights.x * uBoneMatrices[aBoneIndices.x];
    skinTransform += aBoneWeights.y * uBoneMatrices[aBoneIndices.y];
    skinTransform += aBoneWeights.z * uBoneMatrices[aBoneIndices.z];
    skinTransform += aBoneWeights.w * uBoneMatrices[aBoneIndices.w];

    // 应用蒙皮变换
    vec4 skinPos = skinTransform * vec4(aPos, 1.0);
    vec4 skinNormal = skinTransform * vec4(aNormal, 0.0);

    FragPos = vec3(uModel * skinPos);
    Normal = mat3(transpose(inverse(uModel))) * vec3(skinNormal);
    TexCoords = aTexCoords;

    gl_Position = uProjection * uView * uModel * skinPos;
}
```

#### 步骤 4：CPU 端骨骼矩阵计算
```cpp
void Skeleton::CalculateBoneTransform(const Bone* bone, mat4 parentTransform) {
    // 全局变换 = 父节点变换 × 当前骨骼变换
    mat4 globalTransform = parentTransform * bone->mLocalTransform;

    // 最终骨骼矩阵 = 逆绑定矩阵 × 全局变换
    if (bone->mBoneIndex != -1) {
        mFinalBoneMatrices[bone->mBoneIndex] =
            bone->mInverseBindMatrix * globalTransform;
    }

    // 递归处理子骨骼
    for (const auto& child : bone->mChildren) {
        CalculateBoneTransform(child, globalTransform);
    }
}

// 动画插值（每个关键帧之间）
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

### 渲染循环

```cpp
// 每帧更新
float currentTime = GetCurrentTime();
skeleton.Update(currentTime);  // 更新骨骼变换
shader.SetInt("uBoneCount", skeleton.GetBoneCount());
for (int i = 0; i < skeleton.GetBoneCount(); i++) {
    shader.SetMat4("uBoneMatrices[" + to_string(i) + "]",
                   skeleton.GetBoneMatrix(i));
}
model.Draw(shader);
```

---

## 项目成果
构建了底层的渲染框架，支撑了座舱影像的高性能实时可视化展示。
