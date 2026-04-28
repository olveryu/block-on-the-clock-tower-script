# 围城之夜 / Block on the Clock Tower Script

这是"血染钟楼"（Blood on the Clocktower / 染·钟楼谜团）自定义剧本"围城之夜"的工作目录，包含剧本 JSON、模拟记录、说明文档。

## 重要：模拟任务前必读

**任何涉及 BotC / 血染钟楼 / 围城之夜 游戏模拟、剧本平衡测试、角色扮演、说书人裁定的任务，开始前必须先 `Read` 这个文件：**

`.github/instructions/botc-simulation.instructions.md`

里面包含说书人控场原则、角色人数分配表、白天/夜晚流程、信息规则、玩家行为建模、围城之夜特殊规则等。这些是模拟必须遵守的约束，不读会犯系统性错误（如让说书人当中立裁判、让善良玩家上帝视角、违反角色不公开规则等）。

## 目录结构

- `siege.json` / `weicheng.json` — 剧本定义（角色列表、夜晚顺序）
- `simulations/` — 模拟记录输出
- `images/` — 角色图片资源
- `README_CN.md` / `README_EN.md` — 剧本说明（中/英文）
- `migrate.sh` — 资源迁移脚本
