"""
IOSystem.py

An Input-Output System for processing EXIOBASE databases with optimized
performance and unified code style.
"""

import io
import itertools
import json
import logging
import os
import shutil
import sys
import time
import zipfile
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd

# Configure logging for clear output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    stream=sys.stdout 
)

class Index:
    """
    The Index class is responsible for managing sector, region, and impact indices 
    within the IOSystem. It provides functionalities to read and update hierarchical 
    multi-indices, load data from Excel files, and generate new Excel files for sectoral 
    and regional classifications.

    Key Responsibilities:
    - Loading sector, region, and impact data from Excel files.
    - Constructing MultiIndex structures for hierarchical data representation.
    - Updating matrix labels to ensure consistency within the IOSystem.
    - Creating new Excel files for sectoral, regional, and impact classifications.

    Attributes:
        IOSystem: The main input-output system object that stores economic and 
                  environmental data, including matrices for analysis.

    Methods:
        read_configs(): Reads sector, region, and impact data from Excel files 
                       and constructs MultiIndex structures.
        update_multiindices(): Updates all matrices within the IOSystem to use 
                               the correct hierarchical indices.
        write_configs(language=None): Generates and saves sector, region, impact, 
                                      and unit classification data into Excel files.
    """
    
    def __init__(self, iosystem):
        """
        Initializes the Index object with a reference to the IOSystem object.

        Args:
            iosystem: Reference to the IOSystem object
        """
        self.iosystem = iosystem

        # Initialize attributes that will be populated by read_configs
        self.sectors_df = None
        self.raw_materials_df = None
        self.regions_df = None
        self.exiobase_to_map_df = None
        self.impacts_df = None
        self.impact_color_df = None
        self.units_df = None
        self.general_df = None

        self.amount_sectors = None
        self.amount_regions = None
        self.amount_impacts = None

        self.general_dict = {}
        self.raw_material_indices = []
        self.not_raw_material_indices = []
        self.languages = []

    def read_configs(self) -> None:
        """
        Reads and processes multiple Excel files, loading data into corresponding instance variables for later use in 
        the IOSystem. The method validates the structure and content of each Excel sheet, ensuring that the data 
        meets expected formats and lengths.

        The method performs the following actions:
        - Maps each data attribute to its corresponding Excel file and sheet based on the system's language setting.
        - Reads the data from Excel files and assigns them to instance variables (e.g., `self.sectors_df`, `self.regions_df`).
        - Reverses the column order for certain DataFrames to ensure consistency in hierarchical processing.
        - Verifies that the expected number of rows in each DataFrame matches a predefined value to maintain data integrity.
        - Checks for duplicate column names in certain sheets and raises an error if found.
        - Catches and logs `FileNotFoundError` if any required Excel files are missing, and raises the exception with a clear message.
        - Validates data lengths to ensure that each DataFrame has the expected number of rows.
        - Stores unit transformation data for later use in unit calculations and creates a dictionary mapping 'exiobase' to 'translation' from the general data.

        Raises:
        - FileNotFoundError: If a required Excel file is missing.
        - ValueError: If there are any issues with duplicate columns or mismatched row lengths.

        This method ensures that all necessary data is loaded into the system and validated, allowing for reliable processing 
        in subsequent steps.
        """
        
        try:
            # Mapping of df_id to file names, sheet names, and expected lengths
            file_mapping = {
                "sectors_df": ("sectors.xlsx", self.iosystem.language, 200),
                "raw_materials_df": ("sectors.xlsx", "raw_material", 200),
                "regions_df": ("regions.xlsx", self.iosystem.language, 49),
                "exiobase_to_map_df": ("regions.xlsx", "map", 178),
                "impacts_df": ("impacts.xlsx", self.iosystem.language, 126),
                "impact_color_df": ("impacts.xlsx", "color", 126),
                "units_df": ("units.xlsx", self.iosystem.language, 126),
                "general_df": ("general.xlsx", self.iosystem.language, 12)
            }

            # Attempt to load each Excel file and assign it to the corresponding attribute
            for df_id, (file_name, sheet_name, expected_length) in file_mapping.items():
                try:
                    # Read the Excel file and set the corresponding attribute
                    file_path = os.path.join(self.iosystem.current_fast_database_path, file_name)
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    amount = len(df)

                    # For sectors_df, regions_df, and impacts_df: reverse column order and check for duplicates
                    if df_id in ['sectors_df', 'regions_df', 'impacts_df']:
                        # Reverse column order for consistent hierarchical processing
                        df = df.iloc[:, ::-1]

                        # Store the number of rows as reference
                        setattr(self, f"amount_{df_id[:-3]}", amount)

                        # Check for unique column names
                        duplicate_columns = df.columns[df.columns.duplicated()]
                        if len(duplicate_columns) > 0:
                            raise ValueError(
                                f"Sheet '{sheet_name}' in '{file_name}' contains duplicate column names: "
                                f"{', '.join(duplicate_columns)}"
                            )

                    # Verify length
                    if amount != expected_length and file_name != "general.xlsx":
                        raise ValueError(
                            f"Expected {expected_length} rows in sheet '{sheet_name}' of '{file_name}', "
                            f"but found {amount}"
                        )

                    # Set the DataFrame as an instance variable
                    setattr(self, df_id, df)
                    logging.debug(f"Successfully loaded: {file_name}/{sheet_name} ({amount} rows)")

                except FileNotFoundError:
                    logging.error(f"Missing Excel file: {file_name}")
                    raise
                except Exception as e:
                    logging.error(f"Error loading {file_name}/{sheet_name}: {e}")
                    raise

            # Store unit transformations for later use in unit calculations
            self.iosystem.index.unit_transform = self.units_df.values.tolist()

            # Create a dictionary from the 'general_df' DataFrame, mapping 'exiobase' to 'translation'
            self.general_dict = dict(zip(self.general_df['exiobase'], self.general_df['translation']))

            # Create list of all raw material indices
            self._create_raw_material_indices()

            # Determine available languages
            self._determine_available_languages()

            logging.debug("Configuration files successfully read")

        except Exception as e:
            logging.error(f"Error during Excel reading and processing: {e}")
            raise

    def _create_raw_material_indices(self) -> None:
        """
        Creates lists of raw material and non-raw material indices.
        """
        # Create base indices
        raw_material_base = self.raw_materials_df[
            self.raw_materials_df['raw_material'] == True
        ].index.tolist()

        not_raw_material_base = self.raw_materials_df[
            self.raw_materials_df['raw_material'] == False
        ].index.tolist()

        # Create expanded indices for all regions
        self.raw_material_indices = []
        self.not_raw_material_indices = []

        for region in range(1, 49):  # for each region
            self.raw_material_indices.extend([region * 200 + idx for idx in raw_material_base])
            self.not_raw_material_indices.extend([region * 200 + idx for idx in not_raw_material_base])

    def _determine_available_languages(self) -> None:
        """
        Determines available languages from Excel files.
        """
        try:
            file_path = os.path.join(self.iosystem.current_fast_database_path, "general.xlsx")
            with pd.ExcelFile(file_path) as xls:
                self.languages = xls.sheet_names
        except FileNotFoundError:
            logging.warning("Could not find 'general.xlsx' to determine available languages")
            self.languages = []

    def create_multiindices(self) -> None:
        """
        Creates MultiIndex structures for sector, region, and impact matrices in the IOSystem. This method
        generates hierarchical indices to manage the relationships between sectors, regions, and impacts. 

        The method performs the following actions:
        - Expands the `sectors_df` DataFrame to match the number of regions, ensuring each sector exists for each region.
        - Matches regions to sectors by repeating the region indices to align with the number of sectors.

        The method generates the following MultiIndices:
        - `self.sector_multiindex`: A hierarchical MultiIndex for sectors and regions, forming a hierarchical index based on region and sector data.
        - `self.impact_multiindex`: A hierarchical MultiIndex for impacts, allowing for easy reference of impact categories in the system.
        - `self.region_multiindex`: A region-specific MultiIndex, useful for region-based indexing.
        - `self.sector_multiindex_per_region`: A sector-specific MultiIndex for a single region, allowing for region-specific sectoral analysis.

        The MultiIndex structures are used for efficiently referencing and indexing sector-based and impact-based data 
        in matrices, enabling the system to handle complex, multi-dimensional relationships between regions, sectors, 
        and impacts.
        """

        # Expand sectors to match all regions
        self.matching_sectors_df = pd.concat([self.sectors_df] * self.amount_regions, ignore_index=True)

        # Match regions to sectors
        self.matching_regions_df = self.regions_df.loc[
            np.repeat(self.regions_df.index, self.amount_sectors)
        ].reset_index(drop=True)

        # Create MultiIndex for sectors and regions
        self.sector_multiindex = pd.MultiIndex.from_arrays(
            [self.matching_regions_df[col] for col in self.matching_regions_df.columns] +
            [self.matching_sectors_df[col] for col in self.matching_sectors_df.columns],
            names=(self.matching_regions_df.columns.tolist() +
                   self.matching_sectors_df.columns.tolist())
        )

        # Create MultiIndex for impacts
        self.impact_multiindex = pd.MultiIndex.from_arrays(
            [self.impacts_df[col] for col in self.impacts_df.columns],
            names=self.impacts_df.columns.tolist()
        )

        # Create MultiIndex only for regions
        self.region_multiindex = pd.MultiIndex.from_arrays(
            [self.regions_df[col] for col in self.regions_df.columns],
            names=self.regions_df.columns.tolist()
        )

        # Create MultiIndex for sectors per region
        self.sector_multiindex_per_region = pd.MultiIndex.from_arrays(
            [self.sectors_df[col] for col in self.sectors_df.columns],
            names=self.sectors_df.columns.tolist()
        )

        # Create MultiIndex for impact per region
        self.impact_per_region_multiindex = pd.MultiIndex.from_tuples(
            [imp + reg for imp, reg in itertools.product(self.impact_multiindex, self.region_multiindex)],
            names=list(self.impact_multiindex.names) + list(self.region_multiindex.names)
        )

        logging.debug("MultiIndices successfully created")

    def update_multiindices(self) -> None:
        """
        Updates the MultiIndex structures for sector and impact matrices in the IOSystem. This method loads the
        latest Excel data, creates and updates MultiIndex structures for key matrices (A, L, Y, I), impact matrices 
        (S, total, retail, etc.), and regional matrices if available. It also extracts unique sector, region, 
        and impact names for system-wide reference and updates the impact units DataFrame.

        The method performs the following actions:
        - Loads the latest sector, region, and impact data from Excel files.
        - Creates or updates the MultiIndex structures for sector-based matrices (A, L, Y, I).
        - Updates the MultiIndex for impact matrices (S, total, retail, etc.), ensuring correct labeling.
        - If regional matrices exist, updates them with appropriate region-based MultiIndexes.
        - Extracts unique names for sectors, regions, impacts, and units to be used throughout the system.
        - Updates the `regions_exiobase` list from the "regions.xlsx" file.
        - Updates the impact unit DataFrame, ensuring each impact has its corresponding unit.

        The method relies on the `self.sectors_df`, `self.regions_df`, `self.impacts_df`, and other class attributes 
        to manage the data. It is intended to ensure that all matrices in the IOSystem are correctly indexed and 
        labeled for further analysis.
        """

        # Load the latest config data and update sector and impact multiindices
        self.read_configs()
        self.create_multiindices()

        # Extract unique names for system-wide reference
        self.iosystem.sectors = self.sectors_df.iloc[:, -1].unique().tolist()
        self.iosystem.regions = self.regions_df.iloc[:, -1].unique().tolist()
        self.iosystem.impacts = self.impacts_df.iloc[:, -1].unique().tolist()
        self.iosystem.units = self.units_df.iloc[:, -1].tolist()

        # Load 'regions_exiobase' data
        regions_exiobase_path = os.path.join(self.iosystem.current_fast_database_path, 'regions.xlsx')
        regions_exiobase_df = pd.read_excel(regions_exiobase_path, sheet_name="Exiobase")
        self.iosystem.regions_exiobase = regions_exiobase_df.iloc[:, -1].unique().tolist()

        # Update impact units DataFrame
        self.iosystem.impact.unit = pd.DataFrame(
            {"unit": self.iosystem.units},
            index=self.iosystem.impacts
        )

        # Define matrix mappings
        matrix_mappings = {
            "standard_matrices": ["A", "L", "Y", "I"],
            "impact_matrices": ["S", "D_cba"],
            "regional_impact_matrices": ["total", "retail", "direct_suppliers",
                                        "resource_extraction", "preliminary_products"],
            "regional_matrices": ["retail_regional", "direct_suppliers_regional",
                                 "resource_extraction_regional", "preliminary_products_regional"]
        }

        # Update matrix indices
        self._update_matrix_indices(matrix_mappings)

        # Store classification structures
        self.sector_classification = self.sectors_df.columns.tolist()
        self.region_classification = self.regions_df.columns.tolist()
        self.impact_classification = self.impacts_df.columns.tolist()

        # Update the map
        self.update_map()

        logging.debug("MultiIndices successfully updated")

    def _update_matrix_indices(self, matrix_mappings: Dict[str, List[str]]) -> None:
        """
        Updates indices for different matrix groups.
        """
        for matrix_group, matrices in matrix_mappings.items():
            if matrix_group == "standard_matrices":
                for matrix_name in matrices:
                    if hasattr(self.iosystem, matrix_name):
                        matrix_data = getattr(self.iosystem, matrix_name)
                        matrix_data.index = matrix_data.columns = self.sector_multiindex

            elif matrix_group == "impact_matrices":
                for matrix_name in matrices:
                    if hasattr(self.iosystem.impact, matrix_name):
                        impact_matrix = getattr(self.iosystem.impact, matrix_name)
                        impact_matrix.index = self.impact_multiindex
                        impact_matrix.columns = self.sector_multiindex

            elif matrix_group == "regional_impact_matrices":
                for matrix_name in matrices:
                    if hasattr(self.iosystem.impact, matrix_name):
                        impact_matrix = getattr(self.iosystem.impact, matrix_name)
                        impact_matrix.index = self.impact_per_region_multiindex
                        impact_matrix.columns = self.sector_multiindex

            elif (matrix_group == "regional_matrices" and
                  self.iosystem.impact.region_indices is not None):
                for matrix_name in matrices:
                    if hasattr(self.iosystem.impact, matrix_name):
                        regional_matrix = getattr(self.iosystem.impact, matrix_name)
                        regional_matrix.index = self.impact_multiindex
                        regional_matrix.columns = self.sector_multiindex

    def copy_configs(self, new: bool = False, output: bool = True) -> None:
        """
        Copies configuration files from the /config folder to the fast load database.

        Args:
            new: Indicates whether new configuration (not used)
            output: Whether to display logging output
        """
        if output:
            logging.info("Copying config files from /config to the fast load database...")

        config_files = ["sectors.xlsx", "regions.xlsx", "impacts.xlsx", "units.xlsx", "general.xlsx"]

        for file_name in config_files:
            source_file = os.path.join(self.iosystem.config_dir, file_name)
            target_file = os.path.join(self.iosystem.current_fast_database_path, file_name)

            if os.path.exists(source_file):
                try:
                    shutil.copy(source_file, target_file)
                    if output:
                        logging.info(f"File {file_name} has been successfully copied" +
                                   ("\n" if file_name == config_files[-1] else ""))
                except Exception as e:
                    logging.error(f"Error copying {file_name}: {e}")
            else:
                logging.error(f"File {file_name} not found in folder {self.iosystem.config_dir}")

        self.read_configs()

    def write_configs(self, sheet_name: str) -> None:
        """
        Creates or updates Excel files for various datasets (sectors, regions, impacts, etc.) based on the provided 
        or default sheet name. This function will write the data to corresponding Excel files, either creating new ones 
        or appending to existing files. It handles special cases for certain sheets (e.g., 'exiobase') and allows 
        for the creation of sheets with custom names.

        Parameters:
        - sheet_name (str, optional): The name of the sheet to be used for writing the data. If None, 
        the default sheet name is determined by the system's language setting.

        The following files are processed:
        - "sectors.xlsx", "regions.xlsx", "impacts.xlsx", "units.xlsx", "general.xlsx"
        - Additional sheets are written as needed (e.g., "map", "color").

        The method handles the following:
        - Creates DataFrames for sectors, regions, impacts, and related data (units, general info).
        - Writes these DataFrames to the corresponding Excel sheets.
        - Ensures the Excel files are properly updated or created.
        - Provides error handling for common issues, including permission errors when opening files.

        Raises:
        - PermissionError: If any Excel file is open during the write process.
        - Exception: If any unexpected error occurs during the execution of the method.
        """

        # File paths and corresponding DataFrames
        file_data = {
            "sectors.xlsx": [(self.sectors_df.iloc[:, ::-1], sheet_name),
                            (self.raw_materials_df, "raw_material")],
            "regions.xlsx": [(self.regions_df.iloc[:, ::-1], sheet_name),
                            (self.exiobase_to_map_df, "map")],
            "impacts.xlsx": [(self.impacts_df.iloc[:, ::-1], sheet_name),
                            (self.impact_color_df, "color")],
            "units.xlsx": [(self.units_df, sheet_name)],
            "general.xlsx": [(self.general_df, sheet_name)]
        }

        # Write to Excel files
        try:
            for file_name, sheets in file_data.items():
                file_path = os.path.join(self.iosystem.current_fast_database_path, file_name)
                mode = "a" if os.path.exists(file_path) else "w"

                with pd.ExcelWriter(file_path, engine="openpyxl", mode=mode) as writer:
                    for df, sheet in sheets:
                        try:
                            df.to_excel(writer, sheet_name=sheet, index=False)
                        except Exception as e:
                            logging.error(f"Error writing to sheet '{sheet}' "
                                        f"in file '{file_name}': {e}")

            logging.info("Excel files have been successfully created or updated")
        except PermissionError:
            raise PermissionError("Make sure to close all Excel files "
                                "before running the program")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

    def update_map(self, force: bool = False) -> None:
        """
        Creates or updates a GeoDataFrame for world regions, mapping Exiobase regions to geographical regions 
        based on the provided or default natural earth shapefile. This method loads the shapefile, applies the region 
        mapping, and dissolves the geometries by region to create a region-based GeoDataFrame. If a GeoDataFrame 
        already exists, it can be refreshed by setting the `force` parameter to True.

        Parameters:
        - naturalearth_path (str, optional): The path to the Natural Earth shapefile for world countries. 
        If None, a default URL is used to download the shapefile. Default is "ne_110m_admin_0_countries.zip".
        - force (bool, optional): If set to True, the method will force a refresh of the `world` GeoDataFrame, 
        even if it already exists. Default is False.

        The method performs the following actions:
        - Reads the shapefile for world countries using Geopandas.
        - Maps Exiobase regions to the corresponding world regions using `exiobase_to_map_df`.
        - Adds a new column for regions based on the mapping and dissolves geometries by region to create a simplified world map.
        - Returns a copy of the resulting GeoDataFrame.
        """
        try:
            world_map_path = os.path.join(self.iosystem.data_dir, "data_world_map.zip")
            self.world = gpd.read_file(world_map_path)

            self.exiobase_to_map_dict = dict(
                zip(self.exiobase_to_map_df['NAME'], self.exiobase_to_map_df['region'])
            )

            self.world["region"] = self.world["NAME"].map(self.exiobase_to_map_dict)
            self.world = self.world[["region", "geometry"]]
            self.world = self.world.dissolve(by="region")

            logging.debug("World map successfully updated")

        except Exception as e:
            logging.error(f"Error updating map: {e}")

    def get_map(self) -> gpd.GeoDataFrame:
        """
        Returns the geopandas world map with EXIOBASE regions as indices.

        Returns:
            Copy of the world map GeoDataFrame
        """
        return self.world.copy()


class Impact:
    """
    The Impact class handles the loading and storage of impact matrices within an 
    Input-Output system. These matrices are essential for analyzing economic and 
    environmental impacts across different sectors and regions.

    The class reads impact matrices from `.npy` files and stores them as Pandas 
    DataFrames, making them easily accessible for further processing and analysis.

    Args:
        IOSystem (object): An instance of the Input-Output system, which provides 
                           access to stored impact data and configurations.

    Attributes:
        iosystem: Reference to the associated IOSystem instance.
        color: Stores impact colors dictionary 
        unit_transform: Stores unit transformation data for impact calculations.
        region_indices: Stores region-specific indices for impact matrices.

    Loaded Impact Matrices:
        - 'S.npy' → `S`: General impact matrix.
        - 'D_cba.npy' → `D_cba`: Total impact matrix.
        - 'total.npy' → `total`: Total impact matrix.
        - 'retail.npy' → `retail`: Retail impact matrix.
        - 'direct_suppliers.npy' → `direct_suppliers`: Direct suppliers' impact matrix.
        - 'resource_extraction.npy' → `resource_extraction`: Resource extraction impact matrix.
        - 'preliminary_products.npy' → `preliminary_products`: Preliminary products impact matrix.

    These matrices enable detailed analysis of sector-specific and regional impacts 
    within the IOSystem.
    """

    def __init__(self, iosystem):
        """
        Initializes the Impact object with a reference to the IOSystem object.

        Args:
            iosystem: Reference to the IOSystem object
        """
        self.iosystem = iosystem
        self.color = None
        self.unit_transform = None
        self.region_indices = None

    def load(self) -> None:
        """
        This method loads various impact matrices from `.npy` files and stores them as DataFrames in instance variables.
        It first defines the file paths for the impact matrices and then attempts to load each file in a loop. 
        If a file is not found or the data cannot be converted to the expected format, an error is raised and logged. 
        On successful loading, the data is stored as `float32` values in DataFrames for further processing.

        The following impact matrices are loaded:
        - 'S' (Standard matrix)
        - 'total' (Total impact)
        - 'retail' (Retail impact)
        - 'direct_suppliers' (Direct suppliers impact)
        - 'resource_extraction' (Resource extraction impact)
        - 'preliminary_products' (Preliminary products impact)
        """
        # Mapping of file_id to file names and expected shapes
        file_mapping = {
            "S": ("S.npy", (126, 9800)),
            "D_cba": ("D_cba.npy", (126, 9800)),
            "total": ("total.npy", (6174, 9800)),
            "retail": ("retail.npy", (6174, 9800)),
            "direct_suppliers": ("direct_suppliers.npy", (6174, 9800)),
            "resource_extraction": ("resource_extraction.npy", (6174, 9800)),
            "preliminary_products": ("preliminary_products.npy", (6174, 9800))
        }

        for file_id, (filename, expected_shape) in file_mapping.items():
            file_path = os.path.join(self.iosystem.current_fast_database_path, "impacts", filename)
            try:
                array = np.load(file_path).astype(np.float32)
                if array.shape != expected_shape:
                    raise ValueError(f"Unexpected shape of {filename}: {array.shape}")
                setattr(self, file_id, pd.DataFrame(array))
                logging.debug(f"Impact matrix '{file_id}' successfully loaded")
            except Exception as e:
                logging.error(f"Error while loading {filename}: {e}")

    def get_color(self, impact: str) -> str:
        """
        Retrieves the color associated with a specific impact.

        Args:
            impact: Name of the impact

        Returns:
            Hex color code or #ffffff as default
        """
        try:
            # Extract the relevant impact column
            impact_list = self.iosystem.index.impacts_df.iloc[:, -1].tolist()

            # Find index of the impact
            idx = impact_list.index(impact)

            # Retrieve corresponding color
            return self.iosystem.index.impact_color_df.iloc[idx]["color"]

        except (ValueError, AttributeError, IndexError, KeyError) as e:
            # Handle cases where impact is not found
            logging.warning(f"Color for impact '{impact}' not found: {e}")
            return "#ffffff"

    def get_unit(self, impact: str) -> str:
        """
        Retrieves the unit associated with a specific impact.

        Args:
            impact: Name of the impact

        Returns:
            Unit of the impact
        """
        try:
            # Extract the relevant impact column
            impact_list = self.iosystem.index.impacts_df.iloc[:, -1].tolist()

            # Find index of the impact
            idx = impact_list.index(impact)

            # Retrieve corresponding unit
            return self.iosystem.index.units_df.iloc[idx].iloc[4]

        except (ValueError, AttributeError, IndexError) as e:
            logging.warning(f"Unit for impact '{impact}' not found: {e}")
            return "Unknown"

    def get_regional_impacts(self, region_indices: List[int]) -> None:
        """ 
        Adjusts the environmental impact calculations to ensure that all sectors 
        within the specified region (defined by `region_indices`) are counted as part of the 
        final production stage (`retail`). 
    
        This function is used when analyzing the entire supply chain of a region, without focusing 
        on a specific sector. In this case, the region itself is treated as the retail location, 
        meaning that resources, preliminary products, and direct suppliers within the region 
        are included in the retail impact instead of being categorized as external inputs.
    
        Parameters:
        ----------
        region_indices : list of int
            The indices of the sectors that belong to the specified region. These indices 
            determine which sectors should be reassigned from their usual categories 
            (e.g., resource extraction, preliminary products, or direct suppliers) to retail, 
            ensuring that all domestically produced impacts remain within the regional analysis.
        """  
        if region_indices != self.region_indices:
            self.region_indices = region_indices

            logging.info("Calculating regional impact matrices...\n")

            # Convert key matrices to NumPy arrays for efficient calculations
            S = self.S.to_numpy()  # Environmental impact factor matrix
            Y = self.iosystem.Y.to_numpy()  # Final demand matrix
            A = self.iosystem.A.to_numpy()  # Input-output coefficient matrix
            L = self.iosystem.L.to_numpy()  # Leontief inverse matrix

            # Pre-calculate a few matrices for cleaner logic
            I = np.identity(A.shape[0])
            L_minus_I = L - I
            raw_material_indices = self.iosystem.index.raw_material_indices
            not_raw_material_indices = self.iosystem.index.not_raw_material_indices

            # Step 1: Define the supply chain matrices

            # Direct suppliers: Exclude raw material sectors
            direct_suppliers = A.copy()
            direct_suppliers[raw_material_indices, :] = 0

            # Resource extraction: Only consider raw material sectors
            resource_extraction = L_minus_I.copy()
            resource_extraction[not_raw_material_indices, :] = 0

            # Preliminary products: Exclude raw material sectors and direct suppliers
            preliminary_products = L_minus_I - direct_suppliers
            preliminary_products[raw_material_indices, :] = 0

            # Step 2: Calculate the impacts

            # Create the `retail` matrix for the regional reassignment
            retail = I.copy()
            retail[self.region_indices, :] += (
                    direct_suppliers[self.region_indices, :] +
                    resource_extraction[self.region_indices, :] +
                    preliminary_products[self.region_indices, :])

            # Calculate impacts by applying S and Y
            self.retail_regional = pd.DataFrame(S @ (retail @ Y))

            # Zero out the selected region's contributions for the other categories
            direct_suppliers[self.region_indices, :] = 0
            resource_extraction[self.region_indices, :] = 0
            preliminary_products[self.region_indices, :] = 0

            # Calculate the remaining impacts
            self.direct_suppliers_regional = pd.DataFrame(S @ (direct_suppliers @ Y))
            self.resource_extraction_regional = pd.DataFrame(S @ (resource_extraction @ Y))
            self.preliminary_products_regional = pd.DataFrame(S @ (preliminary_products @ Y))

            # Step 3: Update labels for DataFrames
            self.iosystem.index.update_multiindices()

            logging.info("Calculations successful.\n")

    def _calculate_supply_chain_matrices(self, A: np.ndarray, L_minus_I: np.ndarray,
                                       I: np.ndarray, S: np.ndarray, Y: np.ndarray) -> None:
        """
        Calculates the various supply chain matrices.

        Args:
            A: Input-output coefficient matrix
            L_minus_I: Leontief matrix minus identity
            I: Identity matrix
            S: Environmental impact factor matrix
            Y: Final demand matrix
        """
        # Direct suppliers: Exclude raw material sectors
        direct_suppliers = A.copy()
        direct_suppliers[self.iosystem.index.raw_material_indices, :] = 0

        # Resource extraction: Only consider raw material sectors
        resource_extraction = L_minus_I.copy()
        resource_extraction[self.iosystem.index.not_raw_material_indices, :] = 0

        # Preliminary products: Exclude raw material sectors and remove direct suppliers
        preliminary_products = L_minus_I - A
        preliminary_products[self.iosystem.index.raw_material_indices, :] = 0

        # Step 2: Reassign impacts of selected region's sectors to retail
        retail = I.copy()
        retail[self.region_indices, :] += (
            direct_suppliers[self.region_indices, :] +
            resource_extraction[self.region_indices, :] +
            preliminary_products[self.region_indices, :]
        )

        # Step 3: Compute environmental impacts for each supply chain category

        # Retail impact
        retail_impact = S @ (retail @ Y)
        self.retail_regional = pd.DataFrame(retail_impact)

        # Direct suppliers impact
        direct_suppliers[self.region_indices, :] = 0
        direct_suppliers_impact = S @ (direct_suppliers @ Y)
        self.direct_suppliers_regional = pd.DataFrame(direct_suppliers_impact)

        # Resource extraction impact
        resource_extraction[self.region_indices, :] = 0
        resource_extraction_impact = S @ (resource_extraction @ Y)
        self.resource_extraction_regional = pd.DataFrame(resource_extraction_impact)

        # Preliminary products impact
        preliminary_products[self.region_indices, :] = 0
        preliminary_products_impact = S @ (preliminary_products @ Y)
        self.preliminary_products_regional = pd.DataFrame(preliminary_products_impact)


class IOSystem:
    """
    Main class for the Input-Output System, managing database paths,
    language, year, and coordinating data loading and calculations.
    """

    def __init__(self, year: int = 2022, language: str = "Exiobase"):
        """
        Initializes the IOSystem with paths and parameters for the database.

        Args:
            year: Year of the database to use
            language: Language for the labels
        """
        self.year = str(year)
        self.language = language

        # Initialize paths
        self._initialize_paths()

        # Initialize label lists
        self.impacts: Optional[List[str]] = None
        self.units: Optional[List[str]] = None
        self.regions: Optional[List[str]] = None
        self.sectors: Optional[List[str]] = None
        self.regions_exiobase: Optional[List[str]] = None

        # Initialize components
        self.index = Index(self)
        self.impact = Impact(self)

    def _initialize_paths(self) -> None:
        """
        Initializes all paths based on the project directory.
        """
        self.project_directory = os.path.dirname(os.path.dirname(__file__))
        self.config_dir = os.path.join(self.project_directory, 'config')
        self.data_dir = os.path.join(self.project_directory, 'data')
        self.databases_dir = os.path.join(self.project_directory, 'exiobase')
        self.fast_databases_dir = os.path.join(self.databases_dir, 'fast_databases')

        self.current_exiobase_path = os.path.join(self.databases_dir, f'IOT_{self.year}_pxp.zip')
        self.current_fast_database_path = os.path.join(self.fast_databases_dir, f'FAST_IOT_{self.year}_pxp')

    def switch_language(self, language: str = "Exiobase") -> None:
        """
        Switches the language for the system and updates the labels accordingly.

        Args:
            language: New language for the labels
        """
        if language != self.language:
            logging.info(f"Switching language from '{self.language}' to '{language}'")
            self.language = language
            # Update labels by re-reading configs with the new language
            self.index.read_configs()
            self.index.update_multiindices()
            logging.info(f"Language successfully switched to '{language}'")
        else:
            logging.info(f"Language is already set to '{language}'. No action required")

    def switch_year(self, year: int) -> None:
        """
        Switches the year for the system and updates the paths to the
        EXIOBASE and fast-load databases accordingly.

        Args:
            year: New year for the database
        """
        if str(year) != self.year:
            logging.info(f"Switching year from '{self.year}' to '{year}'")
            self.year = str(year)

            # Update file paths based on the new year
            self.current_exiobase_path = os.path.join(self.databases_dir, f'IOT_{year}_pxp.zip')
            self.current_fast_database_path = os.path.join(
                self.fast_databases_dir, f'FAST_IOT_{year}_pxp'
            )

            # Load the database for the new year
            self.load()
            logging.info(f"Year successfully switched to {year}")
        else:
            logging.info(f"Year is already set to {year}. No action required")

    def calc_all(self) -> None:
        """
        Calculates missing matrices and saves them as .npy files.
        """
        logging.info("Starting calculation of all matrices...")

        # Quick loading of matrices (with float32)
        matrix_paths = {
            'A': os.path.join(self.current_fast_database_path, 'A.npy'),
            'Y': os.path.join(self.current_fast_database_path, 'Y.npy'),
            'S': os.path.join(self.current_fast_database_path, 'impacts', 'S.npy')
        }

        try:
            A = np.load(matrix_paths['A']).astype(np.float32)
            Y = np.load(matrix_paths['Y']).astype(np.float32)
            S = np.load(matrix_paths['S']).astype(np.float32)
        except FileNotFoundError as e:
            logging.error(f"Required matrix file not found: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading matrices: {e}")
            raise

        # Create identity matrix
        I = np.eye(A.shape[0], dtype=np.float32)

        # Diagonalize Y matrix
        Y = self._diagonalize_y_matrix(Y)

        # Calculate Leontief Inverse
        logging.info("Calculating Leontief Inverse...")
        try:
            L = np.linalg.inv(I - A)
        except np.linalg.LinAlgError as e:
            logging.error(f"Error calculating Leontief Inverse: {e}")
            raise

        # Calculate impact matrices
        logging.info("Calculating impact matrices...")
        impact_matrices = self._calculate_all_impact_matrices(A, L, I, S, Y)

        # Save calculated matrices
        self._save_calculated_matrices(L, Y, impact_matrices)

    def _diagonalize_y_matrix(self, Y: np.ndarray) -> np.ndarray:
        """
        Diagonalizes the Y matrix if required.

        Args:
            Y: Original Y matrix

        Returns:
            Diagonalized Y matrix
        """
        logging.info("Diagonalizing Y matrix...")

        if Y.shape != (9800, 9800):
            Y = Y.reshape(9800, len(self.regions), 7).sum(axis=2)
            n, num_blocks = Y.shape  # (9800, len(self.regions))
            block_size = n // num_blocks  # 9800 / len(self.regions) = len(self.sectors)
            Y_diag = np.zeros((n, n), dtype=np.float32)
            for i in range(num_blocks):
                block = Y[:, i]  # Column i (size 9800)
                row_idx = np.arange(n)  # 9800 row indices
                col_idx = (row_idx % block_size) + i * block_size
                mask = col_idx < n  # If out of bounds
                Y_diag[row_idx[mask], col_idx[mask]] = block[mask]

            Y = Y_diag

        return Y

    def _calculate_all_impact_matrices(self, A: np.ndarray, L: np.ndarray,
                                     I: np.ndarray, S: np.ndarray,
                                     Y: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Calculates all impact matrices.

        Args:
            A: Input-output coefficient matrix
            L: Leontief Inverse
            I: Identity matrix
            S: Environmental impact factor matrix
            Y: Diagonalized final demand matrix

        Returns:
            Dictionary with calculated impact matrices
        """
        LY = L @ Y
        L_minus_I = L - I

        # Total impact matrix
        total_impact = self._calculate_regional_impacts(S, LY, "total")

        # Retail impact matrix
        retail_impact = self._calculate_regional_impacts(S, Y, "retail")

        # Direct suppliers impact matrix
        direct_suppliers_matrix = A.copy()
        direct_suppliers_matrix[self.index.raw_material_indices, :] = 0
        direct_suppliers_impact = self._calculate_regional_impacts(
            S, direct_suppliers_matrix @ Y, "direct_suppliers"
        )

        # Resource extraction impact matrix
        resource_extraction_matrix = L_minus_I.copy()
        resource_extraction_matrix[self.index.not_raw_material_indices, :] = 0
        resource_extraction_impact = self._calculate_regional_impacts(
            S, resource_extraction_matrix @ Y, "resource_extraction"
        )

        # Preliminary products impact matrix
        preliminary_products_matrix = L_minus_I - A
        preliminary_products_matrix[self.index.raw_material_indices, :] = 0
        preliminary_products_impact = self._calculate_regional_impacts(
            S, preliminary_products_matrix @ Y, "preliminary_products"
        )

        return {
            'total': total_impact,
            'retail': retail_impact,
            'direct_suppliers': direct_suppliers_impact,
            'resource_extraction': resource_extraction_impact,
            'preliminary_products': preliminary_products_impact
        }

    def _calculate_regional_impacts(self, S: np.ndarray, production_matrix: np.ndarray,
                                  matrix_type: str) -> np.ndarray:
        """
        Calculates regional impacts for a given production matrix.

        Args:
            S: Environmental impact factor matrix
            production_matrix: Production matrix
            matrix_type: Type of matrix (for logging)

        Returns:
            Calculated regional impact matrix
        """
        logging.debug(f"Calculating {matrix_type} impact matrix...")

        all_region_impacts = []
        num_regions = len(self.regions)
        num_sectors = len(self.sectors)

        for region in range(num_regions):
            start = region * num_sectors
            end = (region + 1) * num_sectors

            x_region = production_matrix[start:end, :]
            s_region = S[:, start:end]

            E_region = s_region @ x_region
            all_region_impacts.append(E_region)

        # Stack all regional impact matrices vertically
        stacked_impact = np.vstack(all_region_impacts)

        # Reorder from grouped-by-region to grouped-by-impact-category
        return self._reorder_impact_matrix(stacked_impact, len(S), num_regions)

    def _reorder_impact_matrix(self, impact_matrix: np.ndarray,
                             num_impacts: int, num_regions: int) -> np.ndarray:
        """
        Reorders impact matrix from region-grouped to impact-grouped.

        Args:
            impact_matrix: Impact matrix to reorder
            num_impacts: Number of impacts
            num_regions: Number of regions

        Returns:
            Reordered impact matrix
        """
        sorted_impact = np.zeros_like(impact_matrix)
        total_rows = num_impacts * num_regions

        for new_idx in range(total_rows):
            old_idx = (new_idx % num_regions) * num_impacts + (new_idx // num_regions)
            sorted_impact[new_idx] = impact_matrix[old_idx]

        return sorted_impact

    def _save_calculated_matrices(self, L: np.ndarray, Y: np.ndarray,
                                impact_matrices: Dict[str, np.ndarray]) -> None:
        """
        Saves all calculated matrices as .npy files.

        Args:
            L: Leontief Inverse
            Y: Diagonalized Y matrix
            impact_matrices: Dictionary with impact matrices
        """
        logging.info("Calculations successful. Matrices are being saved...")

        try:
            # Save main matrices
            np.save(os.path.join(self.current_fast_database_path, 'L.npy'), L)
            np.save(os.path.join(self.current_fast_database_path, 'Y.npy'), Y)

            # Save impact matrices
            impacts_dir = os.path.join(self.current_fast_database_path, 'impacts')
            for matrix_name, matrix_data in impact_matrices.items():
                np.save(os.path.join(impacts_dir, f'{matrix_name}.npy'), matrix_data)

            logging.info("All matrices successfully saved \n")

        except Exception as e:
            logging.error(f"Error saving matrices: {e}")
            raise

    def _extract_file_parameters(self, zip_archive_path: str) -> Dict[str, Dict[str, int]]:
        """
        Reads all 'file_parameters.json' files from a ZIP archive and extracts
        header and index column information for each file.

        Args:
            zip_archive_path: Path to the ZIP archive

        Returns:
            Dictionary with file parameters
        """
        file_parameters = {}
        found_json_files = []

        try:
            with zipfile.ZipFile(zip_archive_path, 'r') as zf:
                # Iterate through all files in the ZIP archive
                for member_name in zf.namelist():
                    if member_name.endswith('file_parameters.json'):
                        found_json_files.append(member_name)

                if not found_json_files:
                    logging.info(f"No 'file_parameters.json' files found in ZIP archive '{zip_archive_path}'")
                    return file_parameters

                # Process each found 'file_parameters.json' file
                for json_file_name in found_json_files:
                    try:
                        with zf.open(json_file_name) as f:
                            data = json.load(f)
                            if "files" in data:
                                file_parameters.update(
                                    self._process_file_parameters(data["files"], json_file_name)
                                )
                            else:
                                logging.warning(
                                    f"File '{json_file_name}' does not contain a top-level 'files' key"
                                )
                    except json.JSONDecodeError:
                        logging.error(f"File '{json_file_name}' is not a valid JSON file")
                    except Exception as e:
                        logging.error(f"Unexpected error while reading '{json_file_name}': {e}")

        except FileNotFoundError:
            logging.error(f"ZIP archive '{zip_archive_path}' was not found")
        except zipfile.BadZipFile:
            logging.error(f"File '{zip_archive_path}' is not a valid ZIP archive")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

        return file_parameters

    def _process_file_parameters(self, files_data: Dict, json_file_name: str) -> Dict[str, Dict[str, int]]:
        """
        Processes file parameters from a JSON file.

        Args:
            files_data: Dictionary with file parameters
            json_file_name: Name of the JSON file for logging

        Returns:
            Processed file parameters
        """
        processed_params = {}

        for file_key, file_info in files_data.items():
            try:
                # Ensure values are converted to integers
                nr_header = int(file_info.get("nr_header", 0))
                nr_index_col = int(file_info.get("nr_index_col", 0))

                processed_params[file_key] = {
                    "nr_header": nr_header,
                    "nr_index_col": nr_index_col
                }
            except ValueError:
                logging.warning(
                    f"Invalid numeric values in '{json_file_name}' for key '{file_key}'"
                )

        return processed_params

    def _get_file_parameters(self, zip_archive_path: str, file_name: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Retrieves header and index columns for a specific file from a ZIP archive.

        Args:
            zip_archive_path: Path to the ZIP archive
            file_name: Name of the file to search for

        Returns:
            Tuple with (nr_header, nr_index_col) or (None, None) if not found
        """
        # First, extract all file parameters from the ZIP archive
        all_file_params = self._extract_file_parameters(zip_archive_path)

        # Then retrieve specific parameters for the given file name
        if file_name in all_file_params:
            params = all_file_params[file_name]
            return params["nr_header"], params["nr_index_col"]
        else:
            logging.error(f"Parameters for file '{file_name}' were not found")
            return None, None

    def _read_units_and_labels(self, zip_archive_path: str) -> bool:
        """
        Reads all 'unit.txt' files from the given EXIOBASE archive.

        Args:
            zip_archive_path: Path to the EXIOBASE ZIP archive

        Returns:
            True if successful, False on errors
        """
        try:
            with zipfile.ZipFile(zip_archive_path, 'r') as zf:
                for member_name in zf.namelist():
                    if os.path.basename(member_name) != "unit.txt":
                        continue

                    parent_folder = (os.path.dirname(member_name).split('/')[-1]
                                   if '/' in member_name else "")
                    logging.info(f"Found 'unit.txt' in folder: '{parent_folder}'")

                    with zf.open(member_name) as file:
                        df = pd.read_csv(io.StringIO(file.read().decode("utf-8")), sep="\t")

                    self._process_unit_file(df, parent_folder, member_name)
                    del df  # Free memory

            return True

        except Exception as e:
            logging.error(f"Failed to read unit.txt files from '{zip_archive_path}': {e}")
            return False

    def _process_unit_file(self, df: pd.DataFrame, parent_folder: str, member_name: str) -> None:
        """
        Processes a single unit.txt file.

        Args:
            df: DataFrame with loaded data
            parent_folder: Name of the parent folder
            member_name: Name of the file for logging
        """
        if parent_folder == "impacts":
            if {"impact", "unit"}.issubset(df.columns):
                self.impacts = df["impact"].tolist()
                self.units = df["unit"].tolist()
                logging.info("Successfully read 'impacts/unit.txt'")
            else:
                logging.warning(f"Missing columns in '{member_name}'")
        else:
            if {"region", "sector"}.issubset(df.columns):
                self.regions = df["region"].unique().tolist()
                self.sectors = df["sector"].unique().tolist()
                logging.info(f"Successfully read '{parent_folder}/unit.txt' for regions/sectors")
            else:
                logging.warning(f"Missing columns in '{member_name}' - Ignore this if in 'satellite' folder.")

    def _read_and_save_as_npy(self, file_id: str, output_directory: str) -> bool:
        """
        Reads a TSV file from a ZIP archive using header/index column settings
        and saves it as a NumPy array (.npy).

        Args:
            file_id: ID of the file to read
            output_directory: Output directory

        Returns:
            True if successful, False on errors
        """
        ignored_subfolders = ["satellite"]

        logging.info(f"Retrieving parameters for '{file_id}.txt'...")
        nr_header, nr_index_col = self._get_file_parameters(self.current_exiobase_path, file_id)
        if nr_header is None or nr_index_col is None:
            logging.error(f"No header/index info for '{file_id}.txt'")
            return False

        logging.info(f"Detected: Header rows={nr_header}, Index columns={nr_index_col}")

        try:
            with zipfile.ZipFile(self.current_exiobase_path, 'r') as zf:
                target_file_name = f"{file_id}.txt"
                found_path, relative_subfolder_path = self._find_file_in_zip(
                    zf, target_file_name, ignored_subfolders
                )

                if not found_path:
                    logging.error(f"File '{target_file_name}' not found or in ignored folder")
                    return False

                # Create output directory and process file
                return self._process_tsv_file(
                    zf, found_path, file_id, output_directory,
                    relative_subfolder_path, nr_header, nr_index_col
                )

        except Exception as e:
            logging.error(f"Failed to read/save '{file_id}': {e}")
            return False

    def _find_file_in_zip(self, zf: zipfile.ZipFile, target_file_name: str,
                         ignored_subfolders: List[str]) -> Tuple[Optional[str], str]:
        """
        Finds a file in the ZIP archive and returns its path.

        Args:
            zf: ZipFile object
            target_file_name: Name of the file to search for
            ignored_subfolders: List of subfolders to ignore

        Returns:
            Tuple with (found_path, relative_subfolder_path)
        """
        for member_name in zf.namelist():
            if member_name.endswith(f"/{target_file_name}") or member_name == target_file_name:
                member_dir = os.path.dirname(member_name)
                if any(part in ignored_subfolders for part in member_dir.split('/') if part):
                    continue

                relative_subfolder_path = ""
                if member_dir:
                    path_parts = member_dir.split('/')
                    relative_subfolder_path = (os.path.join(*path_parts[1:])
                                             if len(path_parts) > 1 else "")

                return member_name, relative_subfolder_path

        return None, ""

    def _process_tsv_file(self, zf: zipfile.ZipFile, found_path: str, file_id: str,
                         output_directory: str, relative_subfolder_path: str,
                         nr_header: int, nr_index_col: int) -> bool:
        """
        Processes a TSV file from the ZIP archive.

        Args:
            zf: ZipFile object
            found_path: Path to the found file
            file_id: ID of the file
            output_directory: Output directory
            relative_subfolder_path: Relative subfolder path
            nr_header: Number of header rows
            nr_index_col: Number of index columns

        Returns:
            True if successful
        """
        final_output_directory = os.path.join(output_directory, relative_subfolder_path)
        os.makedirs(final_output_directory, exist_ok=True)
        output_npy_path = os.path.join(final_output_directory, f"{file_id}.npy")

        with zf.open(found_path) as f_tsv:
            df = pd.read_csv(
                f_tsv,
                sep='\t',
                skiprows=nr_header,
                header=None,
                index_col=list(range(nr_index_col)) if nr_index_col > 0 else None
            )

        df = df.dropna(how='all').reset_index(drop=True)
        np.save(output_npy_path, df.values)

        logging.info(f"Saved '{found_path}' as '{output_npy_path}'")
        return True

    def create_fast_database(self) -> None:
        """
        Creates the fast database by extracting the current EXIOBASE database,
        processing it, and saving the results in a structured format.
        """
        logging.info("Creating fast database...")

        necessary_files = ["A", "Y", "D_cba", "S"]

        # Create fast database directory if it doesn't exist
        if not os.path.exists(self.current_fast_database_path):
            os.makedirs(self.current_fast_database_path)
            logging.info(f"Folder '{self.current_fast_database_path}' was created\n")
        else:
            logging.info(f"Folder '{self.current_fast_database_path}' already exists\n")

        # Read unit.txt files first
        logging.info("Starting to read unit.txt files...")
        unit_read_success = self._read_units_and_labels(self.current_exiobase_path)
        if not unit_read_success:
            logging.warning("Reading unit.txt files was not entirely successful")
        logging.info("Finished reading unit.txt files\n")

        # Transform .txt files to .npy files
        logging.info(f"Starting creation of fast-load database for year {self.year}...")
        success_count = 0
        for file_id in necessary_files:
            logging.info(f"Processing file: {file_id}.txt")
            success = self._read_and_save_as_npy(file_id, self.current_fast_database_path)
            if success:
                success_count += 1
            else:
                logging.warning(f"Processing of file '{file_id}.txt' was not successful")

        logging.info(f"Fast-load database creation completed for year {self.year} "
                    f"({success_count}/{len(necessary_files)} files successful)\n")

        # Copy config files
        logging.info("Copying configuration files to the fast-load database path...")
        self.index.copy_configs(output=False)
        logging.info("Configuration files copied and Index attributes populated\n")

    def load(self) -> 'IOSystem':
        """
        Loads the fast database. If the database does not exist, it triggers
        its creation and all necessary calculations.

        Returns:
            Self-reference for method chaining
        """
        start_time = time.time()
        l_matrix_path = os.path.join(self.current_fast_database_path, 'L.npy')

        if os.path.exists(l_matrix_path):
            logging.info(f"Fast database for year {self.year} likely exists due to the presence of an L matrix - loading...")

            try:
                self._load_existing_database()
                elapsed_time = time.time() - start_time
                logging.info(f"Database has been loaded successfully in {elapsed_time:.3f} seconds")
                return self

            except Exception as e:
                logging.error(f"There was a problem trying to load the database: {e}")
                logging.info("Attempting to recreate fast database from scratch due to loading error...")
                return self._create_and_calculate_database(start_time)
        else:
            logging.info("Creating fast database from scratch...\n")
            return self._create_and_calculate_database(start_time)

    def _load_existing_database(self) -> None:
        """
        Loads an existing fast database.
        """
        # Load main matrices
        matrix_files = ['A.npy', 'L.npy', 'Y.npy']
        for matrix_file in matrix_files:
            matrix_name = matrix_file[:-4]  # Remove .npy extension
            file_path = os.path.join(self.current_fast_database_path, matrix_file)
            setattr(self, matrix_name, pd.DataFrame(np.load(file_path).astype(np.float32)))

        # Create identity matrix
        self.I = pd.DataFrame(np.identity(9800, dtype=np.float32))

        # Load impact matrices via the Impact class
        self.impact.load()

        # Add multi-indices
        self.index.update_multiindices()

    def _create_and_calculate_database(self, start_time: float) -> 'IOSystem':
        """
        Creates and calculates a new fast database.

        Args:
            start_time: Start time for timing measurement

        Returns:
            Self-reference
        """
        self.create_fast_database()
        self.index.copy_configs()
        self.index.read_configs()
        self.calc_all()

        elapsed_time = time.time() - start_time
        logging.info(f"Database created and calculated in {elapsed_time:.3f} seconds")
        return self


if __name__ == "__main__" and 1 == 2:  # This block is for testing purposes only, not executed in production
    # Create an instance of the IOSystem class
    io_system_instance = IOSystem(year=2022, language="Deutsch")

    # Load the fast database (creates it if necessary)
    io_system_instance.load()

    # Optional: Verify one of the created .npy files (e.g. S.npy)
    output_npy_full_path = os.path.join(io_system_instance.current_fast_database_path, "impacts", "S.npy")
    if os.path.exists(output_npy_full_path):
        print(f"\n--- Verifying file '{output_npy_full_path}' ---")
        loaded_data = np.load(output_npy_full_path)
        print(f"\n--- Loaded data:\n{loaded_data} ---")
        print(f"Shape of loaded data: {loaded_data.shape}")
    else:
        print(f"Error: File '{output_npy_full_path}' was not found after database creation")

    print("\n--- Verifying extracted units and labels ---")
    print(f"Impacts ({len(io_system_instance.impacts)}): {io_system_instance.impacts}")
    print(f"Units ({len(io_system_instance.units)}): {io_system_instance.units}")
    print(f"Regions ({len(io_system_instance.regions)}): {io_system_instance.regions}")
    print(f"Sectors ({len(io_system_instance.sectors)}): {io_system_instance.sectors}")
    