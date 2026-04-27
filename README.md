# 围城之夜 / Siege Night

**Blood on the Clocktower Custom Script · 染·钟楼谜团 自定义剧本**

By Edwin Yan · 12–15 players recommended

---

## 导入链接 / Import

- 中文版 Chinese: `https://raw.githubusercontent.com/olveryu/block-on-the-clock-tower-script/main/weicheng.json`
- English: `https://raw.githubusercontent.com/olveryu/block-on-the-clock-tower-script/main/siege.json`
- [PDF 生成器 / PDF Generator](https://fancy.ravenswoodstudio.xyz/) — 粘贴 JSON 即可生成精美 PDF

---

## 剧本简介 / Overview

**围城之夜**是一个以**傀儡（Puppet）**为核心机制的高级剧本。在这个剧本中，外来者死亡会触发强大的连锁效果——但代价是由恶魔来选择如何执行。善良阵营必须谨慎决定谁该活、谁该死，而邪恶阵营则想方设法触发外来者的死亡效果来制造混乱。

**Siege Night** is an advanced script centered on the **Puppet** ecosystem. When Outsiders die, they trigger powerful chain effects — but the Demon gets to choose how those effects resolve. Good must carefully decide who lives and who dies, while Evil seeks to trigger Outsider death effects to sow chaos.

### 核心特色 / Key Features

🏰 **傀儡生态 / Puppet Ecosystem**
外来者死亡时触发连锁效果：额外击杀（逃兵）、阵营转换（难民）、创造傀儡（伤兵）、角色替换（俘虏）。傀儡死亡还能再触发外来者效果——连锁可以滚雪球。

When Outsiders die, chain effects trigger: extra kills (Deserter), alignment conversion (Refugee), Puppet creation (Wounded), character replacement (Captive). Puppet death can retrigger Outsider effects — chains can snowball.

🛡️ **双重保护 / Dual Protection**
盾卫阻止夜晚死亡的连锁效果（外来者仍然死亡，但不触发效果）；女伯爵阻止处决触发的连锁效果。善良需要灵活运用这两道防线。

The Shieldbearer blocks night death chain effects (Outsiders still die, but effects don't trigger); the Baroness blocks execution chain effects. Good must leverage both lines of defense.

🎭 **四种截然不同的恶魔 / Four Distinct Demons**
- **攻城将军 / Siege Lord** — 首夜看到所有角色，信息碾压型
- **暗箭手 / Shadow Archer** — 首夜制造傀儡，可交换角色隐藏身份
- **先锋官 / Vanguard** — 杀死外来者时额外制造傀儡
- **千面人 / Shapeshifter** — 所有爪牙都变成千面人，多恶魔协作击杀

🕵️ **丰富的信息角色 / Rich Information Roles**
审讯官（查邪恶）、纹章官/巡逻兵（查外来者）、军医（验尸）、牧师（查角色变动）、书记官（外来者座位号之和）、斥候（查恶魔类型）——善良有很多工具，但蛊惑者随时可能让你的信息变假。

Inquisitor (detect evil), Herald/Patrolman (detect Outsiders), Coroner (autopsy), Chaplain (detect character changes), Scribe (Outsider seat sum), Scout (identify Demon type) — Good has many tools, but the Hexer can poison your information at any time.

---

## 角色一览 / Character List

### 镇民 Townsfolk (13)

| 中文 | English | 能力 / Ability |
|------|---------|---------------|
| 瞭望兵 | Lookout | 每晚得知一个不在场的爪牙或外来者角色 / Each night, learn 1 not-in-play Minion or Outsider |
| 密探 | Spy Hunter | 白天指定两人，得知谁离爪牙更近 / Name 2 players by day, learn which is closer to a Minion |
| 军医 | Coroner | 每晚选一名死者，得知是否邪恶 / Each night, choose a dead player, learn if evil |
| 军需官 | Quartermaster | 白天公开选一人，爪牙或外来者则醉酒 / Publicly choose a player by day; Minion/Outsider becomes drunk |
| 牧师 | Chaplain | 每晚选一名存活玩家，得知是否是最初角色 / Each night, choose alive player, learn if original character |
| 盾卫 | Shieldbearer | 存活时，外来者夜晚死亡不触发效果 / While alive, Outsider night deaths don't trigger effects |
| 女伯爵 | Baroness | 存活时，处决不触发外来者死亡效果 / While alive, executions don't trigger Outsider death effects |
| 书记官 | Scribe | 首夜得知所有外来者座位号之和 / First night, learn sum of all Outsider seat numbers |
| 纹章官 | Herald | 每晚选两人，得知是否有外来者 / Each night, choose 2 players, learn if either is an Outsider |
| 游侠 | Ranger | 夜晚死亡时选一人，若非恶魔邪恶则击杀 / If you die at night, choose a player; if non-Demon evil, they die |
| 审讯官 | Inquisitor | 每晚选三人，得知是否有非恶魔邪恶 / Each night, choose 3 players, learn if any is non-Demon evil |
| 巡逻兵 | Patrolman | 每晚选一人，得知其邻座是否有外来者 / Each night, choose a player, learn if neighbours include an Outsider |
| 斥候 | Scout | 首夜得知两个恶魔角色（一个在场），第三天起可确认 / First night learn 2 Demons (1 in play); from day 3, confirm |

### 外来者 Outsiders (5)

| 中文 | English | 死亡效果 / Death Effect |
|------|---------|----------------------|
| 逃兵 | Deserter | 恶魔选一名存活玩家，当晚死亡 / Demon chooses alive player, they die tonight |
| 难民 | Refugee | 恶魔选一名善良死者，转为邪恶（仅一次）/ Demon chooses good dead player, turns evil (once) |
| 伤兵 | Wounded | 恶魔选一名存活玩家，变成傀儡 / Demon chooses alive player, becomes Puppet |
| 俘虏 | Captive | 恶魔选一名邪恶玩家和爪牙角色，变成该角色 / Demon chooses evil player + Minion character, they become it |
| 傀儡 | Puppet | 以为自己是善良角色。死亡时恶魔选外来者角色触发效果 / Thinks they're good. On death, triggers an Outsider death effect |

### 爪牙 Minions (4)

| 中文 | English | 能力 / Ability |
|------|---------|---------------|
| 内应 | Mole | 首夜选一人，次日双方变傀儡 / First night choose a player, both become Puppet tomorrow |
| 死士 | Undead | 伪装外来者，恶魔死后继承恶魔角色 / Disguised as Outsider; if Demon dies, becomes that Demon |
| 叛将 | Turncoat | 每晚可选恶魔角色，自己或恶魔变成该角色，另一个变傀儡 / Each night, may swap self or Demon to a Demon character; the other becomes Puppet |
| 蛊惑者 | Hexer | 每晚选邻座存活玩家变傀儡（持续到明天白天）/ Each night, neighbour becomes Puppet until next day |

### 恶魔 Demons (4)

| 中文 | English | 能力 / Ability |
|------|---------|---------------|
| 攻城将军 | Siege Lord | 首夜看全场角色，每晚杀一人 / First night see all characters; each night kill one |
| 暗箭手 | Shadow Archer | 首夜选一人变傀儡，杀该人可换角色 / First night choose Puppet; killing them lets you swap |
| 先锋官 | Vanguard | 每晚杀一人，杀外来者额外造傀儡 / Each night kill one; killing Outsider creates Puppet |
| 千面人 | Shapeshifter | 所有爪牙变千面人协作杀人，死亡触发傀儡效果 / All Minions become Shapeshifters, joint kill; death triggers Puppet |

---

## 玩法指南 / How to Play

### 善良阵营 / Good Team

**你的目标：处决恶魔。**

1. **保护信息**：不要第一天就公开你的角色。先通过私聊建立信任圈，逐步分享信息。高价值角色（斥候、女伯爵、盾卫）尤其要隐藏——公开就会被夜杀。

2. **警惕蛊惑者**：蛊惑者每晚让一名邻座变成傀儡（=中毒），你收到的信息可能是假的。收到异常信息时，先考虑"我被蛊惑了吗？"而不是盲目信任。

3. **利用外来者连锁推理**：如果盾卫/女伯爵存活但外来者死亡时没有连锁→说明触发被阻止了→侧面验证盾卫/女伯爵身份。

4. **定位蛊惑者**：蛊惑者只能选邻座。如果你的信息出错，看看你的邻座——蛊惑者可能就在附近。

5. **小心傀儡**：傀儡以为自己是善良角色。如果有人的信息持续矛盾，他可能是傀儡而不自知。

**Your goal: execute the Demon.**

1. **Protect information**: Don't reveal your role on day 1. Build trust through private conversations first. High-value roles (Scout, Baroness, Shieldbearer) should stay hidden — revealing means getting killed at night.

2. **Beware the Hexer**: The Hexer turns a neighbour into a Puppet (=poisoned) each night. Your information might be false. When you get odd info, first ask "Am I hexed?" rather than trusting blindly.

3. **Use Outsider chains to reason**: If Shieldbearer/Baroness is alive but Outsider death didn't chain → the effect was blocked → indirectly confirms Shieldbearer/Baroness identity.

4. **Locate the Hexer**: The Hexer can only pick neighbours. If your info was wrong, check your neighbours — the Hexer might be nearby.

5. **Watch for Puppets**: Puppets think they're good. If someone's information is consistently contradictory, they might be an unwitting Puppet.

### 邪恶阵营 / Evil Team

**你的目标：存活到最后（仅剩2名存活玩家时邪恶获胜）。**

1. **主动出击**：私聊善良玩家，交换假信息，套出他们的角色。得知关键角色位置后告诉恶魔精准击杀。

2. **制造"蛊惑者恐慌"**：善良最怕信息不可靠。推动"蛊惑者在那边"的叙事，让善良自相残杀。

3. **互相举报**：邪恶A提名邪恶B→B被处决→善良信任A→A继续潜伏。这是经典且有效的战术。

4. **利用连锁**：故意把外来者死亡效果用到最大价值——制造更多傀儡、转化善良玩家、让邪恶玩家获得新角色。

5. **假冒关键角色**：假女伯爵（让善良以为处决安全）、假牧师（编造查角色信息）、假斥候（误导恶魔类型判断）。

**Your goal: survive to the end (Evil wins when only 2 players remain alive).**

1. **Be proactive**: Chat privately with Good players, share false info, extract their roles. Report key role positions to the Demon for precise kills.

2. **Create "Hexer paranoia"**: Good fears unreliable info. Push the "Hexer is over there" narrative to make Good fight each other.

3. **Frame each other**: Evil A nominates Evil B → B gets executed → Good trusts A → A continues to lurk. Classic and effective.

4. **Maximize chains**: Use Outsider death effects for maximum value — create more Puppets, convert Good players, give Evil players new characters.

5. **Fake key roles**: Fake Baroness (makes Good think executions are safe), fake Chaplain (fabricate character-check info), fake Scout (mislead Demon type analysis).

---

## 说书人指南 / Storyteller Guide

### 配置 / Setup

| 玩家数 Players | 镇民 Townsfolk | 外来者 Outsiders | 爪牙 Minions | 恶魔 Demons |
|:-:|:-:|:-:|:-:|:-:|
| 7 | 5 | 0 | 1 | 1 |
| 8 | 5 | 1 | 1 | 1 |
| 9 | 5 | 2 | 1 | 1 |
| 10 | 7 | 0 | 2 | 1 |
| 11 | 7 | 1 | 2 | 1 |
| 12 | 7 | 2 | 2 | 1 |
| 13 | 9 | 0 | 3 | 1 |
| 14 | 9 | 1 | 3 | 1 |
| 15 | 9 | 2 | 3 | 1 |

**配置修正 / Setup modifiers:**
- 叛将 Turncoat: +1 外来者 Outsider
- 千面人 Shapeshifter: 爪牙全变千面人，-1 外来者 / All Minions become Shapeshifters, -1 Outsider
- 傀儡 Puppet: 配置时不出现 / Does not appear during setup

### 恶魔选择建议 / Demon Selection Tips

| 恶魔 Demon | 适合场景 / Best For | 说书人难度 / ST Difficulty |
|-----------|-------------------|------------------------|
| 攻城将军 Siege Lord | 新说书人入门，信息型恶魔 / New STs, info-based Demon | ⭐⭐ |
| 暗箭手 Shadow Archer | 小型局（8-10人），谍战感 / Small games (8-10), spy thriller feel | ⭐⭐⭐ |
| 先锋官 Vanguard | 外来者多的配置，连锁爆发 / High Outsider setups, chain explosions | ⭐⭐⭐ |
| 千面人 Shapeshifter | 大型局（12+人），高复杂度 / Large games (12+), high complexity | ⭐⭐⭐⭐ |

### 关键提示 / Key ST Tips

1. **夜晚结算严格按顺序**：按 firstNight / otherNight 数字从小到大。蛊惑者(2)→叛将(3)→恶魔(6-9)→外来者死亡效果(10-13)→镇民信息(14-21)。

   **Resolve night strictly in order**: Follow firstNight / otherNight numbers ascending. Hexer(2)→Turncoat(3)→Demons(6-9)→Outsider death effects(10-13)→Townsfolk info(14-21).

2. **蛊惑者的傀儡效果**：被蛊惑者选中的玩家在"当晚和明天白天"变成傀儡。这意味着当晚的信息是假的，明天白天的能力也失效。

   **Hexer's Puppet effect**: The hexed player becomes a Puppet "tonight and tomorrow's day". This means tonight's info is false and tomorrow's day ability is also nullified.

3. **连锁不连锁？** 盾卫存活→夜晚外来者死亡不触发效果（但仍然死亡）。女伯爵存活→处决不触发外来者效果。两者不互相覆盖。

   **Chain or no chain?** Shieldbearer alive → night Outsider deaths don't trigger effects (but they still die). Baroness alive → executions don't trigger Outsider effects. They don't overlap.

4. **死士的特殊性**：死士被视为外来者，但他不是外来者——纹章官/巡逻兵会检测到他，但他死亡时触发的是傀儡效果而非外来者效果。

   **Undead is special**: The Undead registers as an Outsider but isn't one — Herald/Patrolman detect them, but their death triggers Puppet effect, not Outsider effect.

5. **千面人局的信息处理**：千面人被视为外来者和爪牙。审讯官查到千面人=阳性（非恶魔邪恶）。纹章官查到千面人=阳性（外来者）。军需官选千面人=醉酒（爪牙）。

   **Shapeshifter info handling**: Shapeshifters register as both Outsider and Minion. Inquisitor detects them (non-Demon evil). Herald detects them (Outsider). Quartermaster affects them (Minion).

6. **最后一个恶魔被处决→游戏立刻结束**，连锁效果来不及生效（除非死士在场继承恶魔）。

   **Last Demon executed → game ends immediately**, chain effects don't trigger (unless Undead is alive to inherit).

---

## 设计理念 / Design Philosophy

围城之夜的核心张力在于：**外来者既是善良的负担，也是邪恶的资源。**

善良想保护外来者不死（避免连锁），但外来者占了善良的名额却没有主动能力。邪恶想杀外来者触发连锁（制造傀儡、转化阵营），但又要避免连锁被盾卫/女伯爵阻止。

这创造了一个独特的博弈：**处决谁、夜杀谁、保护谁，每个决定都牵一发而动全身。**

The core tension of Siege Night: **Outsiders are both a burden for Good and a resource for Evil.**

Good wants to keep Outsiders alive (to avoid chains), but Outsiders take up Good slots with no proactive abilities. Evil wants to kill Outsiders to trigger chains (create Puppets, convert alignments), but must avoid chains being blocked by Shieldbearer/Baroness.

This creates a unique dynamic: **who to execute, who to kill at night, who to protect — every decision has cascading consequences.**