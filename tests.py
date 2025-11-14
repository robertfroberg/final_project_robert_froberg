# tests.py
# this script tests character_parse.py and magic_items.py

import os
import character_parse
import magic_items

# get the folder where this file is located
base_dir = os.path.dirname(os.path.abspath(__file__))

# path to the data folder
data_dir = os.path.join(base_dir, "data")


def pick_xml_file():
    # find all xml files in the data folder
    xml_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".xml")]

    # no xml files found
    if not xml_files:
        print("No XML files found in the data folder.")
        return None

    # list xml files
    print("Available XML files:")
    for i, f in enumerate(xml_files, 1):
        print(f"{i}. {f}")

    # prompt user to pick one
    while True:
        choice = input("Select a file by number: ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(xml_files):
                return os.path.join(data_dir, xml_files[idx - 1])
        print("Invalid selection. Try again.")


def test_character_parse():
    # choose an xml file
    xml_path = pick_xml_file()
    if not xml_path:
        return

    print("\n=== Character Parse Test ===")
    print(f"Input file: {xml_path}")

    # parse xml into a data dict
    try:
        data = character_parse.parse_character(xml_path)
    except Exception as e:
        print("Error while parsing character file:", e)
        return

    # expect a dict as return value
    if not isinstance(data, dict):
        print("Parsed data type:", type(data))
        print("Raw parsed data:", data)
        return

    # basic character fields
    name = data.get("name", "Unknown")
    hp = data.get("hp", "Unknown")
    ac = data.get("ac", "Unknown")

    print(f"\ncharacter name: {name}")
    print(f"hit points: {hp}")
    print(f"armor class: {ac}")

    # attacks list
    print("\nattacks:")
    attacks = data.get("attacks", [])

    # handle no attacks
    if not attacks:
        print(" - none found")
        print()
        return

    # print each attack in readable format
    for atk in attacks:
        if not isinstance(atk, dict):
            print(f" - {atk}")
            continue

        atk_name = atk.get("name", "Unknown")
        source = atk.get("source")  # e.g., weapon, power
        bonus = atk.get("attack_bonus")
        damage = atk.get("damage", "")
        damage_type = atk.get("damage_type", "")

        # build attack label
        if source:
            label = f"{atk_name} ({source})"
        else:
            label = atk_name

        # handle missing bonus
        bonus_str = "None" if bonus is None else str(bonus)

        # combine damage + damage types
        if damage_type:
            damage_str = f"{damage} {damage_type}"
        else:
            damage_str = damage

        print(f" - {label}: +{bonus_str} to hit, {damage_str}")

    print()


def test_magic_items():
    # path to MagicItemList.xlsx inside data folder
    items_path = os.path.join(data_dir, "MagicItemList.xlsx")

    print("=== Magic Items Test ===")
    print(f"Input file: {items_path}")

    # load magic items
    try:
        df = magic_items.load_magic_items(items_path)
    except Exception as e:
        print("Error while loading magic items:", e)
        return

    # basic summary
    print("Total rows in DataFrame:", len(df))
    print("Columns:", ", ".join(df.columns))
    print()

    # run book count
    print("Running book_count(df)...")
    magic_items.book_count(df)
    print()

    # run rarity summary
    print("Running generate_rarity_summary_table(df)...")
    magic_items.generate_rarity_summary_table(df)
    print()


def main():
    # run the character parser test
    test_character_parse()

    # run the magic item parser test
    test_magic_items()


if __name__ == "__main__":
    main()