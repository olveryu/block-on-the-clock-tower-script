#!/usr/bin/env python3
"""
围城之夜 12 人模拟器
=======================
用 Python 真随机骰子决定关键节点, 避免模拟者上帝视角偏差.

用法:
    python3 botc_simulator.py        # 跑一局完整推演
    python3 botc_simulator.py 30     # 跑 30 局看胜率

最新更新: 2026-04-28 (v17 后)
"""

import random
import sys

# ============= 角色池 =============
TOWNSFOLK_POOL = [
    '斥候', '密探', '巡逻兵', '审讯官', '游侠', '军医',
    '书记官', '军需官', '牧师', '纹章官', '盾卫', '女伯爵', '瞭望兵'
]
OUTSIDER_POOL = ['伤兵', '逃兵', '难民', '俘虏']
MINION_POOL = ['内应', '蛊惑者', '叛将', '死士']
DEMON_POOL = ['攻城将军', '先锋官', '千面人', '暗箭手']

PLAYERS = ['阿信', '小白', '二哥', '月儿', '老王', '阿龙',
           '莉莉', '小七', '大刘', '苗苗', '阿强', '雪儿']


def generate_config():
    """生成 12 人随机配置"""
    demon = random.choice(DEMON_POOL)
    minions_raw = random.sample(MINION_POOL, 2)

    if demon == '千面人':
        outsider_count = 1
        townsfolk_count = 8
        minions = ['千面人', '千面人']
    elif demon == '先锋官' or '叛将' in minions_raw:
        outsider_count = 3
        townsfolk_count = 6
        minions = minions_raw
    else:
        outsider_count = 2
        townsfolk_count = 7
        minions = minions_raw

    townsfolk = random.sample(TOWNSFOLK_POOL, townsfolk_count)
    outsiders = random.sample(OUTSIDER_POOL, outsider_count)
    not_in_play_t = [t for t in TOWNSFOLK_POOL if t not in townsfolk]
    bluffs = random.sample(not_in_play_t, 3)
    not_in_play_o = [o for o in OUTSIDER_POOL if o not in outsiders]

    roles = [demon] + minions + outsiders + townsfolk
    random.shuffle(roles)

    config = {}
    for i, (p, r) in enumerate(zip(PLAYERS, roles), 1):
        is_demon = r == demon or '千面人' in r
        is_minion = r in MINION_POOL
        if is_demon or is_minion:
            team = "邪恶"
        elif r in outsiders:
            team = "外来者"
        else:
            team = "镇民"
        config[i] = {
            'player': p, 'role': r, 'team': team,
            'alive': True, 'puppet': False, 'original_role': r
        }

    setup_info = {
        'demon': demon, 'minions': minions, 'outsiders': outsiders,
        'townsfolk': townsfolk, 'bluffs': bluffs,
        'not_in_play_outsiders': not_in_play_o,
    }

    return config, setup_info


def evil_setup_decisions(config, setup_info):
    """邪恶 N0 决策: 死士自以为, 蛊惑者目标, 内应/暗箭手目标, bluff 选择"""
    decisions = {}

    if '死士' in setup_info['minions']:
        seat = next(i for i in config if config[i]['role'] == '死士')
        decisions['死士'] = {
            'seat': seat,
            'fake_role': random.choice(OUTSIDER_POOL),
        }

    if '蛊惑者' in setup_info['minions']:
        seat = next(i for i in config if config[i]['role'] == '蛊惑者')
        left = (seat - 2) % 12 + 1
        right = seat % 12 + 1
        if left == 0: left = 12
        decisions['蛊惑者'] = {
            'seat': seat,
            'target': random.choice([left, right]),
        }

    if '内应' in setup_info['minions']:
        seat = next(i for i in config if config[i]['role'] == '内应')
        others = [i for i in config if i != seat]
        decisions['内应'] = {
            'seat': seat,
            'target': random.choice(others),
        }

    if setup_info['demon'] == '暗箭手':
        seat = next(i for i in config if config[i]['role'] == '暗箭手')
        others = [i for i in config if i != seat]
        decisions['暗箭手'] = {
            'seat': seat,
            'target': random.choice(others),
        }

    # 邪恶 bluff
    bluffs = setup_info['bluffs']
    not_in_play_o = setup_info['not_in_play_outsiders']

    # 恶魔 bluff
    decisions['demon_bluff'] = random.choice(bluffs)

    # 爪牙 bluff
    decisions['minion_bluffs'] = {}
    for seat in config:
        role = config[seat]['role']
        if role in MINION_POOL and role != '死士':
            # 35% 装外来者捣乱, 65% 装镇民 bluff
            if random.random() < 0.35 and not_in_play_o:
                choice = random.choice(not_in_play_o)
                decisions['minion_bluffs'][seat] = ('外来者', choice)
            else:
                avail = [b for b in bluffs if b != decisions['demon_bluff']]
                choice = random.choice(avail) if avail else random.choice(bluffs)
                decisions['minion_bluffs'][seat] = ('镇民', choice)

    return decisions


def real_outsider_self_bust(config, setup_info):
    """真外来者自爆决策 (高玩谨慎)"""
    decisions = {}
    has_dead_man = '死士' in setup_info['minions']
    for seat in config:
        if config[seat]['team'] == '外来者':
            prob = 0.40 if has_dead_man else 0.55
            decisions[seat] = random.random() < prob
    return decisions


def n1_actions(config, setup_info):
    """N1 善良信息源选择 (真随机)"""
    actions = {}

    if '审讯官' in setup_info['townsfolk']:
        seat = next(i for i in config if config[i]['role'] == '审讯官')
        others = [i for i in config if i != seat and config[i]['alive']]
        targets = sorted(random.sample(others, 3))
        # 检查命中
        non_demon_evil = [t for t in targets if config[t]['team'] == '邪恶'
                           and config[t]['role'] not in DEMON_POOL
                           and '千面人' not in config[t]['role']]
        is_千面人_in = any('千面人' in config[t]['role'] for t in targets)
        actions['审讯官'] = {
            'seat': seat, 'targets': targets,
            'yes': bool(non_demon_evil) or is_千面人_in,
        }

    if '巡逻兵' in setup_info['townsfolk']:
        seat = next(i for i in config if config[i]['role'] == '巡逻兵')
        others = [i for i in config if i != seat and config[i]['alive']]
        target = random.choice(others)
        left = (target - 2) % 12 + 1
        right = target % 12 + 1
        if left == 0: left = 12
        # round-robin 跳死人
        while not config[left]['alive']:
            left = (left - 2) % 12 + 1
            if left == 0: left = 12
        while not config[right]['alive']:
            right = right % 12 + 1
        is_outsider = (config[left]['team'] == '外来者' or '死士' in config[left]['role'] or
                       config[right]['team'] == '外来者' or '死士' in config[right]['role'])
        actions['巡逻兵'] = {
            'seat': seat, 'target': target, 'yes': is_outsider,
        }

    if '书记官' in setup_info['townsfolk']:
        seat = next(i for i in config if config[i]['role'] == '书记官')
        # 外来者+爪牙之和 (按 actual team, 不算 register 多重)
        evil_outsider_seats = [i for i in config
                                 if config[i]['team'] == '外来者' or
                                    config[i]['role'] in MINION_POOL or
                                    '千面人' in config[i]['role']]
        # 但去重
        total = sum(evil_outsider_seats)
        actions['书记官'] = {'seat': seat, 'sum': total}

    if '斥候' in setup_info['townsfolk']:
        seat = next(i for i in config if config[i]['role'] == '斥候')
        # 在场恶魔 + 1 干扰
        in_play = setup_info['demon']
        not_in = [d for d in DEMON_POOL if d != in_play]
        actions['斥候'] = {
            'seat': seat,
            'candidates': sorted([in_play, random.choice(not_in)]),
        }

    if '瞭望兵' in setup_info['townsfolk']:
        seat = next(i for i in config if config[i]['role'] == '瞭望兵')
        # 不在场池: 爪牙+外来者
        not_in = ([m for m in MINION_POOL if m not in setup_info['minions']] +
                  setup_info['not_in_play_outsiders'])
        actions['瞭望兵'] = {
            'seat': seat,
            'told': random.choice(not_in) if not_in else None,
        }

    return actions


def night_kill_choice(config, demon_role, n=2):
    """夜晚击杀目标 (按威胁优先级骰子)"""
    alive_others = [i for i in config if config[i]['alive']]
    # 排除恶魔自己
    demon_seat = next(i for i in config if config[i]['role'] == demon_role
                       or (demon_role == '千面人' and config[i]['role'] == '千面人'))
    alive_others = [i for i in alive_others if i != demon_seat]

    threats = []
    for i in alive_others:
        role = config[i].get('original_role', config[i]['role'])
        if role == '斥候' and not config[i].get('puppet'):
            threats.append((i, 0.30))
        elif role == '军医' and not config[i].get('puppet'):
            threats.append((i, 0.20))
        elif role == '女伯爵' and not config[i].get('puppet'):
            threats.append((i, 0.20))
        elif role == '盾卫' and not config[i].get('puppet'):
            threats.append((i, 0.15))
        elif role == '审讯官' and not config[i].get('puppet'):
            threats.append((i, 0.10))
        elif role == '瞭望兵':
            threats.append((i, 0.08))
        elif role == '纹章官':
            threats.append((i, 0.07))
        elif role == '密探':
            threats.append((i, 0.07))
        else:
            threats.append((i, 0.03))

    seats, weights = zip(*threats)
    return random.choices(seats, weights=weights)[0]


def day_execute(config, day_number):
    """善良处决决策 (基于嫌疑权重 + 不处决概率)"""
    alive = [i for i in config if config[i]['alive']]

    # D1 不处决概率 70%, D2 30%, D3+ 10%
    if day_number == 1:
        non_exec_prob = 0.70
    elif day_number == 2:
        non_exec_prob = 0.30
    else:
        non_exec_prob = 0.10

    if random.random() < non_exec_prob:
        return None

    # 嫌疑权重 (基于 register team + 是否公开身份)
    suspects = []
    for s in alive:
        role = config[s]['role']
        team = config[s]['team']
        if team == '邪恶':
            if role in DEMON_POOL or '千面人' in role:
                suspects.append((s, 0.45))  # 恶魔
            else:
                suspects.append((s, 0.50))  # 爪牙
        elif team == '外来者':
            suspects.append((s, 0.10))
        else:
            suspects.append((s, 0.05))  # 镇民

    seats, weights = zip(*suspects)
    norm = [w/sum(weights) for w in weights]
    return random.choices(seats, weights=norm)[0]


def check_win(config, setup_info):
    """检查胜负"""
    alive = [i for i in config if config[i]['alive']]
    demons_alive = [i for i in alive
                     if config[i]['role'] in DEMON_POOL or
                        '千面人' in config[i]['role']]
    if not demons_alive:
        return '善良'
    if len(alive) <= 2 and demons_alive:
        return '邪恶'
    return None


def run_game(verbose=True):
    """跑一局完整推演"""
    config, setup_info = generate_config()
    decisions = evil_setup_decisions(config, setup_info)
    self_bust = real_outsider_self_bust(config, setup_info)
    n1 = n1_actions(config, setup_info)

    if verbose:
        print(f"\n=== 配置 ===")
        print(f"恶魔: {setup_info['demon']}, 爪牙: {setup_info['minions']}")
        print(f"外来者: {setup_info['outsiders']}")
        print(f"镇民: {setup_info['townsfolk']}")
        print(f"Bluffs: {setup_info['bluffs']}")
        for i in sorted(config):
            print(f"  {i}. {config[i]['player']}: {config[i]['role']} ({config[i]['team']})")

    # 简化的推演循环
    day = 1
    death_log = []
    max_days = 8

    while day <= max_days:
        # 夜晚击杀
        if day > 1:
            try:
                kill_target = night_kill_choice(config, setup_info['demon'])
                config[kill_target]['alive'] = False
                death_log.append((f'N{day}', kill_target, config[kill_target]['role']))
                if verbose:
                    print(f"N{day} 杀: {kill_target} ({config[kill_target]['player']}, {config[kill_target]['role']})")
            except (StopIteration, ValueError):
                pass

        # 检查胜负
        winner = check_win(config, setup_info)
        if winner:
            return winner, day - 1, death_log

        # 白天处决
        exec_target = day_execute(config, day)
        if exec_target:
            config[exec_target]['alive'] = False
            death_log.append((f'D{day}', exec_target, config[exec_target]['role']))
            if verbose:
                print(f"D{day} 处决: {exec_target} ({config[exec_target]['player']}, {config[exec_target]['role']})")
        else:
            if verbose:
                print(f"D{day} 不处决")

        # 检查胜负
        winner = check_win(config, setup_info)
        if winner:
            return winner, day, death_log

        day += 1

    return '平局/超时', day, death_log


def run_batch(n=30):
    """跑 n 局看胜率"""
    results = {'善良': 0, '邪恶': 0, '平局/超时': 0}
    days_total = 0
    print(f"\n=== 跑 {n} 局 (简化推演) ===")
    for i in range(n):
        winner, days, _ = run_game(verbose=False)
        results[winner] += 1
        days_total += days
    print(f"\n善良: {results['善良']}/{n} = {results['善良']*100/n:.1f}%")
    print(f"邪恶: {results['邪恶']}/{n} = {results['邪恶']*100/n:.1f}%")
    if results['平局/超时'] > 0:
        print(f"平局/超时: {results['平局/超时']}")
    print(f"平均天数: {days_total/n:.1f}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
            run_batch(n)
        except ValueError:
            print("Usage: python3 botc_simulator.py [n_games]")
            sys.exit(1)
    else:
        winner, days, deaths = run_game(verbose=True)
        print(f"\n=== 胜负 ===")
        print(f"{winner}胜, 用时 {days} 天")
        print(f"\n死亡顺序:")
        for time, seat, role in deaths:
            print(f"  {time}: 座 {seat} ({role})")
