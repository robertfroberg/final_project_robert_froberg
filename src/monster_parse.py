# imports
import re
from dataclasses import dataclass, field
from typing import List, Optional
import random
import requests
from bs4 import BeautifulSoup


# data classes
@dataclass
class Trait:
    name: str
    text: str


@dataclass
class BonusAction:
    name: str
    text: str
    usage: Optional[str] = None


@dataclass
class LegendaryAction:
    name: str
    text: str
    usage: Optional[str] = None


@dataclass
class Action:
    name: str
    text: str
    category: Optional[str] = None
    usage: Optional[str] = None
    recharge: Optional[str] = None   # e.g. "5–6" or "6"

    attack_bonus: Optional[int] = None
    damage_dice: Optional[str] = None
    damage_type: Optional[str] = None
    reach: Optional[str] = None
    range: Optional[str] = None

    save_ability: Optional[str] = None
    save_dc: Optional[int] = None


@dataclass
class Monster:
    # monster name
    name: str

    # type and alignment
    mtype: Optional[str] = None
    size: Optional[str] = None
    creature_type: Optional[str] = None
    alignment: Optional[str] = None

    # basic stats
    ac: Optional[int] = None
    initiative: Optional[int] = None
    hp: Optional[int] = None
    speed: Optional[str] = None
    skills: Optional[str] = None
    resistances: Optional[str] = None
    immunities: Optional[str] = None
    senses: Optional[str] = None
    languages: Optional[str] = None
    cr: Optional[str] = None
    pb: Optional[str] = None
    passive_perception: Optional[int] = None

    # ability scores and saves
    STR_score: Optional[str] = None
    STR_mod: Optional[str] = None
    STR_save: Optional[str] = None
    DEX_score: Optional[str] = None
    DEX_mod: Optional[str] = None
    DEX_save: Optional[str] = None
    CON_score: Optional[str] = None
    CON_mod: Optional[str] = None
    CON_save: Optional[str] = None
    INT_score: Optional[str] = None
    INT_mod: Optional[str] = None
    INT_save: Optional[str] = None
    WIS_score: Optional[str] = None
    WIS_mod: Optional[str] = None
    WIS_save: Optional[str] = None
    CHA_score: Optional[str] = None
    CHA_mod: Optional[str] = None
    CHA_save: Optional[str] = None

    # structured sections
    traits: List[Trait] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    bonus_actions: List[BonusAction] = field(default_factory=list)
    legendary_actions: List[LegendaryAction] = field(default_factory=list)


# parse traits section inside statblock
def parse_traits(block) -> List[Trait]:
    traits: List[Trait] = []

    header = block.find("p", class_="monster-header", string=re.compile("Traits", re.I))
    if not header:
        return traits

    for p in header.find_all_next("p"):
        if block not in p.parents:
            break
        if "monster-header" in (p.get("class") or []) and p is not header:
            break

        txt = p.get_text(" ", strip=True)
        strong = p.find("strong")
        if not strong:
            continue

        raw = strong.get_text(strip=True)
        name = raw.rstrip(".")
        text = re.sub(r"^" + re.escape(raw), "", txt, count=1).strip()

        traits.append(Trait(name=name, text=text))

    return traits


# parse actions section inside stat block
def parse_actions(block):
    actions: List[Action] = []

    header = block.find("p", class_="monster-header", string=re.compile("Actions", re.I))
    if not header:
        return actions

    for p in header.find_all_next("p"):
        if block not in p.parents:
            break
        if "monster-header" in (p.get("class") or []) and p is not header:
            break

        txt = p.get_text(" ", strip=True)
        strong = p.find("strong")
        if not strong:
            continue

        # remove extra characters
        raw = strong.get_text(strip=True)
        raw_no_dot = raw.rstrip(".")

        # pull out (...) from name line
        parens = re.findall(r"\(([^)]+)\)", raw_no_dot)

        # strip all (...) from base name
        base_name = re.sub(r"\s*\([^)]*\)", "", raw_no_dot).strip()

        name = base_name
        usage: Optional[str] = None
        recharge: Optional[str] = None

        for part in parens:
            # parse recharge logic
            if re.search(r"recharge", part, re.I):
                m_rec = re.search(r"recharge\s*(.+)", part, re.I)
                recharge = m_rec.group(1).strip(" .") if m_rec else part.strip(" .")
            else:
                # parse times usable per day
                usage = part.strip(" .")

        # body text everything after bold name line
        body = re.sub(r"^" + re.escape(raw), "", txt, count=1).strip()

        # classify action
        if re.search(r"Attack Roll", txt):
            category = "attack"
        elif re.search(r"Saving Throw", txt):
            category = "save"
        else:
            category = "other"

        # attack extraction
        m_hit = re.search(r"Attack(?: Roll)?:\s*([+-]\d+)", txt)
        m_dmg = re.search(r"\(([\dd+\-\s]+)\)\s*([A-Za-z]+) damage", txt)
        m_reach = re.search(r"reach\s+([0-9]+(?:\s*ft\.)?)", txt)
        m_range = re.search(r"range\s+([0-9/ ]+ft\.)", txt)

        # save extraction
        m_save = re.search(r"([A-Za-z]+)\s+Saving Throw:\s*DC\s*(\d+)", txt)

        actions.append(
            Action(
                name=name,
                text=body,
                category=category,
                usage=usage,
                recharge=recharge,
                attack_bonus=int(m_hit.group(1)) if m_hit else None,
                damage_dice=m_dmg.group(1).strip() if m_dmg else None,
                damage_type=m_dmg.group(2).lower() if m_dmg else None,
                reach=m_reach.group(1) if m_reach else None,
                range=m_range.group(1) if m_range else None,
                save_ability=m_save.group(1) if m_save else None,
                save_dc=int(m_save.group(2)) if m_save else None,
            )
        )

    return actions


# parse bonus actions inside statblock
def parse_bonus_actions(block) -> List[BonusAction]:
    bonus: List[BonusAction] = []

    header = block.find("p", class_="monster-header", string=re.compile("Bonus Actions", re.I))
    if not header:
        return bonus

    for p in header.find_all_next("p"):
        if block not in p.parents:
            break
        if "monster-header" in (p.get("class") or []) and p is not header:
            break

        txt = p.get_text(" ", strip=True)
        strong = p.find("strong")
        if not strong:
            continue

        raw = strong.get_text(strip=True)
        name = raw.rstrip(".")
        usage: Optional[str] = None

        # pull out usage like
        m_use = re.search(r"\(([^)]+)\)$", name)
        if m_use:
            usage = m_use.group(1)
            name = name[: m_use.start()].strip()

        body = re.sub(r"^" + re.escape(raw), "", txt, count=1).strip()
        bonus.append(BonusAction(name=name, text=body, usage=usage))

    return bonus


# parse legendary actions inside stat block
def parse_legendary_actions(block) -> List[LegendaryAction]:
    legs: List[LegendaryAction] = []

    header = block.find("p", class_="monster-header", string=re.compile("Legendary Actions", re.I))
    if not header:
        return legs

    for p in header.find_all_next("p"):
        if block not in p.parents:
            break
        if "monster-header" in (p.get("class") or []) and p is not header:
            break

        txt = p.get_text(" ", strip=True)
        strong = p.find("strong")
        if not strong:
            continue

        raw = strong.get_text(strip=True)
        name = raw.rstrip(".")
        usage: Optional[str] = None

        # pull out usage
        m_use = re.search(r"\(([^)]+)\)$", name)
        if m_use:
            usage = m_use.group(1)
            name = name[: m_use.start()].strip()

        body = re.sub(r"^" + re.escape(raw), "", txt, count=1).strip()
        legs.append(LegendaryAction(name=name, text=body, usage=usage))

    return legs


# main monster parser
def parse_monster_file(html: str) -> List[Monster]:
    soup = BeautifulSoup(html, "html.parser")
    monsters: List[Monster] = []

    # find heading for start of monster using h2/h3/h4
    for block in soup.find_all("div", class_=lambda c: c and "stat-block" in c):
        header = block.find(["h2", "h3", "h4"], class_=re.compile("heading-anchor")) or \
                 block.find(["h2", "h3", "h4"])

        if not header:
            continue

        # get monster name from tooltip link or header text
        name_tag = header.select_one("a.monster-tooltip") or header.find("a")
        name = name_tag.get_text(strip=True) if name_tag else header.get_text(" ", strip=True)

        # get size/type/alignment data
        type_p = header.find_next("p")
        mtype = type_p.get_text(" ", strip=True) if type_p else None

        size: Optional[str] = None
        creature_type: Optional[str] = None
        alignment: Optional[str] = None

        if mtype:
            parts = mtype.split(",", 1)
            size_type = parts[0].strip()
            alignment = parts[1].strip() if len(parts) > 1 else None

            words = size_type.split()
            if len(words) >= 3 and words[1].lower() == "or":
                size = " ".join(words[:3])
                creature_type = " ".join(words[3:])
            else:
                size = words[0]
                creature_type = " ".join(words[1:])

        # read <p> tags inside stat block for core stats
        ps = block.find_all("p")

        ac: Optional[int] = None
        init: Optional[int] = None
        hp: Optional[int] = None

        for p in ps:
            strong = p.find("strong")
            if not strong:
                continue
            label = strong.get_text(strip=True)
            txt = p.get_text(" ", strip=True)
            if label == "AC":
                m_ac = re.search(r"AC\s+(\d+)", txt)
                ac = int(m_ac.group(1)) if m_ac else None
                m_init = re.search(r"Initiative\s*([+-]?\d+)", txt)
                init = int(m_init.group(1)) if m_init else None
            elif label == "HP":
                m_hp = re.search(r"HP\s+(\d+)", txt)
                hp = int(m_hp.group(1)) if m_hp else None

        # helper extracts oneliners like speed skills etc
        def extract_line(key: str) -> Optional[str]:
            for p in ps:
                strong = p.find("strong")
                if strong and strong.get_text(strip=True) == key:
                    full = p.get_text(" ", strip=True)
                    return re.sub(rf"^{key}\s*", "", full).strip()
            return None

        # extract core lines
        speed = extract_line("Speed")
        skills = extract_line("Skills")
        resistances = extract_line("Resistances")
        immunities = extract_line("Immunities")
        senses = extract_line("Senses")
        languages = extract_line("Languages")
        cr_text = extract_line("CR")

        pb: Optional[str] = None
        cr: Optional[str] = None

        # parse CR line for CR and PB
        if cr_text:
            m_pb = re.search(r"PB\s*([+-]\d+)", cr_text)
            pb = m_pb.group(1) if m_pb else None
            m_cr = re.search(r"([0-9]+(?:/[0-9]+)?)", cr_text)
            cr = m_cr.group(1) if m_cr else None

        # parse passive percep out of senses
        passive: Optional[int] = None
        if senses:
            m_pass = re.search(r"Passive Perception\s*(\d+)", senses)
            if m_pass:
                passive = int(m_pass.group(1))
                senses = re.sub(r";?\s*Passive Perception\s*\d+", "", senses).strip(" ;")
                if senses == "":
                    senses = None

        # set up ability fields
        ability_fields = {
            f"{abbr}_{field}": None
            for abbr in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
            for field in ("score", "mod", "save")
        }

        # parse physical and mental ability tables
        for tbl_class in ("physical abilities-saves", "mental abilities-saves"):
            tbl = block.find("table", class_=tbl_class)
            if tbl and tbl.tbody:
                for row in tbl.tbody.find_all("tr"):
                    th = row.find("th")
                    if not th:
                        continue
                    abbr = th.get_text(" ", strip=True).upper()
                    if abbr not in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
                        continue
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        ability_fields[f"{abbr}_score"] = cells[0].get_text(" ", strip=True)
                        ability_fields[f"{abbr}_mod"] = cells[1].get_text(" ", strip=True)
                        ability_fields[f"{abbr}_save"] = cells[2].get_text(" ", strip=True)

        # parse sections including traits, actions, bonus actions, legendary actions
        traits = parse_traits(block)
        actions = parse_actions(block)
        bonus_actions = parse_bonus_actions(block)
        legendary_actions = parse_legendary_actions(block)

        # build monster object
        monster = Monster(
            name=name,
            mtype=mtype,
            size=size,
            creature_type=creature_type,
            alignment=alignment,
            ac=ac,
            initiative=init,
            hp=hp,
            speed=speed,
            skills=skills,
            resistances=resistances,
            immunities=immunities,
            senses=senses,
            languages=languages,
            cr=cr,
            pb=pb,
            passive_perception=passive,
            traits=traits,
            actions=actions,
            bonus_actions=bonus_actions,
            legendary_actions=legendary_actions,
        )

        # attach ability scores and saves to monster
        for key, value in ability_fields.items():
            setattr(monster, key, value)

        monsters.append(monster)

    return monsters


# pretty print readable stat block for one monstre
def pretty_print_monster(m: Monster) -> None:
    print("=" * 70)
    print(m.name)
    if m.size or m.creature_type:
        type_line = f"{m.size or ''} {m.creature_type or ''}".strip()
        if m.alignment:
            type_line += f", {m.alignment}"
        print(type_line)
    print("-" * 70)

    print(f"AC {m.ac or '—'} | HP {m.hp or '—'} | Initiative {m.initiative or '—'}")
    print(f"Speed: {m.speed or '—'}")

    if m.skills:
        print(f"Skills: {m.skills}")
    if m.resistances:
        print(f"Resistances: {m.resistances}")
    if m.immunities:
        print(f"Immunities: {m.immunities}")

    senses_line = m.senses or "—"
    if m.passive_perception:
        senses_line += f" (Passive Perception {m.passive_perception})"
    print(f"Senses: {senses_line}")

    print(f"Languages: {m.languages or '—'}")

    cr_disp = m.cr or "—"
    if m.pb:
        cr_disp += f" (PB {m.pb})"
    print(f"CR: {cr_disp}")

    print("\nAbility Scores:")

    def score(abbr: str) -> str:
        sc = getattr(m, f"{abbr}_score") or "—"
        md = getattr(m, f"{abbr}_mod") or "—"
        sv = getattr(m, f"{abbr}_save") or "—"
        return f"{abbr} {sc} ({md}) Save {sv}"

    print(f"{score('STR'):28} {score('DEX')}")
    print(f"{score('CON'):28} {score('INT')}")
    print(f"{score('WIS'):28} {score('CHA')}")

    if m.traits:
        print("\nTraits:")
        for t in m.traits:
            print(f"  • {t.name}: {t.text}")

    if m.actions:
        print("\nActions:")
        for a in m.actions:
            tags = []
            if a.recharge:
                tags.append(f"Recharge {a.recharge}")
            if a.usage:
                tags.append(a.usage)

            if tags:
                print(f"  • {a.name} ({'; '.join(tags)}): {a.text}")
            else:
                print(f"  • {a.name}: {a.text}")

    if m.bonus_actions:
        print("\nBonus Actions:")
        for b in m.bonus_actions:
            if b.usage:
                print(f"  • {b.name} ({b.usage}): {b.text}")
            else:
                print(f"  • {b.name}: {b.text}")

    if m.legendary_actions:
        print("\nLegendary Actions:")
        for l in m.legendary_actions:
            if l.usage:
                print(f"  • {l.name} ({l.usage}): {l.text}")
            else:
                print(f"  • {l.name}: {l.text}")

    print("=" * 70)

# find monster with case-insensitive exact name match
def get_monster_by_name(name: str, monsters: List[Monster]) -> Optional[Monster]:
    target = name.lower().strip()
    for m in monsters:
        if m.name.lower() == target:
            return m
    return None

# base url for stat block text files
BASE_URL = "https://froberg5.wpcomstaging.com/wp-content/uploads/2025/11/"

# filenames a.txt through z.txt plus animals.txt
FILENAMES = [f"{chr(c)}.txt" for c in range(ord("a"), ord("z") + 1)]
FILENAMES.append("animals.txt")


# build full URLs for monster txt files
def build_monster_urls(
    base_url: str = BASE_URL,
    filenames: List[str] = FILENAMES,
) -> List[str]:
    return [base_url + fn for fn in filenames]


# parse all monster files and return list of monster objects
def load_all_monsters() -> List["Monster"]:
    urls = build_monster_urls()
    all_monsters: List[Monster] = []

    for url in urls:
        try:
            print(f"Downloading {url} ...")
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  http {resp.status_code}, skipping.")
                continue

            html = resp.content.decode("utf-8", errors="replace")
            if "stat-block" not in html:
                print("  Warning: No 'stat-block' found in this file, skipping.")
                continue

            monsters = parse_monster_file(html)
            print(f"  Parsed {len(monsters)} monsters.")
            all_monsters.extend(monsters)

        except Exception as e:
            print(f"  Error parsing {url}: {e}")

    print(f"Total monsters loaded: {len(all_monsters)}")
    return all_monsters


# main exec for testing this module directly
if __name__ == "__main__":
    all_monsters = load_all_monsters()

    if all_monsters:
        print("Random sample of 10 monsters:")
        sample_size = min(10, len(all_monsters))
        sample = random.sample(all_monsters, sample_size)
        for m in sample:
            print(f"  - {m.name}")


"""
# main exec
if __name__ == "__main__":
    # base url for stat block text files
    base_url = "https://froberg5.wpcomstaging.com/wp-content/uploads/2025/11/"

    # build list of filenames a.txt through z.txt plus animals.txt
    filenames = [f"{chr(c)}.txt" for c in range(ord("a"), ord("z") + 1)]
    filenames.append("animals.txt")

    # join base url and filenames into full urls
    urls = [base_url + fn for fn in filenames]

    # list holding all monsters from all files
    all_monsters: List[Monster] = []

    # download and parse files
    for url in urls:
        try:
            print(f"Downloading {url} ...")
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  http {resp.status_code}, skipping.")
                continue

            # decode utf-8 and keep going even if bytes are weird
            html = resp.content.decode("utf-8", errors="replace")
            if "stat-block" not in html:
                print("  Warning: No 'stat-block' found in this file, skipping.")
                continue

            monsters = parse_monster_file(html)
            print(f"  Parsed {len(monsters)} monsters.")
            all_monsters.extend(monsters)
        except Exception as e:
            print(f"  Error parsing {url}: {e}")

    # final summary of how many monsters were loaded
    print(f"Total monsters loaded: {len(all_monsters)}")

    # show random sample of 10 monsters
    if all_monsters:
        print("Random sample of 10 monsters:")

        sample_size = min(10, len(all_monsters))
        sample = random.sample(all_monsters, sample_size)

        for m in sample:
            print(f"  - {m.name}")
            """
