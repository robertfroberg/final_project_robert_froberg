# tests.py
# this script runs monte carlo combat sims between a parsed pc and a monster

import argparse
import random
import requests

from character_parse import parse_character
from combat_sim import simulate_many_fights
import monster_parse  # use its Monster dataclass + parse_monster_file + get_monster_by_name


# ---------- monster loading helpers ----------

BASE_URL = "https://froberg5.wpcomstaging.com/wp-content/uploads/2025/11/"
FILENAMES = [f"{chr(c)}.txt" for c in range(ord("a"), ord("z") + 1)] + ["animals.txt"]

ALL_MONSTERS = []  # cache of Monster objects


def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def ensure_monsters_loaded():
    """download and parse all monster files once, store in ALL_MONSTERS"""
    global ALL_MONSTERS
    if ALL_MONSTERS:
        return

    print_header("loading monsters from web")

    urls = [BASE_URL + fn for fn in FILENAMES]
    all_monsters = []

    for url in urls:
        try:
            print(f"downloading {url} ...")
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  http {resp.status_code}, skipping.")
                continue

            html = resp.content.decode("utf-8", errors="replace")
            if "stat-block" not in html:
                print("  warning: no 'stat-block' found, skipping.")
                continue

            monsters = monster_parse.parse_monster_file(html)
            print(f"  parsed {len(monsters)} monsters.")
            all_monsters.extend(monsters)

        except Exception as e:
            print(f"  error parsing {url}: {e}")

    ALL_MONSTERS = all_monsters
    print(f"total monsters loaded: {len(ALL_MONSTERS)}")


def get_monster_by_name_from_all(name: str):
    ensure_monsters_loaded()
    m = monster_parse.get_monster_by_name(name, ALL_MONSTERS)
    if m is None:
        raise ValueError(f"monster '{name}' not found")
    return m


def get_random_monster_from_all():
    ensure_monsters_loaded()
    return random.choice(ALL_MONSTERS)


# ---------- loader wrappers ----------

def load_pc(pc_xml):
    """pc_xml is something like 'aeric20.xml' (character_parse will look in data/)"""
    return parse_character(pc_xml)


def load_monster(monster_name):
    """if monster_name is None, pick a random monster from the full list"""
    if monster_name:
        return get_monster_by_name_from_all(monster_name)
    return get_random_monster_from_all()


def print_results(stats, pc, monster):
    print("\n============================================================")
    print("combat setup")
    print("============================================================")
    print(f"pc:      {getattr(pc, 'name', 'PC')}")
    print(f"monster: {getattr(monster, 'name', 'Monster')}")
    print(f"total fights: {stats['total_fights']}")

    # ---------------------------------------------------------
    print("\n============================================================")
    print("wins and losses")
    print("============================================================")
    w = stats["wins"]
    total = stats["total_fights"]
    print(f"pc wins:      {w['pc']} ({w['pc'] / total * 100:.1f}%)")
    print(f"monster wins: {w['monster']} ({w['monster'] / total * 100:.1f}%)")
    print(f"draws:        {w['draw']} ({w['draw'] / total * 100:.1f}%)")

    # ---------------------------------------------------------
    print("\n============================================================")
    print("initiative results")
    print("============================================================")
    init = stats["init_wins"]
    print(f"pc wins init:      {init['pc']} ({init['pc'] / total * 100:.1f}%)")
    print(f"monster wins init: {init['monster']} ({init['monster'] / total * 100:.1f}%)")

    # ---------------------------------------------------------
    print("\n============================================================")
    print("hits and misses")
    print("============================================================")
    hits = stats["hits"]
    misses = stats["misses"]
    for side in ("pc", "monster"):
        total_att = hits[side] + misses[side]
        print(f"{side} total attacks: {total_att}")
        print(f"  hits:   {hits[side]}")
        print(f"  misses: {misses[side]}")
        if total_att > 0:
            print(f"  hit rate: {hits[side] / total_att * 100:.1f}%")
        else:
            print(f"  hit rate: n/a")

    # ---------------------------------------------------------
    print("\n============================================================")
    print("per-fight averages")
    print("============================================================")
    avg_atk = stats["avg_attacks_per_fight"]
    avg_hit = stats["avg_hits_per_fight"]
    avg_miss = stats["avg_misses_per_fight"]
    avg_rate = stats["avg_hit_rate_per_fight"]

    for side in ("pc", "monster"):
        print(f"\n{side}:")
        print(f"  avg attacks per fight: {avg_atk[side]:.2f}")
        print(f"  avg hits per fight:    {avg_hit[side]:.2f}")
        print(f"  avg misses per fight:  {avg_miss[side]:.2f}")
        print(f"  avg hit rate per fight: {avg_rate[side]:.2f}%")

    # ---------------------------------------------------------
    print("\n============================================================")
    print("rounds per fight")
    print("============================================================")
    print(f"average rounds: {stats['avg_rounds']:.2f}")

    # ---------------------------------------------------------
    print("\n============================================================")
    print("average damage by attack")
    print("============================================================")
    dmg = stats["avg_damage_per_attack"]

    pc_attacks = [(name, val) for ((side, name), val) in dmg.items() if side == "pc"]
    mon_attacks = [(name, val) for ((side, name), val) in dmg.items() if side == "monster"]

    print("\npc attacks:")
    if pc_attacks:
        for name, val in sorted(pc_attacks):
            print(f"  {name}: {val:.2f} avg damage (on attacks that dealt damage)")
    else:
        print("  none")

    print("\nmonster attacks:")
    if mon_attacks:
        for name, val in sorted(mon_attacks):
            print(f"  {name}: {val:.2f} avg damage (on attacks that dealt damage)")
    else:
        print("  none")

    print()


# ---------- summary printing ----------

def print_summary(pc, monster, stats):
    # unpack core stats
    total_fights = stats["total_fights"]
    wins = stats["wins"]
    init_wins = stats["init_wins"]
    hits = stats["hits"]
    misses = stats["misses"]
    avg_rounds = stats["avg_rounds"]
    avg_damage_per_attack = stats["avg_damage_per_attack"]

    # new per-fight averages
    avg_attacks_per_fight = stats.get("avg_attacks_per_fight", {})
    avg_hits_per_fight = stats.get("avg_hits_per_fight", {})
    avg_misses_per_fight = stats.get("avg_misses_per_fight", {})
    avg_hit_rate_per_fight = stats.get("avg_hit_rate_per_fight", {})

    pc_name = getattr(pc, "name", "PC")
    monster_name = getattr(monster, "name", "Monster")

    print_header("combat setup")
    print(f"pc:      {pc_name}")
    print(f"monster: {monster_name}")
    print(f"total fights: {total_fights}")

    print_header("wins and losses")
    pc_wins = wins.get("pc", 0)
    monster_wins = wins.get("monster", 0)
    draws = wins.get("draw", 0)

    if total_fights > 0:
        pc_win_rate = pc_wins / total_fights * 100.0
        monster_win_rate = monster_wins / total_fights * 100.0
        draw_rate = draws / total_fights * 100.0
    else:
        pc_win_rate = monster_win_rate = draw_rate = 0.0

    print(f"pc wins:      {pc_wins} ({pc_win_rate:.1f}%)")
    print(f"monster wins: {monster_wins} ({monster_win_rate:.1f}%)")
    print(f"draws:        {draws} ({draw_rate:.1f}%)")

    print_header("initiative results")
    pc_init_wins = init_wins.get("pc", 0)
    monster_init_wins = init_wins.get("monster", 0)
    total_inits = pc_init_wins + monster_init_wins
    if total_inits > 0:
        pc_init_rate = pc_init_wins / total_inits * 100.0
        monster_init_rate = monster_init_wins / total_inits * 100.0
    else:
        pc_init_rate = monster_init_rate = 0.0

    print(f"pc wins init:      {pc_init_wins} ({pc_init_rate:.1f}%)")
    print(f"monster wins init: {monster_init_wins} ({monster_init_rate:.1f}%)")

    print_header("hits and misses (global totals)")
    for side_label, label_name in (("pc", "pc"), ("monster", "monster")):
        side_hits = hits.get(side_label, 0)
        side_misses = misses.get(side_label, 0)
        total_attacks = side_hits + side_misses
        if total_attacks > 0:
            hit_rate = side_hits / total_attacks * 100.0
        else:
            hit_rate = 0.0
        print(f"{label_name} total attacks: {total_attacks}")
        print(f"  hits:   {side_hits}")
        print(f"  misses: {side_misses}")
        print(f"  hit rate: {hit_rate:.1f}%")

    print_header("per-fight averages")
    for side in ("pc", "monster"):
        atks = avg_attacks_per_fight.get(side, 0.0)
        h = avg_hits_per_fight.get(side, 0.0)
        m = avg_misses_per_fight.get(side, 0.0)
        hr = avg_hit_rate_per_fight.get(side, 0.0)
        print(f"{side}:")
        print(f"  avg attacks per fight: {atks:.2f}")
        print(f"  avg hits per fight:    {h:.2f}")
        print(f"  avg misses per fight:  {m:.2f}")
        print(f"  avg hit rate per fight:{hr:6.2f}%")

    print_header("rounds per fight")
    print(f"average rounds: {avg_rounds:.2f}")

    print_header("average damage by attack")
    print("\npc attacks:")
    for (side, attack_name), avg_dmg in sorted(avg_damage_per_attack.items()):
        if side != "pc":
            continue
        print(f"  {attack_name}: {avg_dmg:.2f} avg damage (on attacks that dealt damage)")

    print("\nmonster attacks:")
    for (side, attack_name), avg_dmg in sorted(avg_damage_per_attack.items()):
        if side != "monster":
            continue
        print(f"  {attack_name}: {avg_dmg:.2f} avg damage (on attacks that dealt damage)")


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(description="run monte carlo combat sim")
    parser.add_argument("pc_xml", help="PC XML file located in data/")
    parser.add_argument("-m", "--monster-name", default=None)
    parser.add_argument("-n", "--num-fights", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    print_header("loading pc and monster")

    pc = load_pc(args.pc_xml)
    print(f"loaded pc: {getattr(pc, 'name', 'PC')}")

    monster = load_monster(args.monster_name)
    print(f"loaded monster: {getattr(monster, 'name', 'Monster')}")

    print_header("running simulation")
    print(f"simulating {args.num_fights} fights...")
    stats = simulate_many_fights(pc, monster, n_fights=args.num_fights, seed=args.seed)

    print_summary(pc, monster, stats)


# ============================================================
# Optional visualization support (visualize_outcomes.py)
# ============================================================

def attempt_visualization(pc, monster, args):
    """
    If --visualize is passed, this function calls visualize_outcomes.py
    internally to generate all figures.
    """
    if not args.visualize:
        return

    print("\n============================================================")
    print("running visualization tools")
    print("============================================================")

    try:
        import visualize_outcomes as viz

        # run analysis using same number of fights and seed
        stats, fights = viz.run_fights_for_analysis(
            pc,
            monster,
            n_fights=args.num_fights,
            seed=args.seed
        )

        # call plotting functions
        outdir = args.outdir or "figs"
        prefix = args.prefix or "analysis"

        viz.ensure_output_dir(outdir)

        viz.plot_win_distribution(stats, prefix, outdir)
        viz.plot_hits_misses_totals(stats, prefix, outdir)
        viz.plot_per_fight_averages(stats, prefix, outdir)
        viz.plot_rounds_hist(fights, prefix, outdir)
        viz.plot_initiative_vs_outcome(fights, prefix, outdir)
        viz.plot_damage_per_attack(stats, prefix, outdir)
        viz.plot_damage_per_fight_hist(fights, prefix, outdir)

        print(f"visualizations saved in: {outdir}")
        print("opening windows...")
        import matplotlib.pyplot as plt
        plt.show()

    except ImportError as e:
        print("visualization module not found: visualize_outcomes.py not in project?")
        print("error detail:", e)
    except Exception as e:
        print("error during visualization:")
        print(e)


# ============================================================
# Modify the CLI parser to accept visualization flags
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="combat simulation test driver")
    parser.add_argument("pc_xml", help="PC xml filename (in data/)")
    parser.add_argument("-m", "--monster-name", default=None, help="monster name (exact match) or None for random")
    parser.add_argument("-n", "--num-fights", type=int, default=1000, help="number of Monte Carlo fights to run")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--visualize", action="store_true", help="run charts/plots from visualize_outcomes.py")
    parser.add_argument("--outdir", default="figs", help="output folder for charts")
    parser.add_argument("--prefix", default="analysis", help="filename prefix for charts")
    args = parser.parse_args()

    # existing loading logic
    print("loading pc/monster...")
    pc = load_pc(args.pc_xml)
    monster = load_monster(args.monster_name)

    # run your core simulation
    stats = simulate_many_fights(pc, monster, n_fights=args.num_fights, seed=args.seed)

    # print results
    print_results(stats, pc, monster)

    # call visualization tree
    attempt_visualization(pc, monster, args)