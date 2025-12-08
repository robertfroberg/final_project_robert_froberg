# main.py
# main script for combat simulator

import argparse
import os
import sys

# add src folder to path
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from config import DEFAULT_RESULTS_DIR_NAME
from combat_sim import simulate_many_fights
from magic_items import load_default_magic_items, print_items_for_pc_name
from visualize_outcomes import load_pc, load_monster, print_header, run_visuals


# print text summary of simulation
def print_basic_summary(pc, monster, stats) -> None:
    pc_name = getattr(pc, "name", "PC")
    mon_name = getattr(monster, "name", "Monster")

    total = stats["total_fights"]
    wins = stats["wins"]
    init = stats["init_wins"]
    hits = stats["hits"]
    misses = stats["misses"]
    avg_rounds = stats["avg_rounds"]

    # show fight setup
    print_header("Combat Setup")
    print(f"PC:      {pc_name}")
    print(f"Monster: {mon_name}")
    print(f"Total replications: {total}")

    # wins and losses
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

    # initiative
    print_header("Initiative")
    pc_i = init.get("pc", 0)
    mon_i = init.get("monster", 0)
    if total > 0:
        print(f"PC wins init:      {pc_i} ({pc_i / total * 100:.1f}%)")
        print(f"Monster wins init: {mon_i} ({mon_i / total * 100:.1f}%)")
    else:
        print("no initiative rolled")

    # hits and misses
    print_header("Hits and Misses")
    lbl = {"pc": "PC", "monster": "Monster"}
    for side in ("pc", "monster"):
        h = hits.get(side, 0)
        m = misses.get(side, 0)
        att = h + m
        print(f"{lbl[side]} total attacks: {att}")
        print(f"  Hits:   {h}")
        print(f"  Misses: {m}")
        if att > 0:
            print(f"  Hit rate: {h / att * 100:.1f}%")
        else:
            print("  Hit rate: n/a")

    # rounds per fight
    print_header("Rounds per replication")
    print(f"Average number of rounds per replication: {avg_rounds:.2f}")


def main() -> None:
    # parse command line args
    parser = argparse.ArgumentParser(description="combat simulation driver")
    parser.add_argument(
        "pc_xml",
        nargs="?",
        default="aeric20.xml",
        help="pc xml filename in xml/ (default: aeric20.xml)",
    )
    parser.add_argument(
        "-m",
        "--monster-name",
        default="Adult Blue Dragon",
        help='monster name (default: "Adult Blue Dragon")',
    )
    parser.add_argument(
        "-n",
        "--num-fights",
        type=int,
        default=1000,
        help="number of replications",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="random seed",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="generate charts for results",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="output folder for charts (default: project-level results/)",
    )
    args = parser.parse_args()

    # if user provided nothing but main.py, turn visualization on
    if len(sys.argv) == 1:
        args.visualize = True
    
    # set output dir default
    if args.outdir is None:
        args.outdir = os.path.join(project_root, DEFAULT_RESULTS_DIR_NAME)

    # load magic item workbook from configured url
    items_df = load_default_magic_items()

    # load pc and monster
    print_header("Loading PC and Monster . . . ")
    pc = load_pc(args.pc_xml)
    print(f"Loaded PC: {getattr(pc, 'name', 'PC')}")

    monster = load_monster(args.monster_name)
    print(f"Loaded Monster: {getattr(monster, 'name', 'Monster')}")

    # show pc magic items
    if items_df is not None:
        pc_name = getattr(pc, "name", None)
        print_items_for_pc_name(pc_name, items_df)

    # run simulations
    print_header(f"Running {args.num_fights} replications . . .")
    stats = simulate_many_fights(pc, monster, n_fights=args.num_fights, seed=args.seed)

    # print text summary
    print_basic_summary(pc, monster, stats)

    # optional charts
    if args.visualize:
        run_visuals(pc, monster, args.num_fights, args.seed, args.outdir, prefix="analysis")


if __name__ == "__main__":
    main()