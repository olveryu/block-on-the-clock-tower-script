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

TOWNSFOLK = ['斥候', '密探', '巡逻兵', '审讯官', '游侠', '军医',
             '书记官', '军需官', '牧师', '纹章官', '盾卫', '女伯爵', '瞭望兵']
OUTSIDERS = ['伤兵', '逃兵', '难民', '俘虏']
MINIONS = ['内应', '蛊惑者', '叛将', '死士']
DEMONS = ['攻城将军', '先锋官', '千面人', '暗箭手']
INFO_SOURCES = {'斥候', '密探', '巡逻兵', '审讯官', '书记官', '纹章官', '瞭望兵', '军医', '牧师'}
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
    elif demon == '先锋官' or '叛将' in minions_raw:
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
        'refugee_used': False,
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

        state['players'][str(i)] = {
            'seat': i,
            'name': p,
            'role': r,
            'original_role': r,
            'team': team,
            'alive': True,
            'is_drunk': False,
            'is_hexed': False,
            'register_outsider': r in outsiders or r == '死士' or '千面人' in r,
            'register_minion': is_m or r == '死士' or '千面人' in r,
            'bluff_role': bluff,
            'claimed_role': bluff if team == '邪恶' else r,
            'puppet': False,
        }

        if team == '邪恶':
            state['evil_seats'].append(i)
        if r == '死士':
            state['dead_man_seat'] = i
            state['dead_man_active'] = True
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
    print(f"难民已用: {s['refugee_used']}, 邪恶死人变票: {s['evil_dead_votes']}")
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

    # 死士复活栈
    if is_demon(p['role']) and s['dead_man_active']:
        if s['dead_man_seat'] and get_p(s, s['dead_man_seat'])['alive']:
            old = get_p(s, s['dead_man_seat'])['role']
            new = p['original_role']
            get_p(s, s['dead_man_seat'])['role'] = new
            get_p(s, s['dead_man_seat'])['team'] = '邪恶'
            s['demon_seats'].append(s['dead_man_seat'])
            s['dead_man_active'] = False
            log.append(f"  ★ 死士复活: {s['dead_man_seat']} 从 {old} 变 {new}")

    # 触发死亡链 (v6 机制: 保险栓吸收而不是阻止)
    role = p['role']
    triggers_chain = (role in OUTSIDERS or role == '死士'
                      or role == '傀儡' or '千面人' in role)
    absorbed = False
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
            elif role == '死士' or role == '傀儡' or '千面人' in role:
                log.append(f"  → 触发傀儡死亡能力 (需手动调 trigger_puppet)")
            # 先锋官 setup: 外来者"视为傀儡"只是 register, 不触发 (剧本没明说触发)

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
    """难民触发: 选善良死人变邪恶"""
    if s['refugee_used']:
        return "难民已用"
    good_dead = [int(k) for k, v in s['players'].items()
                 if not v['alive'] and v['team'] != '邪恶'
                 and int(k) not in s['evil_dead_votes']]
    if not good_dead:
        return "没善良死人"
    # 默认随机, master 可指定
    chosen = random.choice(good_dead)
    s['evil_dead_votes'].append(chosen)
    s['refugee_used'] = True
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


def trigger_captive(s, target_seat, madness_role):
    """俘虏触发 (剧本): 邪恶选活人 + 不在场善良角色, 该玩家"疯狂"声称是该角色, 否则 storyteller 可处决.
    "疯狂" = BotC 标准 Madness 机制:
      - 玩家被告知必须装该角色
      - 必须公开/私下都坚持声称
      - 如果违反, storyteller 可执行处决 (任意时候)
    target_seat = 选的活人 (善良), madness_role = 不在场善良角色名.
    """
    p = get_p(s, target_seat)
    if not p['alive'] or p['team'] == '邪恶':
        return f"无效目标 {target_seat}"
    p['madness_role'] = madness_role
    p['madness_violated'] = False  # storyteller 跟踪是否违反
    save(s)
    return (f"俘虏触发: {target_seat} ({p['name']}) 被强制'疯狂'装 {madness_role}, "
            f"否则 storyteller 可处决")


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
    if len(alive) <= 2 and demons: return '邪恶'
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
