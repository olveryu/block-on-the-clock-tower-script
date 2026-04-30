#!/usr/bin/env python3
"""
围城之夜 12 人模拟器 v4 (Bayesian + Game Theory)
=================================================
4 层框架:
- 层 1 (Approx Bayesian): 维护 P(seat=role/team) 边际概率表
- 层 2 (Game Theory): 邪恶发言作策略行动建模, likelihood = π_real / π_evil_bluff
- 层 4 (Heuristic fallback): 高熵时退化到 v23 风格统计

本会话 (1) 实现:
- WorldState + Policy + BayesianReasoner 架构
- 审讯官 + 瞭望兵 policy pair
- 跑批量验证

后续会话每加 1-2 角色 policy. 每个角色: 真 policy + 邪恶 bluff policy.

用法:
    python3 botc_simulator_v4.py        # 跑 1 局
    python3 botc_simulator_v4.py 200    # 跑 N 局
"""

import random
import sys
import math
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set, Dict, Tuple
from itertools import combinations

# ============= 角色池 (与 v3 同) =============
TOWNSFOLK_POOL = [
    '斥候', '密探', '巡逻兵', '审讯官', '游侠', '军医',
    '书记官', '军需官', '牧师', '纹章官', '盾卫', '女伯爵', '瞭望兵'
]
OUTSIDER_POOL = ['伤兵', '逃兵', '难民', '俘虏']
MINION_POOL = ['内应', '蛊惑者', '叛将', '死士']
DEMON_POOL = ['攻城将军', '先锋官', '千面人', '暗箭手']
INFO_SOURCES = {'斥候', '密探', '巡逻兵', '审讯官', '书记官', '纹章官', '瞭望兵', '军医', '牧师'}
ALL_ROLES = TOWNSFOLK_POOL + OUTSIDER_POOL + MINION_POOL + DEMON_POOL
PLAYERS = ['阿信', '小白', '二哥', '月儿', '老王', '阿龙',
           '莉莉', '小七', '大刘', '苗苗', '阿强', '雪儿']


def is_demon_role(r): return r in DEMON_POOL or '千面人' in r
def is_minion_role(r): return r in MINION_POOL
def is_outsider_role(r): return r in OUTSIDER_POOL


# ============= InfoEvent =============
@dataclass
class InfoEvent:
    source_seat: int
    claimed_role: str       # 公开声称
    actual_role: str        # 真实 (善良不知)
    day: int
    is_night: bool
    targets: List[int] = field(default_factory=list)
    actual_result: Any = None
    declared_result: Any = None
    is_distorted: bool = False     # 蛊惑/醉酒
    is_fake_bluff: bool = False    # 邪恶装 (claimed != actual)


# ============= PlayerState =============
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


# ============= WorldState (Bayesian core) =============
class WorldState:
    """维护每个 seat 的 team 概率分布 (粗粒度).
    更精细可扩展为 P(seat=role) 但先简化."""

    def __init__(self, setup_info):
        """setup_info = {demon: str, n_outsider: int, n_minion: int, n_townsfolk: int, is_lunatic: bool}"""
        self.setup = setup_info
        # P(seat=team): 镇民/外来者/邪恶
        # 先验: 设 setup 比例
        n_total = 12
        n_evil = 1 + setup_info['n_minion'] if not setup_info['is_lunatic'] else 3
        n_outsider = setup_info['n_outsider']
        n_townsfolk = n_total - n_evil - n_outsider

        prior_evil = n_evil / n_total
        prior_outsider = n_outsider / n_total
        prior_townsfolk = n_townsfolk / n_total

        self.p_team: Dict[int, Dict[str, float]] = {}
        for s in range(1, 13):
            self.p_team[s] = {
                '镇民': prior_townsfolk,
                '外来者': prior_outsider,
                '邪恶': prior_evil,
            }

        # P(seat=具体 role) 简化: 只追踪 claimed role 的可信度
        # P(seat 是真 claimed_role | claimed_role 已声称)
        self.p_real_role: Dict[int, float] = {s: 0.5 for s in range(1, 13)}

        # 死亡 retrocative trust boost
        self.dead_info_sources: Set[int] = set()

    def normalize(self, seat):
        d = self.p_team[seat]
        total = sum(d.values())
        if total > 0:
            for k in d:
                d[k] /= total

    def update_team(self, seat, team_likelihoods: Dict[str, float]):
        """multiplicative update: posterior ∝ prior × likelihood"""
        for team, lik in team_likelihoods.items():
            self.p_team[seat][team] *= max(0.001, lik)
        self.normalize(seat)

    def kill(self, seat, team_actual=None):
        # 死人 prior 不变 (用于 reasoner 仍可推导)
        pass

    def entropy(self, seat):
        d = self.p_team[seat]
        e = 0
        for v in d.values():
            if v > 0:
                e -= v * math.log(v)
        return e

    def p_evil(self, seat):
        return self.p_team[seat]['邪恶']

    def __repr__(self):
        lines = []
        for s in sorted(self.p_team):
            d = self.p_team[s]
            lines.append(f"  {s}: 镇 {d['镇民']:.2f}, 外 {d['外来者']:.2f}, 邪 {d['邪恶']:.2f}")
        return '\n'.join(lines)


# ============= Policy 框架 =============
class Policy:
    """抽象基类. 每个 role 需要:
    - real action distribution: π(action | seat is true role R, world)
    - evil bluff action distribution: π(action | seat is evil bluffing R, world)
    - likelihood: 给定观察, 返回 likelihood values for ratio
    """

    def __init__(self, role: str):
        self.role = role

    def likelihood_real(self, event: InfoEvent, world_state: WorldState, alive_seats: List[int]) -> float:
        """π_real_role(event)"""
        raise NotImplementedError

    def likelihood_evil_bluff(self, event: InfoEvent, world_state: WorldState, alive_seats: List[int]) -> float:
        """π_evil_bluff_role(event)"""
        raise NotImplementedError


class InterrogatorPolicy(Policy):
    """审讯官: 真+邪恶 bluff policy pair
    真审讯官: random 选 3 alive (非自己) + actual ground truth yes/no
    邪恶 bluff: 选 3 (避队友, 偏低嫌疑真镇民), 多偏 yes 框人"""

    def __init__(self):
        super().__init__('审讯官')

    def likelihood_real(self, event, world_state, alive_seats):
        """真审讯官 likelihood:
        - P(picks targets) = 1/C(N-1, 3) (uniform random)
        - P(declared | targets, world) = P(declared 等于 actual ground truth | world)
          但 actual 取决于实际 world. 善良不知, 用 prior P 估计:
          P(actual=yes) = P(恰好 1 非恶魔邪恶 in targets | world prior)
        """
        n_alive = len(alive_seats)
        if event.source_seat not in alive_seats: return 0
        if n_alive < 4: return 0
        # 选 3 random from alive (non-self)
        other_count = n_alive - 1
        p_pick = 1.0 / max(1, math.comb(other_count, 3))

        # P(actual=yes | world): 估每个 target 是非恶魔邪恶概率 (prior 下用 minion register share)
        # 简化: 目标里至少 1 邪恶 → yes 概率
        p_evil_per_seat = sum(world_state.p_evil(t) for t in event.targets) / max(1, len(event.targets))
        # 假设 3 个独立: P(恰好 1 邪恶) ≈ 3 * p * (1-p)^2 (Bernoulli approx)
        p = p_evil_per_seat
        p_actual_yes = 3 * p * (1 - p) ** 2 if p < 1 else 0.0
        # 蛊惑/醉酒 distortion 概率小, 忽略 (后续会话补)

        if event.declared_result == True:
            return p_pick * p_actual_yes
        else:
            return p_pick * (1 - p_actual_yes)

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        """邪恶装审讯官 likelihood (启发式策略):
        - 避免选邪恶队友 (从 P(seat=邪恶) 高的不选)
        - 偏向选 P(seat=镇民) 高的 (框真镇民)
        - declared 多偏 yes (推怀疑)
        """
        if event.source_seat not in alive_seats: return 0
        if len(alive_seats) < 4: return 0

        # P(picks targets | strategy):
        # weight 每个 target = P(seat=镇民) (越镇民越愿框)
        target_weights = []
        for t in event.targets:
            w = world_state.p_team[t]['镇民']
            target_weights.append(max(0.05, w))
        # 概率近似: 这组 targets 被选中的概率
        all_others = [s for s in alive_seats if s != event.source_seat]
        all_weights = [max(0.05, world_state.p_team[s]['镇民']) for s in all_others]
        total_w = sum(all_weights)
        # 正比于 product / sum: 简化为乘积归一
        p_pick = 1.0
        remaining_total = total_w
        for w in target_weights:
            p_pick *= w / max(0.001, remaining_total)
            remaining_total -= w
        # 不选邪恶队友 — 检查 targets 中没有 high-evil prob seats
        for t in event.targets:
            if world_state.p_evil(t) > 0.7:
                p_pick *= 0.1  # 不太可能选高邪恶嫌疑

        # declared yes 偏 (邪恶 bluff yes 概率 ~0.7, 真审讯官随机 yes ~0.4)
        p_declared = 0.7 if event.declared_result == True else 0.3
        return p_pick * p_declared


class ScoutPolicy(Policy):
    """斥候 (v6): N1 学 3 demon 角色 (1 真), D3+ 白天学真 demon 角色.
    旧版 N1 学 2 demon, 改为 3 demon 是首夜情报削弱."""

    def __init__(self):
        super().__init__('斥候')

    def likelihood_real(self, event, world_state, alive_seats):
        if event.is_night and event.day == 1:
            # N1: declared = sorted [demon1, demon2, demon3], 1 真
            if not isinstance(event.declared_result, list) or len(event.declared_result) != 3:
                return 0
            # 善良 prior: demon 角色均匀分布 (4 选 1)
            # P(真斥候 declares this triplet | demon=d):
            #   if d ∈ triplet: 1/3 (pick 2 fakes from 3 non-d, C(3,2)=3 ways), else 0
            p = 0.0
            for d in DEMON_POOL:
                if d in event.declared_result:
                    p += 0.25 * (1.0 / 3)
            return p
        elif not event.is_night and event.day >= 3:
            # D3+: declared = single demon role (= true demon)
            if event.declared_result not in DEMON_POOL:
                return 0
            # P(declared = X | demon = X) = 1, else 0. Prior uniform 1/4.
            return 0.25
        return 0

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        if event.is_night and event.day == 1:
            if not isinstance(event.declared_result, list) or len(event.declared_result) != 3:
                return 0
            # 邪恶 装斥候: 知真 demon, 偏向编不含真 demon 的 triplet (避暴露)
            # 4 demons 选 3 = C(4,3)=4 种 triplet:
            #   1 种不含 d (= 3 非真 demon) — 邪恶 avoiding 唯一选择
            #   3 种含 d — 邪恶 装诚实 (低概率)
            p = 0.0
            for d in DEMON_POOL:
                if d not in event.declared_result:
                    # 邪恶 picks the unique avoid-triplet (all 3 non-d demons)
                    p += 0.25 * 1.0
                else:
                    # 邪恶 也可能装诚实 (含真 demon), 概率较低
                    p += 0.25 * 0.1
            return p
        elif not event.is_night and event.day >= 3:
            if event.declared_result not in DEMON_POOL:
                return 0
            # 邪恶装斥候 D3+: 编非真 demon (3/4 概率), 真 demon (1/4)
            # P(declared=X | demon=d): if X=d, 0.1; else 0.3
            p = 0.0
            for d in DEMON_POOL:
                if d == event.declared_result:
                    p += 0.25 * 0.1
                else:
                    p += 0.25 * 0.3
            return p
        return 0


class ClerkPolicy(Policy):
    """书记官 N1: 学外来者+爪牙 seat sum"""

    def __init__(self):
        super().__init__('书记官')

    def _register_count(self, world_state):
        n_o = world_state.setup['n_outsider']
        if world_state.setup['is_lunatic']:
            return n_o + 3  # 千面人 register both
        else:
            return n_o + world_state.setup.get('n_minion', 2)

    def _sum_range(self, world_state):
        k = self._register_count(world_state)
        if k == 0: return None, None
        return sum(range(1, k + 1)), sum(range(12 - k + 1, 13))

    def likelihood_real(self, event, world_state, alive_seats):
        if event.day != 1 or not event.is_night: return 0
        if not isinstance(event.declared_result, int): return 0
        min_s, max_s = self._sum_range(world_state)
        if min_s is None: return 0
        N = event.declared_result
        if not (min_s <= N <= max_s): return 0
        # 真书记官: declared = actual sum. 善良 prior over actual sum: count of register-subsets summing to N
        k = self._register_count(world_state)
        n_subsets = sum(1 for c in combinations(range(1, 13), k) if sum(c) == N)
        total = math.comb(12, k)
        if total == 0: return 0
        # P(actual sum = N) = n_subsets / total
        return n_subsets / total

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        if event.day != 1 or not event.is_night: return 0
        if not isinstance(event.declared_result, int): return 0
        min_s, max_s = self._sum_range(world_state)
        if min_s is None: return 0
        N = event.declared_result
        if not (min_s <= N <= max_s): return 0
        # 邪恶 bluff: 偏向 sum 指向真镇民组合 (frame). 善良 prior 类似真但平滑
        # 邪恶 picks N from valid range, slight bias toward middle
        return 1.0 / (max_s - min_s + 1)


class PatrollerPolicy(Policy):
    """巡逻兵: 选 1 玩家学邻座是否有外来者"""

    def __init__(self):
        super().__init__('巡逻兵')

    def likelihood_real(self, event, world_state, alive_seats):
        if not event.targets: return 0
        # 真巡逻兵: 选 random target, declared = 真实结果
        # P(declared=yes | random target) = P(随机目标邻座有 register 外来者)
        # 估计: P(任意 seat 是 register 外来者) × 2 邻座
        n_o = world_state.setup['n_outsider']
        if world_state.setup['is_lunatic']:
            n_register_o = n_o + 3  # 千面人 register 外来者
        else:
            n_register_o = n_o
        p_per_seat = n_register_o / 12
        # 邻座 2 个独立 (近似), P(at least 1 是 register 外来者) ≈ 1 - (1-p)^2
        p_yes = 1 - (1 - p_per_seat) ** 2
        if event.declared_result == True:
            return p_yes / 11  # 1/11 选 target
        else:
            return (1 - p_yes) / 11

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        if not event.targets: return 0
        # 邪恶 bluff: 偏 yes/no 框真镇民邻居
        # 简化: 略偏 yes (推怀疑邻座)
        if event.declared_result == True:
            return 0.6 / 11
        else:
            return 0.4 / 11


class DoctorPolicy(Policy):
    """军医 (v2): 选 2 名其他存活玩家, 至少 1 人今晚被唤醒.
    旧版: 选 1 玩家死人验邪恶/活人验唤醒, 改为 2 人范围 yes 是削弱."""

    def __init__(self):
        super().__init__('军医')

    def likelihood_real(self, event, world_state, alive_seats):
        if not event.targets or len(event.targets) != 2: return 0
        # 真军医: 选 2 人中至少 1 被唤醒
        # 估计 P(target 被唤醒) ≈ 0.45 (邪恶+信息源+恶魔约 5-6/12 角色)
        # P(2 人至少 1 被唤醒) = 1 - (1-0.45)^2 ≈ 0.70
        p_yes = 0.70
        if event.declared_result == True:
            return p_yes / 66  # C(11,2) 约略
        else:
            return (1 - p_yes) / 66

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        if not event.targets or len(event.targets) != 2: return 0
        # 邪恶 bluff 军医: 偏 yes 框真镇民
        if event.declared_result == True:
            return 0.75 / 66
        else:
            return 0.25 / 66


class PriestPolicy(Policy):
    """牧师 N2+: 学有多少 alive 不再是最初角色"""

    def __init__(self):
        super().__init__('牧师')

    def likelihood_real(self, event, world_state, alive_seats):
        if event.day < 2 or not event.is_night: return 0
        if not isinstance(event.declared_result, int): return 0
        N = event.declared_result
        # 通常 changed 数 = 0-3 (蛊惑者目标, 叛将变身, 暗箭手 N1 傀儡, 内应双傀儡)
        # 真牧师 declared 大致正态在 1-2
        if 0 <= N <= 4:
            return 0.20
        return 0.05

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        if event.day < 2 or not event.is_night: return 0
        if not isinstance(event.declared_result, int): return 0
        N = event.declared_result
        # 邪恶 编一个数, 大致均匀
        if 0 <= N <= 4:
            return 0.20
        return 0.10


class HeraldPolicy(Policy):
    """纹章官: 白天指定 3 学是否恰好 1 外来者 register"""

    def __init__(self):
        super().__init__('纹章官')

    def likelihood_real(self, event, world_state, alive_seats):
        if event.is_night: return 0
        if not event.targets or len(event.targets) != 3: return 0
        n_o = world_state.setup['n_outsider']
        if world_state.setup['is_lunatic']:
            n_register_o = n_o + 3
        else:
            n_register_o = n_o
        p_per_seat = n_register_o / 12
        # P(恰好 1 外来者 in 3) ≈ C(3,1) × p × (1-p)^2
        p_yes = 3 * p_per_seat * (1 - p_per_seat) ** 2
        if event.declared_result == True:
            return p_yes / 220
        else:
            return (1 - p_yes) / 220

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        if event.is_night: return 0
        if not event.targets or len(event.targets) != 3: return 0
        # 邪恶 bluff 多偏 yes
        if event.declared_result == True:
            return 0.65 / 220
        else:
            return 0.35 / 220


class SpyPolicy(Policy):
    """密探: 白天指定 2 学谁离爪牙近"""

    def __init__(self):
        super().__init__('密探')

    def likelihood_real(self, event, world_state, alive_seats):
        if event.is_night: return 0
        if not event.targets or len(event.targets) != 2: return 0
        # 真密探 declared = 真离 minion 近. 善良不知 minion 位置
        # likelihood 平均 0.5 (50% 各)
        return 0.5 / 66

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        if event.is_night: return 0
        if not event.targets or len(event.targets) != 2: return 0
        # 邪恶 bluff: 偏指真镇民 "离爪牙近"
        # 这里简化 likelihood 略不同
        return 0.5 / 66


class LookoutPolicy(Policy):
    """瞭望兵: 真+邪恶 bluff policy pair
    真瞭望兵: 每夜随机选 1 个不在场爪牙/外来者 declare
    邪恶 bluff: 故意 declare 真在场角色当"不在场" (框真镇民如果他装那角色)"""

    def __init__(self):
        super().__init__('瞭望兵')

    def likelihood_real(self, event, world_state, alive_seats):
        """真瞭望兵 likelihood:
        - P(declared=R) = 1/N_not_in_play if R 是不在场角色, 0 otherwise
        但善良不知 not_in_play set. 用 setup 先验.
        """
        # 不在场角色总数: 4 outsider - n_in_play_outsider + 4 minion - n_in_play_minion
        n_not_in_outsider = 4 - world_state.setup['n_outsider']
        n_not_in_minion = 4 - world_state.setup.get('n_minion', 0)
        if world_state.setup['is_lunatic']:
            n_not_in_minion = 4  # 千面人 setup 没真爪牙
        n_not_in = n_not_in_outsider + n_not_in_minion
        if n_not_in == 0: return 0
        # P(declared=R | R 不在场) = 1/n_not_in
        # 但 R 可能在场 (邪恶 bluff). 真瞭望兵的 declared 必然在不在场池.
        # likelihood = 1/n_not_in if 我们假设 R 不在场, else 0. 但善良不知, 用先验:
        # 整体 likelihood = P(R 不在场 | setup) × 1/n_not_in
        # P(R 不在场) = n_not_in / 8 (8 total outsider+minion roles)
        return (n_not_in / 8) * (1 / n_not_in)

    def likelihood_evil_bluff(self, event, world_state, alive_seats):
        """邪恶装瞭望兵 likelihood (启发式):
        - 偏向 declare 真在场角色 当"不在场" (框装该角色的玩家)
        - 邪恶不知谁装什么 (其实知道队友, 不知善良 claim)
        """
        # 启发式: declared 多偏向被某 seat claim 的角色 (框那 seat)
        # 简化: 如果 declared 角色当前被某活 seat claim, likelihood 略高
        claimed_targets = []
        if hasattr(world_state, '_current_claims'):
            for s, role in world_state._current_claims.items():
                if role == event.declared_result and s != event.source_seat:
                    claimed_targets.append(s)
        if claimed_targets:
            return 0.30  # 框人意图明显
        else:
            return 0.10  # 没人 claim, 随便骗


# ============= BayesianReasoner =============
class BayesianReasoner:
    """根据 InfoEvent 序列 + Policy, 更新 WorldState"""

    def __init__(self, world_state: WorldState):
        self.world = world_state
        self.policies: Dict[str, Policy] = {
            '审讯官': InterrogatorPolicy(),
            '瞭望兵': LookoutPolicy(),
            '斥候': ScoutPolicy(),
            '书记官': ClerkPolicy(),
            '巡逻兵': PatrollerPolicy(),
            '军医': DoctorPolicy(),
            '牧师': PriestPolicy(),
            '纹章官': HeraldPolicy(),
            '密探': SpyPolicy(),
        }

    def process_event(self, event: InfoEvent, alive_seats: List[int], current_claims: Dict[int, str]):
        """对每个事件, 用 policy 比值更新 source seat 的 team 分布."""
        if event.claimed_role in self.policies and event.source_seat in alive_seats:
            policy = self.policies[event.claimed_role]
            self.world._current_claims = current_claims
            try:
                l_real = policy.likelihood_real(event, self.world, alive_seats)
                l_evil = policy.likelihood_evil_bluff(event, self.world, alive_seats)
            except Exception:
                return
            if l_real <= 0 and l_evil <= 0: return
            total = l_real + l_evil + 1e-6
            l_real_n = l_real / total
            l_evil_n = l_evil / total
            team_likelihoods = {
                '镇民': max(0.1, l_real_n + 0.3),
                '外来者': 0.4,
                '邪恶': max(0.1, l_evil_n + 0.3),
            }
            self.world.update_team(event.source_seat, team_likelihoods)

    def _trust_boosted(self, source_seat, all_players_state, deaths_log):
        """source 可信度: 夜杀死的信息源 → 高度信任 (邪恶专杀真信息源)"""
        if all_players_state and source_seat in all_players_state:
            p = all_players_state[source_seat]
            if not p.alive:
                # 检查是否夜杀死
                for time, seat, role in deaths_log:
                    if seat == source_seat and time.startswith('N'):
                        return 1.5  # 死信息源 retroactive trust
        # 活的 source: 用 world_state 估计
        return self.world.p_team[source_seat]['镇民'] if source_seat in self.world.p_team else 0.3

    def apply_claim_conflicts(self, current_claims: Dict[int, str], alive_seats: List[int]):
        """启发式 fallback: multi-claim 同 role → 各方嫌疑上升"""
        groups: Dict[str, List[int]] = {}
        for s, r in current_claims.items():
            if r in INFO_SOURCES or r in {'盾卫', '女伯爵', '游侠', '军需官'}:
                groups.setdefault(r, []).append(s)
        for r, seats in groups.items():
            if len(seats) >= 2:
                for s in seats:
                    if s in alive_seats:
                        # 加邪恶嫌疑
                        self.world.update_team(s, {'镇民': 0.5, '外来者': 0.5, '邪恶': 1.5})

    def apply_lookout_cross_check(self, events: List[InfoEvent], alive_seats: List[int],
                                    current_claims: Dict[int, str]):
        """瞭望兵 declared X → 任何 claim X 的座位嫌疑上升"""
        for ev in events:
            if ev.claimed_role != '瞭望兵': continue
            for s in alive_seats:
                if current_claims.get(s) == ev.declared_result and s != ev.source_seat:
                    self.world.update_team(s, {'镇民': 0.5, '外来者': 0.5, '邪恶': 2.0})

    def apply_interrogator_active_inference(self, events: List[InfoEvent], alive_seats: List[int],
                                              all_players_state=None, deaths_log=None):
        """真审讯官 yes 推 3 targets 包含 1 邪恶 → 各 +嫌疑."""
        for ev in events:
            if ev.claimed_role != '审讯官': continue
            if ev.declared_result != True: continue
            src_trust = self._trust_boosted(ev.source_seat, all_players_state, deaths_log or [])
            if src_trust < 0.3: continue
            evil_lik = 1.0 + 0.7 * src_trust
            for t in ev.targets:
                if t in alive_seats:
                    self.world.update_team(t, {'镇民': 0.7, '外来者': 0.7, '邪恶': evil_lik})

    def apply_scout_cross_check(self, events: List[InfoEvent], alive_seats: List[int]):
        """多个斥候 claim 之间互相验证.
        - N1 pair 必须有交集 (都含真 demon)
        - D3+ single demon 必须一致
        - 不一致 = 至少 1 个邪恶 bluff
        """
        # N1 pairs
        n1_pairs = [(ev.source_seat, set(ev.declared_result)) for ev in events
                    if ev.claimed_role == '斥候' and ev.is_night and ev.day == 1
                    and isinstance(ev.declared_result, list)]
        if len(n1_pairs) >= 2:
            # 所有真斥候 pair 必须有公共 demon
            common = set.intersection(*[p for _, p in n1_pairs])
            if not common:
                # 完全不交 → 必有 1 邪恶
                for s, _ in n1_pairs:
                    if s in alive_seats:
                        self.world.update_team(s, {'镇民': 0.5, '外来者': 0.5, '邪恶': 1.8})

        # D3+ single demon
        d3_decls = [(ev.source_seat, ev.declared_result) for ev in events
                    if ev.claimed_role == '斥候' and not ev.is_night
                    and ev.declared_result in DEMON_POOL]
        if len(d3_decls) >= 2:
            unique_demons = set(d for _, d in d3_decls)
            if len(unique_demons) >= 2:
                # 不一致 → 必有 1 邪恶
                for s, _ in d3_decls:
                    if s in alive_seats:
                        self.world.update_team(s, {'镇民': 0.5, '外来者': 0.5, '邪恶': 1.8})

    def apply_doctor_dead_evil_inference(self, events: List[InfoEvent], alive_seats: List[int],
                                          all_players_state):
        """军医 yes 验死人 → 该死人确认邪恶 (强 retroactive 信号)"""
        for ev in events:
            if ev.claimed_role != '军医': continue
            if not ev.targets or ev.declared_result != True: continue
            t = ev.targets[0]
            # 检查 t 是否死人
            if all_players_state.get(t) and not all_players_state[t].alive:
                # source trust
                if ev.source_seat in alive_seats:
                    src_trust = self.world.p_team[ev.source_seat]['镇民']
                    if src_trust > 0.4:
                        # 死人确认邪恶 = 强信号. 但 t 已死, 无影响. 如果 source 仍 alive,
                        # 反过来说明 source 是真军医 (验对了死人邪恶)
                        # 这里加强 source 的镇民概率
                        self.world.update_team(ev.source_seat, {'镇民': 1.5, '外来者': 0.5, '邪恶': 0.5})

    def apply_patroller_active_inference(self, events: List[InfoEvent], alive_seats: List[int],
                                          all_players_state=None, deaths_log=None):
        """巡逻兵 yes → 邻座有 register 外来者. 累积多次提升嫌疑"""
        neighbor_yes_count: Dict[int, float] = {}
        for ev in events:
            if ev.claimed_role != '巡逻兵': continue
            if ev.declared_result != True or not ev.targets: continue
            src_trust = self._trust_boosted(ev.source_seat, all_players_state, deaths_log or [])
            if src_trust < 0.3: continue
            t = ev.targets[0]
            l = t - 1 if t > 1 else 12
            r = t + 1 if t < 12 else 1
            for nb in [l, r]:
                if nb in alive_seats:
                    neighbor_yes_count[nb] = neighbor_yes_count.get(nb, 0) + src_trust
        for seat, score in neighbor_yes_count.items():
            if score >= 0.5:
                self.world.update_team(seat, {'镇民': 0.8, '外来者': 1.3, '邪恶': 1.2})

    def apply_herald_active_inference(self, events: List[InfoEvent], alive_seats: List[int],
                                       all_players_state=None, deaths_log=None):
        """纹章官 yes → 3 中恰好 1 register 外来者."""
        for ev in events:
            if ev.claimed_role != '纹章官': continue
            if ev.declared_result != True or not ev.targets: continue
            src_trust = self._trust_boosted(ev.source_seat, all_players_state, deaths_log or [])
            if src_trust < 0.3: continue
            for t in ev.targets:
                if t in alive_seats:
                    self.world.update_team(t, {'镇民': 0.85, '外来者': 1.2, '邪恶': 1.05})

    def apply_scout_d3_register_inference(self, events: List[InfoEvent], alive_seats: List[int]):
        """斥候 D3+ 确认 demon 角色 → 该角色 in play 的 setup 已知 → register 推理可锐化"""
        # 找最可信的 D3+ 斥候 declaration
        d3_decls = [(ev.source_seat, ev.declared_result) for ev in events
                    if ev.claimed_role == '斥候' and not ev.is_night
                    and ev.declared_result in DEMON_POOL
                    and ev.source_seat in alive_seats]
        if not d3_decls: return None
        # 用 trust 最高的 (P_镇民最大)
        best = max(d3_decls, key=lambda x: self.world.p_team[x[0]]['镇民'])
        src_trust = self.world.p_team[best[0]]['镇民']
        if src_trust < 0.4: return None
        return best[1]  # confirmed demon role

    def apply_clerk_subset_inference(self, events: List[InfoEvent], alive_seats: List[int],
                                      register_count: int):
        """书记官 sum=N → 枚举 register_count-子集 sum=N → 出现频次高的 seat = 高 register prob (邪恶/外来者)"""
        clerk_evs = [e for e in events if e.claimed_role == '书记官']
        if len(clerk_evs) != 1: return  # 多 claim 时不用
        ev = clerk_evs[0]
        src_trust = self.world.p_team[ev.source_seat]['镇民']
        if src_trust < 0.3: return
        if register_count <= 0 or register_count > 5: return
        all_seats = list(range(1, 13))
        valid = [c for c in combinations(all_seats, register_count)
                 if sum(c) == ev.declared_result]
        if not valid or len(valid) > 200: return
        membership = {s: 0 for s in all_seats}
        for sub in valid:
            for s in sub:
                membership[s] += 1
        for s, count in membership.items():
            if s not in alive_seats: continue
            p = count / len(valid)
            # P 高 → 该 seat 是 register (邪恶 or 外来者)
            evil_lik = 1.0 + p * 0.8 * src_trust
            outsider_lik = 1.0 + p * 0.5 * src_trust
            self.world.update_team(s, {'镇民': max(0.2, 1.0 - p),
                                        '外来者': outsider_lik,
                                        '邪恶': evil_lik})

    def process_all(self, events: List[InfoEvent], alive_seats: List[int],
                     current_claims: Dict[int, str], register_count: int = 0,
                     all_players_state=None, deaths_log=None):
        for ev in events:
            self.process_event(ev, alive_seats, current_claims)
        self.apply_claim_conflicts(current_claims, alive_seats)
        self.apply_lookout_cross_check(events, alive_seats, current_claims)
        self.apply_scout_cross_check(events, alive_seats)
        self.apply_interrogator_active_inference(events, alive_seats, all_players_state, deaths_log)
        self.apply_patroller_active_inference(events, alive_seats, all_players_state, deaths_log)
        self.apply_herald_active_inference(events, alive_seats, all_players_state, deaths_log)
        if all_players_state:
            self.apply_doctor_dead_evil_inference(events, alive_seats, all_players_state)
        if register_count > 0:
            self.apply_clerk_subset_inference(events, alive_seats, register_count)

    def execute_target(self, alive_seats: List[int]) -> Optional[int]:
        """处决目标 = argmax P(seat=邪恶), 若 P 接近均匀则不处决"""
        if not alive_seats: return None
        evil_probs = [(s, self.world.p_evil(s)) for s in alive_seats]
        evil_probs.sort(key=lambda x: -x[1])
        max_p = evil_probs[0][1]
        # 平均 P_邪
        avg_p = sum(p for _, p in evil_probs) / len(evil_probs)
        # 信号 = max_p - avg_p; 信号低 = 没明显高峰
        signal = max_p - avg_p
        if signal < 0.05:
            return None  # 没明显信号
        top_k = [(s, p) for s, p in evil_probs if p >= max_p - 0.05]
        if len(top_k) == 1:
            return top_k[0][0]
        seats, weights = zip(*top_k)
        return random.choices(seats, weights=weights)[0]


# ============= Game (复用 v3 机制层, 替换 reasoner) =============
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
        self.drunk_target = None

        self.events: List[InfoEvent] = []
        self.deaths: List[Tuple[str, int, str]] = []

        self._generate_config()
        self._init_bluffs()

        # Bayesian core
        setup_info = {
            'demon': self.demon_role,
            'is_lunatic': self.is_lunatic_setup,
            'n_outsider': len(self.outsiders),
            'n_minion': len(self.minion_seats),
            'n_townsfolk': len(self.townsfolk),
        }
        self.world_state = WorldState(setup_info)
        self.reasoner = BayesianReasoner(self.world_state)

    def log(self, msg, indent=0):
        if self.verbose: print('  ' * indent + msg)

    def _generate_config(self):
        demon = random.choice(DEMON_POOL)
        minions_raw = random.sample(MINION_POOL, 2)
        self.is_lunatic_setup = (demon == '千面人')

        if demon == '千面人':
            outsider_count, townsfolk_count = 2, 7  # 剧本只'爪牙变千面人', 不改外来者
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
            if is_demon: team = '邪恶'; self.demon_seats.append(i)
            elif is_minion: team = '邪恶'; self.minion_seats.append(i)
            elif r in outsiders: team = '外来者'
            else: team = '镇民'

            ps = PlayerState(seat=i, name=p, role=r, original_role=r, team=team)
            ps.register_outsider = (r in outsiders) or (r == '死士') or ('千面人' in r)
            ps.register_minion = is_minion or (r == '死士') or ('千面人' in r)
            self.players[i] = ps
            if team == '邪恶': self.evil_seats.append(i)
            if r == '死士':
                self.dead_man_seat = i
                self.dead_man_active = True
            if r == '女伯爵': self.has_save_baron = True
            if r == '盾卫': self.has_save_shield = True

    def _init_bluffs(self):
        used = set()
        for seat in self.evil_seats:
            p = self.players[seat]
            options = []
            if is_demon_role(p.role) or '千面人' in p.role:
                options = [b for b in self.bluffs if b not in used]
            else:
                if random.random() < 0.6:
                    # 爪牙装外来者只从"不在场外来者"里选, 避免与场上真外来者撞角色
                    # (高玩级邪恶 N0 不会撞角色; 此处修复 setup bug)
                    pool = self.not_in_play_outsiders
                    options = [r for r in pool if r not in used]
                if not options:
                    options = [b for b in self.bluffs if b not in used]
            if options:
                p.bluff_role = random.choice(options)
                used.add(p.bluff_role)
            else:
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

    def neighbors(self, seat):
        def find_alive(start, direction):
            cur = start
            for _ in range(12):
                cur = (cur + direction)
                if cur < 1: cur = 12
                if cur > 12: cur = 1
                if self.players[cur].alive: return cur
            return None
        return find_alive(seat, -1), find_alive(seat, 1)

    def is_seat_outsider_register(self, seat):
        p = self.players[seat]
        return p.team == '外来者' or p.register_outsider or p.role == '傀儡'

    def is_info_distorted(self, seat):
        p = self.players[seat]
        return p.is_hexed or p.is_drunk or p.role == '傀儡' or p.puppet

    def strategic_pick(self, candidates, k, prefer_high_evil=True):
        """选 k 个 targets:
        - prefer_high_evil=True (真镇民): 偏向 P_evil 高的
        - prefer_high_evil=False (邪恶 bluff): 偏向 P_镇民 高的 (框真镇民)"""
        if len(candidates) <= k:
            return list(candidates)
        if prefer_high_evil:
            weights = [max(0.05, self.world_state.p_evil(s)) for s in candidates]
        else:
            weights = [max(0.05, self.world_state.p_team[s]['镇民']) for s in candidates]
        pool = list(candidates)
        pw = list(weights)
        chosen = []
        for _ in range(k):
            if not pool: break
            idx = random.choices(range(len(pool)), weights=pw)[0]
            chosen.append(pool[idx])
            pool.pop(idx); pw.pop(idx)
        return chosen

    # ============= 信息生成 (复用 v3 简化版) =============
    def gen_interrogator_event(self, seat, is_real=True):
        p = self.players[seat]
        cands = [s for s in self.alive_seats() if s != seat]
        if len(cands) < 3: return None
        if is_real:
            chosen = random.sample(cands, 3)
            non_demon_evil = sum(1 for s in chosen if self.players[s].team == '邪恶'
                                  and not is_demon_role(self.players[s].role))
            actual = (non_demon_evil == 1)
            declared = (not actual) if self.is_info_distorted(seat) else actual
            return InfoEvent(seat, '审讯官', p.role, self.day, True,
                            targets=chosen, actual_result=actual, declared_result=declared,
                            is_distorted=self.is_info_distorted(seat))
        else:
            # 邪恶 bluff: 选 3 真镇民, 多偏 yes (random pick, 不策略)
            innocents = [s for s in cands if s not in self.evil_seats]
            if len(innocents) >= 3:
                chosen = random.sample(innocents, 3)
                declared = random.choices([True, False], weights=[0.7, 0.3])[0]
                return InfoEvent(seat, '审讯官', p.role, self.day, True,
                                targets=chosen, declared_result=declared,
                                is_fake_bluff=True)
            return None

    def gen_clerk_event(self, seat, is_real=True):
        """书记官 N1: 学外来者+爪牙 seat sum"""
        if self.day != 1: return None
        p = self.players[seat]
        if is_real:
            register_seats = {s for s in self.players
                              if self.is_seat_outsider_register(s)
                              or self.players[s].register_minion}
            register_seats.discard(seat)
            actual = sum(register_seats)
            declared = actual + random.choice([-3, 3, 5]) if self.is_info_distorted(seat) else actual
            return InfoEvent(seat, '书记官', p.role, 1, True,
                             actual_result=actual, declared_result=max(1, declared),
                             is_distorted=self.is_info_distorted(seat))
        else:
            # 邪恶 bluff: 编一个指向真镇民组合的 sum
            innocents = [s for s in self.alive_seats() if self.players[s].team == '镇民' and s != seat]
            register_count = sum(1 for s in self.players if self.is_seat_outsider_register(s) or self.players[s].register_minion)
            if len(innocents) >= register_count and register_count > 0:
                fake_subset = random.sample(innocents, register_count)
                fake_sum = sum(fake_subset)
                return InfoEvent(seat, '书记官', p.role, 1, True,
                                declared_result=fake_sum, is_fake_bluff=True)
            return None

    def gen_scout_event(self, seat, is_real=True):
        """斥候 N1 / D3+ (v6: N1 改为 3 demon, 之前是 2 demon)"""
        p = self.players[seat]
        if is_real:
            true_demon = self.players[self.demon_seats[0]].role if self.demon_seats else None
            if not true_demon: return None
            others = [d for d in DEMON_POOL if d != true_demon]
            # N1: 3 demon (real + 2 fakes). 仅有 3 个非真 demon, 取 2 个伪
            fakes = random.sample(others, 2)
            actual = sorted([true_demon] + fakes)
            if self.is_info_distorted(seat):
                # 醉酒/中毒: 看到 3 个非真 demon (确定性, 因为只有 3 个非真)
                declared = sorted(others)
            else:
                declared = actual
            return InfoEvent(seat, '斥候', p.role, self.day, self.day == 1,
                            actual_result=actual, declared_result=declared,
                            is_distorted=self.is_info_distorted(seat))
        else:
            # 邪恶装斥候: 随机 3 demon (与原版 2-demon 一致, 简化处理 — 不建模 avoid 策略)
            declared = sorted(random.sample(DEMON_POOL, 3))
            return InfoEvent(seat, '斥候', p.role, self.day, self.day == 1,
                            declared_result=declared, is_fake_bluff=True)

    def gen_patroller_event(self, seat, is_real=True):
        p = self.players[seat]
        cands = [s for s in self.alive_seats() if s != seat]
        if not cands: return None
        chosen = random.choice(cands)
        if is_real:
            l, r = self.neighbors(chosen)
            actual = ((l and self.is_seat_outsider_register(l)) or
                      (r and self.is_seat_outsider_register(r)))
            declared = (not actual) if self.is_info_distorted(seat) else actual
            return InfoEvent(seat, '巡逻兵', p.role, self.day, True,
                            targets=[chosen], actual_result=actual, declared_result=declared,
                            is_distorted=self.is_info_distorted(seat))
        else:
            return InfoEvent(seat, '巡逻兵', p.role, self.day, True,
                            targets=[chosen], declared_result=random.choice([True, False]),
                            is_fake_bluff=True)

    def gen_doctor_event(self, seat, is_real=True):
        """军医 v2: 选 2 名其他存活玩家, 至少 1 人今晚被唤醒"""
        p = self.players[seat]
        cands = [s for s in self.alive_seats() if s != seat]
        if len(cands) < 2: return None
        chosen = random.sample(cands, 2)
        if is_real:
            # 至少 1 人被唤醒: 邪恶/信息源/恶魔被视为有夜活
            def is_woken(s):
                pp = self.players[s]
                return pp.team == '邪恶' or pp.role in INFO_SOURCES or is_demon_role(pp.role)
            actual = any(is_woken(s) for s in chosen)
            declared = (not actual) if self.is_info_distorted(seat) else actual
            return InfoEvent(seat, '军医', p.role, self.day, True,
                            targets=chosen, actual_result=actual, declared_result=declared,
                            is_distorted=self.is_info_distorted(seat))
        else:
            return InfoEvent(seat, '军医', p.role, self.day, True,
                            targets=chosen, declared_result=random.choice([True, False]),
                            is_fake_bluff=True)

    def gen_priest_event(self, seat, is_real=True):
        if self.day < 2: return None
        p = self.players[seat]
        if is_real:
            changed = sum(1 for s in self.players if self.players[s].alive
                          and self.players[s].role != self.players[s].original_role)
            declared = changed + random.choice([-1, 1, 2]) if self.is_info_distorted(seat) else changed
            return InfoEvent(seat, '牧师', p.role, self.day, True,
                            actual_result=changed, declared_result=max(0, declared),
                            is_distorted=self.is_info_distorted(seat))
        else:
            return InfoEvent(seat, '牧师', p.role, self.day, True,
                            declared_result=random.randint(0, 3), is_fake_bluff=True)

    def gen_herald_event(self, seat, is_real=True):
        p = self.players[seat]
        cands = [s for s in self.alive_seats() if s != seat]
        if len(cands) < 3: return None
        chosen = random.sample(cands, 3)
        if is_real:
            count = sum(1 for s in chosen if self.is_seat_outsider_register(s))
            actual = (count == 1)
            declared = (not actual) if self.is_info_distorted(seat) else actual
            return InfoEvent(seat, '纹章官', p.role, self.day, False,
                            targets=chosen, actual_result=actual, declared_result=declared,
                            is_distorted=self.is_info_distorted(seat))
        else:
            return InfoEvent(seat, '纹章官', p.role, self.day, False,
                            targets=chosen, declared_result=True, is_fake_bluff=True)

    def gen_spy_event(self, seat, is_real=True):
        p = self.players[seat]
        cands = [s for s in self.alive_seats() if s != seat]
        if len(cands) < 2: return None
        chosen = random.sample(cands, 2)
        if is_real:
            def dist(s):
                alive_minions = [m for m in self.minion_seats if self.players[m].alive]
                # 千面人 setup: 用 demon_seats (千面人 register 爪牙)
                if not alive_minions and self.is_lunatic_setup:
                    alive_minions = [d for d in self.demon_seats if self.players[d].alive]
                if not alive_minions: return 999
                return min(min(abs(s - m), 12 - abs(s - m)) for m in alive_minions)
            d0, d1 = dist(chosen[0]), dist(chosen[1])
            if d0 == 999 and d1 == 999:
                return None
            actual = chosen[0] if d0 <= d1 else chosen[1]
            declared = chosen[1] if (self.is_info_distorted(seat) and actual == chosen[0]) else (chosen[0] if (self.is_info_distorted(seat) and actual == chosen[1]) else actual)
            return InfoEvent(seat, '密探', p.role, self.day, False,
                            targets=chosen, actual_result=actual, declared_result=declared,
                            is_distorted=self.is_info_distorted(seat))
        else:
            return InfoEvent(seat, '密探', p.role, self.day, False,
                            targets=chosen, declared_result=random.choice(chosen),
                            is_fake_bluff=True)

    def gen_lookout_event(self, seat, is_real=True):
        p = self.players[seat]
        if is_real:
            not_in = self.not_in_play_outsiders + self.not_in_play_minions
            if not not_in: return None
            actual = random.choice(not_in)
            declared = random.choice(self.outsiders + [self.players[s].original_role for s in self.minion_seats]) \
                       if self.is_info_distorted(seat) else actual
            return InfoEvent(seat, '瞭望兵', p.role, self.day, True,
                            actual_result=actual, declared_result=declared,
                            is_distorted=self.is_info_distorted(seat))
        else:
            # 邪恶 bluff: 偏向真在场角色 (尤其是有人 claim 的)
            in_play = self.outsiders + [self.players[s].original_role for s in self.minion_seats]
            if not in_play:
                in_play = self.not_in_play_outsiders + self.not_in_play_minions
            if not in_play: return None
            declared = random.choice(in_play)
            return InfoEvent(seat, '瞭望兵', p.role, self.day, True,
                            declared_result=declared, is_fake_bluff=True)

    def night_info_gather(self):
        gen_map = {
            '审讯官': self.gen_interrogator_event,
            '瞭望兵': self.gen_lookout_event,
            '书记官': self.gen_clerk_event,
            '斥候': self.gen_scout_event,
            '巡逻兵': self.gen_patroller_event,
            '军医': self.gen_doctor_event,
            '牧师': self.gen_priest_event,
        }
        # 真信息源
        for seat in self.alive_seats():
            p = self.players[seat]
            if p.role in gen_map:
                ev = gen_map[p.role](seat, is_real=True)
                if ev:
                    self.events.append(ev)
                    if self.verbose:
                        d = ' [扭曲]' if ev.is_distorted else ''
                        self.log(f'  {seat}({p.role}): {ev.declared_result}{d}', 1)
        # 邪恶 bluff
        for seat in self.evil_seats:
            if not self.players[seat].alive: continue
            p = self.players[seat]
            if p.bluff_role in gen_map:
                ev = gen_map[p.bluff_role](seat, is_real=False)
                if ev:
                    self.events.append(ev)
                    if self.verbose:
                        self.log(f'  {seat}({p.bluff_role},bluff): {ev.declared_result}', 1)

    def day_info_gather(self):
        gen_map = {
            '纹章官': self.gen_herald_event,
            '密探': self.gen_spy_event,
        }
        if self.day >= 3:
            gen_map['斥候'] = self.gen_scout_event  # D3+ 白天
        for seat in self.alive_seats():
            p = self.players[seat]
            if p.role in gen_map:
                ev = gen_map[p.role](seat, is_real=True)
                if ev:
                    self.events.append(ev)
                    if self.verbose:
                        self.log(f'  {seat}({p.role}): {ev.declared_result}', 1)
        for seat in self.evil_seats:
            if not self.players[seat].alive: continue
            p = self.players[seat]
            if p.bluff_role in gen_map:
                ev = gen_map[p.bluff_role](seat, is_real=False)
                if ev:
                    self.events.append(ev)
                    if self.verbose:
                        self.log(f'  {seat}({p.bluff_role},bluff): {ev.declared_result}', 1)

    # ============= 杀人 + 死亡链 (修复后含 trigger) =============
    def kill(self, seat, method='夜杀'):
        if not self.players[seat].alive: return False
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
        # 触发死亡链 (修复 bug)
        if self._should_trigger_death(seat, method):
            self._trigger_death_chain(seat)
        return True

    def _should_trigger_death(self, seat, method):
        """新机制 (v6): 保险栓不再"阻止", 而是"吸收" — 触发时本人变傀儡 (silent),
        has_save_baron/has_save_shield 翻转. 一次有效."""
        p = self.players[seat]
        # 死亡是否触发链由角色决定 (注册为外来者者: 外来者/傀儡/死士/千面人)
        triggers_chain = (p.role in OUTSIDER_POOL or p.role == '傀儡'
                          or '千面人' in p.role or p.role == '死士')
        if not triggers_chain:
            return False
        # 保险栓吸收: 处决 → 女伯爵; 夜杀 → 盾卫
        if method == '处决' and self.has_save_baron:
            baron_seat = next((s for s in self.alive_seats()
                               if self.players[s].role == '女伯爵'), None)
            if baron_seat is not None:
                self._absorb_into_puppet(baron_seat, '女伯爵')
                return False
        if method == '夜杀' and self.has_save_shield:
            shield_seat = next((s for s in self.alive_seats()
                                if self.players[s].role == '盾卫'), None)
            if shield_seat is not None:
                self._absorb_into_puppet(shield_seat, '盾卫')
                return False
        return True

    def _absorb_into_puppet(self, seat, old_role):
        """保险栓吸收外来者死亡链: 自己变傀儡 (不告知本人, 玩家仍以为有能力).
        触发后角色翻转为'傀儡', register_outsider=True, has_save_* 翻转 False.
        日后该玩家死亡时仍会触发傀儡死亡链 (新弹药)."""
        p = self.players[seat]
        p.role = '傀儡'
        p.puppet = True
        p.register_outsider = True
        if old_role == '女伯爵':
            self.has_save_baron = False
        elif old_role == '盾卫':
            self.has_save_shield = False
        self.log(f'  ★ {old_role}吸收: {seat} ({p.name}) 变傀儡 (不告知)', 1)

    def _trigger_death_chain(self, seat):
        """外来者死亡只触发自己能力. 死士/傀儡/千面人 才触发傀儡能力 (各自 ability 明说)."""
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
        # 先锋官 setup: 外来者"被视为傀儡"只是 register, 不触发 (剧本没明说触发)

    def _trigger_puppet_death(self):
        """傀儡死亡链 — 剧本: '不能与上次相同'"""
        valid = []
        last = getattr(self, 'last_puppet_chain', None)
        if not self.refugee_used and any(not self.players[s].alive and self.players[s].team != '邪恶'
                                          and s not in self.evil_dead_votes for s in self.players):
            if last != '难民':
                valid.append(('难民', 0.4))
        if [s for s in self.alive_seats() if s not in self.evil_seats]:
            if last != '伤兵':
                valid.append(('伤兵', 0.3))
            if last != '逃兵':
                valid.append(('逃兵', 0.4))
        if self.evil_alive(exclude_demon=True) and last != '俘虏':
            valid.append(('俘虏', 0.2))
        if not valid: return
        choices_v, weights = zip(*valid)
        chosen = random.choices(choices_v, weights=weights)[0]
        self.last_puppet_chain = chosen  # 记录避免下次重复
        self.log(f'  傀儡死亡 → 邪恶选: {chosen} (上次={last})', 1)
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
        self.log(f'  ★ 难民触发: {chosen} 变邪恶死人', 1)

    def _trigger_wounded(self):
        cands = [s for s in self.alive_seats() if s not in self.evil_seats]
        if not cands: return
        weights = [0.30 if self.players[s].role in ['军医', '盾卫', '审讯官']
                   else 0.25 if self.players[s].role in ['女伯爵', '斥候']
                   else 0.05 for s in cands]
        chosen = random.choices(cands, weights=weights)[0]
        old = self.players[chosen].role
        self.players[chosen].role = '傀儡'
        self.players[chosen].puppet = True
        self.players[chosen].register_outsider = True
        if old == '女伯爵': self.has_save_baron = False
        if old == '盾卫': self.has_save_shield = False
        self.log(f'  ★ 伤兵触发: {chosen} 从 {old} 变傀儡', 1)

    def _trigger_deserter(self):
        cands = [s for s in self.alive_seats() if s not in self.evil_seats]
        if not cands: return
        weights = [0.30 if self.players[s].role in ['军医', '审讯官', '斥候']
                   else 0.05 if self.players[s].role == '游侠'
                   else 0.10 for s in cands]
        chosen = random.choices(cands, weights=weights)[0]
        self.log(f'  ★ 逃兵触发: 选 {chosen} 当晚死', 1)
        self.kill(chosen, method='夜杀')

    def _trigger_captive(self):
        """俘虏 (新规则): 邪恶选活人 + 不在场善良角色, 强制疯狂. 简化处理: 50% 玩家 violate → 死."""
        cands = [s for s in self.alive_seats() if s not in self.evil_seats]
        if not cands: return
        chosen = random.choice(cands)
        # 简化 madness: 50% violate, storyteller 处决
        if random.random() < 0.5:
            self.log(f'  ★ 俘虏触发: {chosen} 疯狂违反 → storyteller 处决', 1)
            self.kill(chosen, method='处决')
        else:
            self.log(f'  ★ 俘虏触发: {chosen} 疯狂保持假声称 (信息流混乱)', 1)
            self.players[chosen].puppet = True  # 信息源失能

    def n_kill(self):
        if self.day < 2: return
        # 简化攻击: 排除恶魔
        demons = [s for s in self.alive_seats() if is_demon_role(self.players[s].role)]
        if not demons: return
        cands = [s for s in self.alive_seats() if s not in demons]
        if not cands: return
        # 优先杀信息源
        weights = []
        for s in cands:
            r = self.players[s].role
            weights.append(0.30 if r in INFO_SOURCES else 0.05)
        target = random.choices(cands, weights=weights)[0]
        self.log(f'  恶魔杀: {target}')
        self.kill(target, method='夜杀')

    # ============= 处决 =============
    def day_execute(self):
        alive = self.alive_seats()
        if not alive: return None

        # 让 reasoner 处理所有事件
        current_claims = {s: self.players[s].claimed_role for s in alive
                          if self.players[s].claimed_role}
        register_count = sum(1 for s in self.players
                             if self.is_seat_outsider_register(s) or self.players[s].register_minion)
        self.reasoner.process_all(self.events, alive, current_claims, register_count,
                                    self.players, self.deaths)

        # 不处决率
        if self.day == 1: non_exec = 0.70
        elif self.day == 2: non_exec = 0.30
        else: non_exec = 0.10
        if len(alive) <= 4: non_exec = 0.05
        if random.random() < non_exec:
            self.log(f'  D{self.day} 不处决')
            return None

        target = self.reasoner.execute_target(alive)
        if target is None:
            self.log(f'  D{self.day} 嫌疑不足, 不处决')
            return None

        # 投票通过率
        actually_evil = self.players[target].team == '邪恶'
        p_evil = self.world_state.p_evil(target)
        pass_prob = 0.30 + p_evil * 0.5
        if random.random() > pass_prob:
            self.log(f'  D{self.day} 提名 {target} (P邪={p_evil:.2f}) 失败')
            return None

        self.log(f'  D{self.day} 处决: {target} ({self.players[target].name}, {self.players[target].role}, P邪={p_evil:.2f})')
        self.kill(target, method='处决')
        return target

    # ============= 主循环 =============
    def check_win(self):
        alive = self.alive_seats()
        demons = self.alive_demons()
        if not demons: return '善良'
        if len(alive) <= 2 and demons: return '邪恶'
        # 修复模拟器死锁: 善良全死(alive 全是邪恶) → 邪恶胜
        # (真实游戏中这种局面下千面人会互相投出一个 → alive 降到 2,
        # 但模拟器投票模型不够强, 会 D8-D15 干瞪眼超时)
        evil_alive = [s for s in alive if self.players[s].team == '邪恶']
        if alive and len(evil_alive) == len(alive): return '邪恶'
        return None

    def play(self):
        self.print_config()
        self.log('=== N1 ===')
        self.day = 1
        self.night_info_gather()

        max_days = 15
        while self.day <= max_days:
            self.log(f'\n=== D{self.day} ===')
            self.day_info_gather()
            self.day_execute()
            w = self.check_win()
            if w: return w, self.day
            self.day += 1
            if self.day > max_days: break
            self.log(f'\n=== N{self.day} ===')
            self.n_kill()
            self.night_info_gather()
            w = self.check_win()
            if w: return w, self.day
        return '平局/超时', self.day - 1

    def print_config(self):
        if not self.verbose: return
        self.log('=== 配置 ===')
        self.log(f'恶魔: {self.demon_role}, 外来者: {self.outsiders}')
        self.log(f'镇民: {self.townsfolk}, Bluffs: {self.bluffs}')
        for i in sorted(self.players):
            p = self.players[i]
            bluff = f' [bluff:{p.bluff_role}]' if p.bluff_role else ''
            self.log(f'  {i}. {p.name}: {p.role} ({p.team}){bluff}')
        self.log('')


def run_batch(n=200, verbose=False):
    results = {'善良': 0, '邪恶': 0, '平局/超时': 0}
    setups = {}
    days = 0
    for i in range(n):
        g = Game(verbose=verbose)
        key = '千面人' if g.is_lunatic_setup else g.demon_role
        winner, d = g.play()
        results[winner] += 1
        days += d
        setups.setdefault(key, {'善良': 0, '邪恶': 0, '平局/超时': 0, 'n': 0})
        setups[key][winner] += 1
        setups[key]['n'] += 1
    print(f'\n=== {n} 局 v4 (Bayesian + 审讯官+瞭望兵 policy) ===')
    print(f'善良: {results["善良"]*100/n:.1f}% / 邪恶: {results["邪恶"]*100/n:.1f}% / 超时: {results["平局/超时"]*100/n:.1f}%')
    print(f'平均天数: {days/n:.1f}\n')
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
        try: n = int(args[0]); run_batch(n, verbose=verbose)
        except ValueError: print('Usage: python3 botc_simulator_v4.py [n] [-v]'); sys.exit(1)
    else:
        g = Game(verbose=True)
        winner, d = g.play()
        print(f'\n=== {winner}胜, {d}天 ===')
