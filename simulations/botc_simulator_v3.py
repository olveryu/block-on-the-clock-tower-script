#!/usr/bin/env python3
"""
围城之夜 12 人模拟器 v3 (完整剧本机制 + 信息流 + 善良 reasoner)
================================================================
按官方 weicheng.json 完整建模:
- 9 个信息源镇民每夜/白天产生 InfoEvent
- 蛊惑者/军需官醉酒会扭曲信息 (declared != actual)
- 邪恶玩家 N0 各选 bluff role, 按所装角色生成假信息
- 善良 reasoner: 维护 claims 注册, 用矛盾检测算嫌疑, 处决基于嫌疑

用法:
    python3 botc_simulator_v3.py        # 跑 1 局详细
    python3 botc_simulator_v3.py 100    # 跑 N 局批量
"""

import random
import sys
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set, Dict, Tuple
from itertools import combinations

# ============= 角色池 =============
TOWNSFOLK_POOL = [
    '斥候', '密探', '巡逻兵', '审讯官', '游侠', '军医',
    '书记官', '军需官', '牧师', '纹章官', '盾卫', '女伯爵', '瞭望兵'
]
OUTSIDER_POOL = ['伤兵', '逃兵', '难民', '俘虏']
MINION_POOL = ['内应', '蛊惑者', '叛将', '死士']
DEMON_POOL = ['攻城将军', '先锋官', '千面人', '暗箭手']
INFO_SOURCES = {'斥候', '密探', '巡逻兵', '审讯官', '书记官', '纹章官', '瞭望兵', '军医', '牧师'}
PLAYERS = ['阿信', '小白', '二哥', '月儿', '老王', '阿龙',
           '莉莉', '小七', '大刘', '苗苗', '阿强', '雪儿']


def is_demon_role(role): return role in DEMON_POOL or '千面人' in role
def is_minion_role(role): return role in MINION_POOL
def is_outsider_role(role): return role in OUTSIDER_POOL


# ============= InfoEvent =============
@dataclass
class InfoEvent:
    source_seat: int
    claimed_role: str
    actual_role: str
    day: int
    is_night: bool
    targets: List[int] = field(default_factory=list)
    actual_result: Any = None
    declared_result: Any = None
    is_distorted: bool = False
    is_fake_bluff: bool = False

    def __repr__(self):
        marker = ''
        if self.is_fake_bluff:
            marker = '★bluff'
        elif self.is_distorted:
            marker = '★distorted'
        return (f'<{self.claimed_role}@{self.source_seat} '
                f'{"N" if self.is_night else "D"}{self.day} '
                f'targets={self.targets} -> {self.declared_result} {marker}>')


# ============= 玩家状态 =============
@dataclass
class PlayerState:
    seat: int
    name: str
    role: str
    original_role: str
    team: str
    alive: bool = True
    is_drunk: bool = False
    is_hexed: bool = False
    register_outsider: bool = False
    register_minion: bool = False
    bluff_role: Optional[str] = None
    claimed_role: Optional[str] = None
    puppet: bool = False


# ============= 主游戏类 =============
class Game:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.day = 0
        self.players: Dict[int, PlayerState] = {}

        self.demon_role = None
        self.is_lunatic_setup = False
        self.demon_seats: List[int] = []
        self.minion_seats: List[int] = []
        self.evil_seats: List[int] = []
        self.bluffs: List[str] = []
        self.not_in_play_outsiders: List[str] = []
        self.not_in_play_minions: List[str] = []
        self.outsiders: List[str] = []
        self.townsfolk: List[str] = []

        self.has_save_baron = False
        self.has_save_shield = False
        self.dead_man_seat = None
        self.dead_man_active = False
        self.refugee_used = False
        self.evil_dead_votes: Set[int] = set()

        self.archer_n1_target = None
        self.archer_swapped = False

        self.hex_target = None
        self.hex_target_yesterday = None
        self.drunk_target = None

        self.events: List[InfoEvent] = []
        self.deaths: List[Tuple[str, int, str]] = []
        self.suspicion: Dict[int, float] = {}

        self._generate_config()
        self._init_bluffs()

    def log(self, msg, indent=0):
        if self.verbose:
            print('  ' * indent + msg)

    # ============= 配置 =============
    def _generate_config(self):
        demon = random.choice(DEMON_POOL)
        minions_raw = random.sample(MINION_POOL, 2)
        self.is_lunatic_setup = (demon == '千面人')

        if demon == '千面人':
            outsider_count, townsfolk_count = 1, 8
            minions_assignment = ['千面人', '千面人']
        elif demon == '先锋官' or '叛将' in minions_raw:
            outsider_count, townsfolk_count = 3, 6
            minions_assignment = minions_raw
        else:
            outsider_count, townsfolk_count = 2, 7
            minions_assignment = minions_raw

        townsfolk = random.sample(TOWNSFOLK_POOL, townsfolk_count)
        outsiders = random.sample(OUTSIDER_POOL, outsider_count)
        not_in_play_t = [t for t in TOWNSFOLK_POOL if t not in townsfolk]
        bluffs = random.sample(not_in_play_t, 3)

        self.demon_role = demon
        self.outsiders = outsiders
        self.townsfolk = townsfolk
        self.bluffs = bluffs
        self.not_in_play_outsiders = [o for o in OUTSIDER_POOL if o not in outsiders]
        self.not_in_play_minions = [m for m in MINION_POOL if m not in minions_assignment]

        roles = [demon] + minions_assignment + outsiders + townsfolk
        random.shuffle(roles)

        for i, (p, r) in enumerate(zip(PLAYERS, roles), 1):
            is_demon = (r == demon and demon != '千面人') or '千面人' in r
            is_minion = r in MINION_POOL and r != '千面人'
            if is_demon:
                team = '邪恶'
                self.demon_seats.append(i)
            elif is_minion:
                team = '邪恶'
                self.minion_seats.append(i)
            elif r in outsiders:
                team = '外来者'
            else:
                team = '镇民'

            ps = PlayerState(seat=i, name=p, role=r, original_role=r, team=team)
            ps.register_outsider = (r in outsiders) or (r == '死士') or ('千面人' in r)
            ps.register_minion = is_minion or (r == '死士') or ('千面人' in r)
            self.players[i] = ps

            if team == '邪恶':
                self.evil_seats.append(i)
            if r == '死士':
                self.dead_man_seat = i
                self.dead_man_active = True
            if r == '女伯爵':
                self.has_save_baron = True
            if r == '盾卫':
                self.has_save_shield = True

    def _init_bluffs(self):
        """N0 邪恶各选 bluff 角色, 不撞."""
        used = set()
        for seat in self.evil_seats:
            p = self.players[seat]
            options = []
            if is_demon_role(p.role) or '千面人' in p.role:
                # 恶魔/千面人 装 bluffs 给的镇民
                options = [b for b in self.bluffs if b not in used]
            else:
                # 爪牙: 60% 装外来者, 40% 装镇民
                if random.random() < 0.6:
                    pool = self.not_in_play_outsiders + self.outsiders
                    options = [r for r in pool if r not in used]
                if not options:
                    options = [b for b in self.bluffs if b not in used]
            if options:
                p.bluff_role = random.choice(options)
                used.add(p.bluff_role)
            else:
                # 实在没得选, 装镇民 bluff
                p.bluff_role = random.choice(self.bluffs)
            p.claimed_role = p.bluff_role

        for seat in self.players:
            if seat not in self.evil_seats:
                self.players[seat].claimed_role = self.players[seat].role

    def alive_seats(self, exclude=None):
        excl = set(exclude or [])
        return [s for s in self.players if self.players[s].alive and s not in excl]

    def alive_demons(self):
        return [s for s in self.players if self.players[s].alive and is_demon_role(self.players[s].role)]

    def evil_alive(self, exclude_demon=False):
        result = [s for s in self.players if self.players[s].alive and self.players[s].team == '邪恶']
        if exclude_demon:
            result = [s for s in result if not is_demon_role(self.players[s].role)]
        return result

    def good_alive(self):
        return [s for s in self.players if self.players[s].alive and self.players[s].team != '邪恶']

    def neighbors(self, seat):
        left = seat - 1 if seat > 1 else 12
        right = seat + 1 if seat < 12 else 1
        # 找活的邻座 (跳过死人)
        def find_alive(start, direction):
            cur = start
            for _ in range(12):
                cur = (cur - 1) if direction == -1 else (cur + 1)
                if cur < 1: cur = 12
                if cur > 12: cur = 1
                if self.players[cur].alive:
                    return cur
            return None
        return find_alive(seat, -1), find_alive(seat, 1)

    def is_seat_evil_register(self, seat):
        """该座位是否被视为邪恶 (爪牙/恶魔/死士/千面人/傀儡)"""
        p = self.players[seat]
        return p.team == '邪恶' or p.register_minion

    def is_seat_outsider_register(self, seat):
        p = self.players[seat]
        return p.team == '外来者' or p.register_outsider or p.role == '傀儡'

    # ============= 信息生成器 =============
    def is_info_distorted(self, seat):
        """该玩家的信息是否被扭曲 (蛊惑/醉酒/傀儡)"""
        p = self.players[seat]
        if p.is_hexed or p.is_drunk or p.role == '傀儡' or p.puppet:
            return True
        return False

    def gen_scout_n1(self, seat):
        """斥候 N1: 学 2 个恶魔角色, 1 个真. 蛊惑/醉酒 → 2 个假"""
        p = self.players[seat]
        true_demon_role = self.players[self.demon_seats[0]].role if self.demon_seats else None
        if not true_demon_role:
            return None
        # 千面人 setup: true_demon_role = '千面人'
        other_demons = [d for d in DEMON_POOL if d != true_demon_role]
        fake = random.choice(other_demons)
        actual = sorted([true_demon_role, fake])
        if self.is_info_distorted(seat):
            fake_pair = random.sample(other_demons, 2)
            declared = sorted(fake_pair)
        else:
            declared = actual
        return InfoEvent(seat, '斥候', p.role, self.day, True,
                         targets=[], actual_result=actual,
                         declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_scout_d3(self, seat):
        """斥候 D3+: 白天问得知恶魔角色 (只学一次?剧本是每天可问, 简化为 D3 每天一次)"""
        p = self.players[seat]
        true_demon_role = self.players[self.demon_seats[0]].role if self.demon_seats else None
        if not true_demon_role:
            return None
        if self.is_info_distorted(seat):
            declared = random.choice([d for d in DEMON_POOL if d != true_demon_role])
        else:
            declared = true_demon_role
        return InfoEvent(seat, '斥候', p.role, self.day, False,
                         targets=[], actual_result=true_demon_role,
                         declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_clerk_n1(self, seat):
        """书记官 N1: 学外来者+爪牙的座位号总和"""
        p = self.players[seat]
        outsider_seats = [s for s in self.players if self.is_seat_outsider_register(s) and s != seat]
        minion_seats = [s for s in self.players if self.players[s].register_minion and s != seat]
        actual_sum = sum(set(outsider_seats + minion_seats))
        if self.is_info_distorted(seat):
            declared = actual_sum + random.choice([-5, -3, 3, 5, 7])
            declared = max(0, declared)
        else:
            declared = actual_sum
        return InfoEvent(seat, '书记官', p.role, 1, True,
                         actual_result=actual_sum, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_lookout_night(self, seat):
        """瞭望兵: 每夜学 1 个不在场的爪牙/外来者"""
        p = self.players[seat]
        not_in_play = self.not_in_play_outsiders + self.not_in_play_minions
        in_play_minions = [self.players[s].original_role for s in self.minion_seats]
        in_play_outsiders = self.outsiders
        if not not_in_play:
            return None
        actual = random.choice(not_in_play)
        if self.is_info_distorted(seat):
            # 假: 给一个在场的角色
            in_play = in_play_minions + in_play_outsiders
            if in_play:
                declared = random.choice(in_play)
            else:
                declared = actual
        else:
            declared = actual
        return InfoEvent(seat, '瞭望兵', p.role, self.day, True,
                         actual_result=actual, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_interrogator_night(self, seat):
        """审讯官: 每夜选 3 名活人, 学是否恰好 1 名非恶魔邪恶"""
        p = self.players[seat]
        candidates = [s for s in self.alive_seats() if s != seat]
        if len(candidates) < 3:
            return None
        chosen = random.sample(candidates, 3)
        non_demon_evil = sum(1 for s in chosen
                              if self.players[s].team == '邪恶'
                              and not is_demon_role(self.players[s].role))
        actual = (non_demon_evil == 1)
        if self.is_info_distorted(seat):
            declared = not actual
        else:
            declared = actual
        return InfoEvent(seat, '审讯官', p.role, self.day, True,
                         targets=chosen, actual_result=actual, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_patroller_night(self, seat):
        """巡逻兵: 每夜选 1 名玩家, 学他邻座有没有外来者"""
        p = self.players[seat]
        candidates = [s for s in self.alive_seats() if s != seat]
        if not candidates:
            return None
        chosen = random.choice(candidates)
        l, r = self.neighbors(chosen)
        actual = (l is not None and self.is_seat_outsider_register(l)) or \
                 (r is not None and self.is_seat_outsider_register(r))
        if self.is_info_distorted(seat):
            declared = not actual
        else:
            declared = actual
        return InfoEvent(seat, '巡逻兵', p.role, self.day, True,
                         targets=[chosen], actual_result=actual, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_doctor_night(self, seat):
        """军医: 每夜选 1 名, 死人验邪恶/活人验是否被唤醒"""
        p = self.players[seat]
        all_seats = [s for s in self.players if s != seat]
        if not all_seats:
            return None
        chosen = random.choice(all_seats)
        target = self.players[chosen]
        if not target.alive:
            actual = self.is_seat_evil_register(chosen)
        else:
            # 是否当晚被唤醒 (恶魔/爪牙/某些镇民会被唤醒)
            actual = (target.team == '邪恶' or
                      target.role in {'斥候', '审讯官', '瞭望兵', '巡逻兵', '军医', '牧师', '蛊惑者', '内应'} or
                      is_demon_role(target.role))
        if self.is_info_distorted(seat):
            declared = not actual
        else:
            declared = actual
        return InfoEvent(seat, '军医', p.role, self.day, True,
                         targets=[chosen], actual_result=actual, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_priest_night(self, seat):
        """牧师: 每夜学有多少人不再是最初的角色"""
        p = self.players[seat]
        changed = sum(1 for s in self.players if self.players[s].alive
                      and self.players[s].role != self.players[s].original_role)
        if self.is_info_distorted(seat):
            declared = changed + random.choice([-1, 1, 2])
            declared = max(0, declared)
        else:
            declared = changed
        return InfoEvent(seat, '牧师', p.role, self.day, True,
                         actual_result=changed, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_herald_day(self, seat):
        """纹章官: 白天指定 3 名学是否恰好 1 名外来者"""
        p = self.players[seat]
        candidates = [s for s in self.alive_seats() if s != seat]
        if len(candidates) < 3:
            return None
        chosen = random.sample(candidates, 3)
        outsider_count = sum(1 for s in chosen if self.is_seat_outsider_register(s))
        actual = (outsider_count == 1)
        if self.is_info_distorted(seat):
            declared = not actual
        else:
            declared = actual
        return InfoEvent(seat, '纹章官', p.role, self.day, False,
                         targets=chosen, actual_result=actual, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    def gen_spy_day(self, seat):
        """密探: 白天指定 2 名学谁离爪牙更近"""
        p = self.players[seat]
        candidates = [s for s in self.alive_seats() if s != seat]
        if len(candidates) < 2:
            return None
        chosen = random.sample(candidates, 2)
        # 计算每人到最近爪牙距离
        def dist_to_minion(s):
            min_d = 12
            for m in self.minion_seats:
                if not self.players[m].alive:
                    continue
                d = min(abs(s - m), 12 - abs(s - m))
                if d < min_d:
                    min_d = d
            return min_d
        d0 = dist_to_minion(chosen[0])
        d1 = dist_to_minion(chosen[1])
        actual = chosen[0] if d0 <= d1 else chosen[1]
        if self.is_info_distorted(seat):
            declared = chosen[1] if actual == chosen[0] else chosen[0]
        else:
            declared = actual
        return InfoEvent(seat, '密探', p.role, self.day, False,
                         targets=chosen, actual_result=actual, declared_result=declared,
                         is_distorted=self.is_info_distorted(seat))

    # ============= 邪恶 bluff 假信息 =============
    def gen_evil_bluff_info(self, seat):
        """邪恶玩家按 bluff_role 生成假信息 (装那个角色的能力)."""
        p = self.players[seat]
        if not p.bluff_role:
            return None
        bluff = p.bluff_role

        # 装外来者 — 不产生信息 (外来者死亡才触发)
        if bluff in OUTSIDER_POOL:
            return None

        # 装信息源镇民 — 编一个合理假信息
        if bluff == '斥候':
            if self.day != 1:
                return None
            # 给 2 个恶魔角色 (但都不是真的, 或巧合包含真)
            options = list(DEMON_POOL)
            random.shuffle(options)
            declared = sorted(options[:2])
            return InfoEvent(seat, '斥候', p.role, 1, True,
                             actual_result=None, declared_result=declared,
                             is_fake_bluff=True)
        elif bluff == '书记官':
            if self.day != 1:
                return None
            # 编 sum: 用一个对邪恶有利的伪和 (指向真镇民的座位)
            target_innocents = [s for s in self.alive_seats() if self.players[s].team == '镇民']
            if len(target_innocents) >= 2:
                fake_sum = sum(random.sample(target_innocents, 2))
                return InfoEvent(seat, '书记官', p.role, 1, True,
                                 actual_result=None, declared_result=fake_sum,
                                 is_fake_bluff=True)
            return None
        elif bluff == '瞭望兵':
            # 假声称一个不在场角色 (实际上可能在场)
            in_play = [self.players[s].original_role for s in self.minion_seats] + self.outsiders
            if in_play:
                declared = random.choice(in_play)  # 故意指真在场角色当"不在场"
                return InfoEvent(seat, '瞭望兵', p.role, self.day, True,
                                 actual_result=None, declared_result=declared,
                                 is_fake_bluff=True)
            return None
        elif bluff == '审讯官':
            # 假声称 3 名玩家中"恰好 1 邪恶" — 选 3 真镇民+假指控
            innocents = [s for s in self.alive_seats() if self.players[s].team == '镇民' and s != seat]
            if len(innocents) >= 3:
                chosen = random.sample(innocents, 3)
                declared = True  # 假说 yes
                return InfoEvent(seat, '审讯官', p.role, self.day, True,
                                 targets=chosen, declared_result=declared,
                                 is_fake_bluff=True)
            return None
        elif bluff == '巡逻兵':
            cands = [s for s in self.alive_seats() if s != seat]
            if cands:
                chosen = random.choice(cands)
                declared = random.choice([True, False])
                return InfoEvent(seat, '巡逻兵', p.role, self.day, True,
                                 targets=[chosen], declared_result=declared,
                                 is_fake_bluff=True)
            return None
        elif bluff == '军医':
            cands = [s for s in self.alive_seats() if s != seat]
            if cands:
                chosen = random.choice(cands)
                # 假说该真镇民"被唤醒" → 推善良怀疑他
                declared = (self.players[chosen].team == '镇民')  # 故意框真镇民
                return InfoEvent(seat, '军医', p.role, self.day, True,
                                 targets=[chosen], declared_result=declared,
                                 is_fake_bluff=True)
            return None
        elif bluff == '牧师':
            declared = random.randint(0, 3)
            return InfoEvent(seat, '牧师', p.role, self.day, True,
                             declared_result=declared, is_fake_bluff=True)
        elif bluff == '纹章官':
            innocents = [s for s in self.alive_seats() if self.players[s].team == '镇民' and s != seat]
            if len(innocents) >= 3:
                chosen = random.sample(innocents, 3)
                return InfoEvent(seat, '纹章官', p.role, self.day, False,
                                 targets=chosen, declared_result=True,
                                 is_fake_bluff=True)
            return None
        elif bluff == '密探':
            cands = [s for s in self.alive_seats() if s != seat]
            if len(cands) >= 2:
                chosen = random.sample(cands, 2)
                # 假指真镇民"离爪牙近"
                target_inn = [s for s in chosen if self.players[s].team == '镇民']
                declared = target_inn[0] if target_inn else chosen[0]
                return InfoEvent(seat, '密探', p.role, self.day, False,
                                 targets=chosen, declared_result=declared,
                                 is_fake_bluff=True)
            return None
        return None

    # ============= 杀人 / 死亡链 =============
    def kill(self, seat, method='夜杀', track_demon_kill=True):
        if not self.players[seat].alive:
            return False
        self.players[seat].alive = False
        time = f'D{self.day}' if method == '处决' else f'N{self.day}'
        self.deaths.append((time, seat, self.players[seat].role))
        self.log(f'  → {time} 死亡: {seat} ({self.players[seat].name}, {self.players[seat].role})', 1)

        if self.players[seat].role == '女伯爵': self.has_save_baron = False
        if self.players[seat].role == '盾卫': self.has_save_shield = False

        # 死士复活栈
        if is_demon_role(self.players[seat].role) and self.dead_man_active:
            if self.dead_man_seat and self.players[self.dead_man_seat].alive:
                old = self.players[self.dead_man_seat].role
                new = self.players[seat].original_role
                self.players[self.dead_man_seat].role = new
                self.players[self.dead_man_seat].team = '邪恶'
                self.demon_seats.append(self.dead_man_seat)
                self.dead_man_active = False
                self.log(f'  ★ 死士复活: {self.dead_man_seat} 从 {old} 变 {new}', 1)

        # 触发死亡链
        if self._should_trigger(seat, method):
            self._trigger_chain(seat)
        return True

    def _should_trigger(self, seat, method):
        c = self.players[seat]
        if method == '处决' and self.has_save_baron:
            return False
        if method == '夜杀' and self.has_save_shield:
            return False
        # 先锋官特性: 外来者视为傀儡 → 触发傀儡死亡链
        # 我们简化: 外来者本身触发自己的死亡能力, 这里看角色
        return (c.role in OUTSIDER_POOL or c.role == '傀儡' or
                '千面人' in c.role or c.role == '死士')

    def _trigger_chain(self, seat):
        role = self.players[seat].role
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
        # 先锋官 setup: 外来者也触发傀儡 (额外)
        if self.demon_role == '先锋官' and role in OUTSIDER_POOL:
            # 已经触发了自己的, 还要再触发傀儡 (额外效果)
            self._trigger_puppet_death()

    def _trigger_puppet_death(self):
        """傀儡死亡 → 选外来者发动死亡能力"""
        valid = []
        if not self.refugee_used and any(not self.players[s].alive and self.players[s].team != '邪恶'
                                          and s not in self.evil_dead_votes for s in self.players):
            valid.append(('难民', 0.4))
        if self.alive_seats(exclude=self.evil_seats):
            valid.append(('伤兵', 0.3))
            valid.append(('逃兵', 0.4))
        if self.evil_alive(exclude_demon=True):
            valid.append(('俘虏', 0.2))
        if not valid:
            return
        choices_v, weights = zip(*valid)
        chosen = random.choices(choices_v, weights=weights)[0]
        self.log(f'  傀儡死亡 → 恶魔选: {chosen}', 1)
        if chosen == '难民': self._trigger_refugee()
        elif chosen == '伤兵': self._trigger_wounded()
        elif chosen == '逃兵': self._trigger_deserter()
        elif chosen == '俘虏': self._trigger_captive()

    def _trigger_refugee(self):
        if self.refugee_used: return
        good_dead = [s for s in self.players if not self.players[s].alive
                      and self.players[s].team != '邪恶' and s not in self.evil_dead_votes]
        if not good_dead: return
        chosen = random.choice(good_dead)
        self.evil_dead_votes.add(chosen)
        self.refugee_used = True
        self.log(f'  ★ 难民触发: {chosen} ({self.players[chosen].name}) 死人变邪恶', 1)

    def _trigger_wounded(self):
        # 排除恶魔队友
        cands = [s for s in self.alive_seats() if s not in self.evil_seats]
        if not cands: return
        weights = []
        for s in cands:
            r = self.players[s].role
            if r in ['军医', '盾卫', '审讯官']: weights.append(0.30)
            elif r in ['女伯爵', '斥候']: weights.append(0.25)
            else: weights.append(0.05)
        chosen = random.choices(cands, weights=weights)[0]
        old = self.players[chosen].role
        self.players[chosen].role = '傀儡'
        self.players[chosen].puppet = True
        self.players[chosen].register_outsider = True
        if old == '女伯爵': self.has_save_baron = False
        if old == '盾卫': self.has_save_shield = False
        self.log(f'  ★ 伤兵触发: {chosen} ({self.players[chosen].name}) 从 {old} 变傀儡', 1)

    def _trigger_deserter(self):
        # 排除恶魔队友 — bug fix
        cands = [s for s in self.alive_seats() if s not in self.evil_seats]
        if not cands: return
        weights = []
        for s in cands:
            r = self.players[s].role
            if r in ['军医', '审讯官', '斥候']: weights.append(0.30)
            elif r == '游侠': weights.append(0.05)
            else: weights.append(0.10)
        chosen = random.choices(cands, weights=weights)[0]
        self.log(f'  ★ 逃兵触发: 选 {chosen} ({self.players[chosen].name}) 当晚死', 1)
        self.kill(chosen, method='夜杀')

    def _trigger_captive(self):
        evil_alive = self.evil_alive(exclude_demon=True)
        if not evil_alive: return
        chosen_seat = random.choice(evil_alive)
        options = ['蛊惑者', '内应', '叛将']
        if not self.dead_man_active:
            options.append('死士')
        chosen_role = random.choice(options)
        old = self.players[chosen_seat].role
        self.players[chosen_seat].role = chosen_role
        if chosen_role == '死士':
            self.dead_man_seat = chosen_seat
            self.dead_man_active = True
        self.log(f'  ★ 俘虏触发: {chosen_seat} ({self.players[chosen_seat].name}) 从 {old} 变 {chosen_role}', 1)

    # ============= 夜晚行动 =============
    def n0_setup(self):
        self.log('=== N0 邪恶互知 ===')
        self.log(f'  bluffs: {self.bluffs}')
        for s in self.evil_seats:
            p = self.players[s]
            self.log(f'  {s} ({p.role}) bluff: {p.bluff_role}')
        if self.dead_man_seat:
            fake_o = random.choice(OUTSIDER_POOL)
            self.log(f'  死士({self.dead_man_seat}) 自以为: {fake_o}')

    def night_action_evil(self):
        """夜晚邪恶行动 (蛊惑/暗箭手 N1/恶魔杀)"""
        # 蛊惑者
        for hex_seat in [s for s in self.minion_seats if self.players[s].alive
                         and self.players[s].role == '蛊惑者']:
            l, r = self.neighbors(hex_seat)
            cands = [x for x in [l, r] if x is not None]
            if cands:
                t = random.choice(cands)
                self.hex_target = t
                self.players[t].is_hexed = True
                self.log(f'  蛊惑者({hex_seat}) 蛊惑 {t}')

        # 暗箭手 N1
        if self.day == 1 and self.demon_role == '暗箭手':
            arrow = self.demon_seats[0]
            others = [s for s in self.alive_seats(exclude=[arrow]) if s not in self.evil_seats]
            if others:
                t = random.choice(others)
                self.archer_n1_target = t
                self.players[t].role = '傀儡'
                self.players[t].puppet = True
                self.players[t].register_outsider = True
                self.log(f'  暗箭手({arrow}) 选 {t} 变傀儡')

        # 内应 N1
        if self.day == 1:
            for mole in [s for s in self.minion_seats if self.players[s].role == '内应']:
                others = [s for s in self.alive_seats(exclude=[mole])]
                if others:
                    t = random.choice(others)
                    # 明天白天双变傀儡 (这里直接处理)
                    self.players[mole].role = '傀儡'
                    self.players[mole].puppet = True
                    self.players[mole].register_outsider = True
                    self.players[t].role = '傀儡'
                    self.players[t].puppet = True
                    self.players[t].register_outsider = True
                    self.log(f'  内应({mole}) 选 {t} → 双变傀儡')

        # 叛将 N2+
        if self.day >= 2:
            for tc in [s for s in self.minion_seats if self.players[s].alive and self.players[s].role == '叛将']:
                if random.random() < 0.20:
                    new_demon_role = random.choice([d for d in DEMON_POOL if d != self.demon_role])
                    if self.demon_seats and self.players[self.demon_seats[0]].alive:
                        # 50% 自己变, 50% 恶魔变 + 另一变傀儡
                        if random.random() < 0.5:
                            old = self.players[tc].role
                            self.players[tc].role = new_demon_role
                            self.demon_seats.append(tc)
                            # 真恶魔变傀儡
                            d_seat = self.demon_seats[0]
                            self.players[d_seat].role = '傀儡'
                            self.players[d_seat].puppet = True
                            self.demon_seats.remove(d_seat)
                            self.demon_role = new_demon_role
                            self.log(f'  叛将({tc}) 自变 {new_demon_role}, 恶魔变傀儡', 1)
                        else:
                            d_seat = self.demon_seats[0]
                            self.players[d_seat].role = new_demon_role
                            self.players[tc].role = '傀儡'
                            self.players[tc].puppet = True
                            self.demon_role = new_demon_role
                            self.log(f'  叛将({tc}) 让恶魔变 {new_demon_role}, 自变傀儡', 1)

        # 恶魔/千面人共同杀 (N2+)
        if self.day >= 2:
            # 攻击池: 默认排除恶魔本身 (恶魔不杀自己), 但保留爪牙 (战略自杀触发死亡链)
            demon_seats_active = [s for s in self.alive_seats()
                                   if is_demon_role(self.players[s].role)]
            attackable = [s for s in self.alive_seats() if s not in demon_seats_active]
            if any('千面人' in self.players[s].role for s in self.alive_seats()):
                t = self._choose_kill(attackable)
                if t:
                    self.log(f'  千面人共同杀: {t}')
                    self._execute_attack(t)
            elif self.demon_seats and self.players[self.demon_seats[0]].alive:
                t = self._choose_kill(attackable)
                if t:
                    self.log(f'  {self.players[self.demon_seats[0]].role}({self.demon_seats[0]}) 杀: {t}')
                    self._execute_attack(t)

    def _choose_kill(self, cands):
        """邪恶选夜杀目标. 包括战略性杀爪牙 (傀儡爪牙触发死亡链)"""
        if not cands: return None
        weights = []
        for s in cands:
            p = self.players[s]
            r = p.role
            # 战略性杀自己人 (傀儡爪牙: 死后触发傀儡死亡链, 多收益)
            if s in self.evil_seats:
                if p.puppet or r == '傀儡':
                    weights.append(0.20)  # 杀傀儡爪牙触发死亡链
                elif r == '死士':
                    # 杀死士 → 触发傀儡死亡能力 (但失去复活栈, 需权衡)
                    weights.append(0.05)
                else:
                    weights.append(0.02)  # 一般不杀普通爪牙
            # 不杀游侠 (反杀)
            elif r == '游侠': weights.append(0.05)
            # 信息源镇民优先 (清除信息)
            elif r in INFO_SOURCES: weights.append(0.30)
            elif r == '军医': weights.append(0.20)
            elif r == '盾卫': weights.append(0.20)
            elif r == '女伯爵': weights.append(0.20)
            else: weights.append(0.05)
        return random.choices(cands, weights=weights)[0]

    def _execute_attack(self, seat):
        if not self.players[seat].alive: return
        # 游侠反杀
        if self.players[seat].role == '游侠':
            evil_nd = self.evil_alive(exclude_demon=True)
            if evil_nd:
                rev = random.choice(evil_nd)
                self.log(f'  ★ 游侠夜死反杀 {rev}', 1)
                self.kill(rev, method='夜杀')

        # 暗箭手交换
        if (self.demon_role == '暗箭手' and seat == self.archer_n1_target
                and not self.archer_swapped):
            if random.random() < 0.4:
                evil_nd = self.evil_alive(exclude_demon=True)
                if evil_nd:
                    swap = random.choice(evil_nd)
                    arrow = self.demon_seats[0]
                    new_role = self.players[arrow].role
                    swap_role = self.players[swap].role
                    self.players[swap].role = new_role
                    self.players[arrow].role = swap_role
                    self.demon_seats.remove(arrow)
                    self.demon_seats.append(swap)
                    if not is_minion_role(swap_role):
                        # 暗箭手变成爪牙不在 minion_seats, 加入
                        self.minion_seats.append(arrow)
                    self.archer_swapped = True
                    self.log(f'  ★ 暗箭手交换: {arrow}<->{swap}', 1)

        self.kill(seat, method='夜杀')

    # ============= 信息收集 =============
    def night_info_gather(self):
        """所有信息源镇民+邪恶 bluff 产生当夜信息"""
        # 真镇民信息
        for seat in self.alive_seats():
            p = self.players[seat]
            if p.role not in INFO_SOURCES: continue
            ev = None
            if p.role == '斥候' and self.day == 1:
                ev = self.gen_scout_n1(seat)
            elif p.role == '书记官' and self.day == 1:
                ev = self.gen_clerk_n1(seat)
            elif p.role == '瞭望兵':
                ev = self.gen_lookout_night(seat)
            elif p.role == '审讯官':
                ev = self.gen_interrogator_night(seat)
            elif p.role == '巡逻兵':
                ev = self.gen_patroller_night(seat)
            elif p.role == '军医':
                ev = self.gen_doctor_night(seat)
            elif p.role == '牧师' and self.day >= 2:
                ev = self.gen_priest_night(seat)
            if ev:
                self.events.append(ev)
                if self.verbose:
                    distort = ' [扭曲]' if ev.is_distorted else ''
                    self.log(f'  信息: {seat}({p.role}) → {ev.declared_result}{distort}', 1)

        # 邪恶 bluff 信息 (装信息源镇民的)
        for seat in self.evil_seats:
            if not self.players[seat].alive: continue
            ev = self.gen_evil_bluff_info(seat)
            if ev:
                self.events.append(ev)
                if self.verbose:
                    self.log(f'  bluff: {seat}({self.players[seat].bluff_role}) → {ev.declared_result} [假]', 1)

    def day_info_gather(self):
        """白天行动: 军需官醉酒, 纹章官, 密探"""
        # 军需官 (醉酒邪恶/外来者)
        for seat in self.alive_seats():
            p = self.players[seat]
            if p.role != '军需官': continue
            cands = [s for s in self.alive_seats() if s != seat]
            if not cands: continue
            # 真军需官随机选一个 (现实中善良选嫌疑高的)
            chosen = random.choice(cands)
            target = self.players[chosen]
            # 如果选中真邪恶/外来者: 醉酒
            hit = (target.team == '邪恶' or target.team == '外来者')
            if hit and not self.is_info_distorted(seat):
                target.is_drunk = True
                self.drunk_target = chosen
                self.log(f'  军需官({seat}) 醉酒 {chosen} (命中)', 1)
            else:
                self.log(f'  军需官({seat}) 选 {chosen} (无效)', 1)

        # 纹章官+密探+斥候 D3+
        for seat in self.alive_seats():
            p = self.players[seat]
            ev = None
            if p.role == '纹章官':
                ev = self.gen_herald_day(seat)
            elif p.role == '密探':
                ev = self.gen_spy_day(seat)
            elif p.role == '斥候' and self.day >= 3:
                ev = self.gen_scout_d3(seat)
            if ev:
                self.events.append(ev)
                self.log(f'  信息: {seat}({p.role}) → {ev.declared_result}', 1)

        # 邪恶 bluff 白天信息
        for seat in self.evil_seats:
            if not self.players[seat].alive: continue
            p = self.players[seat]
            if p.bluff_role not in ['纹章官', '密探']: continue
            ev = self.gen_evil_bluff_info(seat)
            if ev:
                self.events.append(ev)
                self.log(f'  bluff: {seat}({p.bluff_role}) → {ev.declared_result} [假]', 1)

    # ============= Reasoner =============
    def compute_suspicion(self):
        """基于信息事件 + claims 计算每个活人的嫌疑分.
        分两轮: 先算 source 自身嫌疑 (claim 冲突/数学错), 再用 trusted source 信息推断 target."""
        susp = {s: 0.0 for s in self.alive_seats()}
        confirmed_good: Set[int] = set()  # 高度确认为善良 (信息一致的多 source)

        # === 第一轮: source 自身嫌疑 (基于 claims/数学) ===

        # A. 多人声称同 role → 各 +1.5
        claim_groups: Dict[str, List[int]] = {}
        for seat in self.alive_seats():
            cr = self.players[seat].claimed_role
            if cr and (cr in INFO_SOURCES or cr in {'盾卫', '女伯爵', '游侠', '军需官'}):
                claim_groups.setdefault(cr, []).append(seat)
        for role, seats in claim_groups.items():
            if len(seats) >= 2:
                for s in seats:
                    susp[s] += 1.5

        # B. 书记官 sum 数学合理性
        for ev in self.events:
            if ev.source_seat not in susp: continue
            if ev.claimed_role == '书记官':
                register_seats = {s for s in self.players
                                  if self.is_seat_outsider_register(s)
                                  or self.players[s].register_minion}
                total = len(register_seats)
                if total > 0:
                    min_sum = sum(range(1, total + 1))
                    max_sum = sum(range(12 - total + 1, 13))
                    if not (min_sum <= ev.declared_result <= max_sum):
                        susp[ev.source_seat] += 2.5

        # C. 瞭望兵 declared 是已确认在场 (来自其他源) → 矛盾
        lookout_decls = []
        for ev in self.events:
            if ev.claimed_role == '瞭望兵' and ev.source_seat in susp:
                lookout_decls.append((ev.source_seat, ev.declared_result))

        # 多个瞭望兵 declared 重复 → 至少 1 假
        seen = {}
        for s, d in lookout_decls:
            seen.setdefault(d, []).append(s)
        for d, seats in seen.items():
            if len(seats) >= 2:
                for s in seats:
                    susp[s] += 0.7

        # D. 自爆外来者超过场上数量 → 多余的是 bluff
        outsider_claims = [s for s in self.alive_seats()
                            if self.players[s].claimed_role in OUTSIDER_POOL]
        true_outsider_count = len(self.outsiders)
        if len(outsider_claims) > true_outsider_count:
            extra = len(outsider_claims) - true_outsider_count
            # 平均加 (实际邪恶 bluff 在其中)
            for s in outsider_claims:
                susp[s] += 0.5 * extra / len(outsider_claims)

        # === 第二轮: 用低自身嫌疑的 source 信息推断 target ===
        # 夜杀死的信息源 → 高度可信 (邪恶专杀真信息源)
        night_killed_info_sources = set()
        for time, seat, role in self.deaths:
            if time.startswith('N') and role in INFO_SOURCES:
                night_killed_info_sources.add(seat)

        def trust(seat):
            """source 可信度"""
            if seat in night_killed_info_sources:
                return 1.8  # 死信息源 → 追溯高度信任
            base = max(0.1, 1.0 - susp.get(seat, 0) * 0.3)
            return base

        for ev in self.events:
            # 死信息源仍提供信息 (夜杀死的 retroactively trust)
            if ev.source_seat not in susp and ev.source_seat not in night_killed_info_sources:
                continue
            tr = trust(ev.source_seat)

            # E. 审讯官 yes → targets 中至少 1 非恶魔邪恶
            if ev.claimed_role == '审讯官' and ev.declared_result == True:
                for t in ev.targets:
                    if t in susp:
                        susp[t] += 0.5 * tr
            elif ev.claimed_role == '审讯官' and ev.declared_result == False:
                # 0 邪恶 → targets 都是镇民/外来者/恶魔 (但恶魔不算非恶魔邪恶)
                for t in ev.targets:
                    if t in susp:
                        susp[t] -= 0.2 * tr

            # F. 巡逻兵 yes/no on邻座
            if ev.claimed_role == '巡逻兵' and ev.targets:
                t = ev.targets[0]
                l, r = self.neighbors(t)
                if ev.declared_result == True:
                    # 邻座有外来者 — 可能是真外来者也可能是 register 外来者 (爪牙/千面人/傀儡)
                    for nb in [l, r]:
                        if nb and nb in susp:
                            susp[nb] += 0.2 * tr
                else:
                    for nb in [l, r]:
                        if nb and nb in susp:
                            susp[nb] -= 0.1 * tr

            # G. 纹章官 yes → targets 中恰好 1 外来者/register 外来者
            if ev.claimed_role == '纹章官' and ev.declared_result == True:
                for t in ev.targets:
                    if t in susp:
                        susp[t] += 0.15 * tr

            # H. 密探 declared → 该座位离爪牙近
            if ev.claimed_role == '密探' and ev.declared_result in susp:
                susp[ev.declared_result] += 0.4 * tr

            # I. 军医 死人验邪恶 yes → 该死人是邪恶 (不影响活人 susp 但提供爪牙数信号)
            # 简化: 军医 declared yes 在死人身上 → 暂时不处理
            if ev.claimed_role == '军医' and ev.targets:
                t = ev.targets[0]
                # 活人验"被唤醒" yes → 该人是邪恶或唤醒角色
                if t in susp and ev.declared_result == True:
                    susp[t] += 0.2 * tr

            # J. 斥候 declared = 2 个恶魔角色 — 真恶魔角色应该是其中之一
            # 但善良不知哪个真, 不能直接降本身嫌疑
            # 不处理

            # K. 瞭望兵 declared X = 不在场 → 任何声称是 X 的玩家是邪恶 bluff
            if ev.claimed_role == '瞭望兵':
                for s in self.alive_seats():
                    if self.players[s].claimed_role == ev.declared_result and s != ev.source_seat:
                        susp[s] += 0.8 * tr

        # === 第三轮: 多夜交集推理 ===

        # L. 审讯官多夜 yes 交集: 同一 claimed_审讯官 的 yes 事件目标 intersect
        #    出现在多个 yes 事件的 seat = 高度嫌疑 (1 of 3 evil 锁定)
        interrogator_yes: Dict[int, List[Set[int]]] = {}  # source_seat -> [target sets]
        for ev in self.events:
            if ev.claimed_role != '审讯官': continue
            if not ev.declared_result: continue
            interrogator_yes.setdefault(ev.source_seat, []).append(set(ev.targets))
        for source, target_sets in interrogator_yes.items():
            if len(target_sets) < 2:
                continue
            tr = trust(source) if source in self.players else 0.5
            # 按 seat 计数出现次数
            count: Dict[int, int] = {}
            for ts in target_sets:
                for t in ts:
                    count[t] = count.get(t, 0) + 1
            # 同一 seat 出现 >=2 次 → 高度嫌疑
            for seat, c in count.items():
                if seat not in susp: continue
                if c >= 2:
                    susp[seat] += 0.6 * tr * (c - 1)

        # M. 巡逻兵多夜 yes 邻座: 找重复出现的邻座
        patrol_yes_neighbors: Dict[int, int] = {}
        for ev in self.events:
            if ev.claimed_role != '巡逻兵': continue
            if not ev.declared_result: continue
            if not ev.targets: continue
            t = ev.targets[0]
            l, r = self.neighbors(t)
            tr = trust(ev.source_seat)
            for nb in [l, r]:
                if nb and nb in susp:
                    patrol_yes_neighbors[nb] = patrol_yes_neighbors.get(nb, 0) + 1
        for seat, c in patrol_yes_neighbors.items():
            if c >= 2:
                susp[seat] += 0.3 * (c - 1)

        # N. 瞭望兵多夜 declared 累积: 任何 claimed_role 在多个不同瞭望兵 declared 中 = 强 bluff 证据
        lookout_decls_all = []
        for ev in self.events:
            if ev.claimed_role == '瞭望兵':
                lookout_decls_all.append((ev.source_seat, ev.declared_result, trust(ev.source_seat)))
        # 对每个 declared 的角色, 看 claimed 它的玩家
        for source, declared_role, tr in lookout_decls_all:
            for s in self.alive_seats():
                if self.players[s].claimed_role == declared_role and s != source:
                    susp[s] += 0.6 * tr

        # O. 斥候 D3+ declared 恶魔角色 — 该角色 currently in play
        #    任何 register 不一致的玩家 = 嫌疑
        scout_d3_declared = set()
        for ev in self.events:
            if ev.claimed_role == '斥候' and not ev.is_night and self.day >= 3:
                tr = trust(ev.source_seat)
                if ev.declared_result and tr > 0.7:
                    scout_d3_declared.add(ev.declared_result)
        # 不直接 boost (善良不知谁是该角色), 但加全局信号

        # Q. 书记官 sum 子集反推: 找所有 k-子集和=N 的, 高重叠 seat = 高嫌疑
        # 仅在仅 1 个书记官声称时使用 (避免冲突)
        clerk_claims = [ev for ev in self.events if ev.claimed_role == '书记官']
        if len(clerk_claims) == 1:
            ev = clerk_claims[0]
            tr = trust(ev.source_seat)
            if tr >= 0.6:
                register_count = sum(1 for s in self.players
                                     if self.is_seat_outsider_register(s)
                                     or self.players[s].register_minion)
                if register_count > 0 and register_count <= 5:
                    all_seats = list(range(1, 13))
                    valid = [c for c in combinations(all_seats, register_count)
                             if sum(c) == ev.declared_result]
                    if 0 < len(valid) <= 200:
                        membership = {s: 0 for s in all_seats}
                        for sub in valid:
                            for s in sub:
                                membership[s] += 1
                        for s, count in membership.items():
                            if s in susp:
                                p = count / len(valid)
                                susp[s] += p * tr * 0.6

        # P. 死信息源数量 → 信息真空, 整体信任度下降
        dead_info_sources = len(night_killed_info_sources)
        if dead_info_sources >= 2:
            # 信息真空时, 高嫌疑也要打折 (因为信息可能不准)
            for s in susp:
                susp[s] *= 0.85

        # 不允许负嫌疑
        for s in susp:
            susp[s] = max(0.0, susp[s])

        return susp

    # ============= 白天处决 =============
    def day_execute(self):
        alive = self.alive_seats()
        if not alive:
            return None

        # 不处决率
        if self.day == 1: non_exec = 0.70
        elif self.day == 2: non_exec = 0.30
        else: non_exec = 0.10
        if len(alive) <= 4: non_exec = 0.05

        if random.random() < non_exec:
            self.log(f'  D{self.day} 不处决')
            return None

        susp = self.compute_suspicion()
        self.suspicion = susp

        if not susp:
            return None

        max_susp = max(susp.values())
        # 嫌疑阈值: 没明显高峰就不处决 (善良谨慎)
        # 决战日 (alive<=4) 必须处决, 阈值降低
        threshold = 0.5 if len(alive) > 4 else 0.0

        # 候选: 嫌疑 >= max_susp - 0.3 且 >= threshold
        candidates = [(s, v) for s, v in susp.items()
                      if v >= threshold and v >= max_susp - 0.3]
        if not candidates:
            self.log(f'  D{self.day} 嫌疑不足, 不处决 (max={max_susp:.1f})')
            return None

        seats = [s for s, _ in candidates]
        weights = [v + 0.1 for _, v in candidates]
        target = random.choices(seats, weights=weights)[0]

        # 投票通过率
        actually_evil = self.players[target].team == '邪恶'
        if actually_evil:
            pass_prob = 0.75
        else:
            pass_prob = 0.30
        pass_prob += min(0.25, susp[target] * 0.08)
        pass_prob -= len(self.evil_dead_votes) * 0.05

        if random.random() > pass_prob:
            self.log(f'  D{self.day} 提名 {target} ({self.players[target].name}, 嫌疑={susp[target]:.1f}) 失败')
            return None

        self.log(f'  D{self.day} 处决: {target} ({self.players[target].name}, {self.players[target].role}, 嫌疑={susp[target]:.1f})')
        self.kill(target, method='处决')
        return target

    # ============= 主循环 =============
    def reset_nightly_distortion(self):
        for s in self.players:
            self.players[s].is_drunk = False
            self.players[s].is_hexed = False
        self.hex_target_yesterday = self.hex_target
        self.hex_target = None

    def check_win(self):
        alive = self.alive_seats()
        demons = self.alive_demons()
        if not demons:
            return '善良'
        if len(alive) <= 2 and demons:
            return '邪恶'
        return None

    def play(self):
        self.print_config()
        self.n0_setup()
        self.day = 1

        # N1 信息收集
        self.log('\n=== N1 ===')
        self.night_action_evil()  # 蛊惑+暗箭手 N1+内应
        self.night_info_gather()  # 镇民信息
        self.day = 1

        max_days = 15
        while self.day <= max_days:
            # 白天
            self.log(f'\n=== D{self.day} ===')
            self.day_info_gather()  # 纹章官+密探+军需官
            self.day_execute()
            w = self.check_win()
            if w: return w, self.day
            self.reset_nightly_distortion()

            # 夜晚 (N>=2)
            self.day += 1
            if self.day > max_days: break
            self.log(f'\n=== N{self.day} ===')
            self.night_action_evil()
            self.night_info_gather()
            w = self.check_win()
            if w: return w, self.day

        return '平局/超时', self.day - 1

    def print_config(self):
        if not self.verbose: return
        self.log('=== 配置 ===')
        self.log(f'恶魔: {self.demon_role}, 外来者: {self.outsiders}')
        self.log(f'镇民: {self.townsfolk}')
        self.log(f'Bluffs: {self.bluffs}')
        for i in sorted(self.players):
            p = self.players[i]
            bluff_str = f' [bluff:{p.bluff_role}]' if p.bluff_role else ''
            self.log(f'  {i}. {p.name}: {p.role} ({p.team}){bluff_str}')
        self.log('')


def run_batch(n=100, verbose=False):
    results = {'善良': 0, '邪恶': 0, '平局/超时': 0}
    setups = {}
    days_total = 0
    for i in range(n):
        g = Game(verbose=verbose)
        setup_key = '千面人' if g.is_lunatic_setup else g.demon_role
        winner, days = g.play()
        results[winner] += 1
        days_total += days
        if setup_key not in setups:
            setups[setup_key] = {'善良': 0, '邪恶': 0, '平局/超时': 0, 'n': 0}
        setups[setup_key][winner] += 1
        setups[setup_key]['n'] += 1

    print(f'\n=== {n} 局 v3 结果 ===')
    print(f'善良: {results["善良"]*100/n:.1f}% / 邪恶: {results["邪恶"]*100/n:.1f}% / 超时: {results["平局/超时"]*100/n:.1f}%')
    print(f'平均天数: {days_total/n:.1f}\n')
    print(f'{"setup":<10} {"局数":<6} {"善良%":<8} {"邪恶%":<8} {"超时%":<8}')
    print('-'*42)
    for k, v in sorted(setups.items()):
        nn = v['n']
        print(f'{k:<10} {nn:<6} {v["善良"]*100/nn:<8.1f} {v["邪恶"]*100/nn:<8.1f} {v["平局/超时"]*100/nn:<8.1f}')


if __name__ == '__main__':
    args = sys.argv[1:]
    verbose = '-v' in args
    args = [a for a in args if a != '-v']
    if args:
        try:
            n = int(args[0])
            run_batch(n, verbose=verbose)
        except ValueError:
            print('Usage: python3 botc_simulator_v3.py [n_games] [-v]')
            sys.exit(1)
    else:
        g = Game(verbose=True)
        winner, days = g.play()
        print(f'\n=== 胜负 ===\n{winner}胜, {days} 天')
        print(f'\n死亡顺序:')
        for time, seat, role in g.deaths:
            print(f'  {time}: 座 {seat} ({role})')
