#!/usr/bin/env python3
"""
围城之夜 v5 manual — 我手动扮演 12 玩家用的薄 script
================================================
机制层 (kill/death chains/setup/ground truth) 用 Python.
对话/推理/决策 由 master Claude 手动扮演每个 agent.

状态持久化在 v5_state.json. 每次操作 read-modify-write.

用法 (从对话中调):
    python3 botc_v5_manual.py setup [seed]    # 初始化局
    python3 botc_v5_manual.py state           # 看当前状态
    python3 botc_v5_manual.py kill <seat> <method>  # 杀人 + 触发死亡链
    python3 botc_v5_manual.py night_info_for <seat> <role>  # 该角色当夜会得到的真信息
    python3 botc_v5_manual.py advance <new_phase>  # 推进到下一阶段
"""
import sys, json, random, os
from itertools import combinations

STATE_FILE = 'v5_state.json'

TOWNSFOLK = ['斥候', '密探', '巡逻兵', '审讯官', '游侠', '掘墓人',
             '书记官', '军需官', '牧师', '纹章官', '盾卫', '女伯爵', '瞭望兵']
OUTSIDERS = ['伤兵', '逃兵', '难民', '俘虏']
MINIONS = ['内应', '蛊惑者', '潜伏者', '死士']
DEMONS = ['征服者', '先锋官', '千面人', '暗箭手']
# 信息源(N1+ 唤醒型) - 掘墓人不算(N* 才用一次, 非每晚)
INFO_SOURCES = {'斥候', '密探', '巡逻兵', '审讯官', '书记官', '纹章官', '瞭望兵', '牧师'}
# 复活栈触发: 死士(register 外来者) + 潜伏者(register 镇民) 都"恶魔死则变恶魔"
RESURRECTION_ROLES = {'死士', '潜伏者'}
PLAYERS = ['阿信', '小白', '二哥', '月儿', '老王', '阿龙',
           '莉莉', '小七', '大刘', '苗苗', '阿强', '雪儿']


def is_demon(r): return r in DEMONS or '千面人' in r


def setup(seed=None):
    if seed is not None:
        random.seed(int(seed))
    demon = random.choice(DEMONS)
    is_lunatic = (demon == '千面人')
    minions_raw = random.sample(MINIONS, 2)

    if is_lunatic:
        n_outsider, n_townsfolk = 2, 7  # 千面人剧本只'爪牙变千面人', 不改外来者数
        minions_assignment = ['千面人', '千面人']
    elif demon == '先锋官':
        # 先锋官 +1 外来者 (潜伏者不再带 +1, 不像旧叛将)
        n_outsider, n_townsfolk = 3, 6
        minions_assignment = minions_raw
    else:
        n_outsider, n_townsfolk = 2, 7
        minions_assignment = minions_raw

    townsfolk = random.sample(TOWNSFOLK, n_townsfolk)
    outsiders = random.sample(OUTSIDERS, n_outsider)
    not_in_play_t = [t for t in TOWNSFOLK if t not in townsfolk]
    bluffs = random.sample(not_in_play_t, 3)

    roles = [demon] + minions_assignment + outsiders + townsfolk
    random.shuffle(roles)

    state = {
        'demon_role': demon,
        'is_lunatic': is_lunatic,
        'outsiders': outsiders,
        'townsfolk': townsfolk,
        'bluffs': bluffs,
        'not_in_play_outsiders': [o for o in OUTSIDERS if o not in outsiders],
        'not_in_play_minions': [m for m in MINIONS if m not in minions_assignment],
        'players': {},
        'evil_seats': [],
        'demon_seats': [],
        'minion_seats': [],
        'has_baron': False,
        'has_shield': False,
        'dead_man_seat': None,
        'dead_man_active': False,
        # 'refugee_used' 移除: 难民没每局一次限制, 仅受善良死人池约束
        'evil_dead_votes': [],
        'archer_n1_target': None,
        'archer_swapped': False,
        'hex_target': None,
        'drunk_target': None,
        'deaths': [],
        'events': [],  # 信息事件日志
        'public_log': [],  # 公开发言日志
        'private_log': [],  # 私聊日志
        'phase': 'N0',
        'day': 0,
    }

    # bluff 不撞: 邪恶 N0 选 bluff
    used_bluffs = set()
    for i, (p, r) in enumerate(zip(PLAYERS, roles), 1):
        is_d = (r == demon and not is_lunatic) or '千面人' in r
        is_m = r in MINIONS and r != '千面人'
        if is_d:
            team = '邪恶'
            state['demon_seats'].append(i)
        elif is_m:
            team = '邪恶'
            state['minion_seats'].append(i)
        elif r in outsiders:
            team = '外来者'
        else:
            team = '镇民'

        # bluff role
        bluff = None
        if team == '邪恶':
            if is_d or '千面人' in r:
                # 恶魔/千面人 用 N0 bluffs (镇民)
                avail = [b for b in bluffs if b not in used_bluffs]
                if avail:
                    bluff = random.choice(avail)
                    used_bluffs.add(bluff)
                else:
                    bluff = random.choice(bluffs)
            else:
                # 爪牙: 60% 装外来者, 40% 装镇民
                # 装外来者只从"不在场外来者"里选, 避免与场上真外来者撞角色
                # (高玩级邪恶 N0 不会撞角色; 此处修复 setup bug)
                if random.random() < 0.6:
                    pool = state['not_in_play_outsiders']
                    avail = [r for r in pool if r not in used_bluffs]
                    if avail:
                        bluff = random.choice(avail)
                        used_bluffs.add(bluff)
                if not bluff:
                    avail = [b for b in bluffs if b not in used_bluffs]
                    bluff = random.choice(avail) if avail else random.choice(bluffs)
                    used_bluffs.add(bluff)

        # claimed_role: 死士自以为外来者(说书人选), 潜伏者自以为镇民(说书人选)
        if r == '死士':
            self_belief = random.choice(state['not_in_play_outsiders']) if state['not_in_play_outsiders'] else random.choice(outsiders)
            claimed = self_belief
        elif r == '潜伏者':
            # 自以为是某个镇民角色 (说书人选, 通常 not_in_play_townsfolk)
            self_belief = random.choice([t for t in TOWNSFOLK if t not in townsfolk]) if [t for t in TOWNSFOLK if t not in townsfolk] else random.choice(townsfolk)
            claimed = self_belief
        elif team == '邪恶':
            claimed = bluff
        else:
            claimed = r

        state['players'][str(i)] = {
            'seat': i,
            'name': p,
            'role': r,
            'original_role': r,
            'team': team,
            'alive': True,
            'is_drunk': False,
            'is_hexed': False,
            # 死士 register 外来者 (剧本明说); 潜伏者不 register (普通爪牙)
            'register_outsider': r in outsiders or r == '死士' or '千面人' in r,
            'register_minion': is_m or r == '死士' or '千面人' in r,
            'bluff_role': bluff,
            'claimed_role': claimed,
            'puppet': False,
        }

        if team == '邪恶':
            state['evil_seats'].append(i)
        # 复活栈: 死士 OR 潜伏者 (两者都 "恶魔死则变恶魔")
        if r in RESURRECTION_ROLES:
            state['dead_man_seat'] = i  # 仍叫 dead_man_seat (向后兼容)
            state['dead_man_active'] = True
            state['dead_man_role'] = r  # 记录是死士还是潜伏者
        if r == '女伯爵':
            state['has_baron'] = True
        if r == '盾卫':
            state['has_shield'] = True

    save(state)
    return state


def load():
    with open(STATE_FILE) as f:
        return json.load(f)


def save(s):
    with open(STATE_FILE, 'w') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def alive_seats(s, exclude=None):
    excl = set(exclude or [])
    return [int(k) for k, v in s['players'].items() if v['alive'] and int(k) not in excl]


def get_p(s, seat):
    return s['players'][str(seat)]


def is_register_outsider(s, seat):
    p = get_p(s, seat)
    return p['team'] == '外来者' or p['register_outsider'] or p['role'] == '傀儡'


def neighbors(s, seat):
    """活的左右邻"""
    def find(start, dir):
        cur = start
        for _ in range(12):
            cur = cur + dir
            if cur < 1: cur = 12
            if cur > 12: cur = 1
            if get_p(s, cur)['alive']:
                return cur
        return None
    return find(seat, -1), find(seat, 1)


def show(s):
    print(f"=== 阶段: {s['phase']} ===")
    print(f"恶魔: {s['demon_role']}, 外来者: {s['outsiders']}")
    print(f"镇民: {s['townsfolk']}")
    print(f"Bluffs (不在场, 邪恶用): {s['bluffs']}")
    print(f"\n座位:")
    for i in range(1, 13):
        p = get_p(s, i)
        alive = '' if p['alive'] else ' [☠]'
        bluff = f" [bluff:{p['bluff_role']}]" if p['bluff_role'] else ''
        drunk = ' [drunk]' if p['is_drunk'] else ''
        hexed = ' [hexed]' if p['is_hexed'] else ''
        puppet = ' [puppet]' if p['puppet'] else ''
        print(f"  {i}. {p['name']} ({p['claimed_role']}/真:{p['role']}, {p['team']}){bluff}{alive}{drunk}{hexed}{puppet}")
    print(f"\n保险栓: 女伯爵={'活' if s['has_baron'] else '死'}, 盾卫={'活' if s['has_shield'] else '死'}")
    if s['dead_man_seat']:
        print(f"死士({s['dead_man_seat']}): active={s['dead_man_active']}")
    print(f"邪恶死人变票: {s['evil_dead_votes']}")
    print(f"\n死亡: {s['deaths']}")
    print(f"事件数: {len(s['events'])}, 公开发言: {len(s['public_log'])}, 私聊: {len(s['private_log'])}")


def kill_seat(s, seat, method):
    """杀人 + 触发死亡链"""
    p = get_p(s, seat)
    if not p['alive']:
        return f"已死"
    p['alive'] = False
    time = f"D{s['day']}" if method == '处决' else f"N{s['day']}"
    s['deaths'].append([time, seat, p['role']])
    log = [f"{time}: {seat} ({p['name']}, {p['role']}) 死"]

    if p['role'] == '女伯爵': s['has_baron'] = False
    if p['role'] == '盾卫': s['has_shield'] = False

    # 复活栈: 恶魔死 → 死士 OR 潜伏者 变成那个恶魔
    if is_demon(p['role']) and s['dead_man_active']:
        if s['dead_man_seat'] and get_p(s, s['dead_man_seat'])['alive']:
            stack_seat = s['dead_man_seat']
            old = get_p(s, stack_seat)['role']
            new = p['original_role']
            get_p(s, stack_seat)['role'] = new
            get_p(s, stack_seat)['team'] = '邪恶'
            s['demon_seats'].append(stack_seat)
            s['dead_man_active'] = False
            stack_role = s.get('dead_man_role', '死士')
            log.append(f"  ★ {stack_role}复活: {stack_seat} 从 {old} 变 {new}")

    # 触发死亡链 (v6 机制: 保险栓吸收而不是阻止)
    role = p['role']
    # 死士/潜伏者死亡也触发傀儡死亡链
    triggers_chain = (role in OUTSIDERS or role == '死士' or role == '潜伏者'
                      or role == '傀儡' or '千面人' in role)
    absorbed = False

    # 先锋官在场 + 外来者死亡 → 改触发傀儡死亡链 (邪恶任选外来者效果)
    vanguard_alive = any(v['alive'] and v['role'] == '先锋官' for v in s['players'].values())
    if triggers_chain and role in OUTSIDERS and vanguard_alive:
        log.append(f"  ★ 先锋官在场: {role}死亡改为触发傀儡死亡链")
        # 仍然走吸收检查, 但改成傀儡链 trigger
        if method == '处决' and s['has_baron']:
            baron_seat = next((int(k) for k, v in s['players'].items()
                               if v['alive'] and v['role'] == '女伯爵'), None)
            if baron_seat:
                absorb_into_puppet(s, baron_seat, '女伯爵')
                log.append(f"  ★ 女伯爵吸收: {baron_seat} 变傀儡 (不告知)")
                absorbed = True
        elif method == '夜杀' and s['has_shield']:
            shield_seat = next((int(k) for k, v in s['players'].items()
                                if v['alive'] and v['role'] == '盾卫'), None)
            if shield_seat:
                absorb_into_puppet(s, shield_seat, '盾卫')
                log.append(f"  ★ 盾卫吸收: {shield_seat} 变傀儡 (不告知)")
                absorbed = True
        if not absorbed:
            log.append(f"  → 触发傀儡死亡能力(先锋官重定向, 需手动调 trigger_puppet)")
        save(s)
        return '\n'.join(log)

    if triggers_chain:
        if method == '处决' and s['has_baron']:
            baron_seat = next((int(k) for k, v in s['players'].items()
                               if v['alive'] and v['role'] == '女伯爵'), None)
            if baron_seat:
                absorb_into_puppet(s, baron_seat, '女伯爵')
                log.append(f"  ★ 女伯爵吸收: {baron_seat} ({get_p(s, baron_seat)['name']}) 变傀儡 (不告知)")
                absorbed = True
        elif method == '夜杀' and s['has_shield']:
            shield_seat = next((int(k) for k, v in s['players'].items()
                                if v['alive'] and v['role'] == '盾卫'), None)
            if shield_seat:
                absorb_into_puppet(s, shield_seat, '盾卫')
                log.append(f"  ★ 盾卫吸收: {shield_seat} ({get_p(s, shield_seat)['name']}) 变傀儡 (不告知)")
                absorbed = True

        if not absorbed:
            if role in OUTSIDERS:
                log.append(f"  → 触发外来者死亡链: {role} (需手动调 trigger)")
            elif role == '死士' or role == '潜伏者' or role == '傀儡' or '千面人' in role:
                log.append(f"  → 触发傀儡死亡能力 (需手动调 trigger_puppet)")

    save(s)
    return '\n'.join(log)


def absorb_into_puppet(s, seat, old_role):
    """保险栓吸收: 自己变傀儡 (不告知本人, 玩家仍以为有能力).
    触发后日后该玩家死亡时仍会触发傀儡死亡链 (新弹药)."""
    p = get_p(s, seat)
    p['role'] = '傀儡'
    p['puppet'] = True
    p['register_outsider'] = True
    if old_role == '女伯爵':
        s['has_baron'] = False
    elif old_role == '盾卫':
        s['has_shield'] = False


def trigger_refugee(s):
    """难民触发: 选善良死人变邪恶. 没"每局一次"限制——只受善良死人池约束."""
    good_dead = [int(k) for k, v in s['players'].items()
                 if not v['alive'] and v['team'] != '邪恶'
                 and int(k) not in s['evil_dead_votes']]
    if not good_dead:
        return "没善良死人"
    # 默认随机, master 可指定
    chosen = random.choice(good_dead)
    s['evil_dead_votes'].append(chosen)
    save(s)
    return f"难民触发: {chosen} ({get_p(s, chosen)['name']}) 变邪恶死人"


def trigger_wounded(s, target):
    """伤兵触发: 选活人变傀儡 (target 由 master 指定)"""
    p = get_p(s, target)
    if not p['alive'] or p['team'] == '邪恶':
        return f"无效目标 {target}"
    old = p['role']
    p['role'] = '傀儡'
    p['puppet'] = True
    p['register_outsider'] = True
    if old == '女伯爵': s['has_baron'] = False
    if old == '盾卫': s['has_shield'] = False
    save(s)
    return f"伤兵触发: {target} ({p['name']}) 从 {old} 变傀儡"


def trigger_deserter(s, target):
    """逃兵触发: 杀活人 (target 由 master 指定, 排除恶魔)"""
    p = get_p(s, target)
    if int(target) in s['demon_seats']:
        return f"不能选恶魔 {target}"
    return kill_seat(s, target, '夜杀')


def trigger_captive(s, seat_a, seat_b):
    """俘虏触发 (剧本): 邪恶选 2 名玩家绑定 — 处决其一另一当晚死.
    seat_a, seat_b = 绑定的两名玩家.
    """
    pa = get_p(s, seat_a)
    pb = get_p(s, seat_b)
    if not pa['alive'] or not pb['alive']:
        return f"绑定要求两人都存活"
    s['captive_bound'] = [int(seat_a), int(seat_b)]
    save(s)
    return f"俘虏触发: 绑定 {seat_a} ({pa['name']}) ↔ {seat_b} ({pb['name']})"


def trigger_archer_n1(s, target_seat):
    """暗箭手 N1: 选一名玩家变傀儡 (master 手动调用)"""
    if s.get('demon_role') != '暗箭手':
        return f"非暗箭手局, 无效"
    p = get_p(s, target_seat)
    if not p['alive']:
        return f"无效目标 (已死)"
    p['role'] = '傀儡'
    p['puppet'] = True
    p['register_outsider'] = True
    s['archer_n1_target'] = int(target_seat)
    save(s)
    return f"暗箭手 N1 傀儡: {target_seat} ({p['name']}) 变傀儡 (不告知)"


def trigger_archer_swap(s, evil_seat):
    """暗箭手交换: 与一名邪恶玩家交换角色 (杀首夜目标后)"""
    if s.get('archer_swapped'):
        return "暗箭手交换已用过"
    if int(evil_seat) not in s['evil_seats']:
        return f"{evil_seat} 不是邪恶玩家"
    archer = next((int(k) for k, v in s['players'].items()
                   if v['role'] == '暗箭手' and v['alive']), None)
    if not archer:
        return "找不到暗箭手"
    a_role = get_p(s, archer)['role']
    e_role = get_p(s, evil_seat)['role']
    get_p(s, archer)['role'] = e_role
    get_p(s, evil_seat)['role'] = a_role
    if archer in s['demon_seats']:
        s['demon_seats'].remove(archer)
    s['demon_seats'].append(int(evil_seat))
    s['archer_swapped'] = True
    save(s)
    return f"暗箭手交换: {archer} ({a_role}) ↔ {evil_seat} ({e_role})"


def trigger_hex(s, target_seat):
    """蛊惑者每晚: 选邻座玩家变傀儡 (当晚+明天白天)"""
    hexer = next((int(k) for k, v in s['players'].items()
                  if v['role'] == '蛊惑者' and v['alive']), None)
    if not hexer:
        return "无蛊惑者在场"
    l, r = neighbors(s, hexer)
    if int(target_seat) not in [l, r]:
        return f"{target_seat} 不是 {hexer} 的邻座 (应为 {l} 或 {r})"
    p = get_p(s, target_seat)
    p['is_hexed'] = True
    s['hex_target'] = int(target_seat)
    save(s)
    return f"蛊惑者: {hexer} 蛊惑邻座 {target_seat} ({p['name']}) 当晚+明天白天"


def trigger_mole_dawn(s):
    """内应黎明 (D2 起): 内应 + N1 选定目标双变傀儡"""
    target = s.get('mole_n1_target')
    if not target:
        return "内应 N1 没选过目标"
    mole = next((int(k) for k, v in s['players'].items()
                 if v['original_role'] == '内应' and v['alive']), None)
    if mole and get_p(s, mole)['role'] == '内应':
        get_p(s, mole)['role'] = '傀儡'
        get_p(s, mole)['puppet'] = True
    if get_p(s, target)['alive'] and get_p(s, target)['role'] != '傀儡':
        get_p(s, target)['role'] = '傀儡'
        get_p(s, target)['puppet'] = True
        get_p(s, target)['register_outsider'] = True
    s['mole_n1_target'] = None
    save(s)
    return f"内应黎明: {mole} + {target} 双变傀儡"


def set_mole_n1_target(s, target_seat):
    """N1 内应记录目标 (D2 黎明触发)"""
    s['mole_n1_target'] = int(target_seat)
    save(s)
    return f"内应 N1 记录目标 {target_seat}, D2 黎明双变傀儡"


def trigger_ranger(s, ranger_seat, target_seat):
    """游侠夜死反杀: 选活人, 若非恶魔邪恶则失能并死.
    必须在 ranger 死亡当晚调用 (kill_seat 后).
    """
    rp = get_p(s, ranger_seat)
    if rp['alive']:
        return f"游侠 {ranger_seat} 还活着, 反杀只在夜死时触发"
    if rp['original_role'] != '游侠':
        return f"{ranger_seat} 原角色不是游侠"
    tp = get_p(s, target_seat)
    if not tp['alive']:
        return f"目标 {target_seat} 已死"
    # 必须是非恶魔邪恶 (爪牙)
    if tp['team'] == '邪恶' and not is_demon(tp['role']):
        tp['alive'] = False
        s['deaths'].append([f"N{s['day']}", int(target_seat), f"{tp['role']}(游侠反杀)"])
        save(s)
        return f"游侠反杀: {target_seat} ({tp['role']}) 失能并死亡"
    save(s)
    return f"游侠选了 {target_seat} ({tp['role']}, {tp['team']}) — 不是非恶魔邪恶, 无效"


def trigger_quartermaster(s, target_seat):
    """军需官每天: 公开选 1 名玩家, 若爪牙/外来者则醉酒到下个黎明"""
    qm = next((int(k) for k, v in s['players'].items()
               if v['role'] == '军需官' and v['alive']), None)
    if not qm:
        return "无军需官在场"
    p = get_p(s, target_seat)
    if not p['alive']:
        return f"目标 {target_seat} 已死"
    is_minion_or_outsider = (
        (p['team'] == '邪恶' and not is_demon(p['role'])) or
        p['team'] == '外来者' or
        p.get('register_outsider') or
        p.get('register_minion')
    )
    if is_minion_or_outsider:
        p['is_drunk'] = True
        s['drunk_target'] = int(target_seat)
        save(s)
        return f"军需官 D{s['day']}: 选 {target_seat} ({p['role']}) → 醉酒"
    save(s)
    return f"军需官 D{s['day']}: 选 {target_seat} → 不爪牙/外来 (无效)"


def trigger_conqueror_outsider(s, target_seat):
    """征服者杀外来者触发: 邪恶选一名活人变邪恶 (永久)"""
    p = get_p(s, target_seat)
    if not p['alive']:
        return f"无效目标 {target_seat} (已死)"
    if p['team'] == '邪恶':
        return f"无效目标 {target_seat} (已是邪恶)"
    p['team'] = '邪恶'
    if int(target_seat) not in s['evil_seats']:
        s['evil_seats'].append(int(target_seat))
    p['turned_evil'] = True
    save(s)
    return f"征服者外来者击杀触发: {target_seat} ({p['name']}, {p['role']}) 变邪恶活人"


def trigger_gravedigger(s, gd_seat, dead_seat):
    """掘墓人触发: 选死亡玩家, 自己变成他的角色 (一次性). 继承 original_role."""
    gd = get_p(s, gd_seat)
    target = get_p(s, dead_seat)
    if gd['role'] != '掘墓人':
        return f"{gd_seat} 不是掘墓人 (现在是 {gd['role']})"
    if target['alive']:
        return f"目标 {dead_seat} 必须是死人"
    if s.get('gravedigger_used'):
        return f"掘墓人已用过"
    new_role = target['role']
    gd['role'] = new_role
    # 不改 original_role (牧师查的是 original_role 变化)
    # 触发牧师"角色不再是最初"计数
    s['gravedigger_used'] = True
    save(s)
    return f"掘墓人触发: {gd_seat} ({gd['name']}) 变成 {new_role} (复制 {dead_seat} 的角色)"


def final_judgment(s, evil_about_to_win=True):
    """征服者末日反胜: 邪恶达胜利条件时, 善良闭眼指 2 人, 若 top 2 = 初始邪恶, 善良反胜.

    简化建模:
    - 善良玩家 (alive 或 dead 都参与) 用各自直觉指 2 个嫌疑邪恶
    - 此处用随机 (master 可手动覆盖) - master 应实际推算每个善良玩家的"指认"
    - 统计每个玩家被指次数, 取 top 2
    - 若 top 2 = 初始邪恶 (3 人中至少 2 人) → 善良反胜

    返回: '善良' 或 '邪恶'
    """
    if not s.get('demon_role') == '征服者' and s['demon_role'] != '征服者':
        # 不是征服者, 末日不触发
        return '邪恶' if evil_about_to_win else None

    # 初始邪恶玩家集合
    initial_evil = set()
    for k, p in s['players'].items():
        if p['original_role'] in DEMONS or '千面人' in p['original_role']:
            initial_evil.add(int(k))
        elif p['original_role'] in MINIONS:
            initial_evil.add(int(k))

    # 善良玩家 (基于初始角色判定; 已"变邪恶"的难民/征服者活人不算善良指认者)
    good_voters = [int(k) for k, p in s['players'].items()
                   if p['original_role'] not in DEMONS
                   and p['original_role'] not in MINIONS
                   and '千面人' not in p['original_role']
                   and p.get('team') != '邪恶']  # 排除被难民/征服者 turn 的

    if not good_voters:
        return '邪恶'

    # 简化: 每个善良玩家随机指 2 个非自己玩家
    # 真实场景 master 应基于 reasoner 选, 这里用随机近似
    votes = {}  # seat -> count
    all_players = list(s['players'].keys())
    for voter in good_voters:
        cands = [int(k) for k in all_players if int(k) != voter]
        picks = random.sample(cands, min(2, len(cands)))
        for pick in picks:
            votes[pick] = votes.get(pick, 0) + 1

    # Top 2 by votes
    sorted_votes = sorted(votes.items(), key=lambda x: -x[1])
    top2 = set(s for s, _ in sorted_votes[:2])

    # 若 top 2 都在初始邪恶 → 善良反胜
    if top2 and top2.issubset(initial_evil):
        return '善良'
    return '邪恶'


def trigger_puppet(s, outsider_choice, target=None):
    """傀儡死亡触发: 选一个外来者死亡能力发动. outsider_choice in OUTSIDERS"""
    if outsider_choice == '难民':
        return trigger_refugee(s)
    elif outsider_choice == '伤兵':
        return trigger_wounded(s, target)
    elif outsider_choice == '逃兵':
        return trigger_deserter(s, target)
    elif outsider_choice == '俘虏':
        # target = (seat, role)
        return trigger_captive(s, target[0], target[1])


def info_for(s, seat, role, distorted=False):
    """该角色当前状态下会得到的真信息. distorted=True 给假"""
    p = get_p(s, seat)
    if role == '斥候':
        true_demon = get_p(s, s['demon_seats'][0])['role'] if s['demon_seats'] else None
        if not true_demon: return None
        if s['day'] == 1:
            # v6: N1 学 3 demon (1 真 + 2 伪), 之前是 2 demon
            others = [d for d in DEMONS if d != true_demon]
            fakes = random.sample(others, 2)
            actual = sorted([true_demon] + fakes)
            if distorted:
                # 醉酒/中毒: 3 个非真 demon (确定性)
                return {'declared': sorted(others), 'actual': actual}
            return {'declared': actual, 'actual': actual}
        else:
            if distorted:
                return {'declared': random.choice([d for d in DEMONS if d != true_demon]), 'actual': true_demon}
            return {'declared': true_demon, 'actual': true_demon}

    elif role == '书记官':
        if s['day'] != 1: return None
        register = {int(k) for k, v in s['players'].items()
                    if v['register_outsider'] or v['register_minion']
                    and int(k) != seat}
        actual = sum(register)
        if distorted:
            return {'declared': max(1, actual + random.choice([-3, 3, 5])), 'actual': actual}
        return {'declared': actual, 'actual': actual}

    elif role == '瞭望兵':
        not_in = s['not_in_play_outsiders'] + s['not_in_play_minions']
        if not not_in: return None
        actual = random.choice(not_in)
        if distorted:
            in_play = s['outsiders'] + [get_p(s, ms)['original_role'] for ms in s['minion_seats']]
            return {'declared': random.choice(in_play) if in_play else actual, 'actual': actual}
        return {'declared': actual, 'actual': actual}

    return None


def announce_info(s, seat, role, declared, distorted=False, is_bluff=False):
    """玩家公开 declare 信息. 写入 events"""
    s['events'].append({
        'source': seat,
        'role': role,
        'day': s['day'],
        'declared': declared,
        'distorted': distorted,
        'bluff': is_bluff,
    })
    save(s)


def advance(s, new_phase):
    """推进阶段: N0 -> N1 -> D1 -> N2 -> D2 ..."""
    s['phase'] = new_phase
    if new_phase.startswith('N'):
        try:
            s['day'] = int(new_phase[1:])
        except: pass
    elif new_phase.startswith('D'):
        try:
            s['day'] = int(new_phase[1:])
        except: pass
    # Reset distortion (next day)
    if new_phase.startswith('D'):
        for k, v in s['players'].items():
            v['is_drunk'] = False
            v['is_hexed'] = False
        s['hex_target'] = None
    save(s)
    return f"阶段 → {new_phase} (day={s['day']})"


def public_say(s, seat, content):
    """公开发言"""
    s['public_log'].append({
        'day': s['day'], 'phase': s['phase'], 'seat': seat,
        'name': get_p(s, seat)['name'], 'content': content,
    })
    save(s)


def private_say(s, sender, recipient, content):
    """私聊"""
    s['private_log'].append({
        'day': s['day'], 'phase': s['phase'],
        'from': sender, 'to': recipient, 'content': content,
    })
    save(s)


def check_win(s):
    alive = alive_seats(s)
    demons = [int(k) for k, v in s['players'].items() if v['alive'] and is_demon(v['role'])]
    if not demons: return '善良'
    # 修复模拟器死锁: 善良全死(alive 全是邪恶) → 邪恶胜
    evil_alive = [int(k) for k, v in s['players'].items() if v['alive'] and v['team'] == '邪恶']
    if alive and len(evil_alive) == len(alive):
        # 征服者末日反胜检查
        if s.get('demon_role') == '征服者':
            judgment = final_judgment(s, evil_about_to_win=True)
            return judgment
        return '邪恶'
    if len(alive) <= 2 and demons:
        # 征服者末日反胜检查
        if s.get('demon_role') == '征服者':
            judgment = final_judgment(s, evil_about_to_win=True)
            return judgment
        return '邪恶'
    return None


# CLI
if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)
    cmd = args[0]
    if cmd == 'setup':
        seed = int(args[1]) if len(args) > 1 else None
        s = setup(seed)
        show(s)
    elif cmd == 'state':
        s = load()
        show(s)
    elif cmd == 'kill':
        seat = int(args[1]); method = args[2]
        s = load()
        print(kill_seat(s, seat, method))
    elif cmd == 'info':
        seat = int(args[1]); role = args[2]
        distorted = '--distorted' in args
        s = load()
        result = info_for(s, seat, role, distorted)
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == 'announce':
        seat = int(args[1]); role = args[2]; declared = args[3]
        is_bluff = '--bluff' in args
        s = load()
        # try parse declared as int/list
        try: declared = json.loads(declared)
        except: pass
        announce_info(s, seat, role, declared, is_bluff=is_bluff)
        print('OK')
    elif cmd == 'advance':
        s = load()
        print(advance(s, args[1]))
    elif cmd == 'say':
        seat = int(args[1]); content = ' '.join(args[2:])
        s = load()
        public_say(s, seat, content)
        print('OK')
    elif cmd == 'priv':
        sender = int(args[1]); recipient = int(args[2]); content = ' '.join(args[3:])
        s = load()
        private_say(s, sender, recipient, content)
        print('OK')
    elif cmd == 'check_win':
        s = load()
        print(check_win(s))
    elif cmd == 'trigger':
        s = load()
        sub = args[1]
        if sub == 'refugee': print(trigger_refugee(s))
        elif sub == 'wounded': print(trigger_wounded(s, int(args[2])))
        elif sub == 'deserter': print(trigger_deserter(s, int(args[2])))
        elif sub == 'captive': print(trigger_captive(s, int(args[2]), args[3]))
        elif sub == 'puppet':
            outsider = args[2]
            target = json.loads(args[3]) if len(args) > 3 else None
            print(trigger_puppet(s, outsider, target))
    else:
        print(f"未知命令: {cmd}")
