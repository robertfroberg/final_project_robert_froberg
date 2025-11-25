from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
import os


# helper converts values to ints safely
def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ensure damage dice always start with a number
def normalize_dice(dice):
    # if dice begins with d add leading 1
    if dice and dice.startswith("d"):
        return "1" + dice
    return dice


# dataclass for single attack
@dataclass
class Attack:
    name: str
    source: str
    to_hit: int
    damage_dice: str
    damage_bonus: int
    damage_type: str

    # string form for printing
    def __str__(self):
        return (
            f"{self.name} ({self.source}): "
            f"+{self.to_hit} to hit, {self.damage_dice}+{self.damage_bonus} {self.damage_type}"
        )


# feat dataclass
@dataclass
class Feat:
    name: str
    source: str = ""
    text: str = ""


# class species features dataclass
@dataclass
class Feature:
    name: str
    level: int = 0
    source: str = ""
    specialization: str = ""
    text: str = ""


# trait dataclass
@dataclass
class Trait:
    name: str
    source: str = ""
    trait_type: str = ""
    text: str = ""


# proficiency dataclass
@dataclass
class Proficiency:
    name: str


# language dataclass
@dataclass
class Language:
    name: str


# skill dataclass
@dataclass
class Skill:
    name: str
    stat: str
    total: int
    prof: int = 0
    misc: int = 0


# character dataclass
@dataclass
class Character:
    name: str
    level: int
    hp: int
    ac: int
    abilities: dict
    saves: dict
    prof_bonus: int
    initiative: int
    attacks: list = field(default_factory=list)
    feats: list = field(default_factory=list)
    features: list = field(default_factory=list)
    traits: list = field(default_factory=list)
    proficiencies: list = field(default_factory=list)
    languages: list = field(default_factory=list)
    skills: list = field(default_factory=list)


# parse abilities and modifiers from character xml
def parse_abilities(character_elem):
    abilities = {}
    for abil_name in ["strength", "dexterity", "constitution",
                      "intelligence", "wisdom", "charisma"]:
        abil_elem = character_elem.find(f"./abilities/{abil_name}")
        if abil_elem is None:
            continue
        score = safe_int(abil_elem.findtext("score", default="0"))
        mod = safe_int(abil_elem.findtext("bonus", default="0"))
        abilities[abil_name] = {"score": score, "mod": mod}
    return abilities


# parse saving throws from character xml
def parse_saves(character_elem):
    saves = {}
    for abil_name in ["strength", "dexterity", "constitution",
                      "intelligence", "wisdom", "charisma"]:
        abil_elem = character_elem.find(f"./abilities/{abil_name}")
        if abil_elem is None:
            continue
        save_val = safe_int(abil_elem.findtext("save", default="0"))
        saves[abil_name] = save_val
    return saves


# parse total hit points from character xml
def parse_hp(character_elem):
    return safe_int(character_elem.findtext("./hp/total", default="0"))


# parse armor class from character xml
def parse_ac(character_elem):
    return safe_int(character_elem.findtext("./defenses/ac/total", default="0"))


# parse proficiency bonus from character xml
def parse_prof_bonus(character_elem):
    return safe_int(character_elem.findtext("./profbonus", default="0"))


# parse level from character xml
def parse_level(character_elem):
    return safe_int(character_elem.findtext("./level", default="0"))


# parse init bonus from character xml
def parse_initiative(character_elem):
    init_elem = character_elem.find("./initiative")
    if init_elem is None:
        return 0
    total = safe_int(init_elem.findtext("total", default="0"))
    return total


# helper to decide which ability mod to use for attack
def get_attack_ability_mod(weapon_elem, abilities):
    # weapon type 0 = melee, 2 = ranged is a fantasy grounds convention
    w_type = safe_int(weapon_elem.findtext("type", default="0"))
    if w_type == 2:
        abil_name = "dexterity"
    else:
        abil_name = "strength"
    return abilities.get(abil_name, {}).get("mod", 0)


# helper to decide which ability mod to use for damage
def get_damage_ability_mod(dmg_elem, weapon_elem, abilities):
    stat_field = dmg_elem.findtext("stat", default="base")
    # base means same ability used for attack
    if stat_field == "base":
        return get_attack_ability_mod(weapon_elem, abilities)
    # if specific ability given use it
    if stat_field in abilities:
        return abilities[stat_field]["mod"]
    # default to strength
    return abilities.get("strength", {}).get("mod", 0)


# parse attacks listed under weaponlist into attack objects
def parse_weapon_attacks(character_elem, abilities, prof_bonus):
    attacks = []

    for weapon in character_elem.findall("./weaponlist/*"):
        name = weapon.findtext("name", default="unknown weapon")
        base_attack_bonus = safe_int(weapon.findtext("attackbonus", default="0"))
        prof_flag = safe_int(weapon.findtext("prof", default="0"))

        # ability used attack
        abil_mod = get_attack_ability_mod(weapon, abilities)

        # total to hit = proficiency + ability mod + weapon specific bonus
        to_hit = abil_mod + base_attack_bonus
        if prof_flag:
            to_hit += prof_bonus

        # process any damage entries with weapon
        for dmg in weapon.findall("./damagelist/*"):
            dice_raw = dmg.findtext("dice", default="")
            dice = normalize_dice(dice_raw)
            bonus = safe_int(dmg.findtext("bonus", default="0"))
            stat_mult = safe_int(dmg.findtext("statmult", default="1"))
            dmg_type = dmg.findtext("type", default="")

            # ability mod used for damage
            dmg_abil_mod = get_damage_ability_mod(dmg, weapon, abilities)

            # total damage bonus includes ability mod * stat_mult plus flat bonus
            total_damage_bonus = dmg_abil_mod * stat_mult + bonus

            attack = Attack(
                name=name,
                source="weapon",
                to_hit=to_hit,
                damage_dice=dice,
                damage_bonus=total_damage_bonus,
                damage_type=dmg_type,
            )
            attacks.append(attack)

    # sort highest to hit attacks to lowest
    attacks.sort(key=lambda a: (-a.to_hit, a.name))
    return attacks


# parse powers with damage entries and attack rolls into attack objects
def parse_power_attacks(character_elem, abilities, prof_bonus):
    attacks = []

    for power in character_elem.findall("./powers/*"):
        name = power.findtext("name", default="unnamed power")
        attack_bonus = None
        atk_ability_mod = 0

        # find casting actions to determine attack bonus and stat
        for action in power.findall("./actions/*"):
            if action.findtext("type", default="") == "cast":
                atkmod = safe_int(action.findtext("atkmod", default="0"))
                atkprof_flag = safe_int(action.findtext("atkprof", default="0"))
                atkstat = action.findtext("atkstat", default="strength")

                atk_ability_mod = abilities.get(atkstat, {}).get("mod", 0)
                attack_bonus = atk_ability_mod + atkmod
                if atkprof_flag:
                    attack_bonus += prof_bonus
                break

        # collect any damage entries for power
        for action in power.findall("./actions/*"):
            damagelist = action.find("damagelist")
            if damagelist is None:
                continue

            for dmg in damagelist.findall("./*"):
                dice_raw = dmg.findtext("dice", default="")
                dice = normalize_dice(dice_raw)
                bonus = safe_int(dmg.findtext("bonus", default="0"))
                dmg_type = dmg.findtext("type", default="")
                stat_mult = safe_int(dmg.findtext("statmult", default="0"))

                # damage ability mod from action stat if present else strength
                dmg_abil_mod = atk_ability_mod or abilities.get("strength", {}).get("mod", 0)
                total_damage_bonus = dmg_abil_mod * stat_mult + bonus

                attack = Attack(
                    name=name,
                    source="power",
                    to_hit=attack_bonus if attack_bonus is not None else 0,
                    damage_dice=dice,
                    damage_bonus=total_damage_bonus,
                    damage_type=dmg_type,
                )
                attacks.append(attack)

    return attacks


# parse feats from featlist
def parse_feats(character_elem):
    feats = []
    featlist = character_elem.find("featlist")
    if featlist is None:
        return feats
    for feat in featlist:
        name = feat.findtext("name", default="").strip()
        source = feat.findtext("source", default="").strip()
        text = feat.findtext("text", default="").strip()
        if name:
            feats.append(Feat(name=name, source=source, text=text))
    return feats


# parse features from featurelist
def parse_features(character_elem):
    features = []
    featurelist = character_elem.find("featurelist")
    if featurelist is None:
        return features
    for feat in featurelist:
        name = feat.findtext("name", default="").strip()
        source = feat.findtext("source", default="").strip()
        specialization = feat.findtext("specialization", default="").strip()
        text = feat.findtext("text", default="").strip()
        level = safe_int(feat.findtext("level", default="0"))
        if name:
            features.append(Feature(
                name=name,
                level=level,
                source=source,
                specialization=specialization,
                text=text,
            ))
    return features


# parse traits from traitlist
def parse_traits(character_elem):
    traits = []
    traitlist = character_elem.find("traitlist")
    if traitlist is None:
        return traits
    for t in traitlist:
        name = t.findtext("name", default="").strip()
        source = t.findtext("source", default="").strip()
        trait_type = t.findtext("type", default="").strip()
        text = t.findtext("text", default="").strip()
        if name:
            traits.append(Trait(
                name=name,
                source=source,
                trait_type=trait_type,
                text=text,
            ))
    return traits


# parse proficiencies from proficiencylist
def parse_proficiencies(character_elem):
    profs = []
    plist = character_elem.find("proficiencylist")
    if plist is None:
        return profs
    for p in plist:
        name = p.findtext("name", default="").strip()
        if name:
            profs.append(Proficiency(name=name))
    return profs


# parse languages from languagelist
def parse_languages(character_elem):
    langs = []
    llist = character_elem.find("languagelist")
    if llist is None:
        return langs
    for l in llist:
        name = l.findtext("name", default="").strip()
        if name:
            langs.append(Language(name=name))
    return langs


# parse skills from skilllist and calc final totals including prof bonus
def parse_skills(character_elem, abilities, prof_bonus):
    skills = []
    slist = character_elem.find("skilllist")
    if slist is None:
        return skills

    for s in slist:
        name = s.findtext("name", default="").strip()
        if not name:
            continue

        stat = s.findtext("stat", default="").strip()
        abil_mod = abilities.get(stat, {}).get("mod", 0)

        prof_flag = safe_int(s.findtext("prof", default="0"))  # 0=no prof, 1=prof, 2=expertise
        misc = safe_int(s.findtext("misc", default="0"))

        # final total skill modifier
        total = abil_mod + (prof_bonus * prof_flag) + misc

        skills.append(Skill(
            name=name,
            stat=stat,
            total=total,
            prof=prof_flag,
            misc=misc,
        ))

    return skills


# main parser that reads the xml file and builds a character object
def parse_character(xml_path):
    import os

    # if xml_path is absolute and exists, use it directly
    if os.path.isabs(xml_path) and os.path.exists(xml_path):
        resolved_path = xml_path
    else:
        # base directory is the folder this script is in (src/)
        base_dir = os.path.dirname(__file__)

        # candidate locations to search
        candidates = [
            os.path.join(base_dir, xml_path),                  # src/aeric20.xml
            os.path.join(base_dir, "data", xml_path),          # src/data/aeric20.xml
            os.path.join(base_dir, "..", "data", xml_path),    # ../data/aeric20.xml  (one level up)
        ]

        resolved_path = None
        for cand in candidates:
            if os.path.exists(cand):
                resolved_path = cand
                break

        if resolved_path is None:
            # helpful error message listing where was checked
            raise FileNotFoundError(
                "could not find xml file. tried:\n  " +
                "\n  ".join(candidates)
            )

    tree = ET.parse(resolved_path)
    root = tree.getroot()

    # fantasy grounds stores the pc under <character>
    character = root.find("character")
    if character is None:
        raise ValueError("no <character> element found in xml")

    # read basic character fields
    name = character.findtext("name", default="unknown")
    level = parse_level(character)
    hp = parse_hp(character)
    ac = parse_ac(character)
    prof_bonus = parse_prof_bonus(character)
    initiative = parse_initiative(character)

    # read abilities and saves
    abilities = parse_abilities(character)
    saves = parse_saves(character)

    # collect attacks from weapons and powers
    attacks = []
    attacks.extend(parse_weapon_attacks(character, abilities, prof_bonus))
    attacks.extend(parse_power_attacks(character, abilities, prof_bonus))

    # parse feat like stuff
    feats = parse_feats(character)
    features = parse_features(character)
    traits = parse_traits(character)
    proficiencies = parse_proficiencies(character)
    languages = parse_languages(character)
    skills = parse_skills(character, abilities, prof_bonus)

    return Character(
        name=name,
        level=level,
        hp=hp,
        ac=ac,
        abilities=abilities,
        saves=saves,
        prof_bonus=prof_bonus,
        initiative=initiative,
        attacks=attacks,
        feats=feats,
        features=features,
        traits=traits,
        proficiencies=proficiencies,
        languages=languages,
        skills=skills,
    )


# print character info in readable format
def display_character(character):
    print("\nCharacter Name:", character.name)
    print("Level:", character.level)
    print("Hit Points:", character.hp)
    print("Armor Class:", character.ac)
    print("Initiative Bonus:", character.initiative)
    print("Proficiency Bonus:", character.prof_bonus)

    # abilities stay in STR to CHA order
    print("\nAbilities and Saves:")
    order = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
    for abil in order:
        abil_data = character.abilities.get(abil, {})
        score = abil_data.get("score", None)
        mod = abil_data.get("mod", None)
        save = character.saves.get(abil, None)
        label = abil.capitalize()
        print(f" - {label:12s} Score: {score:2}  Mod: {mod:2}  Save: {save:2}")

    # alphabetized skills
    print("\nSkills:")
    for sk in sorted(character.skills, key=lambda s: s.name.lower()):
        stat_label = sk.stat.capitalize()
        print(
            f" - {sk.name:20s} ({stat_label:12s}) "
            f"Total: {sk.total:2}  Proficiency: {sk.prof}  Misc: {sk.misc}"
        )

    # attacks stay sorted by to-hit
    print("\nAttacks:")
    for atk in character.attacks:
        print(f" - {atk}")

    # alphabetized feats
    print("\nFeats:")
    for f in sorted(character.feats, key=lambda x: x.name.lower()):
        print(f" - {f.name}")

    # alphabetized features
    print("\nFeatures:")
    for f in sorted(character.features, key=lambda x: x.name.lower()):
        print(f" - {f.name} (Level {f.level}, Source {f.source})")

    # alphabetized traits
    print("\nTraits:")
    for t in sorted(character.traits, key=lambda x: x.name.lower()):
        print(f" - {t.name} ({t.trait_type})")

    # alphabetized proficiencies
    print("\nProficiencies:")
    for p in sorted(character.proficiencies, key=lambda x: x.name.lower()):
        print(f" - {p.name}")

    # alphabetized languages
    print("\nLanguages:")
    for l in sorted(character.languages, key=lambda x: x.name.lower()):
        print(f" - {l.name}")


# run the parser if this file is executed directly
if __name__ == "__main__":
    import sys

    # detect if running inside jupyter nb
    if "ipykernel" in sys.modules:
        # defaults to aeric20.xml as this project scope has ballooned a little bit
        pc = parse_character("aeric20.xml")
        display_character(pc)
    else:
        if len(sys.argv) < 2:
            print(f"usage: python {sys.argv[0]} <character_xml_file>")
            sys.exit(1)
        pc = parse_character(sys.argv[1])
        display_character(pc)