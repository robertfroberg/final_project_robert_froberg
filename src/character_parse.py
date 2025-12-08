# character_parse.py
# parses fantasy grounds pc xml into a Character object

from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
import os

from config import DATA_DIR


# helper converts values to ints
def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# helper normalizes dice strings
def normalize_dice(dice):
    if dice and dice.startswith("d"):
        return "1" + dice
    return dice


# attack dataclass
@dataclass
class Attack:
    name: str
    source: str
    to_hit: int
    damage_dice: str
    damage_bonus: int
    damage_type: str

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


# class/feature dataclass
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


# parse ability scores/modifiers
def parse_abilities(character_elem):
    abilities = {}
    for abil_name in ["strength", "dexterity", "constitution",
                      "intelligence", "wisdom", "charisma"]:
        abil_elem = character_elem.find(f"./abilities/{abil_name}")
        if abil_elem is None:
            continue
        score = safe_int(abil_elem.findtext("score", "0"))
        mod = safe_int(abil_elem.findtext("bonus", "0"))
        abilities[abil_name] = {"score": score, "mod": mod}
    return abilities


# parse saving throws
def parse_saves(character_elem):
    saves = {}
    for abil_name in ["strength", "dexterity", "constitution",
                      "intelligence", "wisdom", "charisma"]:
        abil_elem = character_elem.find(f"./abilities/{abil_name}")
        if abil_elem is None:
            continue
        saves[abil_name] = safe_int(abil_elem.findtext("save", "0"))
    return saves


# parse hp
def parse_hp(character_elem):
    return safe_int(character_elem.findtext("./hp/total", "0"))


# parse ac
def parse_ac(character_elem):
    return safe_int(character_elem.findtext("./defenses/ac/total", "0"))


# parse proficiency bonus
def parse_prof_bonus(character_elem):
    return safe_int(character_elem.findtext("./profbonus", "0"))


# parse level
def parse_level(character_elem):
    return safe_int(character_elem.findtext("./level", "0"))


# parse initiative bonus
def parse_initiative(character_elem):
    init_elem = character_elem.find("./initiative")
    if init_elem is None:
        return 0
    return safe_int(init_elem.findtext("total", "0"))


# ability mod used for weapon attack
def get_attack_ability_mod(weapon_elem, abilities):
    w_type = safe_int(weapon_elem.findtext("type", "0"))
    abil_name = "dexterity" if w_type == 2 else "strength"
    return abilities.get(abil_name, {}).get("mod", 0)


# ability mod used for damage
def get_damage_ability_mod(dmg_elem, weapon_elem, abilities):
    stat_field = dmg_elem.findtext("stat", "base")
    if stat_field == "base":
        return get_attack_ability_mod(weapon_elem, abilities)
    if stat_field in abilities:
        return abilities[stat_field]["mod"]
    return abilities.get("strength", {}).get("mod", 0)


# parse attacks from weaponlist
def parse_weapon_attacks(character_elem, abilities, prof_bonus):
    attacks = []

    for weapon in character_elem.findall("./weaponlist/*"):
        name = weapon.findtext("name", "unknown weapon")
        base_attack_bonus = safe_int(weapon.findtext("attackbonus", "0"))
        prof_flag = safe_int(weapon.findtext("prof", "0"))

        abil_mod = get_attack_ability_mod(weapon, abilities)
        to_hit = abil_mod + base_attack_bonus + (prof_bonus if prof_flag else 0)

        for dmg in weapon.findall("./damagelist/*"):
            dice = normalize_dice(dmg.findtext("dice", ""))
            bonus = safe_int(dmg.findtext("bonus", "0"))
            stat_mult = safe_int(dmg.findtext("statmult", "1"))
            dmg_type = dmg.findtext("type", "")

            dmg_abil_mod = get_damage_ability_mod(dmg, weapon, abilities)
            total_damage_bonus = dmg_abil_mod * stat_mult + bonus

            attacks.append(
                Attack(
                    name=name,
                    source="weapon",
                    to_hit=to_hit,
                    damage_dice=dice,
                    damage_bonus=total_damage_bonus,
                    damage_type=dmg_type,
                )
            )

    # sort strongest to weakest
    attacks.sort(key=lambda a: (-a.to_hit, a.name))
    return attacks


# parse spell/power attacks
def parse_power_attacks(character_elem, abilities, prof_bonus):
    attacks = []

    for power in character_elem.findall("./powers/*"):
        name = power.findtext("name", "unnamed power")
        attack_bonus = None
        atk_ability_mod = 0

        # find cast line
        for action in power.findall("./actions/*"):
            if action.findtext("type", "") == "cast":
                atkmod = safe_int(action.findtext("atkmod", "0"))
                atkprof_flag = safe_int(action.findtext("atkprof", "0"))
                atkstat = action.findtext("atkstat", "strength")

                atk_ability_mod = abilities.get(atkstat, {}).get("mod", 0)
                attack_bonus = atk_ability_mod + atkmod + (prof_bonus if atkprof_flag else 0)
                break

        # damage entries
        for action in power.findall("./actions/*"):
            damagelist = action.find("damagelist")
            if damagelist is None:
                continue

            for dmg in damagelist.findall("./*"):
                dice = normalize_dice(dmg.findtext("dice", ""))
                bonus = safe_int(dmg.findtext("bonus", "0"))
                dmg_type = dmg.findtext("type", "")
                stat_mult = safe_int(dmg.findtext("statmult", "0"))

                dmg_abil_mod = atk_ability_mod or abilities.get("strength", {}).get("mod", 0)
                total_damage_bonus = dmg_abil_mod * stat_mult + bonus

                attacks.append(
                    Attack(
                        name=name,
                        source="power",
                        to_hit=attack_bonus or 0,
                        damage_dice=dice,
                        damage_bonus=total_damage_bonus,
                        damage_type=dmg_type,
                    )
                )
    return attacks


# parse feats
def parse_feats(character_elem):
    feats = []
    featlist = character_elem.find("featlist")
    if featlist is None:
        return feats

    for feat in featlist:
        name = feat.findtext("name", "").strip()
        if name:
            feats.append(
                Feat(
                    name=name,
                    source=feat.findtext("source", "").strip(),
                    text=feat.findtext("text", "").strip(),
                )
            )
    return feats


# parse features
def parse_features(character_elem):
    features = []
    featurelist = character_elem.find("featurelist")
    if featurelist is None:
        return features

    for f in featurelist:
        name = f.findtext("name", "").strip()
        if name:
            features.append(
                Feature(
                    name=name,
                    level=safe_int(f.findtext("level", "0")),
                    source=f.findtext("source", "").strip(),
                    specialization=f.findtext("specialization", "").strip(),
                    text=f.findtext("text", "").strip(),
                )
            )
    return features


# parse traits
def parse_traits(character_elem):
    traits = []
    traitlist = character_elem.find("traitlist")
    if traitlist is None:
        return traits

    for t in traitlist:
        name = t.findtext("name", "").strip()
        if name:
            traits.append(
                Trait(
                    name=name,
                    source=t.findtext("source", "").strip(),
                    trait_type=t.findtext("type", "").strip(),
                    text=t.findtext("text", "").strip(),
                )
            )
    return traits


# parse proficiencies
def parse_proficiencies(character_elem):
    profs = []
    plist = character_elem.find("proficiencylist")
    if plist is None:
        return profs
    for p in plist:
        name = p.findtext("name", "").strip()
        if name:
            profs.append(Proficiency(name=name))
    return profs


# parse languages
def parse_languages(character_elem):
    langs = []
    llist = character_elem.find("languagelist")
    if llist is None:
        return langs
    for l in llist:
        name = l.findtext("name", "").strip()
        if name:
            langs.append(Language(name=name))
    return langs


# parse skills
def parse_skills(character_elem, abilities, prof_bonus):
    skills = []
    slist = character_elem.find("skilllist")
    if slist is None:
        return skills

    for s in slist:
        name = s.findtext("name", "").strip()
        if not name:
            continue

        stat = s.findtext("stat", "").strip()
        abil_mod = abilities.get(stat, {}).get("mod", 0)

        prof_flag = safe_int(s.findtext("prof", "0"))
        misc = safe_int(s.findtext("misc", "0"))

        total = abil_mod + prof_bonus * prof_flag + misc

        skills.append(
            Skill(
                name=name,
                stat=stat,
                total=total,
                prof=prof_flag,
                misc=misc,
            )
        )

    return skills


# load pc xml from /data
def parse_character(xml_filename: str):
    path = os.path.join(DATA_DIR, xml_filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"PC XML not found: {path}")

    tree = ET.parse(path)
    root = tree.getroot()

    character = root.find("character")
    if character is None:
        raise ValueError("No <character> element found")

    name = character.findtext("name", "unknown")
    level = parse_level(character)
    hp = parse_hp(character)
    ac = parse_ac(character)
    prof_bonus = parse_prof_bonus(character)
    initiative = parse_initiative(character)

    abilities = parse_abilities(character)
    saves = parse_saves(character)

    attacks = []
    attacks.extend(parse_weapon_attacks(character, abilities, prof_bonus))
    attacks.extend(parse_power_attacks(character, abilities, prof_bonus))

    feats = parse_feats(character)
    features = parse_features(character)
    traits = parse_traits(character)
    profs = parse_proficiencies(character)
    langs = parse_languages(character)
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
        proficiencies=profs,
        languages=langs,
        skills=skills,
    )


# pretty printer for debugging
def display_character(character):
    print("\nName:", character.name)
    print("Level:", character.level)
    print("Hit Points:", character.hp)
    print("Armor Class:", character.ac)
    print("Initiative:", character.initiative)
    print("Proficientcy Bonus:", character.prof_bonus)

    print("\nAbilities:")
    for k in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        a = character.abilities.get(k, {})
        print(f"  {k:12s} score {a.get('score')}  mod {a.get('mod')}  save {character.saves.get(k)}")

    print("\nSkills:")
    for s in sorted(character.skills, key=lambda x: x.name.lower()):
        print(f"  {s.name:20s} ({s.stat:10s}) total {s.total}")

    print("\nAttacks:")
    for atk in character.attacks:
        print(f"  {atk}")

    print("\nFeats:")
    for f in sorted(character.feats, key=lambda x: x.name.lower()):
        print(f"  {f.name}")

    print("\nFeatures:")
    for f in sorted(character.features, key=lambda x: x.name.lower()):
        print(f"  {f.name} (lvl {f.level})")

    print("\nTraits:")
    for t in sorted(character.traits, key=lambda x: x.name.lower()):
        print(f"  {t.name}")

    print("\nProficiencies:")
    for p in sorted(character.proficiencies, key=lambda x: x.name.lower()):
        print(f"  {p.name}")

    print("\nLanguages:")
    for l in sorted(character.languages, key=lambda x: x.name.lower()):
        print(f"  {l.name}")


# quick test
if __name__ == "__main__":
    char = parse_character("aeric20.xml")
    display_character(char)