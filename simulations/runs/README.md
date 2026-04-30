# 模拟记录索引

每次 run 一局都存一份在这里。命名规范：

```
YYYYMMDD_seedNNNNN_<mechanic>_<runner>.md
```

- `mechanic`: `v1` (持续阻止) / `v2` (吸收型，原叫 v6)
- `runner`: `v4`(自动) / `v5manual`(手动详细) / `subagent`(派出 sub-agent)

每个文件 frontmatter 包含 setup（seed、角色分配、bluff）+ 完整流水 + 结局 + 关键转折点 + 机制相关观察。

## 当前记录

| 日期 | seed | 机制 | runner | 胜方 | 天数 | 备注 |
|---|---|---|---|---|---|---|
| 2026-04-29 | 44 | v2 | subagent (compact) | 善良 | D4 | 第一次 v6 单局测试 |
| 2026-04-29 | 44 | v1 | subagent (compact) | 善良 | D4 | 同 setup 旧机制对照 |
| 2026-04-29 | 44 | v1 | subagent (3 runs) | 1邪 / 2善 | avg 4.67 | 激进邪恶 batch |
| 2026-04-29 | 44 | v2 | subagent (3 runs) | 1邪 / 2善 | avg 5.00 | 激进邪恶 batch |
| 2026-04-29 | 24065 | v2 | subagent (compact) | 善良 | D3 | 随机 seed，无盾卫单保险栓 |
| 2026-04-29 | 91019 | v2 | v5manual (detailed) | 善良 | D3 | 详细 3 层结构推演 |

## 批量自动测试

| 日期 | n_games | 配置 | 结果 |
|---|---|---|---|
| 2026-04-29 | 100 v4 | v1 vs v2 对照 | v2 善良 -4% (29% → 25%) |
| 2026-04-29 | 100 v5 | autoplay (random heuristic) | 决策模型太蠢，结果无信号 |

## 待补的历史记录

之前对话里的 sub-agent 报告内容很完整但没存盘——如需 backfill，可以根据对话日志补回。
