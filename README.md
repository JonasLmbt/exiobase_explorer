# Exiobase Explorer 

NOTE: This project is still in development 

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
    venv\Scripts\activate

### 3️⃣ Install dependencies

    pip install -r requirements.txt

---

## Usage

Download databases from exiobase on their website (don't change the name!) and put them into the empty folder "exiobase".

    https://zenodo.org/records/14869924

Setup the fast load databases:

    python setup.py

Run main.py to use the exiobase explorer.

---

## Modules
IOSystem

Handles the loading and processing of input-output data from Exiobase. It includes methods for managing databases and calculating IO matrices.

SupplyChain

Models and analyzes supply chains using hierarchical structures, with functions for managing different sectors and economic divisions.
