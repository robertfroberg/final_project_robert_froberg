# visualize_outcomes.py
# charts and graphics for the combat simulator
import argparse
import os
import random
from collections import defaultdict
from typing import Any, Dict, List, Tuple
import matplotlib.pyplot as plt
from character_parse import parse_character
import monster_parse
from combat_sim import simulate_single_fight


# all parsed monsters
ALL_MONSTERS: List[Any] = []


# formatted section header for screen output readablitiy
def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# one-time monster load using monster_parse
def ensure_monsters_loaded() -> None:
    global ALL_MONSTERS
    if ALL_MONSTERS:
        return

    print_header("Loading monsters from web ...")
    ALL_MONSTERS = monster_parse.load_all_monsters()


# look up one monster by name (case-insensitive exact match)
def get_monster_by_name_from_all(name: str) -> Any:
    ensure_monsters_loaded()
    m = monster_parse.get_monster_by_name(name, ALL_MONSTERS)
    if m is None:
        raise ValueError(f"Monster '{name}' not found")
    return m


# pick random monster from full list
def get_random_monster_from_all() -> Any:
    ensure_monsters_loaded()
    return random.choice(ALL_MONSTERS)


# parse pc xml looks inside /data
def load_pc(pc_xml: str) -> Any:
    return parse_character(pc_xml)


# load chosen monster or random if name is none
def load_monster(monster_name: str | None) -> Any:
    if monster_name:
        return get_monster_by_name_from_all(monster_name)
    return get_random_monster_from_all()


# run n_fights single combats and build stats for plotting
def run_fights_for_analysis(
    pc: Any,
    monster: Any,
    n_fights: int,
    seed: int | None = None,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:

    # rng for reproducible monte carlo sim
    rng = random.Random(seed) if seed is not None else random.Random()

    # store per fight results
    fights: List[Dict[str, Any]] = []

    # global tallies
    wins = {"pc": 0, "monster": 0, "draw": 0}
    init_wins = {"pc": 0, "monster": 0}
    hits = {"pc": 0, "monster": 0}
    misses = {"pc": 0, "monster": 0}
    total_rounds = 0

    # damage samples keyed by (side, attack_name)
    damage_samples: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    # per fight totals to compute averages
    sum_attacks_per_fight = {"pc": 0, "monster": 0}
    sum_hits_per_fight = {"pc": 0, "monster": 0}
    sum_misses_per_fight = {"pc": 0, "monster": 0}
    sum_hit_rate_per_fight = {"pc": 0.0, "monster": 0.0}

    # main sim loop
    for _ in range(n_fights):
        result = simulate_single_fight(pc, monster, rng=rng)
        fights.append(result)

        # winner tally
        winner = result["winner"]
        wins[winner] += 1

        # initiative tally
        if result["pc_init"] > result["monster_init"]:
            init_wins["pc"] += 1
        else:
            init_wins["monster"] += 1

        total_rounds += result["rounds"]

        # hit/miss and per fight tracking
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

        # damage samples for each attack name
        for key, samples in result["attack_damage_by_name"].items():
            damage_samples[key].extend(samples)

    # average damage per attack across all fights
    avg_damage_per_attack = {
        key: (sum(vals) / len(vals) if vals else 0.0)
        for key, vals in damage_samples.items()
    }

    # per fight averages if any fights were run
    if n_fights > 0:
        avg_rounds = total_rounds / n_fights
        avg_attacks_per_fight = {s: sum_attacks_per_fight[s] / n_fights for s in ("pc", "monster")}
        avg_hits_per_fight = {s: sum_hits_per_fight[s] / n_fights for s in ("pc", "monster")}
        avg_misses_per_fight = {s: sum_misses_per_fight[s] / n_fights for s in ("pc", "monster")}
        avg_hit_rate_per_fight = {s: (sum_hit_rate_per_fight[s] / n_fights * 100.0) for s in ("pc", "monster")}
    else:
        avg_rounds = 0.0
        avg_attacks_per_fight = {"pc": 0.0, "monster": 0.0}
        avg_hits_per_fight = {"pc": 0.0, "monster": 0.0}
        avg_misses_per_fight = {"pc": 0.0, "monster": 0.0}
        avg_hit_rate_per_fight = {"pc": 0.0, "monster": 0.0}

    # final stats dict used by all plots
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


# sum all damage by pc and monster for single fight
def compute_total_damage_by_side_for_fight(result: Dict[str, Any]) -> Dict[str, int]:
    totals = {"pc": 0, "monster": 0}
    for (side, _attack), samples in result["attack_damage_by_name"].items():
        totals[side] += sum(samples)
    return totals


# make sure output directory exists before saving plots
def ensure_output_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


# bar chart of win counts for pc monster and draws (which will [well should] not happen)
def plot_win_distribution(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    wins = stats["wins"]
    labels = ["PC Wins", "Monster Wins", "Draws"]
    values = [wins["pc"], wins["monster"], wins["draw"]]

    plt.figure()
    plt.bar(labels, values)
    plt.title("Win Distribution")
    plt.ylabel("Count of Fights")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_win_distribution.png"), dpi=150)


# grouped bar chart of hits and misses for pc and monster
def plot_hits_misses_totals(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    hits = stats["hits"]
    misses = stats["misses"]

    labels = ["PC", "Monster"]
    hits_vals = [hits["pc"], hits["monster"]]
    miss_vals = [misses["pc"], misses["monster"]]

    x = range(len(labels))
    width = 0.35

    plt.figure()
    plt.bar([i - width/2 for i in x], hits_vals, width=width, label="Hits")
    plt.bar([i + width/2 for i in x], miss_vals, width=width, label="Misses")
    plt.xticks(list(x), labels)
    plt.ylabel("Total Attacks")
    plt.title("Hits vs Misses")
    plt.legend()
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_hits_misses_totals.png"), dpi=150)


# bar charts of per fight avearge and hit rate
def plot_per_fight_averages(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    avg_attacks = stats["avg_attacks_per_fight"]
    avg_hits = stats["avg_hits_per_fight"]
    avg_misses = stats["avg_misses_per_fight"]
    avg_hit_rate = stats["avg_hit_rate_per_fight"]

    labels = ["PC", "Monster"]
    x = range(len(labels))
    width = 0.2

    plt.figure()
    plt.bar([i - width for i in x], [avg_attacks[s.lower()] for s in labels], width=width, label="Avg Attacks")
    plt.bar([i for i in x],        [avg_hits[s.lower()]    for s in labels], width=width, label="Avg Hits")
    plt.bar([i + width for i in x],[avg_misses[s.lower()]  for s in labels], width=width, label="Avg Misses")
    plt.xticks(list(x), labels)
    plt.ylabel("Average per Fight")
    plt.title("Per-Fight Averages")
    plt.legend()
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_per_fight_averages.png"), dpi=150)

    # separate chart for hit rate percent
    plt.figure()
    plt.bar(labels, [avg_hit_rate[s.lower()] for s in labels])
    plt.ylabel("Percent")
    plt.title("Hit Rate per Fight")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_per_fight_hit_rate.png"), dpi=150)


# histogram of fight length in rounds
def plot_rounds_hist(fights: List[Dict[str, Any]], prefix: str, outdir: str) -> None:
    rounds = [f["rounds"] for f in fights]

    plt.figure()
    plt.hist(rounds, bins=range(1, max(rounds) + 2), align="left", rwidth=0.8)
    plt.xlabel("Rounds")
    plt.ylabel("Count")
    plt.title("Fight Length (Rounds)")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_rounds_hist.png"), dpi=150)


# bar chart relating initiative winner and fight winner
def plot_initiative_vs_outcome(fights: List[Dict[str, Any]], prefix: str, outdir: str) -> None:
    counts = {
        ("pc", "pc"): 0,
        ("pc", "monster"): 0,
        ("pc", "draw"): 0,
        ("monster", "pc"): 0,
        ("monster", "monster"): 0,
        ("monster", "draw"): 0,
    }

    for f in fights:
        init = "pc" if f["pc_init"] > f["monster_init"] else "monster"
        win = f["winner"]
        counts[(init, win)] += 1

    labels = [
        "PC Init → PC Win",
        "PC Init → Monster Win",
        "PC Init → Draw",
        "Monster Init → PC Win",
        "Monster Init → Monster Win",
        "Monster Init → Draw",
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
    plt.ylabel("Count")
    plt.title("Initiative vs Outcome")
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_initiative_vs_outcome.png"), dpi=150)


# horizontal bar charts of average damage per attack name
def plot_damage_per_attack(stats: Dict[str, Any], prefix: str, outdir: str) -> None:
    dmg = stats["avg_damage_per_attack"]

    pc_attacks = [(name, v) for (side, name), v in dmg.items() if side == "pc"]
    mon_attacks = [(name, v) for (side, name), v in dmg.items() if side == "monster"]

    if pc_attacks:
        labels, vals = zip(*sorted(pc_attacks, key=lambda x: x[1], reverse=True))
        plt.figure()
        plt.barh(labels, vals)
        plt.xlabel("Average Damage")
        plt.title("PC Damage per Attack")
        plt.gca().invert_yaxis()
        plt.tight_layout()

        if outdir:
            plt.savefig(os.path.join(outdir, f"{prefix}_pc_damage_per_attack.png"), dpi=150)

    if mon_attacks:
        labels, vals = zip(*sorted(mon_attacks, key=lambda x: x[1], reverse=True))
        plt.figure()
        plt.barh(labels, vals)
        plt.xlabel("Average Damage")
        plt.title("Monster Damage per Attack")
        plt.gca().invert_yaxis()
        plt.tight_layout()

        if outdir:
            plt.savefig(os.path.join(outdir, f"{prefix}_monster_damage_per_attack.png"), dpi=150)


# histogram of total damage per fight for pc and monster
def plot_damage_per_fight_hist(fights: List[Dict[str, Any]], prefix: str, outdir: str) -> None:
    pc_totals = []
    mon_totals = []

    for f in fights:
        totals = compute_total_damage_by_side_for_fight(f)
        pc_totals.append(totals["pc"])
        mon_totals.append(totals["monster"])

    plt.figure()
    plt.hist(pc_totals, bins=20, alpha=0.7, label="PC")
    plt.hist(mon_totals, bins=20, alpha=0.7, label="Monster")
    plt.xlabel("Total Damage")
    plt.ylabel("Count")
    plt.title("Damage per Fight")
    plt.legend()
    plt.tight_layout()

    if outdir:
        plt.savefig(os.path.join(outdir, f"{prefix}_damage_per_fight_hist.png"), dpi=150)


# main
def main() -> None:
    # default output directory one level up in /results
    default_results = os.path.join(os.path.dirname(__file__), "..", "results")
    
    parser = argparse.ArgumentParser(description="visual analysis for combat simulator")
    parser.add_argument("pc_xml", help="PC XML filename (in data/)")
    parser.add_argument("-m", "--monster-name", default=None, help="monster name (exact match)")
    parser.add_argument("-n", "--num-fights", type=int, default=1000, help="number of simulations")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--outdir", default=default_results, help="directory for output charts")
    parser.add_argument("--prefix", default="analysis", help="filename prefix")
    args = parser.parse_args()

    ensure_output_dir(args.outdir)

    print_header("Load PC and Monster")
    pc = load_pc(args.pc_xml)
    print(f"loaded pc: {getattr(pc, 'name', 'PC')}")

    monster = load_monster(args.monster_name)
    print(f"loaded monster: {getattr(monster, 'name', 'Monster')}")

    print_header("Running Simulations")
    stats, fights = run_fights_for_analysis(pc, monster, args.num_fights, args.seed)

    # generate all charts
    plot_win_distribution(stats, args.prefix, args.outdir)
    plot_hits_misses_totals(stats, args.prefix, args.outdir)
    plot_per_fight_averages(stats, args.prefix, args.outdir)
    plot_rounds_hist(fights, args.prefix, args.outdir)
    plot_initiative_vs_outcome(fights, args.prefix, args.outdir)
    plot_damage_per_attack(stats, args.prefix, args.outdir)
    plot_damage_per_fight_hist(fights, args.prefix, args.outdir)

    print_header("Charts Saved")
    print(f"charts written to: {os.path.abspath(args.outdir)}")

    plt.show()


if __name__ == "__main__":
    main()