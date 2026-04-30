# Siege Night

**Blood on the Clocktower Custom Script** · By Edwin Yan · 12–15 players recommended

Import URL: `https://raw.githubusercontent.com/olveryu/blood-on-the-clock-tower-script/main/siege.json`

---

## Overview

**Siege Night** is an advanced script centered on the **Puppet** ecosystem. When Outsiders die, they trigger powerful chain effects — but the Demon gets to choose how those effects resolve. Good must carefully decide who lives and who dies, while Evil seeks to trigger Outsider death effects to sow chaos.

### Key Features

🏰 **Puppet Ecosystem**
When Outsiders die, chain effects trigger: extra kills (Deserter), alignment conversion (Refugee), Puppet creation (Wounded), execution binding (Captive). Puppet death can retrigger Outsider effects — chains can snowball.

🛡️ **Dual Protection (Absorption-style)**
The Shieldbearer absorbs an Outsider's night-death chain — they become a Puppet, the chain effect doesn't trigger. The Baroness does the same for executions. One-shot each, and the absorbed bolt doesn't know they've been converted — they still believe they have the ability.

🎭 **Four Distinct Demons**
- **Conqueror** — Kills Outsiders to convert the living. Final accusation showdown.
- **Shadow Archer** — Creates a Puppet on the first night. Can swap characters to hide identity.
- **Vanguard** — Outsider deaths trigger Puppet death chain instead. Flexible chain explosions.
- **Shapeshifter** — All Minions become Shapeshifters. Multiple Demons coordinate kills.

🕵️ **Rich Information Roles**
Inquisitor (detect evil), Herald/Patrolman (detect Outsiders), Gravedigger (inherit dead player's ability), Chaplain (detect character changes), Scribe (Outsider+Minion seat sum), Scout (identify Demon type) — Good has many tools, but the Hexer can poison your information at any time.

---

## Character List

### Townsfolk (13)

| Character | Ability |
|-----------|---------|
| Lookout | Each night, you learn 1 Minion or Outsider character that is not in play. |
| Spy Hunter | Each day, you may privately visit the Storyteller & name 2 players: the Storyteller tells you which is closer to a Minion. |
| Gravedigger | Once per game, at night*, choose a dead player: you become their character. |
| Quartermaster | Each day, you may publicly choose a player: if they are a Minion or Outsider, they are drunk until next dawn. |
| Chaplain | Each night, you learn how many alive players are no longer their original character. |
| Shieldbearer | When an Outsider dies at night, you become a Puppet — that Outsider's death ability does not trigger. |
| Baroness | When an Outsider is executed, you become a Puppet — that Outsider's death ability does not trigger. |
| Scribe | On your first night, you learn the sum of all Outsider & all Minion players' seats. |
| Herald | Each day, you may privately visit the Storyteller & name 3 players: you learn if exactly one of them is an Outsider. |
| Ranger | If you die at night, choose an alive player: if they are a non-Demon evil player, they lose their ability & die. |
| Inquisitor | Each night, choose 3 other alive players: you learn if exactly one of them is a non-Demon evil player. |
| Patrolman | Each night, choose a player: you learn if either alive neighbor of that player is an Outsider. |
| Scout | On your first night, you learn 3 Demon characters; one is in play. From day 3, during the day, you may privately ask the Storyteller: learn the Demon character. |

### Outsiders (5)

| Character | Death Effect |
|-----------|-------------|
| Deserter | When you die, that night the Demon must choose one of the Demon's alive neighbours: they die tonight. |
| Refugee | When you die, that night the Demon must choose a good dead player: they turn evil. |
| Wounded | When you die, that night the Demon must choose an alive player: they become a Puppet. |
| Captive | When you die, that night the Demon must choose 2 players: they are bound — if one of them is executed, the other dies that night. |
| Puppet | You think you are a good character, but you are not. When you die, that night the Demon must choose an Outsider character (different to last time): trigger that Outsider's death ability. [Does not appear during setup] |

### Minions (4)

| Character | Ability |
|-----------|---------|
| Mole | On your first night, choose an alive player: at the start of tomorrow's day, you both become a Puppet. |
| Undead | You think you are an Outsider character, but you are not. You also register as an Outsider. If the Demon dies, you become that Demon. When you die, trigger a Puppet's death ability. The Demon & Minions know you are the Undead. |
| Sleeper | You think you are a Townsfolk character, but you are not. You also register as an Outsider. If the Demon dies, you become that Demon. When you die, a Puppet's death effect is triggered. The Demon & Minions know you are the Sleeper. |
| Hexer | Each night, choose an alive neighbor: they become a Puppet tonight and tomorrow day. |

### Demons (4)

| Character | Ability |
|-----------|---------|
| Conqueror | Each night*, choose a player: they die. If you killed an Outsider, choose an alive player: they turn evil. When evil would win, all players close their eyes & each point at 2 players; evil players lower their hands — if the top 2 among good players' choices are the starting evil players, good wins instead. |
| Shadow Archer | On your first night, choose a player: they become a Puppet. Each night*, choose a player: they die. If you kill the player you chose on your first night, you may swap characters with an evil player. |
| Vanguard | Each night*, choose a player: they die. When an Outsider dies, a Puppet's death effect is triggered instead. [+1 Outsider] |
| Shapeshifter | Each night*, the Shapeshifters must jointly choose a player: they die. When you die, trigger a Puppet's death ability. You also register as an Outsider & a Minion. [During setup, Minions become Shapeshifters] |

---

## How to Play

### Good Team

**Your goal: execute the Demon.**

1. **Protect information**: Don't reveal your role on day 1. Build trust through private conversations first. High-value roles (Scout, Baroness, Shieldbearer) should stay hidden — revealing means getting killed at night.

2. **Beware the Hexer**: The Hexer turns a neighbor into a Puppet (=poisoned) each night. Your information might be false. When you get odd info, first ask "Am I hexed?" rather than trusting blindly.

3. **Use Outsider chains to reason**: If the first Outsider death has no chain → Shieldbearer/Baroness was triggered and is now a Puppet. **Only the first triggers** — subsequent Outsider deaths chain normally. The converted Shieldbearer doesn't know they've been turned and may keep publicly claiming "I'm the Shieldbearer" — that's now Evil's smokescreen.

4. **Locate the Hexer**: The Hexer can only pick neighbors. If your info was wrong, check your neighbors — the Hexer might be nearby.

5. **Watch for Puppets**: Puppets think they're good. If someone's information is consistently contradictory, they might be an unwitting Puppet.

### Evil Team

**Your goal: survive to the end (Evil wins when only 2 players remain alive).**

1. **Be proactive**: Chat privately with Good players, share false info, extract their roles. Report key role positions to the Demon for precise kills.

2. **Create "Hexer paranoia"**: Good fears unreliable info. Push the "Hexer is over there" narrative to make Good fight each other.

3. **Frame each other**: Evil A nominates Evil B → B gets executed → Good trusts A → A continues to lurk. Classic and effective.

4. **Maximize chains**: Use Outsider death effects for maximum value — create more Puppets, convert Good players, give Evil players new characters.

5. **Fake key roles**: Fake Baroness (makes Good think executions are safe), fake Chaplain (fabricate character-check info), fake Scout (mislead Demon type analysis).

---

## Storyteller Guide

### Setup

| Players | Townsfolk | Outsiders | Minions | Demons |
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

**Setup modifiers:**
- Shapeshifter: All Minions become Shapeshifters
- Puppet: Does not appear during setup

### Demon Selection Tips

| Demon | Best For | ST Difficulty |
|-------|---------|--------------|
| Conqueror | Conversion-expansion, final social deduction | ⭐⭐⭐ |
| Shadow Archer | Small games (8-10), spy thriller feel | ⭐⭐⭐ |
| Vanguard | High Outsider setups, chain explosions | ⭐⭐⭐ |
| Shapeshifter | Large games (12+), high complexity | ⭐⭐⭐⭐ |

### Key Storyteller Tips

1. **Resolve night strictly in order**: Follow firstNight / otherNight numbers ascending. Hexer(2) → Demons(6-9) → Outsider death effects(10-13) → Townsfolk info(14-21).

2. **Hexer's Puppet effect**: The hexed player becomes a Puppet "tonight and tomorrow day". This means tonight's info is false and tomorrow's day ability is also nullified.

3. **Chain & absorption**: When an Outsider dies at night and the Shieldbearer is alive, sober, and healthy — the Shieldbearer instantly becomes a Puppet (swap their token in the Grimoire; do NOT tell them) and the Outsider death effect doesn't trigger. Baroness works the same for executions. After triggering, the bolt has no ability but still thinks they do — keep deceiving them per Puppet/Marionette protocol (wake them at night, give "no Outsider died" feedback, etc.).

4. **Undead is special**: The Undead registers as an Outsider but isn't one — Herald/Patrolman detect them, but their death triggers the Puppet effect, not an Outsider effect.

5. **Shapeshifter info handling**: Shapeshifters register as both Outsider and Minion. Inquisitor detects them (non-Demon evil). Herald detects them (Outsider). Quartermaster affects them (Minion).

6. **Last Demon executed → game ends immediately**, chain effects don't trigger (unless the Undead is alive to inherit the Demon).

---

## Design Philosophy

The core tension of Siege Night: **Outsiders are both a burden for Good and a resource for Evil.**

Good wants to keep Outsiders alive (to avoid chains), but Outsiders take up Good slots with no proactive abilities. Evil wants to kill Outsiders to trigger chains (create Puppets, convert alignments). Shieldbearer/Baroness can each absorb one chain, but the cost is becoming new Puppet ammunition — when they later die, an Outsider death effect still triggers.

This creates a unique dynamic: **who to execute, who to kill at night, who to protect — every decision has cascading consequences.**
