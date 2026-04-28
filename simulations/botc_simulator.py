#!/usr/bin/env python3
"""
围城之夜 12 人模拟器 v2 (完整机关版)
=======================
真随机骰子 + 全部邪恶机关:
- 外来者死亡链 (难民/伤兵/逃兵/俘虏)
- 保险栓阻止 (女伯爵阻处决/盾卫阻夜杀)
- 死士复活栈 (恶魔死时变恶魔)
- 蛊惑者邻座傀儡 (每晚)
- 内应 N1 双傀儡
- 暗箭手 N1 + 交换能力
- 叛将变身 (N2+)
- 千面人多恶魔
- 难民触发后死人变邪恶+死票

用法:
    python3 botc_simulator.py        # 跑一局完整推演
    python3 botc_simulator.py 30     # 跑 N 局看胜率
    python3 botc_simulator.py 100 -v # 跑 100 局, 详细输出
"""

import random
import sys

# ============= 角色池 =============
TOWNSFOLK_POOL = [
    '斥候', '密探', '巡逻兵', '审讯官', '游侠', '军医',
    '书记官', '军需官', '牧师', '纹章官', '盾卫', '女伯爵', '瞭望兵'
]
# 信息源镇民 (产生推理用信息) — 死亡 → 信息真空
INFO_SOURCES = {'斥候', '密探', '巡逻兵', '审讯官', '书记官', '纹章官', '瞭望兵'}
OUTSIDER_POOL = ['伤兵', '逃兵', '难民', '俘虏']
MINION_POOL = ['内应', '蛊惑者', '叛将', '死士']
DEMON_POOL = ['攻城将军', '先锋官', '千面人', '暗箭手']

PLAYERS = ['阿信', '小白', '二哥', '月儿', '老王', '阿龙',
           '莉莉', '小七', '大刘', '苗苗', '阿强', '雪儿']


def is_demon_role(role):
    return role in DEMON_POOL or '千面人' in role


def is_minion_role(role):
    return role in MINION_POOL


def is_outsider_role(role):
    return role in OUTSIDER_POOL


class Game:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.config = {}
        self.deaths = []  # [(time, seat, role)]
        self.day = 0
        self.day_log = []

        # 邪恶状态
        self.demon_role = None
        self.minions = []
        self.outsiders = []
        self.bluffs = []
        self.evil_seats = []
        self.demon_seats = []  # 千面人时多个

        # 状态追踪
        self.has_save_baron = False  # 女伯爵在场 alive
        self.has_save_shield = False  # 盾卫在场 alive
        self.dead_man_seat = None  # 死士位置
        self.dead_man_active = False  # 死士复活栈是否还在
        self.refugee_used = False  # 难民能力一次性

        # 暗箭手追踪
        self.archer_n1_target = None
        self.archer_swapped = False

        # 蛊惑/傀儡状态
        self.puppet_status = {}  # {seat: True if puppet}
        self.hex_target = None  # 当晚被蛊惑的人

        # 难民变邪恶死人
        self.evil_dead_votes = set()

        # 假信息流 / 信任崩塌追踪 (v3 新增)
        self.demons_killed = 0  # 已死恶魔总数 (含千面人)
        self.hex_died_day = None  # 蛊惑者死亡日 (用于残留期判定)
        self.first_demon_kill_day = None  # 第一个恶魔死亡日 (千面人信任崩塌起点)

        # 信息真空追踪
        self.initial_info_sources = 0  # setup 时信息源镇民总数

        self._generate_config()
        # setup 后统计初始信息源
        self.initial_info_sources = sum(
            1 for s in self.config
            if self.config[s]['role'] in INFO_SOURCES
        )

    def log(self, msg, indent=0):
        if self.verbose:
            print('  ' * indent + msg)

    def _generate_config(self):
        """生成 12 人随机配置"""
        demon = random.choice(DEMON_POOL)
        minions_raw = random.sample(MINION_POOL, 2)

        self.is_lunatic_setup = (demon == '千面人')  # 锁定原始 setup, 不被叛将变身改

        if demon == '千面人':
            outsider_count = 1
            townsfolk_count = 8
            minions_assignment = ['千面人', '千面人']
        elif demon == '先锋官' or '叛将' in minions_raw:
            outsider_count = 3
            townsfolk_count = 6
            minions_assignment = minions_raw
        else:
            outsider_count = 2
            townsfolk_count = 7
            minions_assignment = minions_raw

        townsfolk = random.sample(TOWNSFOLK_POOL, townsfolk_count)
        outsiders = random.sample(OUTSIDER_POOL, outsider_count)
        not_in_play_t = [t for t in TOWNSFOLK_POOL if t not in townsfolk]
        bluffs = random.sample(not_in_play_t, 3)

        self.demon_role = demon
        self.minions = minions_assignment
        self.outsiders = outsiders
        self.townsfolk = townsfolk
        self.bluffs = bluffs
        self.not_in_play_outsiders = [o for o in OUTSIDER_POOL if o not in outsiders]

        roles = [demon] + minions_assignment + outsiders + townsfolk
        random.shuffle(roles)

        for i, (p, r) in enumerate(zip(PLAYERS, roles), 1):
            is_demon = (r == demon and demon != '千面人') or '千面人' in r
            is_minion = r in MINION_POOL and r != '千面人'
            if is_demon:
                team = "邪恶"
                self.demon_seats.append(i)
            elif is_minion:
                team = "邪恶"
            elif r in outsiders:
                team = "外来者"
            else:
                team = "镇民"

            # 爪牙/恶魔 bluff 战术
            # 爪牙: 装外来者 60%, 装镇民 40%
            # 恶魔: 用 N0 给的 3 bluffs 之一装镇民 (不能装外来者)
            # 千面人: 自以为镇民, 完全装镇民
            # bluff_until_day = 善良识破伪装的那一天
            bluff_type = None
            bluff_until_day = 0
            if is_minion:
                bluff_type = random.choices(
                    ['outsider', 'townsfolk'], weights=[0.60, 0.40]
                )[0]
                bluff_until_day = random.randint(3, 5)
            elif is_demon:
                if '千面人' in r:
                    # 千面人 N0 互知, 共同装镇民 bluff
                    # 善良知道 setup 有多恶魔, 主动找 → 识破较早
                    bluff_type = 'townsfolk'
                    bluff_until_day = random.randint(3, 4)
                else:
                    # 单恶魔用 N0 给的 bluff 装镇民 (D4-D6 被锁)
                    bluff_type = 'townsfolk'
                    bluff_until_day = random.randint(4, 6)

            self.config[i] = {
                'player': p,
                'role': r,
                'original_role': r,
                'team': team,
                'alive': True,
                'puppet': False,
                'register_outsider': r in outsiders or r == '死士' or '千面人' in r,
                'register_minion': is_minion or r == '死士' or '千面人' in r,
                'self_busted': False,
                'bluff_type': bluff_type,  # 爪牙伪装类型
                'bluff_until_day': bluff_until_day,  # 善良识破日
            }
            if team == "邪恶":
                self.evil_seats.append(i)
            if r == '死士':
                self.dead_man_seat = i
                self.dead_man_active = True
                self.config[i]['register_outsider'] = True
            if r == '女伯爵':
                self.has_save_baron = True
            if r == '盾卫':
                self.has_save_shield = True

    def print_config(self):
        if not self.verbose:
            return
        self.log(f"=== 配置 ===")
        self.log(f"恶魔: {self.demon_role}, 爪牙: {self.minions}")
        self.log(f"外来者: {self.outsiders}")
        self.log(f"镇民: {self.townsfolk}")
        self.log(f"Bluffs: {self.bluffs}")
        for i in sorted(self.config):
            c = self.config[i]
            self.log(f"  {i}. {c['player']}: {c['role']} ({c['team']})")
        self.log("")

    def alive_seats(self, exclude=None):
        excl = set(exclude or [])
        return [i for i in self.config if self.config[i]['alive'] and i not in excl]

    def alive_demons(self):
        return [i for i in self.config if self.config[i]['alive'] and is_demon_role(self.config[i]['role'])]

    def kill(self, seat, method='夜杀', by_demon=True):
        """杀玩家, 返回是否触发死亡链"""
        if not self.config[seat]['alive']:
            return False
        self.config[seat]['alive'] = False
        time = f"D{self.day}" if method == '处决' else f"N{self.day}"
        self.deaths.append((time, seat, self.config[seat]['role']))
        self.log(f"  → {time} 死亡: {seat} ({self.config[seat]['player']}, {self.config[seat]['role']})", 1)

        # 更新保险栓状态
        if self.config[seat]['role'] == '女伯爵':
            self.has_save_baron = False
        if self.config[seat]['role'] == '盾卫':
            self.has_save_shield = False

        # 假信息流 / 信任崩塌追踪
        if self.config[seat]['role'] == '蛊惑者':
            self.hex_died_day = self.day
        if is_demon_role(self.config[seat]['role']):
            self.demons_killed += 1
            if self.first_demon_kill_day is None:
                self.first_demon_kill_day = self.day

        # 死士复活栈检查 - 如果恶魔死, 死士变恶魔
        if is_demon_role(self.config[seat]['role']) and self.dead_man_active:
            if self.dead_man_seat is not None and self.config[self.dead_man_seat]['alive']:
                # 死士变恶魔
                old_role = self.config[self.dead_man_seat]['role']
                new_demon = self.config[seat]['original_role'] if 'original_role' in self.config[seat] else self.config[seat]['role']
                self.config[self.dead_man_seat]['role'] = new_demon
                self.config[self.dead_man_seat]['team'] = '邪恶'
                self.demon_seats.append(self.dead_man_seat)
                self.dead_man_active = False
                self.log(f"  ★ 死士复活: {self.dead_man_seat} 从 {old_role} 变 {new_demon}", 1)

        # 触发外来者/傀儡/死士死亡链
        if self._should_trigger_death(seat, method):
            self._trigger_death_chain(seat)

        return True

    def _should_trigger_death(self, seat, method):
        """检查死亡链是否触发"""
        c = self.config[seat]
        # 检查保护
        if method == '处决' and self.has_save_baron:
            return False
        if method == '夜杀' and self.has_save_shield:
            return False

        # 是否是触发型角色
        if c['role'] in OUTSIDER_POOL or c['role'] == '傀儡' or '千面人' in c['role'] or c['role'] == '死士':
            return True
        return False

    def _trigger_death_chain(self, seat):
        """触发外来者/傀儡/死士死亡能力"""
        role = self.config[seat]['role']
        # 死士死亡触发傀儡死亡能力
        if role == '死士' or role == '傀儡' or '千面人' in role:
            self._trigger_puppet_death()
        elif role == '难民':
            self._trigger_refugee()
        elif role == '伤兵':
            self._trigger_wounded()
        elif role == '逃兵':
            self._trigger_deserter()
        elif role == '俘虏':
            self._trigger_captive()

    def _trigger_puppet_death(self):
        """傀儡死亡 → 选外来者角色发动死亡能力"""
        # 恶魔选外来者 (按优先级)
        choices = ['难民', '伤兵', '逃兵', '俘虏']
        # 限制只能选场上有效的能力
        valid = []
        for c in choices:
            if c == '难民' and not self.refugee_used and any(self.config[s]['team'] == '镇民' and not self.config[s]['alive'] and s not in self.evil_dead_votes for s in self.config):
                valid.append((c, 0.4))
            elif c == '伤兵' and self.alive_seats():
                valid.append((c, 0.3))
            elif c == '逃兵' and self.alive_seats():
                valid.append((c, 0.4))
            elif c == '俘虏' and any(self.config[s]['team'] == '邪恶' and self.config[s]['alive'] for s in self.config):
                valid.append((c, 0.2))

        if not valid:
            return
        choices_v, weights = zip(*valid)
        chosen = random.choices(choices_v, weights=weights)[0]
        self.log(f"  傀儡死亡 → 恶魔选: {chosen}", 1)
        if chosen == '难民':
            self._trigger_refugee()
        elif chosen == '伤兵':
            self._trigger_wounded()
        elif chosen == '逃兵':
            self._trigger_deserter()
        elif chosen == '俘虏':
            self._trigger_captive()

    def _trigger_refugee(self):
        """难民死亡 → 选善良死人变邪恶"""
        if self.refugee_used:
            return
        good_dead = [s for s in self.config if not self.config[s]['alive']
                      and self.config[s]['team'] != '邪恶'
                      and s not in self.evil_dead_votes]
        if not good_dead:
            return
        chosen = random.choice(good_dead)
        self.evil_dead_votes.add(chosen)
        self.refugee_used = True
        self.log(f"  ★ 难民触发: {chosen} ({self.config[chosen]['player']}) 死人变邪恶", 1)

    def _trigger_wounded(self):
        """伤兵死亡 → 选活人变傀儡"""
        candidates = self.alive_seats()
        if not candidates:
            return
        # 邪恶选关键威胁
        weights = []
        for s in candidates:
            role = self.config[s]['role']
            if role in ['军医', '盾卫', '审讯官']:
                weights.append(0.30)
            elif role in ['女伯爵', '斥候']:
                weights.append(0.25)
            else:
                weights.append(0.05)
        chosen = random.choices(candidates, weights=weights)[0]
        old_role = self.config[chosen]['role']
        self.config[chosen]['role'] = '傀儡'
        self.config[chosen]['puppet'] = True
        self.config[chosen]['register_outsider'] = True
        if old_role == '女伯爵':
            self.has_save_baron = False
        if old_role == '盾卫':
            self.has_save_shield = False
        self.log(f"  ★ 伤兵触发: {chosen} ({self.config[chosen]['player']}) 从 {old_role} 变傀儡", 1)

    def _trigger_deserter(self):
        """逃兵死亡 → 选活人当晚死"""
        candidates = self.alive_seats()
        if not candidates:
            return
        # 邪恶选关键
        weights = []
        for s in candidates:
            role = self.config[s]['role']
            if role in ['军医', '审讯官', '斥候']:
                weights.append(0.30)
            elif role == '游侠':
                weights.append(0.05)  # 不杀游侠
            else:
                weights.append(0.10)
        chosen = random.choices(candidates, weights=weights)[0]
        self.log(f"  ★ 逃兵触发: 选 {chosen} ({self.config[chosen]['player']}) 当晚死", 1)
        self.kill(chosen, method='夜杀', by_demon=True)

    def _trigger_captive(self):
        """俘虏死亡 → 选邪恶玩家变爪牙角色立即用"""
        evil_alive = [s for s in self.config if self.config[s]['alive']
                       and self.config[s]['team'] == '邪恶'
                       and not is_demon_role(self.config[s]['role'])]
        if not evil_alive:
            return
        chosen_seat = random.choice(evil_alive)
        # 邪恶选爪牙角色 (优先 死士 - 复活栈)
        good_options = ['蛊惑者', '内应', '叛将', '死士']
        options = []
        if self.dead_man_active:
            # 已经有死士活, 选其他
            options = ['蛊惑者', '内应', '叛将']
        else:
            options = good_options
        chosen_role = random.choices(options, weights=[0.3]*len(options))[0]
        old_role = self.config[chosen_seat]['role']
        self.config[chosen_seat]['role'] = chosen_role
        if chosen_role == '死士':
            self.dead_man_seat = chosen_seat
            self.dead_man_active = True
        self.log(f"  ★ 俘虏触发: {chosen_seat} ({self.config[chosen_seat]['player']}) 从 {old_role} 变 {chosen_role}", 1)

    def _execute_attack(self, target_seat, by_demon=True):
        """夜晚攻击"""
        if not self.config[target_seat]['alive']:
            return
        # 检查游侠死亡反杀
        role = self.config[target_seat]['role']
        if role == '游侠':
            # 游侠选活人, 如果是非恶魔邪恶则失能并死
            evil_non_demon = [s for s in self.config if self.config[s]['alive']
                                and self.config[s]['team'] == '邪恶'
                                and not is_demon_role(self.config[s]['role'])]
            if evil_non_demon:
                rev_target = random.choice(evil_non_demon)
                self.log(f"  ★ 游侠夜死反杀 {rev_target} ({self.config[rev_target]['player']})", 1)
                self.kill(rev_target, method='夜杀', by_demon=False)

        # 暗箭手交换检查
        if (self.demon_role == '暗箭手' and target_seat == self.archer_n1_target
                and not self.archer_swapped):
            # 50% 概率使用交换
            if random.random() < 0.4:
                evil_alive = [s for s in self.config if self.config[s]['alive']
                                and self.config[s]['team'] == '邪恶'
                                and not is_demon_role(self.config[s]['role'])]
                if evil_alive:
                    swap_seat = random.choice(evil_alive)
                    arrow_seat = self.demon_seats[0]
                    new_demon = self.config[arrow_seat]['role']
                    self.config[swap_seat]['role'] = new_demon
                    self.config[swap_seat]['team'] = '邪恶'
                    self.config[arrow_seat]['role'] = '蛊惑者'  # 简化: 变蛊惑者
                    self.demon_seats.remove(arrow_seat)
                    self.demon_seats.append(swap_seat)
                    self.archer_swapped = True
                    self.log(f"  ★ 暗箭手交换: {arrow_seat} 与 {swap_seat} 换角色", 1)

        # 实际死亡
        self.kill(target_seat, method='夜杀', by_demon=by_demon)

    def n0_setup(self):
        """N0 邪恶互知"""
        self.log("=== N0 邪恶互知 ===")
        self.log(f"  3 bluffs: {self.bluffs}")
        if self.dead_man_seat:
            fake = random.choice(OUTSIDER_POOL)
            self.log(f"  死士({self.dead_man_seat}) 自以为: {fake}")

    def n1_actions(self):
        """N1 行动"""
        self.log(f"\n=== N1 ===")
        # 内应
        if '内应' in self.minions:
            mole_seat = next(i for i in self.config if self.config[i]['role'] == '内应')
            others = self.alive_seats(exclude=[mole_seat])
            target = random.choice(others)
            # 内应+目标 D1 早上变傀儡
            self.config[mole_seat]['puppet_pending'] = True
            self.config[target]['puppet_pending'] = True
            self.config[mole_seat]['knows_puppet'] = True
            self.log(f"  内应({mole_seat}) 选 {target} → D1 早上双变傀儡")

        # 暗箭手 N1 选玩家变傀儡 (不选队友)
        if self.demon_role == '暗箭手':
            arrow_seat = self.demon_seats[0]
            others = [s for s in self.alive_seats(exclude=[arrow_seat])
                       if s not in self.evil_seats]
            if others:
                target = random.choice(others)
                self.archer_n1_target = target
                self.config[target]['role'] = '傀儡'
                self.config[target]['puppet'] = True
                self.config[target]['register_outsider'] = True
                self.log(f"  暗箭手({arrow_seat}) 选 {target} 变傀儡")

        # 蛊惑者 N1
        if '蛊惑者' in self.minions:
            hex_seat = next(i for i in self.config if self.config[i]['role'] == '蛊惑者')
            left = (hex_seat - 2) % 12 + 1
            right = hex_seat % 12 + 1
            if left == 0: left = 12
            target = random.choice([left, right])
            self.hex_target = target
            self.log(f"  蛊惑者({hex_seat}) 蛊惑邻座 {target}")

    def n_kill(self):
        """夜晚击杀 N>=2"""
        if not self.demon_seats:
            return

        # 蛊惑者每晚选 (但 N1 已选, N2+ 续)
        if '蛊惑者' in [self.config[s]['role'] for s in self.config if self.config[s]['alive']]:
            hex_seats = [s for s in self.config if self.config[s]['alive'] and self.config[s]['role'] == '蛊惑者']
            if hex_seats:
                hex_seat = hex_seats[0]
                left = (hex_seat - 2) % 12 + 1
                right = hex_seat % 12 + 1
                if left == 0: left = 12
                if self.config[left]['alive'] or self.config[right]['alive']:
                    candidates = []
                    if self.config[left]['alive']:
                        candidates.append(left)
                    if self.config[right]['alive']:
                        candidates.append(right)
                    if candidates:
                        self.hex_target = random.choice(candidates)

        # 叛将 N2+ 用能力 (15% 概率)
        if '叛将' in [self.config[s]['role'] for s in self.config if self.config[s]['alive']]:
            if random.random() < 0.20 and self.day >= 2:
                turncoat_seat = next(s for s in self.config if self.config[s]['alive'] and self.config[s]['role'] == '叛将')
                # 让恶魔变其他恶魔角色
                if self.demon_seats:
                    new_demon_role = random.choice([d for d in DEMON_POOL if d != self.demon_role])
                    old_demon_role = self.demon_role
                    demon_seat = self.demon_seats[0]
                    self.config[demon_seat]['role'] = new_demon_role
                    self.config[turncoat_seat]['role'] = '傀儡'
                    self.config[turncoat_seat]['puppet'] = True
                    self.config[turncoat_seat]['register_outsider'] = True
                    self.demon_role = new_demon_role
                    self.log(f"  叛将({turncoat_seat}) 让 {demon_seat} 变 {new_demon_role}, 自己变傀儡", 1)

        # 攻城将军/暗箭手/先锋官 杀人 (千面人共同)
        attackable = [s for s in self.config if self.config[s]['alive']
                      and s not in self.evil_seats]

        # 千面人共同选择
        if any('千面人' in self.config[s]['role'] for s in self.config if self.config[s]['alive']):
            # 多个千面人共同选择
            target = self._choose_kill_target(attackable)
            if target:
                self.log(f"  千面人共同杀: {target}")
                self._execute_attack(target)
        else:
            # 单恶魔杀
            if self.demon_seats and self.config[self.demon_seats[0]]['alive']:
                target = self._choose_kill_target(attackable)
                if target:
                    self.log(f"  {self.config[self.demon_seats[0]]['role']}({self.demon_seats[0]}) 杀: {target}")
                    self._execute_attack(target)

    def _choose_kill_target(self, candidates):
        """邪恶选击杀目标 - 按威胁优先级"""
        if not candidates:
            return None
        weights = []
        for s in candidates:
            role = self.config[s]['role']
            # 不杀游侠 (会反杀)
            if role == '游侠':
                weights.append(0.05)
                continue
            # 杀外来者会触发链 - 但有保险栓不触发
            if role in OUTSIDER_POOL or role == '傀儡':
                if self.has_save_shield:
                    weights.append(0.05)  # 没用
                else:
                    weights.append(0.25)  # 触发链
            elif role == '斥候' and self.day < 3:
                weights.append(0.30)  # D3 之前必杀
            elif role == '军医':
                weights.append(0.15)
            elif role == '女伯爵':
                weights.append(0.20)
            elif role == '盾卫':
                weights.append(0.20)
            elif role == '审讯官':
                weights.append(0.10)
            else:
                weights.append(0.05)
        return random.choices(candidates, weights=weights)[0]

    def d1_morning(self):
        """D1 黎明: 处理 内应延迟变傀儡"""
        for s in self.config:
            if self.config[s].get('puppet_pending'):
                self.config[s]['role'] = '傀儡'
                self.config[s]['puppet'] = True
                self.config[s]['register_outsider'] = True
                self.config[s].pop('puppet_pending', None)
        # 对于 暗箭手 N1 选的, 已经在 n1 时变傀儡

    def day_execute(self):
        """善良处决决策 (基于嫌疑+信息累积+真实玩家失误率)"""
        alive = self.alive_seats()
        if not alive:
            return None

        # 不处决概率 (高玩 D1-D2 谨慎, D3+ 必动)
        if self.day == 1:
            non_exec = 0.70
        elif self.day == 2:
            non_exec = 0.35
        else:
            non_exec = 0.10

        # 决战日(alive<=4) 必须处决
        if len(alive) <= 4:
            non_exec = 0.05

        if random.random() < non_exec:
            self.log(f"  D{self.day} 不处决")
            return None

        # 嫌疑权重 - 真实玩家 D1 几乎随机, D 越大信息越多
        # 这模拟"信息累积让锁定速度增加"
        evil_weight_by_day = {
            1: 0.10, 2: 0.15, 3: 0.30, 4: 0.50, 5: 0.70, 6: 0.85, 7: 0.90,
        }
        evil_w = evil_weight_by_day.get(self.day, 0.90)
        good_w = 0.10  # 善良误杀基线
        outsider_w = 0.02  # 外来者很少处决 (自爆 = 善良信任)

        # === 假信息流 (蛊惑者污染) ===
        # 蛊惑者活着 → 信息源被污染, 善良 alignment 推断不准
        hex_alive = any(self.config[s]['alive'] and self.config[s]['role'] == '蛊惑者'
                        for s in self.config)
        hex_residual = (self.hex_died_day is not None
                        and 0 < self.day - self.hex_died_day <= 2)
        if hex_alive:
            # 蛊惑者活: 假信息持续注入
            evil_w *= 0.60
            good_w *= 1.40
            self.log(f"  [蛊惑者活] 假信息流 → 锁定能力 -40%, 误杀率 +40%", 1)
        elif hex_residual:
            # 蛊惑者死后 1-2 天残留: 善良还在消化历史假信息
            evil_w *= 0.80
            good_w *= 1.20
            self.log(f"  [蛊惑者残留] 历史假信息 → 锁定能力 -20%", 1)

        # === 信息真空崩塌 ===
        # 信息源被夜杀挖空 → 善良只能凭旧信息+行为推理 → 锁定能力下降, 错杀飙升
        if self.initial_info_sources > 0:
            dead_info = sum(
                1 for s in self.config
                if not self.config[s]['alive']
                and self.config[s].get('original_role') in INFO_SOURCES
            )
            vacuum_ratio = dead_info / self.initial_info_sources
            if vacuum_ratio >= 0.75:
                evil_w *= 0.50
                good_w *= 3.0
                outsider_w *= 2.5
                self.log(f"  [信息真空 严重] 信息源死亡 {dead_info}/{self.initial_info_sources} → 锁定 -50%, 错杀 ×3", 1)
            elif vacuum_ratio >= 0.50:
                evil_w *= 0.70
                good_w *= 2.0
                outsider_w *= 1.8
                self.log(f"  [信息真空] 信息源死亡 {dead_info}/{self.initial_info_sources} → 锁定 -30%, 错杀 ×2", 1)

        # === 千面人信任崩塌 ===
        # 千面人 setup: 处决1恶魔但游戏没结束 → 善良发现"还有恶魔" → 信任崩塌
        # 真实玩家崩塌 ≠ 不处决, 崩塌 = 错杀(嫌疑洗牌+邪恶引导)
        if (self.is_lunatic_setup and self.demons_killed >= 1
                and len(self.alive_demons()) >= 1):
            # 信任崩塌: 锁定能力跌, 错杀率飙
            collapse_factor = 0.50 if self.demons_killed == 1 else 0.65
            evil_w *= collapse_factor
            good_w *= 3.0  # 错杀率飙升 (善良乱杀 + 邪恶发言引导)
            outsider_w *= 2.0  # 外来者也成为嫌疑目标
            self.log(f"  [千面人信任崩塌] 已死{self.demons_killed}恶魔仍有恶魔 → 锁定 -{int((1-collapse_factor)*100)}%, 错杀率 ×3", 1)

        # 自爆角色 (公开身份的) 嫌疑降低
        # 这里简化: 真外来者已经"看起来善良" (假设他们 D1 自爆), 不应处决
        suspects = []
        for s in alive:
            team = self.config[s]['team']
            role = self.config[s]['role']
            c = self.config[s]
            if team == '邪恶':
                # 爪牙 bluff 战术: 在被识破前嫌疑等同于装的角色
                bluff_type = c.get('bluff_type')
                bluff_until = c.get('bluff_until_day', 0)
                if bluff_type and self.day < bluff_until:
                    if bluff_type == 'outsider':
                        # 装外来者 → 自爆免死金牌, 比真外来者还安全
                        w = outsider_w * 0.7
                    else:  # 装镇民
                        # 装镇民 → 善良信任直到识破
                        w = good_w
                elif bluff_type and self.day == bluff_until:
                    # 识破当天: 半信半疑
                    w = evil_w * 0.5
                else:
                    # 已识破: 全嫌疑
                    w = evil_w
            elif team == '外来者' or role == '傀儡':
                w = outsider_w  # 外来者+傀儡 (但 register 外来者) 都很少处决
            else:
                w = good_w
            suspects.append((s, w))

        seats, weights = zip(*suspects)
        norm = [w/sum(weights) for w in weights]
        target = random.choices(seats, weights=norm)[0]

        # 投票通过率 - 真邪恶通过率高, 错杀通过率低
        actually_evil = self.config[target]['team'] == '邪恶'
        evil_dead_total = len(self.evil_dead_votes)
        if actually_evil:
            pass_prob = 0.80
        else:
            pass_prob = 0.40  # 错杀难通过 (善良会犹豫)
        pass_prob -= evil_dead_total * 0.06  # 邪恶死票阻投票

        if random.random() > pass_prob:
            self.log(f"  D{self.day} 提名 {target} ({self.config[target]['player']}) 失败")
            return None

        self.log(f"  D{self.day} 处决: {target} ({self.config[target]['player']}, {self.config[target]['role']})")
        self.kill(target, method='处决')
        return target

    def check_win(self):
        alive = self.alive_seats()
        demons_alive = self.alive_demons()
        if not demons_alive:
            return '善良'
        if len(alive) <= 2 and demons_alive:
            return '邪恶'
        return None

    def play(self):
        """完整游戏"""
        self.print_config()
        self.n0_setup()
        self.day = 1

        max_days = 15  # 真实游戏不超时, 给足窗口让游戏自然结束
        while self.day <= max_days:
            # 夜晚
            if self.day == 1:
                self.n1_actions()
                self.d1_morning()
            else:
                self.log(f"\n=== N{self.day} ===")
                self.n_kill()

            # 检查胜负
            w = self.check_win()
            if w:
                return w, self.day

            # 白天
            self.log(f"\n=== D{self.day} ===")
            self.day_execute()

            # 检查胜负
            w = self.check_win()
            if w:
                return w, self.day

            self.day += 1

        return '平局/超时', self.day - 1


def run_batch(n=30, verbose=False):
    results = {'善良': 0, '邪恶': 0, '平局/超时': 0}
    days_total = 0
    print(f"\n=== 跑 {n} 局 ===\n")
    for i in range(n):
        g = Game(verbose=verbose)
        winner, days = g.play()
        results[winner] += 1
        days_total += days
        if verbose:
            print(f"\n>>> 第 {i+1} 局: {winner}胜, {days} 天\n" + "="*60)

    print(f"\n=== 结果 ===")
    print(f"善良: {results['善良']}/{n} = {results['善良']*100/n:.1f}%")
    print(f"邪恶: {results['邪恶']}/{n} = {results['邪恶']*100/n:.1f}%")
    if results['平局/超时'] > 0:
        print(f"平局/超时: {results['平局/超时']}")
    print(f"平均天数: {days_total/n:.1f}")


if __name__ == '__main__':
    args = sys.argv[1:]
    verbose = '-v' in args
    args = [a for a in args if a != '-v']

    if args:
        try:
            n = int(args[0])
            run_batch(n, verbose=verbose)
        except ValueError:
            print("Usage: python3 botc_simulator.py [n_games] [-v]")
            sys.exit(1)
    else:
        g = Game(verbose=True)
        winner, days = g.play()
        print(f"\n=== 胜负 ===")
        print(f"{winner}胜, 用时 {days} 天")
        print(f"\n死亡顺序:")
        for time, seat, role in g.deaths:
            print(f"  {time}: 座 {seat} ({role})")
