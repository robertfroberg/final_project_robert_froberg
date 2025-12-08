# tests.py
# quick tests for combat simulator project

import os
import random

from config import DATA_DIR, DEFAULT_PC_XML_FILENAME
from character_parse import parse_character
import monster_parse
from combat_sim import simulate_single_fight, simulate_many_fights
from magic_items import (
    load_default_magic_items,
    print_items_for_pc_name,
    book_count,
    generate_rarity_summary_table,
)


# simple header for readability
def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# test reading pc xml and printing key fields
def test_character_parse() -> None:
    print_header("Test: Character_parse")

    xml_filename = DEFAULT_PC_XML_FILENAME
    xml_path = os.path.join(DATA_DIR, xml_filename)
    print(f"Using PC file: {xml_path}")

    pc = parse_character(xml_filename)

    print(f"Name:  {pc.name}")
    print(f"Level: {pc.level}")
    print(f"AC:    {pc.ac}")
    print(f"HP:    {pc.hp}")
    print(f"Initiative bonus: {pc.initiative}")
    print(f"Attacks found: {len(pc.attacks)}")
    print(f"Skills found:  {len(pc.skills)}")
    print(f"Feats found:   {len(pc.feats)}")


# test loading monsters from web and basic lookup
def test_monster_parse() -> None:
    print_header("Test: Monster_parse load_all_monsters")

    monsters = monster_parse.load_all_monsters()
    print(f"Total monsters loaded: {len(monsters)}")

    if not monsters:
        print("No monsters loaded, skipping further checks.")
        return

    print("Sample of first 5 monsters:")
    for m in monsters[:5]:
        print(f"  - {m.name}")

    # pretty print first monster for visual check
    print("\nPretty print of first monster:")
    monster_parse.pretty_print_monster(monsters[0])

    name = "Adult Blue Dragon"
    dragon = monster_parse.get_monster_by_name(name, monsters)
    if dragon:
        print(f"\nLookup: Found '{name}'")
        print(f"AC: {dragon.ac}  HP: {dragon.hp}  Initiative: {dragon.initiative}")
        print(f"CR: {dragon.cr}  PB: {dragon.pb}")
    else:
        print(f"\nLookup: Monster '{name}' not found.")


# test loading magic item workbook and basic queries
def test_magic_items() -> None:
    print_header("Test: Magic_items")

    df = load_default_magic_items()
    if df is None or df.empty:
        print("Magic item DataFrame not loaded or is empty.")
        return

    print(f"Rows in magic item DataFrame: {len(df)}")
    print("Columns:", ", ".join(df.columns))

    owners = df["owner"].dropna().unique()
    owners_list = list(owners)
    print(f"Unique owners: {len(owners_list)}")

    if owners_list:
        print("Sample owners:")
        for name in owners_list[:5]:
            print(f"  - {name}")

    pc_name = "Aeric Thunderfoot"
    print(f"\nTrying to match items for PC name: {pc_name}")
    print_items_for_pc_name(pc_name, df)

    print("\nBook count (tradeable only):")
    book_count(df)

    print("\nRarity summary table:")
    generate_rarity_summary_table(df)


# test single fight and small monte carlo run
def test_combat_sim() -> None:
    print_header("Test: Combat_sim")

    xml_filename = DEFAULT_PC_XML_FILENAME
    pc = parse_character(xml_filename)

    monsters = monster_parse.load_all_monsters()
    if not monsters:
        print("No monsters loaded, skipping combat tests.")
        return

    name = "Adult Blue Dragon"
    dragon = monster_parse.get_monster_by_name(name, monsters)
    if not dragon:
        dragon = monsters[0]
        print(f"Falling back to first monster: {dragon.name}")
    else:
        print(f"Using monster: {dragon.name}")

    rng = random.Random(0)
    print("\nSingle fight:")
    result = simulate_single_fight(pc, dragon, rng=rng)
    print(f"Winner: {result['winner']}")
    print(f"Rounds: {result['rounds']}")
    print(f"PC init: {result['pc_init']}  Monster init: {result['monster_init']}")
    print(f"PC hits: {result['hits']['pc']}  Misses: {result['misses']['pc']}")
    print(f"Monster hits: {result['hits']['monster']}  Misses: {result['misses']['monster']}")

    print("\nMonte Carlo: 100 fights")
    stats = simulate_many_fights(pc, dragon, n_fights=100, seed=1)
    total = stats["total_fights"]
    wins = stats["wins"]

    print(f"Total fights: {total}")
    print(f"PC wins:      {wins['pc']} ({wins['pc'] / total * 100:.1f}%)")
    print(f"Monster wins: {wins['monster']} ({wins['monster'] / total * 100:.1f}%)")
    print(f"Draws:        {wins['draw']} ({wins['draw'] / total * 100:.1f}%)")
    print(f"Average rounds: {stats['avg_rounds']:.2f}")


# test that visual analysis core loop runs without charts
def test_visual_core() -> None:
    print_header("Test: Visualize_outcomes core loop")

    from visualize_outcomes import run_fights_for_analysis

    xml_filename = DEFAULT_PC_XML_FILENAME
    pc = parse_character(xml_filename)

    monsters = monster_parse.load_all_monsters()
    if not monsters:
        print("No monsters loaded, skipping visual core test.")
        return

    name = "Adult Blue Dragon"
    dragon = monster_parse.get_monster_by_name(name, monsters) or monsters[0]

    print(f"PC: {pc.name}, Monster: {dragon.name}")
    stats, fights = run_fights_for_analysis(pc, dragon, n_fights=50, seed=2)

    print(f"Fights simulated: {len(fights)}")
    print("Wins dict:", stats["wins"])
    print(f"Average rounds: {stats['avg_rounds']:.2f}")
    print("Average attacks per fight:", stats["avg_attacks_per_fight"])


# main fucntion
def main() -> None:
    print_header("Starting tests . . . ")

    test_character_parse()
    test_monster_parse()
    test_magic_items()
    test_combat_sim()
    test_visual_core()

    print_header("All tests completed")


if __name__ == "__main__":
    main()
