# Exiobase Explorer 
A Python tool for analyzing Exiobase data with various modules for IO systems, impact analysis, and supply chain management.

## Features
- **IOSystem Module**: Loads and processes input-output data from Exiobase.
- **Impact Module**: Computes environmental impacts and stores them as numpy arrays.
- **Index Module**: Creates and manages indexes for data analysis.
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

    # Import the IOSystem class (or other modules) in your Python code:
    from tools.IOSystem import IOSystem

Insert the downloaded Exiobase Databases into the corresponding folder /exiobase

Create an instance and load data:

    database = IOSystem(compressed_path=compressed_path, year=2022, language="english")
    database.load()

---

## Modules
IOSystem

Handles the loading and processing of input-output data from Exiobase. It includes methods for managing databases and calculating IO matrices.

SupplyChain

Models and analyzes supply chains using hierarchical structures, with functions for managing different sectors and economic divisions.
