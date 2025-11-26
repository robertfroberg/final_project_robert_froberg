import sys
import os
import re
import pandas as pd
import openpyxl


# load workbook and target sheet
def load_magic_items(file_path):
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    sheet = workbook['Items_By_Rarity']

    # prepare dataframe columns
    df = pd.DataFrame(columns=[
        'owner', 'item_name', 'spec_prop', 'rarity',
        'carried', 'trade_will', 'reward', 'certed'
    ])

    # loop through owner columns
    for col_index in range(2, sheet.max_column + 1):
        owner = sheet.cell(row=3, column=col_index).value

        # loop through item rows
        for row_index in range(4, sheet.max_row + 1):
            item_value = sheet.cell(row=row_index, column=col_index).value
            spec_prop = ""

            # skip empty cells
            if pd.isna(item_value):
                continue

            # pull special property text inside parentheses
            text = str(item_value)
            match = re.search(r'\((.*?)\)', text)
            if match:
                spec_prop = match.group(1)
                item_name = text.replace(f"({spec_prop})", "").strip()
            else:
                item_name = text

            # rarity based on font color
            font = sheet.cell(row=row_index, column=col_index).font
            rgb = getattr(font.color, "rgb", None)

            if rgb == "FFFFC000":
                rarity = "Unique"
            elif rgb == "FF7030A0":
                rarity = "Legendary"
            elif rgb == "FF0070C0":
                rarity = "Very Rare"
            elif rgb == "FF00B050":
                rarity = "Rare"
            elif rgb == "FFFF0000":
                rarity = "Uncommon"
            else:
                rarity = "Common"

            # trade willingness via fill color index
            fill = sheet.cell(row=row_index, column=col_index).fill.start_color.index
            if fill == 2:
                trade_will = "Untradeable"
            elif fill == 5:
                trade_will = "Red"
            elif fill == 7:
                trade_will = "Amber"
            elif fill == 9:
                trade_will = "Green"
            else:
                trade_will = "FAILED"
                print(f"[WARN] Unexpected fill index ({fill}) at row {row_index}, col {col_index}")

            # carried = full thin border box
            borders = sheet.cell(row=row_index, column=col_index).border
            carried = (
                borders.top.style == "thin" and
                borders.bottom.style == "thin" and
                borders.left.style == "thin" and
                borders.right.style == "thin"
            )

            # reward = italic text
            reward = font.italic

            # certed = bold text
            certed = font.bold

            # save item entry
            df.loc[len(df)] = [
                owner, item_name, spec_prop, rarity,
                carried, trade_will, reward, certed
            ]

    # export csv for review
    base_name, _ = os.path.splitext(file_path)
    csv_path = base_name + "_items.csv"
    df.to_csv(csv_path, index=False)
    print("DataFrame saved to:", csv_path)

    return df


# list of stat book names
def book_count(dataframe):
    book_names = [
        "Manual of Gainful Exercise",
        "Manual of Quickness of Action",
        "Manual of Bodily Health",
        "Tome of Clear Thought",
        "Tome of Understanding",
        "Tome of Leadership and Influence"
    ]

    print("\n=== Book Count (Tradeable Only) ===")
    results = {}

    # count each book that is not untradeable
    for name in book_names:
        count = dataframe[
            (dataframe['item_name'].str.contains(name, na=False)) &
            (dataframe['trade_will'] != "Untradeable")
        ].shape[0]

        results[name] = count
        print(f"{name}: {count}")

    return results

# pull unique owner names
def list_owners_and_items(dataframe):
    owners = dataframe['owner'].dropna().unique()

    if len(owners) == 0:
        print("No owners found.")
        return

    # show owner menu
    print("\n=== Owners ===")
    for i, owner in enumerate(owners, 1):
        print(f"{i}. {owner}")

    # accept name or number
    while True:
        choice = input("\nSelect a character (name or number): ").strip()

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(owners):
                owner = owners[idx - 1]
                break
        elif choice in owners:
            owner = choice
            break

        print("Invalid selection. Try again.")

    # filter items for selected owner
    items = dataframe[dataframe['owner'] == owner]
    total = len(items)
    carried_total = items['carried'].sum()
    rarity_counts = items['rarity'].value_counts()

    # item summary
    print(f"\n=== Items for {owner} ===")
    print(f"Total items: {total}")
    print(f"Carried items: {carried_total}")
    print("Items by rarity:")
    for r, c in rarity_counts.items():
        print(f"  {r}: {c}")

    # full item list
    print("\nItem List:")
    for _, row in items.iterrows():
        tag = "*" if row['carried'] else ""
        prop = f" ({row['spec_prop']})" if row['spec_prop'] else ""
        print(f"  {row['item_name']}{prop} {tag}")


# function that looks through all times and returns alphabetized list of items willing to trade based on rarity without dups
def generate_trade_list(dataframe):
    # rarity names
    rarity_map = {
        "common": "Common",
        "uncommon": "Uncommon",
        "rare": "Rare",
        "very rare": "Very Rare",
        "legendary": "Legendary"
    }

    # trade tiers that include lower tiers
    trade_map = {
        "red":   ["Red", "Amber", "Green"],
        "amber": ["Amber", "Green"],
        "green": ["Green"]
    }

    # validate menu input
    def ask(prompt, options):
        while True:
            val = input(prompt).strip().lower()
            if val.isdigit():
                num = int(val)
                if 1 <= num <= len(options):
                    return options[num - 1]
            if val in options:
                return val
            print("Invalid option. Try again.")

    print("\n=== Trade List Generator ===")

    # rarity choice
    rarity_opts = list(rarity_map.keys())
    rarity_sel = ask(f"Select rarity ({', '.join(rarity_opts)}): ", rarity_opts)
    rarity_label = rarity_map[rarity_sel]

    # trade tier choice
    trade_opts = list(trade_map.keys())
    trade_sel = ask(f"Select trade tier ({', '.join(trade_opts)}): ", trade_opts)
    allowed_tiers = trade_map[trade_sel]

    # filter by rarity and trade tier
    subset = dataframe[
        (dataframe['rarity'] == rarity_label) &
        (dataframe['trade_will'].isin(allowed_tiers))
    ]

    # collect unique item names
    names = set()
    for _, row in subset.iterrows():
        prop = f" ({row['spec_prop']})" if row['spec_prop'] else ""
        names.add(f"{row['item_name']}{prop}")

    # output result
    print()
    if names:
        print(f"{rarity_label} Trade Items ({', '.join(allowed_tiers)}):")
        print(", ".join(sorted(names)))
        print()
    else:
        print(f"No {rarity_label} items available for {', '.join(allowed_tiers)}.\n")


def generate_rarity_summary_table(dataframe):
    # count items by rarity
    total = dataframe['rarity'].value_counts().sort_index()
    carried = dataframe[dataframe['carried']]['rarity'].value_counts().sort_index()
    untrade = dataframe[dataframe['trade_will'] == "Untradeable"]['rarity'].value_counts().sort_index()

    # build summary dataframe
    table = pd.DataFrame({
        "Total": total,
        "Red": dataframe[dataframe['trade_will'] == "Red"]['rarity'].value_counts(),
        "Amber": dataframe[dataframe['trade_will'] == "Amber"]['rarity'].value_counts(),
        "Green": dataframe[dataframe['trade_will'] == "Green"]['rarity'].value_counts(),
        "Untradeable": untrade,
        "Carried": carried,
    }).fillna(0).astype(int)

    # add totals row
    table.loc["Sum"] = [
        table["Total"].sum(),
        table["Red"].sum(),
        table["Amber"].sum(),
        table["Green"].sum(),
        table["Untradeable"].sum(),
        table["Carried"].sum()
    ]

    print("\n=== Rarity Summary Table ===")
    print(table)
    print()
    return table

# loads excel file from /data and runs interactive magic item menu
def main():
    # require file argument
    if len(sys.argv) < 2:
        print("Usage: python magic_items.py <MagicItemList.xlsx>")
        sys.exit(1)

    # resolve paths relative to script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")

    # use filename provided look in /data
    xlsx_filename = os.path.basename(sys.argv[1])
    file_path = os.path.join(data_dir, xlsx_filename)

    # verify file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found in /data: {file_path}")
        sys.exit(1)

    # load file into dataframe
    try:
        df = load_magic_items(file_path)
    except Exception as e:
        print("Error loading file:", e)
        sys.exit(1)

    # main menu loop
    while True:
        print("\n=== Magic Item Tool ===")
        print("1. Book count")
        print("2. List owners and items")
        print("3. Generate a trade list")
        print("4. Rarity summary table")
        print("5. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            book_count(df)
        elif choice == "2":
            list_owners_and_items(df)
        elif choice == "3":
            generate_trade_list(df)
        elif choice == "4":
            generate_rarity_summary_table(df)
        elif choice == "5":
            print("Exiting.")
            break
        else:
            print("Invalid selection.\n")


if __name__ == "__main__":
    main()
