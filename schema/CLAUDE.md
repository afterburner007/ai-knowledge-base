---
name: knowledge-base-schema
description: Schema for the LLM Wiki knowledge base — tells the LLM how to maintain, ingest, query, and lint the wiki
type: reference
---

# AI 知识库 Schema — 自动驾驶标定与感知

> 本文件是知识库的"宪法"。LLM 在写入、更新、查询 wiki 时必须遵守以下约定。

## 角色

你是这个知识库的维护者。你的职责：
1. **Ingest** — 读取 raw/ 中的新源文件，提取关键信息，写入/更新 wiki/ 中的页面
2. **Query** — 回答用户问题时搜索 wiki 页面，综合答案，并将有价值的分析回写为 wiki 页面
3. **Lint** — 定期检查 wiki 健康：矛盾、过时、孤立页面、缺失交叉引用

## 目录结构

```
ai-knowledge-base/
├── raw/                  # 原始源文件（不可修改，只读）
│   ├── 3dgs/            # 3D Gaussian Splatting 相关论文/笔记
│   ├── avm_render/      # AVM 渲染开发原始笔记
│   ├── avm_calib/       # AVM 标定算法原始笔记
│   ├── cloud_qa/        # 云端质检方案
│   ├── lane_detection/  # 车道线检测（PVLane 等）
│   ├── calibration_geo/ # 几何标定（对极几何、KB 模型等）
│   ├── fusion/          # 传感器融合
│   ├── costmap/         # 代价地图
│   ├── tracking/        # 跟踪算法（KF/EKF/PF）
│   ├── parking/         # 泊车相关
│   ├── platform_optim/  # 平台优化（OpenVX/DMA）
│   ├── debug_tools/     # 调试工具
│   └── assets/          # 图片资源
├── wiki/                 # LLM 维护的知识 wiki（你拥有这一层）
│   ├── 3dgs/            # 3DGS 主题
│   ├── avm/             # AVM 渲染与标定
│   ├── calibration/     # 标定算法
│   ├── perception/      # 感知/检测
│   ├── tracking/        # 跟踪算法
│   ├── fusion/          # 传感器融合
│   ├── platform/        # 嵌入式平台
│   └── tools/           # 工具与优化器
├── schema/
│   └── CLAUDE.md        # 本文件 — wiki 维护规范
├── index.md              # 内容索引（LLM 维护）
├── log.md                # 操作日志（append-only，LLM 维护）
├── server.py             # 轻量 Web 服务
└── public/               # Web 服务静态文件
```

## Wiki 页面规范

### 文件名
- 使用 kebab-case，英文命名（便于搜索和链接）
- 例如：`fish-eye-camera-model.md`、`kalman-filter.md`

### 页面头部
每个 wiki 页面必须以 YAML frontmatter 开头：

```yaml
---
title: 页面中文标题
category: 所属分类（3dgs | avm | calibration | perception | tracking | fusion | platform | tools）
tags: [标签1, 标签2]
created: 2026-04-09
updated: 2026-04-09
sources: [关联的 raw 文件路径]
---
```

### 页面内容
- 使用 Markdown 格式
- 数学公式使用 `$$ ... $$`（块级）和 `$ ... $`（行内）
- 代码块标明语言类型
- **必须包含交叉引用**：在页面底部添加 `## 相关页面` 章节，用 `[标题](../category/page.md)` 链接

### 交叉引用
- 在正文中提及另一个 wiki 页面的概念时，使用内联链接
- 页面底部必须有 `## 相关页面` 章节

## 工作流

### Ingest（摄入新源文件）
1. 读取 `raw/` 中的新文件
2. 提取关键概念、公式、算法、架构
3. 在 `wiki/` 中创建或更新对应页面
4. 更新 `index.md`（添加/更新条目）
5. 在 `log.md` 追加一条 ingest 记录
6. 更新被影响页面的交叉引用和 `updated` 日期

### Query（回答问题）
1. 先读 `index.md` 定位相关页面
2. 读取相关 wiki 页面
3. 综合回答，引用来源
4. 如果答案本身有价值（对比分析、总结），回写为 `wiki/` 中的新页面

### Lint（健康检查）
1. 扫描所有 wiki 页面的 frontmatter 是否完整
2. 检查是否有孤立页面（无 inbound link）
3. 检查是否有矛盾（同一概念在不同页面描述不一致）
4. 检查是否有概念被多次提及但没有独立页面
5. 在 `log.md` 追加 lint 记录

## 主题分类

| 分类 | 内容 |
|------|------|
| 3dgs | 3D Gaussian Splatting、HashGrid 编码、神经渲染 |
| avm | AVM 环视渲染、OpenGL、glTF、骨骼动画 |
| calibration | 相机标定（KB 模型、BEV 投影、LUT、在线标定） |
| perception | 图像分割、点云分割、车道线检测、特征匹配 |
| tracking | 卡尔曼滤波、粒子滤波、EKF、DBSCAN |
| fusion | 多传感器融合、Costmap、概率累加 |
| platform | 嵌入式平台优化（TDA4、OpenVX、DMA） |
| tools | Ceres、ONNX Runtime、匈牙利算法等 |
