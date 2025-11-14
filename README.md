# final\_project\_robert\_froberg

Final Project for DSCI510 Fall 2025



\# DSCI 510 Final Project – D\&D Combat Simulator



This project implements a Monte Carlo combat simulator for Fifth Edition Dungeons \& Dragons. Character data, magic items, and monster statistics are parsed and combined to estimate win probability, expected rounds of combat, and damage output for different scenarios.



Local files are used for character and item information, and monster data is retrieved from the Open5E API. The project is organized with separate modules for data parsing, API access, and simulation logic to keep the workflow modular and easy to test.



\## Project Structure

\- character\_parser.py  

\- item\_parser.py  

\- open5e\_client.py  

\- simulator.py  

\- tests.py  



\## Installation

Use the following command to install required packages:

pip install -r requirements.txt



\## Running Tests

A simple test script is included:

python tests.py



This runs basic checks for data loading, API connectivity, and a sample combat simulation.



\## Usage

After adding your character and item files to the local data folder, you can run simulations to analyze combat performance and compare different configurations.



