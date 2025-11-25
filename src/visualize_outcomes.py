# visual_analysis.py
# create charts/graphics to tell the story of the combat sim

import argparse
import os
import random
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import requests

from character_parse import parse_character
import monster_parse
from combat_sim import simulate_single_fight

# ---------- monster loading helpers (same pattern as tests.py) ----------

BASE_URL = "https://froberg5.wpcomstaging.com/wp-content/uploads/2025/11/"
FILENAMES = [f"{chr(c)}.txt" for c in range(ord("a"), ord("z") + 1)] + ["animals.txt"]

ALL_MONSTERS: List[Any] = []  # cache of Monster objects


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def ensure_monsters_loaded() -> None:
    """download and parse all monster files once, store in ALL_MONSTERS"""
    global ALL_MONSTERS
    if ALL_MONSTERS:
        return

    print_header("loading monsters from web (visual_analysis)")

    urls = [BASE_URL + fn for fn in FILENAMES]
    all_monsters: List[Any] = []

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


def get_monster_by_name_from_all(name: str) -> Any:
    ensure_monsters_loaded()
    m = monster_parse.get_monster_by_name(name, ALL_MONSTERS)
    if m is None:
        raise ValueError(f"monster '{name}' not found")
    return m


def get_random_monster_from_all() -> Any:
    ensure_monsters_loaded()
    return random.choice(ALL_MONSTERS)


def load_pc(pc_xml: str) -> Any:
    """pc_xml is something like 'aeric20.xml' (character_parse will look in data/)"""
    return parse_character(pc_xml)


def load_monster(monster_name: str | None) -> Any:
    """if monster_name is None, pick a random monster from the full list"""
    if monster_name:
        return get_monster_by_name_from_all(monster_name)
    return get_random_monster_from_all()


# ---------- simulate fights and build stats for analysis ----------

def run_fights_for_analysis(
    pc: Any,
    monster: Any,
    n_fights: int,
    seed: int | None = None,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    run n_fights single-fight simulations and build a stats dict
    plus return the list of per-fight results (for histograms, etc.)

    stats dict is similar to combat_sim.simulate_many_fights but computed here
    so all plots use the same sample.
    """
    rng = random.Random(seed) if seed is not None else random.Random()

    fights: List[Dict[str, Any]] = []

    wins = {"pc": 0, "monster": 0, "draw": 0}
    init_wins = {"pc": 0, "monster": 0}
    hits = {"pc": 0, "monster": 0}
    misses = {"pc": 0, "monster": 0}
    total_rounds = 0

    damage_samples: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    # per-fight aggregates
    sum_attacks_per_fight = {"pc": 0, "monster": 0}
    sum_hits_per_fight = {"pc": 0, "monster": 0}
    sum_misses_per_fight = {"pc": 0, "monster": 0}
    sum_hit_rate_per_fight = {"pc": 0.0, "monster": 0.0}

    for _ in range(n_fights):
        result = simulate_single_fight(pc, monster, rng=rng)
        fights.append(result)

        winner = result["winner"]
        wins[winner] += 1

        # initiative wins (pc > monster, else monster wins ties)
        if result["pc_init"] > result["monster_init"]:
            init_wins["pc"] += 1
        else:
            init_wins["monster"] += 1

        total_rounds += result["rounds"]

        # hits/misses and per-fight stats
        for side in ("pc", "monster"):
            side_hits = result["hits"].get(side, 0)
            side_misses = result["misses"].get(side, 0)
            side_attacks = side_hits + side_misses

            hits[side] += side_hits
            misses[side] += side_misses

            sum_attacks_per_fight[side] += side_attacks
            sum_hits_per_fight[side] += side_hits
            sum_misses_per_fight[side] += side_misses
            if side_attacks > 0:
                sum_hit_rate_per_fight[side] += side_hits / side_attacks

        # damage by attack name
        for key, samples in result["attack_damage_by_name"].items():
            damage_samples[key].extend(samples)

    # aggregate stats
    avg_damage_per_attack = {
        key: (sum(vals) / len(vals) if vals else 0.0)
        for key, vals in damage_samples.items()
    }

    if n_fights > 0:
        avg_rounds = total_rounds / n_fights
        avg_attacks_per_fight = {
            side: sum_attacks_per_fight[side] / n_fights for side in ("pc", "monster")
        }
        avg_hits_per_fight = {
            side: sum_hits_per_fight[side] / n_fights for side in ("pc", "monster")
        }
        avg_misses_per_fight = {
            side: sum_misses_per_fight[side] / n_fights for side in ("pc", "monster")
        }
        avg_hit_rate_per_fight = {
            side: (sum_hit_rate_per_fight[side] / n_fights * 100.0)
            for side in ("pc", "monster")
        }
    else:
        avg_rounds = 0.0
        avg_attacks_per_fight = {"pc": 0.0, "monster": 0.0}
        avg_hits_per_fight = {"pc": 0.0, "monster": 0.0}
        avg_misses_per_fight = {"pc": 0.0, "monster": 0.0}
        avg_hit_rate_per_fight = {"pc": 0.0, "monster": 0.0}

    stats = {
        "total_fights": n_fights,
        "wins": wins,
        "init_wins": init_wins,
        "hits": hits,
        "misses": misses,
        "avg_rounds": avg_rounds,
        "avg_damage_per_attack": avg_damage_per_attack,
        "avg_attacks_per_fight": avg_attacks_per_fight,
        "avg_hits_per_fight": avg_hits_per_fight,
        "avg_misses_per_fight": avg_misses_per_fight,
        "avg_hit_rate_per_fight": avg_hit_rate_per_fight,
    }

    return stats, fights


# ---------- helper to compute per-fight damage totals ----------

def compute_total_damage_by_side_for_fight(result: Dict[str, Any]) -> Dict[str, int]:
    """
    given a single fight result from simulate_single_fight, compute total damage
    dealt by pc and monster in that fight (summing all attack_damage_by_name).
    """
    totals = {"pc": 0, "monster": 0}
    for (side, _attack_name), samples in result["attack_damage_by_name"].items():
        totals[side] += sum(samples)
    return totals


# ---------- plotting functions ----------

def ensure_output_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def plot_win_distribution(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    wins = stats["wins"]
    labels = ["pc wins", "monster wins", "draws"]
    values = [wins.get("pc", 0), wins.get("monster", 0), wins.get("draw", 0)]

    plt.figure()
    plt.bar(labels, values)
    plt.title("win distribution")
    plt.ylabel("count of fights")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_win_distribution.png"), dpi=150)


def plot_hits_misses_totals(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    hits = stats["hits"]
    misses = stats["misses"]

    labels = ["pc", "monster"]
    hits_vals = [hits["pc"], hits["monster"]]
    miss_vals = [misses["pc"], misses["monster"]]

    x = range(len(labels))
    width = 0.35

    plt.figure()
    plt.bar([i - width / 2 for i in x], hits_vals, width=width, label="hits")
    plt.bar([i + width / 2 for i in x], miss_vals, width=width, label="misses")
    plt.xticks(list(x), labels)
    plt.ylabel("total attacks over all fights")
    plt.title("hits vs misses (global totals)")
    plt.legend()
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_hits_misses_totals.png"), dpi=150)


def plot_per_fight_averages(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    avg_attacks = stats["avg_attacks_per_fight"]
    avg_hits = stats["avg_hits_per_fight"]
    avg_misses = stats["avg_misses_per_fight"]
    avg_hit_rate = stats["avg_hit_rate_per_fight"]

    labels = ["pc", "monster"]
    x = range(len(labels))
    width = 0.2

    plt.figure()
    plt.bar([i - width for i in x], [avg_attacks[s] for s in labels], width=width, label="attacks/fight")
    plt.bar([i for i in x], [avg_hits[s] for s in labels], width=width, label="hits/fight")
    plt.bar([i + width for i in x], [avg_misses[s] for s in labels], width=width, label="misses/fight")
    plt.xticks(list(x), labels)
    plt.ylabel("average per fight")
    plt.title("per-fight averages (attacks, hits, misses)")
    plt.legend()
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_per_fight_averages.png"), dpi=150)

    # separate plot for hit rate
    plt.figure()
    plt.bar(labels, [avg_hit_rate[s] for s in labels])
    plt.ylabel("avg hit rate per fight (%)")
    plt.title("per-fight hit rate")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_per_fight_hit_rate.png"), dpi=150)


def plot_rounds_hist(fights: List[Dict[str, Any]], prefix: str, outdir: str) -> None:
    rounds = [f["rounds"] for f in fights]

    plt.figure()
    plt.hist(rounds, bins=range(1, max(rounds) + 2), align="left", rwidth=0.8)
    plt.xlabel("rounds per fight")
    plt.ylabel("frequency")
    plt.title("distribution of fight lengths (rounds)")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_rounds_hist.png"), dpi=150)


def plot_initiative_vs_outcome(fights: List[Dict[str, Any]], prefix: str, outdir: str) -> None:
    """
    simple 2x2 layout: who won initiative vs who won fight
    """
    # counts for (init_winner, fight_winner)
    counts = {
        ("pc", "pc"): 0,
        ("pc", "monster"): 0,
        ("pc", "draw"): 0,
        ("monster", "pc"): 0,
        ("monster", "monster"): 0,
        ("monster", "draw"): 0,
    }

    for f in fights:
        init_winner = "pc" if f["pc_init"] > f["monster_init"] else "monster"
        fight_winner = f["winner"]
        counts[(init_winner, fight_winner)] += 1

    labels = [
        "pc init → pc win",
        "pc init → monster win",
        "pc init → draw",
        "monster init → pc win",
        "monster init → monster win",
        "monster init → draw",
    ]
    values = [
        counts[("pc", "pc")],
        counts[("pc", "monster")],
        counts[("pc", "draw")],
        counts[("monster", "pc")],
        counts[("monster", "monster")],
        counts[("monster", "draw")],
    ]

    plt.figure()
    plt.bar(labels, values)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("count of fights")
    plt.title("initiative vs fight outcome")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_initiative_vs_outcome.png"), dpi=150)


def plot_damage_per_attack(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    dmg = stats["avg_damage_per_attack"]

    # separate keys for pc and monster
    pc_attacks = [(name, val) for (side, name), val in dmg.items() if side == "pc"]
    mon_attacks = [(name, val) for (side, name), val in dmg.items() if side == "monster"]

    # pc
    if pc_attacks:
        labels, vals = zip(*sorted(pc_attacks, key=lambda x: x[1], reverse=True))
        plt.figure()
        plt.barh(labels, vals)
        plt.xlabel("avg damage on hit")
        plt.title("pc attacks – average damage per hit")
        plt.gca().invert_yaxis()
        plt.tight_layout()

        if outdir:
            plt.savefig(os.path.join(outdir, f"{prefix}_pc_damage_per_attack.png"), dpi=150)

    # monster
    if mon_attacks:
        labels, vals = zip(*sorted(mon_attacks, key=lambda x: x[1], reverse=True))
        plt.figure()
        plt.barh(labels, vals)
        plt.xlabel("avg damage on hit")
        plt.title("monster attacks – average damage per hit")
        plt.gca().invert_yaxis()
        plt.tight_layout()

        if outdir:
            plt.savefig(os.path.join(outdir, f"{prefix}_monster_damage_per_attack.png"), dpi=150)


def plot_damage_per_fight_hist(fights: List[Dict[str, Any]], prefix: str, outdir: str) -> None:
    pc_totals: List[int] = []
    mon_totals: List[int] = []

    for f in fights:
        totals = compute_total_damage_by_side_for_fight(f)
        pc_totals.append(totals["pc"])
        mon_totals.append(totals["monster"])

    plt.figure()
    plt.hist(pc_totals, bins=20, alpha=0.7, label="pc")
    plt.hist(mon_totals, bins=20, alpha=0.7, label="monster")
    plt.xlabel("total damage in fight")
    plt.ylabel("frequency")
    plt.title("distribution of total damage per fight")
    plt.legend()
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_damage_per_fight_hist.png"), dpi=150)


# ---------- main CLI ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="visual analysis for monte carlo combat sim")
    parser.add_argument("pc_xml", help="PC XML filename (in data/)")
    parser.add_argument("-m", "--monster-name", default=None, help="monster name (exact match). if omitted, random monster")
    parser.add_argument("-n", "--num-fights", type=int, default=1000, help="number of simulated fights")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--outdir", default="figs", help="output directory for charts (default: figs)")
    parser.add_argument("--prefix", default="analysis", help="filename prefix for output images")
    args = parser.parse_args()

    ensure_output_dir(args.outdir)

    print_header("loading pc and monster (visual_analysis)")
    pc = load_pc(args.pc_xml)
    print(f"loaded pc: {getattr(pc, 'name', 'PC')}")

    monster = load_monster(args.monster_name)
    print(f"loaded monster: {getattr(monster, 'name', 'Monster')}")

    print_header("running simulations for visual analysis")
    stats, fights = run_fights_for_analysis(pc, monster, args.num_fights, args.seed)

    # generate charts
    plot_win_distribution(stats, args.prefix, args.outdir)
    plot_hits_misses_totals(stats, args.prefix, args.outdir)
    plot_per_fight_averages(stats, args.prefix, args.outdir)
    plot_rounds_hist(fights, args.prefix, args.outdir)
    plot_initiative_vs_outcome(fights, args.prefix, args.outdir)
    plot_damage_per_attack(stats, args.prefix, args.outdir)
    plot_damage_per_fight_hist(fights, args.prefix, args.outdir)

    print_header("charts saved")
    print(f"charts written to: {os.path.abspath(args.outdir)}")

    # show all figures interactively
    plt.show()


if __name__ == "__main__":
    main()