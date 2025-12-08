# monster_parse.py

# imports
import re
import random
import requests
from dataclasses import dataclass, field
from typing import List, Optional
from bs4 import BeautifulSoup

from config import MONSTER_BASE_URL, MONSTER_FILENAMES


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
    recharge: Optional[str] = None   # ex "5–6" or "6"

    attack_bonus: Optional[int] = None
    damage_dice: Optional[str] = None
    damage_type: Optional[str] = None
    reach: Optional[str] = None
    range: Optional[str] = None

    save_ability: Optional[str] = None
    save_dc: Optional[int] = None


@dataclass
class Monster:
    name: str

    mtype: Optional[str] = None
    size: Optional[str] = None
    creature_type: Optional[str] = None
    alignment: Optional[str] = None

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

    traits: List[Trait] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    bonus_actions: List[BonusAction] = field(default_factory=list)
    legendary_actions: List[LegendaryAction] = field(default_factory=list)


# parse traits
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


# parse actions
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

        raw = strong.get_text(strip=True)
        raw_no_dot = raw.rstrip(".")

        parens = re.findall(r"\(([^)]+)\)", raw_no_dot)
        base_name = re.sub(r"\s*\([^)]*\)", "", raw_no_dot).strip()

        name = base_name
        usage = None
        recharge = None

        for part in parens:
            if re.search(r"recharge", part, re.I):
                m_rec = re.search(r"recharge\s*(.+)", part, re.I)
                recharge = m_rec.group(1).strip(" .") if m_rec else part.strip(" .")
            else:
                usage = part.strip(" .")

        body = re.sub(r"^" + re.escape(raw), "", txt, count=1).strip()

        if re.search(r"Attack Roll", txt):
            category = "attack"
        elif re.search(r"Saving Throw", txt):
            category = "save"
        else:
            category = "other"

        m_hit = re.search(r"Attack(?: Roll)?:\s*([+-]\d+)", txt)
        m_dmg = re.search(r"\(([\dd+\-\s]+)\)\s*([A-Za-z]+) damage", txt)
        m_reach = re.search(r"reach\s+([0-9]+(?:\s*ft\.)?)", txt)
        m_range = re.search(r"range\s+([0-9/ ]+ft\.)", txt)
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


# parse bonus actions
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
        usage = None

        m_use = re.search(r"\(([^)]+)\)$", name)
        if m_use:
            usage = m_use.group(1)
            name = name[: m_use.start()].strip()

        body = re.sub(r"^" + re.escape(raw), "", txt, count=1).strip()
        bonus.append(BonusAction(name=name, text=body, usage=usage))

    return bonus


# parse legendary actions
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
        usage = None

        m_use = re.search(r"\(([^)]+)\)$", name)
        if m_use:
            usage = m_use.group(1)
            name = name[: m_use.start()].strip()

        body = re.sub(r"^" + re.escape(raw), "", txt, count=1).strip()
        legs.append(LegendaryAction(name=name, text=body, usage=usage))

    return legs


# main stat block parser
def parse_monster_file(html: str) -> List[Monster]:
    soup = BeautifulSoup(html, "html.parser")
    monsters: List[Monster] = []

    for block in soup.find_all("div", class_=lambda c: c and "stat-block" in c):
        header = block.find(["h2", "h3", "h4"], class_=re.compile("heading-anchor")) \
                 or block.find(["h2", "h3", "h4"])

        if not header:
            continue

        name_tag = header.select_one("a.monster-tooltip") or header.find("a")
        name = name_tag.get_text(strip=True) if name_tag else header.get_text(" ", strip=True)

        type_p = header.find_next("p")
        mtype = type_p.get_text(" ", strip=True) if type_p else None

        size = None
        creature_type = None
        alignment = None

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

        ps = block.find_all("p")

        ac = None
        init = None
        hp = None

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

        def extract_line(key: str):
            for p in ps:
                strong = p.find("strong")
                if strong and strong.get_text(strip=True) == key:
                    full = p.get_text(" ", strip=True)
                    return re.sub(rf"^{key}\s*", "", full).strip()
            return None

        speed = extract_line("Speed")
        skills = extract_line("Skills")
        resistances = extract_line("Resistances")
        immunities = extract_line("Immunities")
        senses = extract_line("Senses")
        languages = extract_line("Languages")
        cr_text = extract_line("CR")

        pb = None
        cr = None

        if cr_text:
            m_pb = re.search(r"PB\s*([+-]\d+)", cr_text)
            pb = m_pb.group(1) if m_pb else None
            m_cr = re.search(r"([0-9]+(?:/[0-9]+)?)", cr_text)
            cr = m_cr.group(1) if m_cr else None

        passive = None
        if senses:
            m_pass = re.search(r"Passive Perception\s*(\d+)", senses)
            if m_pass:
                passive = int(m_pass.group(1))
                senses = re.sub(r";?\s*Passive Perception\s*\d+", "", senses).strip(" ;")
                if senses == "":
                    senses = None

        ability_fields = {
            f"{abbr}_{field}": None
            for abbr in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
            for field in ("score", "mod", "save")
        }

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

        traits = parse_traits(block)
        actions = parse_actions(block)
        bonus_actions = parse_bonus_actions(block)
        legendary_actions = parse_legendary_actions(block)

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

        for key, value in ability_fields.items():
            setattr(monster, key, value)

        monsters.append(monster)

    return monsters


# pretty print monster
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

            tag_text = f" ({'; '.join(tags)})" if tags else ""
            print(f"  • {a.name}{tag_text}: {a.text}")

    if m.bonus_actions:
        print("\nBonus Actions:")
        for b in m.bonus_actions:
            tag = f" ({b.usage})" if b.usage else ""
            print(f"  • {b.name}{tag}: {b.text}")

    if m.legendary_actions:
        print("\nLegendary Actions:")
        for l in m.legendary_actions:
            tag = f" ({l.usage})" if l.usage else ""
            print(f"  • {l.name}{tag}: {l.text}")

    print("=" * 70)


# find monster by exact name
def get_monster_by_name(name: str, monsters: List[Monster]) -> Optional[Monster]:
    target = name.lower().strip()
    for m in monsters:
        if m.name.lower() == target:
            return m
    return None


# build full URLs for monster txt files
def build_monster_urls(
    base_url: str = MONSTER_BASE_URL,
    filenames: List[str] = MONSTER_FILENAMES,
) -> List[str]:
    return [base_url + fn for fn in filenames]


# download + parse all monsters
def load_all_monsters() -> List[Monster]:
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


# main exec for debugging
if __name__ == "__main__":
    all_monsters = load_all_monsters()
    if all_monsters:
        print("Random sample of 10 monsters:")
        sample = random.sample(all_monsters, min(10, len(all_monsters)))
        for m in sample:
            print(f"  - {m.name}")