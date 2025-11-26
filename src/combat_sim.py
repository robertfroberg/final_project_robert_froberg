# combat_sim.py
# recharge mechanics per-fight averages and simulation loops
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# dice helpers
def roll_d20(rng: Optional[random.Random] = None) -> int:
    rng = rng or random
    return rng.randint(1, 20)


# roll damage for expressions like 2d6, d12, 1d10+4
def roll_dice_expr(expr: str, rng: Optional[random.Random] = None, times: int = 1) -> int:
    rng = rng or random
    if not expr:
        return 0

    expr = expr.strip().lower().replace(" ", "")
    if expr.startswith("d"):
        expr = "1" + expr

    mod = 0
    if "+" in expr:
        dice_part, mod_part = expr.split("+", 1)
        try:
            mod = int(mod_part)
        except:
            mod = 0
    elif "-" in expr[1:]:
        dice_part, mod_part = expr.split("-", 1)
        try:
            mod = -int(mod_part)
        except:
            mod = 0
    else:
        dice_part = expr

    try:
        n_str, s_str = dice_part.split("d")
        n = int(n_str or "1")
        s = int(s_str)
    except:
        return 0

    n *= times
    total = 0
    for _ in range(n):
        total += rng.randint(1, s)
    total += mod
    return total


# ability recharge logic
def get_recharge_threshold(recharge: str) -> int:
    """
    '5–6' → 5
    '6'   → 6
    """
    if not recharge:
        return 6

    text = recharge.replace("–", "-")
    parts = [p for p in text.split("-") if p.strip().isdigit()]
    if parts:
        return int(parts[0])

    for ch in text:
        if ch.isdigit():
            return int(ch)

    return 6

# roll recharge for all actions that have recharge and are on cooldown
def refresh_recharge_actions(creature: Any, rng: Optional[random.Random] = None) -> None:
    rng = rng or random
    actions = getattr(creature, "actions", [])
    for action in actions:
        recharge = getattr(action, "recharge", None)
        if not recharge:
            continue
        if not getattr(action, "_on_cooldown", False):
            continue

        threshold = get_recharge_threshold(recharge)
        roll = rng.randint(1, 6)
        if roll >= threshold:
            action._on_cooldown = False


def mark_recharge_used(action: Any) -> None:
    if getattr(action, "recharge", None):
        action._on_cooldown = True


# helpers for AC, HP, saves, resistance
def get_initiative_bonus(creature: Any) -> int:
    for attr in ("init_bonus", "initiative_bonus", "initiative"):
        if hasattr(creature, attr):
            try:
                return int(getattr(creature, attr))
            except:
                pass

    dex_score = None
    for attr in ("dex", "DEX", "dexterity", "DEX_score"):
        if hasattr(creature, attr):
            dex_score = getattr(creature, attr)
            break

    try:
        dex_score = int(str(dex_score).replace("+", ""))
        return (dex_score - 10) // 2
    except:
        return 0


def get_ac(creature: Any) -> int:
    for attr in ("ac", "armor_class"):
        if hasattr(creature, attr):
            try:
                return int(getattr(creature, attr))
            except:
                pass
    raise AttributeError("Creature has no AC")


def get_max_hp(creature: Any) -> int:
    for attr in ("max_hp", "hp", "HP"):
        if hasattr(creature, attr):
            try:
                return int(getattr(creature, attr))
            except:
                pass
    raise AttributeError("Creature has no HP")


def get_resistances(creature: Any) -> List[str]:
    for attr in ("resistances", "damage_resistances"):
        if hasattr(creature, attr):
            val = getattr(creature, attr)
            if isinstance(val, str):
                return [v.strip().lower() for v in val.split(",") if v.strip()]
            if isinstance(val, list):
                return [v.strip().lower() for v in val]
    return []


def get_immunities(creature: Any) -> List[str]:
    for attr in ("immunities", "damage_immunities"):
        if hasattr(creature, attr):
            val = getattr(creature, attr)
            if isinstance(val, str):
                return [v.strip().lower() for v in val.split(",") if v.strip()]
            if isinstance(val, list):
                return [v.strip().lower() for v in val]
    return []


def damage_after_resistance(creature: Any, dmg: int, dtype: str) -> int:
    if dmg <= 0:
        return 0
    dtype = (dtype or "").lower()

    if any(t in dtype for t in get_immunities(creature)):
        return 0
    if any(t in dtype for t in get_resistances(creature)):
        return max(dmg // 2, 0)
    return dmg


def get_save_mod(creature: Any, ability: str) -> int:
    if not ability:
        return 0
    abbr = ability.upper()[:3]

    # explicit saves dict PC
    if hasattr(creature, "saves"):
        saves = getattr(creature, "saves")
        for key in (ability.upper(), abbr, ability.title(), abbr.title()):
            if key in saves:
                try:
                    return int(saves[key])
                except:
                    pass

    # monster format STR_save etc
    attr_names = [f"{abbr}_save", f"{abbr.lower()}_save"]
    for attr in attr_names:
        if hasattr(creature, attr):
            try:
                return int(str(getattr(creature, attr)).replace("+", ""))
            except:
                pass

    # fallback use ability score
    for attr in (abbr, abbr.lower(), f"{abbr}_score"):
        if hasattr(creature, attr):
            try:
                score = int(str(getattr(creature, attr)).replace("+", ""))
                return (score - 10) // 2
            except:
                pass

    return 0


# attack selection for PC and monster
def get_pc_attacks_for_turn(pc: Any) -> List[Any]:
    attacks = getattr(pc, "attacks", [])
    if not attacks:
        return []

    primary = attacks[0]
    return [primary]


def get_monster_attacks_for_turn(monster: Any) -> List[Any]:
    usable = []
    for a in getattr(monster, "actions", []):
        if a.attack_bonus is not None or a.save_dc is not None:
            if getattr(a, "recharge", None) and getattr(a, "_on_cooldown", False):
                continue
            usable.append(a)
    return usable


# attack resolution
def resolve_attack_roll(attacker, defender, attack, rng=None, attacker_label="") -> Dict[str, Any]:
    rng = rng or random

    try:
        to_hit = int(getattr(attack, "to_hit", getattr(attack, "attack_bonus", 0)))
    except:
        to_hit = 0

    damage_dice = getattr(attack, "damage_dice", "")
    damage_bonus = getattr(attack, "damage_bonus", 0)
    damage_type = getattr(attack, "damage_type", "")

    d20 = roll_d20(rng)
    crit = d20 == 20
    auto_miss = d20 == 1

    defender_ac = get_ac(defender)

    if auto_miss:
        hit = False
    else:
        total = d20 + to_hit
        hit = crit or total >= defender_ac

    raw_damage = 0
    if hit:
        times = 2 if crit else 1
        raw_damage = roll_dice_expr(damage_dice, rng=rng, times=times)
        raw_damage += int(damage_bonus)

    final_damage = damage_after_resistance(defender, raw_damage, damage_type)
    mark_recharge_used(attack)

    return {
        "kind": "attack_roll",
        "attacker": attacker_label,
        "attack_name": getattr(attack, "name", "attack"),
        "d20": d20,
        "crit": crit,
        "hit": hit,
        "raw_damage": raw_damage,
        "final_damage": final_damage,
        "damage_type": damage_type,
    }


# resolve if the target needs to make a saving throw
def resolve_save_attack(attacker, defender, action, rng=None, attacker_label="") -> Dict[str, Any]:
    rng = rng or random

    # extract save information from action
    save_ability = getattr(action, "save_ability", None)
    try:
        save_dc = int(getattr(action, "save_dc", None))
    except:
        save_dc = None

    # if action does not require saving throw treat as normal attack
    if save_dc is None or not save_ability:
        return resolve_attack_roll(attacker, defender, action, rng, attacker_label)

    # pull damage and behavior flags from action
    damage_dice = getattr(action, "damage_dice", "")
    dtype = getattr(action, "damage_type", "")
    half_on_success = bool(getattr(action, "half_on_success", False))

    # defender attempts save
    d20 = roll_d20(rng)
    save_mod = get_save_mod(defender, save_ability)
    total_save = d20 + save_mod
    success = total_save >= save_dc
    hit = not success

    # compute base damage from dice
    dmg = roll_dice_expr(damage_dice, rng=rng)

    # apply half damage on success or no damage on success logic
    if success:
        dmg = dmg // 2 if half_on_success else 0

    # apply defender resistances or vulnerabilities
    final_damage = damage_after_resistance(defender, dmg, dtype)

    # if this action uses recharge mechanics expend
    mark_recharge_used(action)

    # return result dictionary
    return {
        "kind": "save",
        "attacker": attacker_label,
        "attack_name": getattr(action, "name", "save effect"),
        "d20": d20,
        "save_mod": save_mod,
        "total_save": total_save,
        "save_dc": save_dc,
        "success": success,
        "hit": hit,
        "raw_damage": dmg,
        "final_damage": final_damage,
        "damage_type": dtype,
    }


# take offensive action
def resolve_offensive_action(attacker, defender, action, rng=None, attacker_label=""):
    if getattr(action, "save_dc", None) is not None and getattr(action, "save_ability", None):
        return resolve_save_attack(attacker, defender, action, rng, attacker_label)
    return resolve_attack_roll(attacker, defender, action, rng, attacker_label)


# roll initiative
def roll_initiative(pc, monster, rng=None) -> Tuple[str, int, int]:
    rng = rng or random
    pc_init = roll_d20(rng) + get_initiative_bonus(pc)
    m_init = roll_d20(rng) + get_initiative_bonus(monster)
    return ("pc" if pc_init > m_init else "monster", pc_init, m_init)


# one fight logic
def simulate_single_fight(
    pc: Any,
    monster: Any,
    rng: Optional[random.Random] = None,
    max_rounds: int = 1000,
) -> Dict[str, Any]:

    rng = rng or random

    # get each combatants starting hit points
    pc_hp = get_max_hp(pc)
    m_hp = get_max_hp(monster)

    # determine initiative
    order, pc_init, m_init = roll_initiative(pc, monster, rng)

    rounds = 0
    winner = None

    # counters for hits and misses
    hits = {"pc": 0, "monster": 0}
    misses = {"pc": 0, "monster": 0}

    # track damage grouped by attacker, attack name
    dmg_by_name: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    # main combat loop
    while pc_hp > 0 and m_hp > 0 and rounds < max_rounds:
        rounds += 1

        # create ordered list of who won init
        turn_order = ["pc", "monster"] if order == "pc" else ["monster", "pc"]

        # each participant takes a turn
        for acting in turn_order:
            if pc_hp <= 0 or m_hp <= 0:
                break

            # set attacker/defender references for turn
            if acting == "pc":
                attacker = pc
                defender = monster
                defender_hp = m_hp
                refresh_recharge_actions(pc, rng)
                attacks = get_pc_attacks_for_turn(pc)
            else:
                attacker = monster
                defender = pc
                defender_hp = pc_hp
                refresh_recharge_actions(monster, rng)
                attacks = get_monster_attacks_for_turn(monster)

            # execute each attack available
            for action in attacks:
                if defender_hp <= 0:
                    break

                r = resolve_offensive_action(attacker, defender, action, rng, acting)

                # track hit/miss outcome
                if r["hit"]:
                    hits[acting] += 1
                else:
                    misses[acting] += 1

                # apply damage from action
                dmg = r["final_damage"]
                if dmg > 0:
                    dmg_by_name[(acting, r["attack_name"])].append(dmg)

                defender_hp -= dmg

                # write updated HP back to correct combatant
                if acting == "pc":
                    m_hp = defender_hp
                else:
                    pc_hp = defender_hp

                # check for end of fight
                if defender_hp <= 0:
                    winner = acting
                    break

        if winner:
            break

    # if neither combatant won call it a draw - should not happen but here for troubleshooting
    if not winner:
        winner = "draw"

    # return aggregated summary of fight
    return {
        "winner": winner,
        "rounds": rounds,
        "pc_init": pc_init,
        "monster_init": m_init,
        "hits": hits,
        "misses": misses,
        "attack_damage_by_name": dmg_by_name,
    }


# monte carlo sim logic
def simulate_many_fights(
    pc: Any,
    monster: Any,
    n_fights: int = 1000,
    seed: Optional[int] = None,
) -> Dict[str, Any]:

    rng = random.Random(seed) if seed is not None else random

    wins = {"pc": 0, "monster": 0, "draw": 0}
    init_wins = {"pc": 0, "monster": 0}
    hits = {"pc": 0, "monster": 0}
    misses = {"pc": 0, "monster": 0}
    total_rounds = 0
    dmg_samples: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    # per-fight aggregates
    sum_atks = {"pc": 0, "monster": 0}
    sum_hits = {"pc": 0, "monster": 0}
    sum_misses = {"pc": 0, "monster": 0}
    sum_hit_rate = {"pc": 0.0, "monster": 0.0}

    for _ in range(n_fights):
        r = simulate_single_fight(pc, monster, rng)

        # winner
        wins[r["winner"]] += 1

        # initiative
        if r["pc_init"] > r["monster_init"]:
            init_wins["pc"] += 1
        else:
            init_wins["monster"] += 1

        total_rounds += r["rounds"]

        # hits/misses
        for side in ("pc", "monster"):
            h = r["hits"][side]
            m = r["misses"][side]
            a = h + m

            hits[side] += h
            misses[side] += m

            sum_atks[side] += a
            sum_hits[side] += h
            sum_misses[side] += m
            if a > 0:
                sum_hit_rate[side] += h / a

        # damage samples
        for key, vals in r["attack_damage_by_name"].items():
            dmg_samples[key].extend(vals)

    avg_dmg_per_attack = {
        k: (sum(v) / len(v) if v else 0.0)
        for k, v in dmg_samples.items()
    }

    avg_rounds = total_rounds / n_fights if n_fights else 0.0

    if n_fights > 0:
        avg_atks = {s: sum_atks[s] / n_fights for s in ("pc", "monster")}
        avg_hit = {s: sum_hits[s] / n_fights for s in ("pc", "monster")}
        avg_miss = {s: sum_misses[s] / n_fights for s in ("pc", "monster")}
        avg_rate = {s: (sum_hit_rate[s] / n_fights) * 100.0 for s in ("pc", "monster")}
    else:
        avg_atks = {"pc": 0, "monster": 0}
        avg_hit = {"pc": 0, "monster": 0}
        avg_miss = {"pc": 0, "monster": 0}
        avg_rate = {"pc": 0, "monster": 0}

    return {
        "total_fights": n_fights,
        "wins": wins,
        "init_wins": init_wins,
        "hits": hits,
        "misses": misses,
        "avg_rounds": avg_rounds,
        "avg_damage_per_attack": avg_dmg_per_attack,
        "avg_attacks_per_fight": avg_atks,
        "avg_hits_per_fight": avg_hit,
        "avg_misses_per_fight": avg_miss,
        "avg_hit_rate_per_fight": avg_rate,
    }