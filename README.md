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

1.  Download the pxp version of the database from Exiobase and place it in the `exiobase` folder (do not change file names): [Download Exiobase database](https://zenodo.org/records/14869924)

2.  Set up the fast-load databases:

    ```bash
    python setup.py
    ```

3.  Start the tool:

    ```bash
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
