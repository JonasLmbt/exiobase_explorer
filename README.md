# Exiobase Explorer

> **Note:** This project is still under development.

A Python tool for analyzing Exiobase data with modules for input-output systems, impact analysis, and supply chain management.

-----

## Features

  - **IOSystem Module**: Loads and processes input-output data from Exiobase.
  - **SupplyChain Module**: Models and analyzes supply chains with hierarchical structures.

-----

## Installation

1.  **Clone the repository**

    ```bash
    git clone https://github.com/JonasLmbt/exiobase_explorer.git
    ```
    ```bash
    cd exiobase_explorer
    ```

2.  **Create a virtual environment (recommended)**

    ```bash
    python -m venv venv
    ```

    **Windows:**

    ```bash
    venv\Scripts\activate
    ```

    **macOS/Linux:**

    ```bash
    source venv/bin/activate
    ```

3.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

-----

## Usage

1.  Download the databases (select a version prior to 3.9.4 and always use pxp) and place the zip files in a database folder.

    - Default folder: `exiobase/`
    - Required file naming: `IOT_<YEAR>_pxp.zip` (do not rename)
    - 2022 is required (recommended: download all years you need)

    Source: [Download Exiobase database](https://zenodo.org/records/5589597)

2.  Set up the fast-load databases:

    ```bash
    python setup.py
    ```

    Optional arguments:

    - Use a custom database folder:

      ```bash
      python setup.py "D:\EXIOBASE"
      ```

    - Delete the original zip files after a successful fast-db build (default: keep):

      ```bash
      python setup.py --delete-zips
      ```

    Notes:

    - Fast-load databases are created in the same database folder as `FAST_IOT_<YEAR>_pxp/`.
    - Legacy config Excel files inside fast-load folders are removed automatically; configs are managed centrally under `config/`.

3.  Start the tool:

    ```bash
    python main.py
    ```

    If you used a custom database folder, point the app to it via environment variable:

    - PowerShell:

      ```powershell
      $env:EXIOBASE_EXPLORER_DB_DIR="D:\EXIOBASE"
      python main.py
      ```

-----

## Modules

  - **IOSystem**

      - Loading and processing input-output data from Exiobase
      - Database management and calculation of IO matrices

  - **SupplyChain**

      - Modeling and analysis of supply chains with hierarchical structures
      - Functions for managing sectors and economic units

-----
