# final\_project\_robert\_froberg

DSCI 510 Final Project
Dungeons & Dragons Combat Simulator
Monte Carlo Engine for Modeling 5E Combat Outcomes

INTRODUCTION
This project implements a Monte Carlo–based combat simulator for Dungeons & Dragons 5th Edition. It integrates three independent datasets—PC XML files, monster stat blocks, and magic item inventories—to build a complete computational model of one-on-one combat.

The simulator runs thousands of automated combats between a Player Character and a Monster. Each combat resolves initiative, attack rolls, hit and miss outcomes, critical hits, recharge abilities, damage dice, and round-by-round combat resolution. The system produces statistical outputs such as win probability, average rounds per fight, hit percentages, damage distributions, and initiative effects.

DATA SOURCES
This project uses three primary data sources:

Player Character XML File
Description: Full character sheet including AC, HP, ability scores, attacks, and features.
Processing Approach: Parsed using a custom XML parser that extracts attack routines, ability modifiers, HP, AC, initiative, and damage formulas.
Purpose: Provides the PC’s combat statistics.

Monster Stat Blocks (HTML)
Description: Monster AC, HP, actions, recharge abilities, resistances, saves, and action text.
Processing Approach: Cleaned and parsed with BeautifulSoup, actions categorized into attacks or saving-throw-based abilities, recharge mechanics implemented, and structured into Monster dataclasses.
Purpose: Defines enemy combat behavior.

Magic Item Excel Workbook
Description: Magic item inventory by character, including rarity, trade status, carried items, and special properties.
Processing Approach: Loaded with openpyxl and pandas; font colors mapped to rarity; borders determine carried items; bold/italic text indicate rewards and certifications.
Purpose: Generates inventory summaries, rarity tables, and trade lists.

ANALYSIS
The analysis includes several components:

Data Cleaning and Integration
Parsing XML, HTML, and Excel sources; normalizing dice expressions; extracting structured attack routines; and matching PC names to magic item inventories using fuzzy matching.

Combat Simulation Logic
A round-based system handles initiative, attack rolls, critical hits, damage, recharge mechanics, and defeat conditions when HP reaches zero.

Monte Carlo Simulation
The combat engine is repeated independently thousands of times, capturing hits, misses, critical hits, damage totals, rounds fought, and initiative results.

Statistical Summaries
Win/loss/draw percentages, hit/miss accuracy, average rounds per fight, damage distributions, and average performance of individual attacks.

Visualization
Charts include win distribution, hits vs. misses, per-fight averages, round distribution histograms, initiative vs. outcome matrices, damage per attack, and damage per fight histograms.

SUMMARY OF RESULTS
Initial testing shows that PCs with high attack bonuses have significantly higher hit rates. Monster recharge abilities introduce substantial outcome variability. Early-round critical hits heavily influence win probability. Initiative bonuses correlate strongly with overall victory, and defensive builds tend to produce longer but more stable fights.

HOW TO RUN
Project Structure:

final_project
main.py
README.md
requirements.txt
data/
aeric20.xml
results/
src/
tests.py
character_parse.py
combat_sim.py
monster_parse.py
magic_items.py
visualize_outcomes.py
config.py

Dependencies:
Install required packages using:

pip install -r requirements.txt

This installs matplotlib, pandas, openpyxl, requests, and beautifulsoup4.

Data Requirements:
Place the following file in the data folder:

PC XML file

Running the Project:
From the project root:

python main.py

Output:
Simulation summaries print in the console.
Charts and analysis graphs are saved under the results folder.
Magic item lists export to MagicItemList_items.csv.
PC magic item summaries print to the console.

API Keys:
No API keys are required. All data except the XML file is loaded from an internet site.

I attempted to use the Google Drive data workaround but Python couldn’t access my Google Drive files because, on my government computer, it needs to scan the files so when python attempts to download the file it gets an html like page with an error message. Since I cannot test the code without the government machine I feel it was better to have a project I knew that worked rather than a project that might work. I jully understand if points are deducted for my choice. I loaded the non-XMLs on the website I paid for a single month of hosting on to make this project work but XML files are not allowed to be hosted on their site.