import xml.etree.ElementTree as ET


# helper to convert values to int safely
def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# get total hit points from the character xml
def parse_hp(character_elem):
    return safe_int(character_elem.findtext("./hp/total", default="0"))


# get armor class from the character xml
def parse_ac(character_elem):
    return safe_int(character_elem.findtext("./defenses/ac/total", default="0"))


# get proficiency bonus from the character xml
def parse_prof_bonus(character_elem):
    return safe_int(character_elem.findtext("./profbonus", default="0"))


# parse attacks listed under weaponlist
def parse_weapon_attacks(character_elem):
    attacks = []

    for weapon in character_elem.findall("./weaponlist/*"):
        # get weapon name and attack bonus
        name = weapon.findtext("name", default="unknown weapon")
        attack_bonus = safe_int(weapon.findtext("attackbonus", default="0"))

        # process any damage entries tied to this weapon
        for dmg in weapon.findall("./damagelist/*"):
            dice = dmg.findtext("dice", default="")
            bonus = safe_int(dmg.findtext("bonus", default="0"))
            dmg_type = dmg.findtext("type", default="")

            # build the damage string like "2d6+3"
            damage_str = dice
            if bonus > 0:
                damage_str = f"{dice}+{bonus}"
            elif bonus < 0:
                damage_str = f"{dice}{bonus}"

            attacks.append({
                "name": name,
                "source": "weapon",
                "attack_bonus": attack_bonus,
                "damage": damage_str,
                "damage_type": dmg_type,
            })

    return attacks


# parse powers that have damage entries and possible attack rolls
def parse_power_attacks(character_elem, prof_bonus):
    attacks = []

    for power in character_elem.findall("./powers/*"):
        # get power name
        name = power.findtext("name", default="unnamed power")
        attack_bonus = None

        # find cast-type actions to determine attack bonus
        for action in power.findall("./actions/*"):
            if action.findtext("type", default="") == "cast":
                atkmod = safe_int(action.findtext("atkmod", default="0"))
                atkprof_flag = safe_int(action.findtext("atkprof", default="0"))
                attack_bonus = atkmod + atkprof_flag * prof_bonus
                break

        # collect any damage entries for this power
        for action in power.findall("./actions/*"):
            damagelist = action.find("damagelist")
            if damagelist is None:
                continue

            for dmg in damagelist.findall("./*"):
                dice = dmg.findtext("dice", default="")
                bonus = safe_int(dmg.findtext("bonus", default="0"))
                dmg_type = dmg.findtext("type", default="")

                damage_str = dice
                if bonus > 0:
                    damage_str = f"{dice}+{bonus}"
                elif bonus < 0:
                    damage_str = f"{dice}{bonus}"

                attacks.append({
                    "name": name,
                    "source": "power",
                    "attack_bonus": attack_bonus,
                    "damage": damage_str,
                    "damage_type": dmg_type,
                })

    return attacks


# main parser that reads the xml file and gathers the character info
def parse_character(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # fantasy grounds stores the pc under <character>
    character = root.find("character")
    if character is None:
        raise ValueError("no <character> element found in xml")

    # read basic character fields
    name = character.findtext("name", default="unknown")
    hp = parse_hp(character)
    ac = parse_ac(character)
    prof_bonus = parse_prof_bonus(character)

    # collect attacks from weapons and powers
    attacks = []
    attacks.extend(parse_weapon_attacks(character))
    attacks.extend(parse_power_attacks(character, prof_bonus))

    return {
        "name": name,
        "hp": hp,
        "ac": ac,
        "attacks": attacks,
    }


# print character info in a readable format
def display_character(character_data):
    print("\nCharacter Name:", character_data["name"])
    print("Hit Points:", character_data["hp"])
    print("Armor Class:", character_data["ac"])
    print("\nAttacks:")

    for atk in character_data["attacks"]:
        print(
            f" - {atk['name']} ({atk['source']}): "
            f"+{atk['attack_bonus']} to hit, {atk['damage']} {atk['damage_type']}"
        )


# run the parser if this file is executed directly
if __name__ == "__main__":
    import sys

    # detect if running inside a jupyter/ipython environment
    if "ipykernel" in sys.modules:
        # in notebooks we ignore sys.argv and use a fixed file path
        character_data = parse_character("glurp20.xml")  # change path if needed
        display_character(character_data)

    else:
        # running from the command line
        if len(sys.argv) < 2:
            print(f"usage: python {sys.argv[0]} <character_xml_file>")
            sys.exit(1)

        # parse the xml file provided on the command line
        character_data = parse_character(sys.argv[1])
        display_character(character_data)
