# tests.py
# simple driver to run combat sims, show text summary, optional charts, and pc magic items
import argparse
import os
from combat_sim import simulate_many_fights
from magic_items import load_default_magic_items, print_items_for_pc_name
from visualize_outcomes import (
    load_pc,
    load_monster,
    print_header,
    run_visuals,
)


# print text summary of results
def print_basic_summary(pc, monster, stats) -> None:
    pc_name = getattr(pc, "name", "PC")
    mon_name = getattr(monster, "name", "Monster")

    total = stats["total_fights"]
    wins = stats["wins"]
    init = stats["init_wins"]
    hits = stats["hits"]
    misses = stats["misses"]
    avg_rounds = stats["avg_rounds"]

    # show who is fighting
    print_header("Combat Setup")
    print(f"PC:      {pc_name}")
    print(f"Monster: {mon_name}")
    print(f"Total replications: {total}")

    # win loss percentages
    print_header("Wins and Losses")
    pc_w = wins.get("pc", 0)
    mon_w = wins.get("monster", 0)
    dr = wins.get("draw", 0)

    if total > 0:
        print(f"PC wins:      {pc_w} ({pc_w / total * 100:.1f}%)")
        print(f"Monster wins: {mon_w} ({mon_w / total * 100:.1f}%)")
        print(f"Draws:        {dr} ({dr / total * 100:.1f}%)")
    else:
        print("No fights run.")

    # initiative stats
    print_header("Initiative")
    pc_i = init.get("pc", 0)
    mon_i = init.get("monster", 0)
    if total > 0:
        print(f"PC wins init:      {pc_i} ({pc_i / total * 100:.1f}%)")
        print(f"Monster wins init: {mon_i} ({mon_i / total * 100:.1f}%)")
    else:
        print("No initiative rolled.")

    # attack outcome breakdown
    labels = {"pc": "PC", "monster": "Monster"}
    print_header("Hits and Misses")
    for side in ("pc", "monster"):
        h = hits.get(side, 0)
        m = misses.get(side, 0)
        att = h + m
        print(f"{labels[side]} Total attacks: {att}")
        print(f"  Hits:   {h}")
        print(f"  Misses: {m}")
        if att > 0:
            print(f"  Hit rate: {h / att * 100:.1f}%")
        else:
            print("  Hit rate: n/a")

    # fight length
    print_header("Rounds per replication")
    print(f"Average rounds: {avg_rounds:.2f}")


# main
def main() -> None:
    parser = argparse.ArgumentParser(description="combat simulation test driver")
    parser.add_argument("pc_xml", help="PC xml filename (in data/)")
    parser.add_argument("-m", "--monster-name", default=None, help="monster name (exact match) or None for random")
    parser.add_argument("-n", "--num-fights", type=int, default=1000, help="number of fights to run")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--visualize", action="store_true", help="also generate charts using visualize_outcomes.py")
    parser.add_argument("--outdir", default=None, help="output folder for charts (default: project-level results/)")
    parser.add_argument("--prefix", default="analysis", help="filename prefix for charts")
    parser.add_argument(
        "--items-xlsx",
        default="MagicItemList.xlsx",
        help="magic item workbook filename (in data/)",
    )
    args = parser.parse_args()

    # default output location ../results/
    if args.outdir is None:
        script_dir = os.path.dirname(__file__)
        args.outdir = os.path.join(script_dir, "..", "results")

    # load magic item data once
    items_df = load_default_magic_items(args.items_xlsx)

    # load PC + monster from xml
    print_header("Loading PC and Monster")
    pc = load_pc(args.pc_xml)
    print(f"Loaded PC: {getattr(pc, 'name', 'PC')}")

    monster = load_monster(args.monster_name)
    print(f"\nLoaded monster: {getattr(monster, 'name', 'Monster')}")

    # print PC magic items if available
    if items_df is not None:
        pc_name = getattr(pc, "name", None)
        print_items_for_pc_name(pc_name, items_df)

    # run monte carlo replics
    print_header(f"Running simulation with {args.num_fights} replications ...")
    stats = simulate_many_fights(pc, monster, n_fights=args.num_fights, seed=args.seed)

    # show text summary
    print_basic_summary(pc, monster, stats)

    # optional visualization path
    if args.visualize:
        run_visuals(pc, monster, args.num_fights, args.seed, args.outdir, args.prefix)


if __name__ == "__main__":
    main()