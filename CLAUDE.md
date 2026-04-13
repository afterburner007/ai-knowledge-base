# AI 知识库 — LLM Agent 宪法

> 本文件是知识库的"宪法"。任何对 wiki/、index.md、log.md 的读写操作都必须遵守本文件的规则。

## 核心原则

**知识库是一个持久的、复合的知识资产。** 它不是对原始文档的简单索引——LLM 需要阅读源文件、提取关键信息、并将其整合到已有的 wiki 网络中。当新知识与已有知识矛盾时，LLM 需要标记矛盾。当答案本身有价值时，LLM 应该回写为新的 wiki 页面。

**LLM 不做无聊的簿记工作——但擅长做。** 交叉引用更新、索引同步、孤立页面检查——这些是 LLM 最擅长的自动化任务。

## 目录结构

```
ai-knowledge-base/
├── CLAUDE.md              # 本文件 — 知识库宪法
├── index.md               # 内容索引（LLM 维护的目录）
├── log.md                 # 操作日志（append-only）
├── .obsidian/             # Obsidian Vault 配置
├── templates/             # Obsidian 页面模板
├── raw/                   # 原始源文件（只读，人类放入）
│   ├── 3dgs/             # 3DGS 论文/笔记
│   ├── avm_calib/        # AVM 标定笔记
│   ├── avm_render/       # AVM 渲染笔记
│   ├── cloud_qa/         # 云端质检
│   ├── lane_detection/   # 车道线检测
│   ├── calibration_geo/  # 几何标定
│   ├── fusion/           # 传感器融合
│   ├── debug_tools/      # 调试工具
│   └── ...
├── wiki/                  # LLM 拥有的知识 wiki（你维护这一层）
│   ├── 3dgs/             # 3DGS 主题
│   ├── avm/              # AVM 渲染与标定
│   ├── calibration/      # 标定算法
│   ├── perception/       # 感知与检测
│   ├── tracking/         # 跟踪算法
│   ├── fusion/           # 传感器融合
│   ├── platform/         # 嵌入式平台
│   └── tools/            # 工具与优化器
├── schema/                # 数据 schema 定义
├── server.py              # 轻量 Web 服务
└── public/                # 静态文件
```

**边界规则：**
- `raw/` 是人类放入的原始材料。LLM 可以读取，但不应修改。
- `wiki/` 是 LLM 拥有的知识层。LLM 创建、修改、删除这里的内容。
- `index.md` 和 `log.md` 由 LLM 维护。

## 角色与工作流

你是这个知识库的维护者。你的工作包含三个主要操作：

### 1. Ingest（摄入新源文件）

当用户说"处理 raw/某文件.md"或类似指令时：

1. 读取 `raw/` 中的目标文件
2. 提取关键概念、公式、算法、架构图
3. 判断应创建新 wiki 页面还是更新已有页面：
   - 搜索 `wiki/` 中是否有相关页面
   - 如果有，合并信息并更新
   - 如果没有，创建新页面
4. 新页面必须放在正确的 `wiki/<category>/` 子目录下
5. 每个页面必须包含：
   - YAML frontmatter（title, category, tags, created, updated, sources）
   - 结构化的正文内容
   - `## 相关页面` 章节，链接到相关 wiki 页面（使用 `[[wikilink]]` 格式）
6. 更新 `index.md`：添加或更新对应条目
7. 在 `log.md` 追加一条 ingest 记录：`## [日期] ingest | 标题`
8. 检查并更新受影响页面的交叉引用和 `updated` 日期

### 2. Query（回答问题）

当用户提问时：

1. 先读 `index.md` 定位可能相关的 wiki 页面
2. 读取相关 wiki 页面获取详细信息
3. 综合回答，引用来源页面
4. **如果答案本身有价值**（对比分析、总结、新的洞察），创建新的 wiki 页面：
   - 回写为 `wiki/` 中的新页面
   - 更新 `index.md` 和 `log.md`
   - 在相关页面中添加交叉引用

### 3. Lint（健康检查）

定期或用户要求时执行：

1. 扫描所有 wiki 页面的 frontmatter 是否完整（title, category, tags, created, updated, sources）
2. 检查是否有**孤立页面**（无 inbound link）—— 在 `## 相关页面` 中未被其他页面引用
3. 检查是否有**矛盾**（同一概念在不同页面描述不一致）
   - 如果发现矛盾，在 log.md 记录并在相关页面添加 `> [!矛盾]` 标注
4. 检查是否有概念被多次提及但**没有独立页面**
   - 如果有，创建新 wiki 页面或建议创建
5. 检查 `[[wikilink]]` 是否指向有效的 wiki 文件
   - 链接格式应为 `[[filename-stem|显示文本]]` 或 `[[filename-stem]]`
6. 在 `log.md` 追加 lint 记录

## Wiki 页面规范

### 文件名
- 使用 **kebab-case**，**英文命名**（便于搜索和链接）
- 例如：`fish-eye-camera-model.md`、`kalman-filter.md`

### Frontmatter
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

### 内容格式
- 使用 Markdown 格式
- 数学公式使用 `$$ ... $$`（块级）和 `$ ... $`（行内）
- 代码块标明语言类型

### 交叉引用（关键！）
每个 wiki 页面底部必须包含 `## 相关页面` 章节。

**链接格式：** 使用 Obsidian 的 `[[wikilink]]` 语法：
- `[[filename-stem]]` — 链接到文件，显示文件名为文本
- `[[filename-stem|显示文本]]` — 链接到文件，显示自定义文本

**示例：**
```markdown
## 相关页面

- [[fish-eye-camera-model|Kannala-Brandt 鱼眼相机模型]] -- 相机畸变模型
- [[bev-projection|BEV 鸟瞰图投影]] -- 基于精确外参的 BEV 投影
- [[epipolar-geometry|对极几何推导]] -- 多相机几何约束
```

**重要：** `[[wikilink]]` 中的文件名部分必须是**实际文件名（不含 .md）**，而不是 frontmatter 中的 title。Obsidian 通过文件名匹配页面。

## 索引与日志

### index.md
- 内容导向的分类目录
- 按主题分类列出所有 wiki 页面
- 包含：页面标题（带链接）、简短摘要、更新日期
- 每次 ingest 后必须更新

### log.md
- 时间顺序的操作日志
- **append-only**，永不删除内容
- 格式：`## [YYYY-MM-DD] 类型 | 标题` + 简要描述
- 类型包括：ingest, query, lint, init, refactor

## 主题分类

| 分类 key | 内容 |
|----------|------|
| 3dgs | 3D Gaussian Splatting、HashGrid 编码、神经渲染 |
| avm | AVM 环视渲染、OpenGL、glTF、骨骼动画 |
| calibration | 相机标定（KB 模型、BEV 投影、LUT、在线标定） |
| perception | 图像分割、点云分割、车道线检测、特征匹配 |
| tracking | 卡尔曼滤波、粒子滤波、EKF、DBSCAN |
| fusion | 多传感器融合、Costmap、概率累加 |
| platform | 嵌入式平台优化（TDA4、OpenVX、DMA） |
| tools | Ceres、ONNX Runtime、匈牙利算法等 |

## 日常工作流

```
1. 人类将新文章放入 raw/ 目录
2. 人类对 Agent 说："帮我处理 raw/某文件.md"
3. Agent 读取、提取、创建/更新 wiki 页面、更新 index.md、记录 log.md
4. 人类在 Obsidian 中查看自动生成的文件和关系图谱
```

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
