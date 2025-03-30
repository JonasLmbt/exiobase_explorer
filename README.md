# Exiobase Explorer 
A Python tool for analyzing Exiobase data with various modules for IO systems, impact analysis, and supply chain management.

## Features
- **IOSystem Module**: Loads and processes input-output data from Exiobase.
- **SupplyChain Module**: Models supply chains with hierarchical structures.

---

## Installation

### 1️⃣ Clone the repository
git clone https://github.com/Zorbas05/exiobase_explorer.git
cd exiobase_explorer

### 2️⃣ Create a virtual environment (optional, but recommended)

python -m venv venv

### 3️⃣ Install dependencies

pip install -r requirements.txt

---

## Usage

To use the Exiobase Explorer:

    # Write your code into main.py or create new programs in the exiobase_explorer folder. Then import the classes:
    from src.IOSystem import IOSystem
    from src.SupplyChain import SupplyChain

Download exiobases databases (don't change the name) and put them into the empty folder "exiobase".

Create an instance and load data:

    database = IOSystem(year=2022, language="english").load()

---

## Modules
IOSystem

Handles the loading and processing of input-output data from Exiobase. It includes methods for managing databases and calculating IO matrices.

SupplyChain

Models and analyzes supply chains using hierarchical structures, with functions for managing different sectors and economic divisions.
