# config.py
# shared paths and urls for the combat simulator

import os

# folder names inside project root
DATA_DIR_NAME = "data"
DEFAULT_RESULTS_DIR_NAME = "results"

# resolve src and project root based on this file location
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# full path to data folder
DATA_DIR = os.path.join(PROJECT_ROOT, DATA_DIR_NAME)

# url for the magic item workbook
MAGIC_ITEM_URL = (
    "https://froberg5.wpcomstaging.com/wp-content/uploads/2025/12/MagicItemList.xlsx"
)

# base url for monster stat block text files
MONSTER_BASE_URL = "https://froberg5.wpcomstaging.com/wp-content/uploads/2025/11/"

# filenames a.txt through z.txt plus animals.txt
MONSTER_FILENAMES = [f"{chr(c)}.txt" for c in range(ord("a"), ord("z") + 1)]
MONSTER_FILENAMES.append("animals.txt")

DEFAULT_PC_XML_FILENAME = "aeric20.xml"

