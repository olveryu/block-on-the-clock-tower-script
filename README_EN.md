# Siege Night

**Blood on the Clocktower Custom Script** · By Edwin Yan · 12–15 players recommended

Import URL: `https://raw.githubusercontent.com/olveryu/block-on-the-clock-tower-script/main/siege.json`

---

## Overview

**Siege Night** is an advanced script centered on the **Puppet** ecosystem. When Outsiders die, they trigger powerful chain effects — but the Demon gets to choose how those effects resolve. Good must carefully decide who lives and who dies, while Evil seeks to trigger Outsider death effects to sow chaos.

### Key Features

🏰 **Puppet Ecosystem**
When Outsiders die, chain effects trigger: extra kills (Deserter), alignment conversion (Refugee), Puppet creation (Wounded), character replacement (Captive). Puppet death can retrigger Outsider effects — chains can snowball.

🛡️ **Dual Protection**
The Shieldbearer blocks night death chain effects (Outsiders still die, but effects don't trigger); the Baroness blocks execution chain effects. Good must leverage both lines of defense.

🎭 **Four Distinct Demons**
- **Siege Lord** — Sees all characters on the first night. Pure information dominance.
- **Shadow Archer** — Creates a Puppet on the first night. Can swap characters to hide identity.
- **Vanguard** — Killing Outsiders creates additional Puppets.
- **Shapeshifter** — All Minions become Shapeshifters. Multiple Demons coordinate kills.

🕵️ **Rich Information Roles**
Inquisitor (detect evil), Herald/Patrolman (detect Outsiders), Coroner (autopsy), Chaplain (detect character changes), Scribe (Outsider seat sum), Scout (identify Demon type) — Good has many tools, but the Hexer can poison your information at any time.

---

## Character List

### Townsfolk (13)

| Character | Ability |
|-----------|---------|
| Lookout | Each night, you learn 1 Minion or Outsider character that is not in play. |
| Spy Hunter | Each day, you may privately visit the Storyteller and name 2 players: the Storyteller tells you which is closer to a Minion. |
| Coroner | Each night*, choose a dead player: you learn if they are evil. |
| Quartermaster | Each day, you may publicly choose a player: if they are a Minion or Outsider, they are drunk until next dawn. |
| Chaplain | Each night*, choose an alive player: you learn if they are their original character. |
| Shieldbearer | While you are alive, Outsiders do not trigger their death effects when dying at night. |
| Baroness | While you are alive, executed players do not trigger Outsider death effects. |
| Scribe | On your first night, you learn the sum of all Outsider players' seat numbers. |
| Herald | Each night, choose 2 players: you learn if either is an Outsider. |
| Ranger | If you die at night, choose an alive player: if they are a non-Demon evil player, they lose their ability and die. |
| Inquisitor | Each night, choose 3 other alive players: you learn if any is a non-Demon evil player. |
| Patrolman | Each night, choose a player: you learn if either alive neighbour of that player is an Outsider. |
| Scout | On your first night, you learn 2 Demon characters; one is in play. From day 3, during the day, you may privately ask the Storyteller: learn the Demon character. |

### Outsiders (5)

| Character | Death Effect |
|-----------|-------------|
| Deserter | When you die, that night the Demon must choose an alive player: they die tonight. |
| Refugee | When you die, that night the Demon must choose a good dead player: they turn evil. (Once only) |
| Wounded | When you die, that night the Demon must choose an alive player: they become the Puppet. |
| Captive | When you die, that night the Demon must choose an evil player and a Minion character: they become that character and immediately use that ability. |
| Puppet | You think you are a good character, but you are not. When you die, that night the Demon must choose an Outsider character: trigger that Outsider's death ability. [Does not appear during setup] |

### Minions (4)

| Character | Ability |
|-----------|---------|
| Mole | On your first night, choose an alive player: at the start of tomorrow's day, you both become the Puppet. |
| Undead | You think you are an Outsider character, but you are not. You also register as an Outsider. If the Demon dies, you become that Demon. When you die, trigger the Puppet's death ability. The Demon and Minions know you are the Undead. |
| Turncoat | Each night*, you may choose a Demon character: choose to make yourself or the Demon become that character; the other becomes the Puppet. [+1 Outsider] |
| Hexer | Each night, choose an alive neighbour: they become the Puppet tonight and tomorrow's day. |

### Demons (4)

| Character | Ability |
|-----------|---------|
| Siege Lord | On your first night, you learn all players' characters. Each night*, choose a player: they die. |
| Shadow Archer | On your first night, choose a player: they become the Puppet. Each night*, choose a player: they die. If you kill the player you chose on your first night, you may swap characters with an evil player. |
| Vanguard | Each night*, choose a player: they die. If they are an Outsider, choose another alive player: they become the Puppet. |
| Shapeshifter | Each night*, the Shapeshifters must jointly choose a player: they die. When you die, trigger the Puppet's death ability. You also register as an Outsider and a Minion. [During setup, Minions become Shapeshifters, -1 Outsider] |

---

## How to Play

### Good Team

**Your goal: execute the Demon.**

1. **Protect information**: Don't reveal your role on day 1. Build trust through private conversations first. High-value roles (Scout, Baroness, Shieldbearer) should stay hidden — revealing means getting killed at night.

2. **Beware the Hexer**: The Hexer turns a neighbour into a Puppet (=poisoned) each night. Your information might be false. When you get odd info, first ask "Am I hexed?" rather than trusting blindly.

3. **Use Outsider chains to reason**: If Shieldbearer/Baroness is alive but Outsider death didn't chain → the effect was blocked → indirectly confirms Shieldbearer/Baroness identity.

4. **Locate the Hexer**: The Hexer can only pick neighbours. If your info was wrong, check your neighbours — the Hexer might be nearby.

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
- Turncoat: +1 Outsider
- Shapeshifter: All Minions become Shapeshifters, -1 Outsider
- Puppet: Does not appear during setup

### Demon Selection Tips

| Demon | Best For | ST Difficulty |
|-------|---------|--------------|
| Siege Lord | New Storytellers, info-based Demon | ⭐⭐ |
| Shadow Archer | Small games (8-10), spy thriller feel | ⭐⭐⭐ |
| Vanguard | High Outsider setups, chain explosions | ⭐⭐⭐ |
| Shapeshifter | Large games (12+), high complexity | ⭐⭐⭐⭐ |

### Key Storyteller Tips

1. **Resolve night strictly in order**: Follow firstNight / otherNight numbers ascending. Hexer(2) → Turncoat(3) → Demons(6-9) → Outsider death effects(10-13) → Townsfolk info(14-21).

2. **Hexer's Puppet effect**: The hexed player becomes a Puppet "tonight and tomorrow's day". This means tonight's info is false and tomorrow's day ability is also nullified.

3. **Chain or no chain?** Shieldbearer alive → night Outsider deaths don't trigger effects (but they still die). Baroness alive → executions don't trigger Outsider effects. They don't overlap.

4. **Undead is special**: The Undead registers as an Outsider but isn't one — Herald/Patrolman detect them, but their death triggers the Puppet effect, not an Outsider effect.

5. **Shapeshifter info handling**: Shapeshifters register as both Outsider and Minion. Inquisitor detects them (non-Demon evil). Herald detects them (Outsider). Quartermaster affects them (Minion).

6. **Last Demon executed → game ends immediately**, chain effects don't trigger (unless the Undead is alive to inherit the Demon).

---

## Design Philosophy

The core tension of Siege Night: **Outsiders are both a burden for Good and a resource for Evil.**

Good wants to keep Outsiders alive (to avoid chains), but Outsiders take up Good slots with no proactive abilities. Evil wants to kill Outsiders to trigger chains (create Puppets, convert alignments), but must avoid chains being blocked by Shieldbearer/Baroness.

This creates a unique dynamic: **who to execute, who to kill at night, who to protect — every decision has cascading consequences.**
