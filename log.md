# AI 知识库操作日志

> Append-only。每次操作追加一条记录。格式：`## [日期] 类型 | 标题`

## [2026-04-09] init | 知识库初始化

- 创建目录结构：raw/, wiki/, schema/, public/
- 从 /home/aspheric/code/resume/Knowledge 迁移 13 篇源文档到 raw/
- 基于 Karpathy LLM Wiki 模式建立架构
- 创建 20 篇 wiki 页面，覆盖 8 大主题分类
- 创建 index.md 内容索引
- 创建轻量 Web 服务（server.py），支持 PC/手机访问

## [2026-04-09] ingest | 项目知识点汇总

- 源文件：raw/debug-tools/project-knowledge-points.md
- 提取知识点：OpenGL、glTF、骨骼动画、KB 模型、BEV 投影、LUT、在线标定、云端质检、PVLane、3DGS、KF/EKF/PF、DBSCAN、DP 算法、Costmap、OpenVX、匈牙利算法、EMA 等
- 写入 20 篇 wiki 页面

## [2026-04-11] refactor | Karpathy LLM Wiki 模式增强 + Obsidian 集成

- 创建根目录 CLAUDE.md（知识库宪法），综合 Karpathy 原始模式与现有 schema
- 创建 .obsidian/ 配置目录（app.json, templates.json），支持直接作为 Obsidian Vault 打开
- 创建 Obsidian 页面模板：templates/wiki-page.md, templates/raw-source.md
- 统一所有 wiki 页面的 [[wikilink]] 格式为 [[filename|显示文本]]，修复 15 处标题格式链接
- 创建 .gitignore
- 更新 index.md 日期
