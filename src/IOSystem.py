import os
import shutil
import io
import json
import zipfile
import time
import itertools
import pandas as pd 
import numpy as np 
import geopandas as gpd 
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
    
    def __init__(self, IOSystem):
        """
        Initializes the Index object.
        """
        self.IOSystem = IOSystem

    def read_configs(self):
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
            # Mapping of attributes to file names and sheet names
            file_mapping = {
                "sectors_df": ("sectors.xlsx", self.IOSystem.language),  
                "raw_materials_df" : ("sectors.xlsx", "raw_material"),  
                "regions_df": ("regions.xlsx", self.IOSystem.language),  
                "exiobase_to_map_df": ("regions.xlsx", "map"), 
                "impacts_df": ("impacts.xlsx", self.IOSystem.language),   
                "impact_color_df": ("impacts.xlsx", "color"), 
                "units_df": ("units.xlsx", self.IOSystem.language),   
                "general_df": ("general.xlsx", self.IOSystem.language)  
            }

            # Expected lengths for verification
            expected_lengths = {
                'sectors_df': 200,
                "raw_materials_df" : 200,
                'regions_df': 49,
                'exiobase_to_map_df': 178,
                'impacts_df': 126,
                'impact_color_df': 126,
                'units_df': 126,
                'general_df': 12
            }
            
            # Attempt to load each Excel file and assign it to the corresponding attribute
            try:
                for attr, (file_name, sheet_name) in file_mapping.items():
                    # Read the Excel file and set the corresponding attribute
                    df = pd.read_excel(os.path.join(self.IOSystem.fast_db, file_name), sheet_name=sheet_name)
                    
                    amount = len(df)
                    
                    # For sectors_df, regions_df, and impacts_df: reverse the column order and check for duplicates
                    if attr in ['sectors_df', 'regions_df', 'impacts_df']:
                        # Reverse the column order for consistent hierarchical processing
                        df = df.iloc[:, ::-1]

                        # Store the number of rows for each DataFrame as reference
                        setattr(self, f"amount_{attr[:-3]}", amount)

                        # Verify column names are unique
                        duplicate_columns = df.columns[df.columns.duplicated()]
                        if len(duplicate_columns) > 0:
                            raise ValueError(f"The sheet '{sheet_name}' in '{file_name}' contains duplicate column names: {', '.join(duplicate_columns)}.")
                    
                    # Verify length
                    if amount != expected_lengths.get(attr, 0) and file_name != "general.xlsx":
                        raise ValueError(f"Expected {expected_lengths.get(attr)} rows in sheet '{sheet_name}' of '{file_name}', but found {len(df)}.")

                    # Set the DataFrame as an instance variable using setattr
                    setattr(self, attr, df)
                    
            except FileNotFoundError as e:
                logging.error(f"Missing required Excel file: {e.filename}")
                raise FileNotFoundError(f"Missing required Excel file: {e.filename}") from e
                
        except Exception as e:
            logging.error(f"Error during Excel reading and processing: {e}")
            raise e

        # Store unit transformations for later use in unit calculations
        self.IOSystem.Impact.unit_transform = self.units_df.values.tolist()

        # Create a dictionary from the 'general_df' DataFrame, mapping 'exiobase' to 'translation'
        self.general_dict = dict(zip(self.general_df['exiobase'], self.general_df['translation']))

        # Create a list with all raw material indices
        self.raw_material_indices = self.raw_materials_df[self.raw_materials_df['raw_material'] == True].index.tolist()
        self.not_raw_material_indices = self.raw_materials_df[self.raw_materials_df['raw_material'] == False].index.tolist()
        expanded_raw_material_indices = []
        expanded_not_raw_material_indices = []

        for i in range(1, 49):  # for each region
            expanded_raw_material_indices.extend([i * 200 + index for index in self.raw_material_indices])
            expanded_not_raw_material_indices.extend([i * 200 + index for index in self.not_raw_material_indices])

        self.raw_material_indices = expanded_raw_material_indices
        self.not_raw_material_indices = expanded_not_raw_material_indices

        # Create a list with all possible languages
        data = pd.ExcelFile(os.path.join(self.IOSystem.fast_db, file_name))
        self.languages = data.sheet_names
        del data

    def create_multiindices(self):
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
        # Expand sectors to match all regions (ensuring each sector exists for each region)
        self.matching_sectors_df = pd.concat([self.sectors_df] * self.amount_regions, ignore_index=True)
        
        # Match regions to sectors by repeating the region indices to match the number of sectors
        self.matching_regions_df = self.regions_df.loc[np.repeat(self.regions_df.index, self.amount_sectors)].reset_index(drop=True)
        
        # Create MultiIndex for sectors and regions, ensuring hierarchical order
        self.sector_multiindex = pd.MultiIndex.from_arrays(
            # Combine region and sector columns to form a hierarchical index
            [self.matching_regions_df[column] for column in self.matching_regions_df.columns] + 
            [self.matching_sectors_df[column] for column in self.matching_sectors_df.columns],
            names=self.matching_regions_df.columns.to_list() + self.matching_sectors_df.columns.to_list()
        )
        
        # Create MultiIndex for impacts (hierarchical index for impact categories)
        self.impact_multiindex = pd.MultiIndex.from_arrays(
            [self.impacts_df[column] for column in self.impacts_df.columns],
            names=self.impacts_df.columns.to_list()
        )

        # Create just the region MultiIndex (for regions alone)
        self.region_multiindex = pd.MultiIndex.from_arrays(
            [self.regions_df[column] for column in self.regions_df.columns],
            names=self.regions_df.columns.to_list()
        )              

        # Create just the sector MultiIndex for a single region
        self.sector_multiindex_per_region = pd.MultiIndex.from_arrays(
            [self.sectors_df[column] for column in self.sectors_df.columns],
            names=self.sectors_df.columns.to_list()
        )

        # Erstelle den neuen MultiIndex; die Namen werden als Tupel angegeben
        self.impact_per_region_multiindex = pd.MultiIndex.from_tuples(
            [imp + reg for imp, reg in itertools.product(self.impact_multiindex, self.region_multiindex)],
            names=list(self.impact_multiindex.names) + list(self.region_multiindex.names)
        )

    def update_multiindices(self):
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
        self.update_map()

        # Extract unique names for system-wide reference
        self.IOSystem.sectors = self.sectors_df.iloc[:, -1].unique().tolist()
        self.IOSystem.regions = self.regions_df.iloc[:, -1].unique().tolist()
        self.IOSystem.impacts = self.impacts_df.iloc[:, -1].unique().tolist()
        self.IOSystem.units = self.units_df.iloc[:, -1].tolist()

        # Load 'regions_exiobase' data
        regions_exiobase_df = pd.read_excel(os.path.join(self.IOSystem.fast_db, 'regions.xlsx'), sheet_name="Exiobase")
        self.IOSystem.regions_exiobase = regions_exiobase_df.iloc[:, -1].unique().tolist()

        # Update impact units DataFrame
        self.IOSystem.Impact.unit = pd.DataFrame({"unit": self.IOSystem.units}, index=self.IOSystem.impacts)

        # Define matrices that need their MultiIndex updated (both sector and impact matrices)
        matrix_mappings = {
            "standard_matrices": ["A", "L", "Y", "I"],
            "impact_matrices": ["S", "D_cba"],
            "regional_impact_matrices": ["total", "retail", "direct_suppliers", "resource_extraction", "preliminary_products"],
            "regional_matrices": ["retail_regional", "direct_suppliers_regional", "resource_extraction_regional", "preliminary_products_regional"]
        }

        # Update standard matrices' index and columns
        for matrix_group, matrices in matrix_mappings.items():
            if matrix_group == "standard_matrices":
                for matrix in matrices:
                    matrix_data = getattr(self.IOSystem, matrix)
                    matrix_data.index = matrix_data.columns = self.sector_multiindex
            
            if matrix_group == "impact_matrices":
                for matrix in matrices:
                    impact_matrix = getattr(self.IOSystem.Impact, matrix)
                    impact_matrix.index = self.impact_multiindex
                    impact_matrix.columns = self.sector_multiindex

            if matrix_group == "regional_impact_matrices":
                for matrix in matrices:
                    impact_matrix = getattr(self.IOSystem.Impact, matrix)
                    impact_matrix.index = self.impact_per_region_multiindex
                    impact_matrix.columns = self.sector_multiindex

            # Update regional matrices' index and columns if region-specific matrices exist
            if matrix_group == "regional_matrices" and self.IOSystem.Impact.region_indices is not None:
                for matrix in matrices:
                    regional_matrix = getattr(self.IOSystem.Impact, matrix)
                    regional_matrix.index = self.impact_multiindex
                    regional_matrix.columns = self.sector_multiindex

        # Lists to save the classification structure
        self.sector_classification = self.sectors_df.columns.tolist()
        self.region_classification = self.regions_df.columns.tolist()
        self.impact_classification = self.impacts_df.columns.tolist()        

    def copy_configs(self, new=False, output=True):
        if output:
            logging.info("Copying config files from /config to the fast load database...\n")

        config_files = ["sectors.xlsx", "regions.xlsx", "impacts.xlsx", "units.xlsx", "general.xlsx"]
        
        # Loop through each Excel file in the list
        for file_name in config_files:
            source_file = os.path.join(self.IOSystem.config_dir, file_name)
            target_file = os.path.join(self.IOSystem.fast_db, file_name)
            
                # Check if the source file exists
            if os.path.exists(source_file):
                try:
                    shutil.copy(source_file, target_file)
                    if output:
                        logging.info(f"File {file_name} has been successfully copied to {self.IOSystem.fast_db}." + ("\n" if file_name == config_files[-1] else ""))
                except Exception as e:
                    logging.error(f"Error copying {file_name}: {e}")
            else:
                logging.error(f"Error: {file_name} not found in the folder {self.IOSystem.config}.")

    def write_configs(self, sheet_name):
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

        # List of file paths and corresponding DataFrames
        file_data = {
            "sectors.xlsx": [(self.sectors_df.iloc[:, ::-1], sheet_name), (self.raw_materials_df, "raw_material")],
            "regions.xlsx": [(self.regions_df.iloc[:, ::-1], sheet_name), (self.exiobase_to_map_df, "map")],
            "impacts.xlsx": [(self.impacts_df.iloc[:, ::-1], sheet_name), (self.impact_color_df, "color")],
            "units.xlsx": [(self.units_df, sheet_name)],
            "general.xlsx": [(self.general_df, sheet_name)]
        }

        # Write to Excel files
        try: 
            for file_name, sheets in file_data.items():
                file_path = os.path.join(self.IOSystem.fast_db, file_name)
                mode = "a" if os.path.exists(file_path) else "w"

                with pd.ExcelWriter(file_path, engine="openpyxl", mode=mode) as writer:
                    for df, sheet in sheets:
                        try:
                            df.to_excel(writer, sheet_name=sheet, index=False)
                        except Exception as e:
                            print(f"Error writing to sheet '{sheet}' in file '{file_name}': {e}")

            print("Excel files have been successfully created or updated.")
        except PermissionError:
            raise PermissionError("Make sure to close all Excel files before running the program.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def update_map(self, force=False):
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

        Returns:
        - GeoDataFrame: A GeoDataFrame containing regions and their geometries, with regions mapped from Exiobase.

        The method performs the following actions:
        - Reads the shapefile for world countries using Geopandas.
        - Maps Exiobase regions to the corresponding world regions using `exiobase_to_map_df`.
        - Adds a new column for regions based on the mapping and dissolves geometries by region to create a simplified world map.
        - Returns a copy of the resulting GeoDataFrame.
        """
        self.world = world = gpd.read_file(os.path.join(self.IOSystem.data_dir, "ne_110m_admin_0_countries.zip"))

        self.exiobase_to_map_dict = dict(zip(self.exiobase_to_map_df['NAME'], self.exiobase_to_map_df['region']))

        self.world["region"] = self.world["NAME"].map(self.exiobase_to_map_dict)
        
        self.world = self.world[["region", "geometry"]]
        
        self.world = self.world.dissolve(by="region") 

    def get_map(self):
        """
        Returns the geopandas world-map with exiobase regions as indices.
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
        IOSystem: Reference to the associated IOSystem instance.
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

    def __init__(self, IOSystem):
        # Store the provided IOSystem object for later use.
        self.IOSystem = IOSystem
        self.color = None
        self.unit_transform = None
        self.region_indices = None

    def load(self):
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
        try:
            # Define file paths
            impact_files = {
                "S": "S.npy",
                "D_cba": "D_cba.npy",
                "total": "total.npy",
                "retail": "retail.npy",
                "direct_suppliers": "direct_suppliers.npy",
                "resource_extraction": "resource_extraction.npy",
                "preliminary_products": "preliminary_products.npy"
            }

            # Expected shape of the matrices
            expected_shape = {
                "S": (126, 9800),
                "D_cba": (126, 9800),
                "total": (6174, 9800),
                "retail": (6174, 9800),
                "direct_suppliers": (6174, 9800),
                "resource_extraction": (6174, 9800),
                "preliminary_products": (6174, 9800)
            }
            
            # Load the impact matrices
            for attr, filename in impact_files.items():
                file_path = os.path.join(self.IOSystem.fast_db, "impacts", filename)
                try:
                    array = np.load(file_path).astype(np.float32)

                    # Check if the loaded array has the correct shape
                    if array.shape != expected_shape[attr]:
                        logging.error(f"Shape mismatch in {filename}: Expected {expected_shape}, but got {array.shape}")
                        raise ValueError(f"Incorrect shape for {filename}: Expected {expected_shape}, got {array.shape}")

                    setattr(self, attr, pd.DataFrame(array))

                except FileNotFoundError:
                    logging.error(f"File not found: {file_path}")
                    raise FileNotFoundError(f"Missing impact matrix: {filename}")
                except ValueError as ve:
                    logging.error(f"Invalid data in {file_path}: {str(ve)}")
                    raise ValueError(f"Could not load {filename} correctly: {str(ve)}")

        except Exception as e:
            logging.error(f"Error loading impact matrices: {str(e)}")
            raise RuntimeError("Failed to load impact matrices. Consider recreating the fast-load database (force=true).") from e

    def get_color(self, impact):
        """
        Retrieves the color associated with a specific impact from the IOSystem's extension data.
    
        The function looks up the color for the given impact in `impacts_df`. If the impact is not found, 
        it returns a default color ("#ffffff" for white).
    
        Parameters:
        - impact (str): The name or key of the impact for which the color is requested.
    
        Returns:
        - str: A string representing the color code for the given impact. If not found, returns "#ffffff".
        """
        try:
            # Extract the relevant impact column
            impact_list = self.IOSystem.Index.impacts_df.iloc[:, -1].to_list()
    
            # Find index of the impact
            idx = impact_list.index(impact)
    
            # Retrieve corresponding color
            return self.IOSystem.Index.impact_color_df.iloc[idx]["color"]
        
        except ValueError:
            # If the impact is not found in the list
            return "#ffffff"
        except (AttributeError, IndexError, KeyError):
            # Handle cases where the data structure is unexpected
            return "#ffffff"

    def get_regional_impacts(self, region_indices):
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
            Y = self.IOSystem.Y.to_numpy()  # Final demand matrix
        
            # Extract key matrices used in multiple calculations
            I = self.IOSystem.I.to_numpy()  # Identity matrix
            L_minus_I = self.IOSystem.L.to_numpy() - I  # Leontief matrix minus identity
            A = self.IOSystem.A.to_numpy()  # Input-output coefficient matrix    
    
            # Step 1: Identify sectoral impacts before reassignment
    
            # Direct suppliers: Exclude raw material sectors 
            direct_suppliers = A.copy()
            direct_suppliers[self.IOSystem.Index.raw_material_indices, :] = 0
    
            # Resource extraction: Only consider raw material sectors
            resource_extraction = L_minus_I.copy()
            resource_extraction[self.IOSystem.Index.not_raw_material_indices, :] = 0
    
            # Preliminary products: Exclude raw material sectors and remove direct suppliers
            preliminary_products = L_minus_I - A
            preliminary_products[self.IOSystem.Index.raw_material_indices, :] = 0
            
            # Step 2: Reassign impacts of selected region's sectors to retail
            retail = I.copy()
            retail[self.region_indices, :] += (
                direct_suppliers[self.region_indices, :] +
                resource_extraction[self.region_indices, :] +
                preliminary_products[self.region_indices, :])
    
            # Step 3: Compute environmental impacts for each supply chain category
    
            # Retail impact: Total impact for all stages within the region
            retail_impact = S @ (retail @ Y)
            self.retail_regional = pd.DataFrame(retail_impact)
    
            # Direct suppliers impact: Exclude region's direct suppliers
            direct_suppliers[self.region_indices, :] = 0
            direct_suppliers_impact = S @ (direct_suppliers @ Y)
            self.direct_suppliers_regional = pd.DataFrame(direct_suppliers_impact)
    
            # Resource extraction impact: Exclude region's extracted resources
            resource_extraction[self.region_indices, :] = 0
            resource_extraction_impact = S @ (resource_extraction @ Y)
            self.resource_extraction_regional = pd.DataFrame(resource_extraction_impact)
    
            # Preliminary products impact: Exclude region's preliminary products
            preliminary_products[self.region_indices, :] = 0 
            preliminary_products_impact = S @ (preliminary_products @ Y)
            self.preliminary_products_regional = pd.DataFrame(preliminary_products_impact)
    
            # Step 4: Update labels for DataFrames
            self.IOSystem.Index.update_multiindices()   

            logging.info("Calculations successful.\n")     


class IOSystem:

    def __init__(self, year=2022, language="Exiobase", exiobase_dir=None, fast_dir=None, exiobase_db=None, fast_db=None):
        """
        Initializes the IOSystem with paths and parameters for the database.
        
        Args:
            compressed_path: The path to the folder containing the compressed Exiobase ZIP files.
            fast_path: (Optional) The path to the folder for fast-load databases.
            year: (Optional) The year for the database to use (default: 2022).
            language: (Optional) The language of the database (default: "exiobase").
            exiobase_db: (Optional) The path to the compressed database file.
            fast_db: (Optional) The path to the fast-load database.
        """
        # Year as a string
        self.year = str(year)
        
        # Language of the database
        self.language = language
     
        # Paths to the various data folders
        self.current_dir = os.path.dirname(__file__)  
        self.config_dir = os.path.normpath(os.path.join(self.current_dir, '..', 'config'))
        self.data_dir = os.path.normpath(os.path.join(self.current_dir, '..', 'data'))
        self.exiobase_dir = os.path.normpath(exiobase_dir) if exiobase_dir is not None else os.path.normpath(os.path.join(self.current_dir, '..', 'exiobase'))  # Path to the folder with compressed ZIP files
        self.fast_dir = os.path.normpath(fast_dir) if fast_dir is not None else os.path.normpath(os.path.join(self.exiobase_dir, 'fast load databases')) # Path to the folder for fast-load databases
        
        self.exiobase_db = os.path.normpath(exiobase_db) if exiobase_db is not None else os.path.normpath(os.path.join(self.exiobase_dir, f'IOT_{year}_pxp.zip'))  # Default path to the compressed database
        self.fast_db = os.path.normpath(fast_db) if fast_db is not None else os.path.normpath(os.path.join(self.fast_dir, f'Fast_IOT_{year}_pxp'))  # Path to the fast-load database
        
        # Impact and Index Class
        self.Impact = Impact(self)
        self.Index = Index(self)
        self.regions_exiobase = None
        self.start_time = None
    
    def load(self, force=False, attempt=1):  
        """
        The method performs the following actions:
        - Checks if the fast database exists. If so, it loads the matrix files (`A`, `L`, `Y`, `I`) and initializes them as DataFrames.
        - Loads the impact matrices using the `Impact` class and updates the multi-indices using the `Index` class.
        - If the `return_time` parameter is `True`, it records and prints the time taken to load the database.
        - If the database does not exist or if `force=True`, it creates a new fast database by calling the `create_fast_load_database` method 
        and recalculates all necessary data. After creating the database, it loads it again by recursively calling the `load()` method.
        
        Parameters:
        - `force` (bool, default=False): Forces the creation of a new fast database, even if an existing one is found.
        - `return_time` (bool, default=True): Determines whether to measure and print the time taken to load the database.

        Returns:
        - None

        Raises:
        - FileNotFoundError: If any required `.npy` file is missing.
        - Exception: If there are any issues during the loading process.

        This method ensures the system is populated with the necessary matrices and impact data, providing a foundation for further calculations.
        """

        if attempt == 1:
            self.start_time = time.time()  # Record the start time if measuring the elapsed time

        if attempt >= 2:
            raise RuntimeError("Interrupted load-function to prevent recursive actions.")
            return  
        
        if os.path.exists(self.fast_db) and not force:
            if attempt == 1:
                logging.info("Fast database was found - Loading...")
            try:
                # Load the matrices and convert them to DataFrames (without labels)
                self.A = pd.DataFrame(np.load(os.path.join(self.fast_db, 'A.npy')).astype(np.float32))  # Load 'A' matrix
                self.L = pd.DataFrame(np.load(os.path.join(self.fast_db, 'L.npy')).astype(np.float32))  # Load 'L' matrix
                self.Y = pd.DataFrame(np.load(os.path.join(self.fast_db, 'Y.npy')).astype(np.float32))  # Load 'Y' matrix
                self.I = pd.DataFrame(np.identity(9800, dtype=np.float32))  # Identity matrix (9800x9800)
                
                # Load the impact matrices using the Impact class
                self.Impact.load()

                # Add the multi_indices
                self.Index.update_multiindices()
            except:
                logging.info("There was a problem trying to load the database. Force-loading instead...")
                self.load(force=True)

            # Calculate and print the elapsed time
            end_time = time.time()  # Record the end time
            elapsed_time = end_time - self.start_time  # Calculate elapsed time
            logging.info(f"Database has been loaded successfully in {round(float(elapsed_time), 3)} seconds.")
            return self
    
        else:
            # If the fast database doesn't exist or force is True, create it
            logging.info("Creating fast database...\n")
            self.create_fast_load_database(force=force)  # Create the fast load database
            self.Index.copy_configs()
            self.Index.read_configs()
            self.calc_all()  # Perform calculations on the database
            self.load(attempt=attempt + 1) # Call load again after the database is created
       
    def switch_language(self, language="Exiobase"):
        """
        Switches the language for the system and updates the labels accordingly.
        
        Args:
            language: The language to switch to (default is "exiobase").
        """
        
        self.language = language  # Set the new language
        self.Index.update_multiindices()  # Update the labels based on the new language
        logging.info(f"Language has been changed successfully to {self.language}")

    def switch_year(self, year):
        self.year = year
        self.exiobase_db = os.path.normpath(os.path.join(self.exiobase_dir, f'IOT_{year}_pxp.zip'))  # Default path to the compressed database
        self.fast_db = os.path.normpath(os.path.join(self.fast_dir, f'Fast_IOT_{year}_pxp'))  # Path to the fast-load database

    def extract_file_parameters(self, json_filename="file_parameters.json"):
        """
        Extracts parameters from all JSON files in the Zip archive (including subfolders) with the specified name
        and combines them into a single header_lines_dict and indices_lines_dict.
        
        Args:
            json_filename: The name of the JSON file to search for within the Zip archive (default is "file_parameters.json").
            
        Returns:
            header_lines_dict: A dictionary mapping file names to their respective header line counts.
            indices_lines_dict: A dictionary mapping file names to their respective index column line counts.
            
        Raises:
            FileNotFoundError: If the specified JSON file is not found in the Zip archive or any of its subfolders.
        """
        
        header_lines_dict = {}  # Dictionary to store header line counts for each file
        indices_lines_dict = {}  # Dictionary to store index column line counts for each file
        found_any = False  # Flag to track whether the JSON file was found
    
        with zipfile.ZipFile(self.exiobase_db, 'r') as zip_ref:  # Open the Zip archive
            # Iterate through all files in the archive
            for file_name in zip_ref.namelist():
                if os.path.basename(file_name) == json_filename:  # Check if the file is the target JSON file
                    found_any = True  # Mark that the file has been found
                    with zip_ref.open(file_name) as file:  # Open the JSON file within the Zip archive
                        data = json.load(file)  # Load the JSON data
                        # Iterate through all entries in the "files" block of the JSON data
                        for key, file_info in data["files"].items():
                            name = file_info["name"]  # Get the file name
                            # Add or overwrite the header line and index column counts
                            header_lines_dict[name] = int(file_info["nr_header"])
                            indices_lines_dict[name] = int(file_info["nr_index_col"])
    
        # Raise an error if no matching JSON file was found
        if not found_any:
            raise FileNotFoundError(f"{json_filename} was not found in the Zip archive or in a subfolder.")
    
        return header_lines_dict, indices_lines_dict  # Return the dictionaries with extracted parameters

    def create_fast_load_database(self, force=False):
        """
        Formats the fast load database and saves it in the specified directory.
        
        Args:
            force: Whether to overwrite existing files in the target directory (default is False).
        
        Raises:
            ValueError: If the target directory already exists and force is not set to True, or if the archive is not a ZIP file.
        """
        
        necessary_files = ["D_cba.txt", "A.txt", "S.txt", "Y.txt"]  # List of required files to process
        ignored_subfolders = ["satellite"]  # Subfolders to ignore when extracting files
        
        # Retrieve the parameters from the Zip file
        header_lines_dict, indices_lines_dict = self.extract_file_parameters()
        
        # Check if self.exiobase_db is a file and ends with ".zip"
        if os.path.isfile(self.exiobase_db) and self.exiobase_db.endswith(".zip"):         
            try:
                os.makedirs(self.fast_db, exist_ok=False)  # Create the target folder for fast load database
                logging.info(f"Folder '{self.fast_db}' was successfully created. \n")
            except FileExistsError:
                # Handle folder existence
                if force:
                    logging.info(f"Folder '{self.fast_db}' already exists. Its contents will be overwritten... (force-mode) \n")
                else:
                    raise ValueError(f"Custom Error: Folder '{self.fast_db}' already exists! To overwrite: force=True")
            
            # Open the ZIP archive for extraction
            with zipfile.ZipFile(self.exiobase_db, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    normalized_path = os.path.normpath(file_name)  # Normalize the file path
                    path_parts = normalized_path.split(os.sep)  # Split path into components
                    if any(ignored in path_parts for ignored in ignored_subfolders):  # Skip ignored subfolders
                        continue
                    base_name = os.path.basename(file_name)   # Extract the base file name
                    relative_file_path = os.path.join(self.fast_db, *path_parts[1:])  # Create the relative path for the file
                    
                    # Read unit.txt-files
                    if base_name== "unit.txt":
                        parent_folder = normalized_path.split(os.sep)[1]
                        if parent_folder == "impacts":   
                            with zip_ref.open(file_name) as file:
                                df = pd.read_csv(io.StringIO(file.read().decode("utf-8")), sep="\t")
                                self.impacts = df["impact"].tolist()
                                self.units = df["unit"].tolist()
                                del df
                        else:
                            with zip_ref.open(file_name) as file:
                                df = pd.read_csv(io.StringIO(file.read().decode("utf-8")), sep="\t")
                                self.regions = df["region"].unique().tolist()
                                self.sectors = df["sector"].unique().tolist()
                                del df
                    
                    # If the file is in necessary_files, convert it and save as .npy
                    if base_name in necessary_files:
                        header_lines = header_lines_dict.get(base_name, 1)  # Get the number of header lines
                        indices_lines = indices_lines_dict.get(base_name, 1)  # Get the number of index columns
                        output_file_path = os.path.splitext(relative_file_path)[0] + '.npy'  # Define the output file path
                        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)  # Ensure the directory exists
                        with zip_ref.open(file_name) as file_obj:
                            # Read the CSV content and convert it to numpy array
                            content = pd.read_csv(file_obj, index_col=list(range(indices_lines)), header=list(range(header_lines)), sep='\t')
                            np.save(output_file_path, content.values.astype(np.float32))  # Save as .npy
                            logging.info(f"{file_name} was found and converted. Saved as: {os.path.basename(output_file_path)} \n")
                        del content  # Clean up the content variable to free memory
                        

        else:
            raise ValueError("The archive must be a ZIP file.")  

    def calc_all(self):
        """
        Calculates missing matrices and saves them in a .npy file.
        """
        
        # Quick loading of matrices (with float32)
        A = np.load(os.path.join(self.fast_db, 'A.npy')).astype(np.float32)
        Y = np.load(os.path.join(self.fast_db, 'Y.npy')).astype(np.float32)
        S = np.load(os.path.join(self.fast_db, 'impacts', 'S.npy')).astype(np.float32)
        
        # Create an identity matrix
        I = np.eye(A.shape[0], dtype=np.float32)
        
        # Create the diagonalized Y matrix
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
                mask = col_idx < n  # If it goes out of bounds
                Y_diag[row_idx[mask], col_idx[mask]] = block[mask]
            
            Y = Y_diag
        
        # Calculate Leontief Inverse (L)
        logging.info("Calculating Leontief Inverse...")
        L = np.linalg.inv(I - A)
        
        # Calculate impact matrices
        logging.info("Calculating impact matrices...")

        # Total impact matrix
        LY = L @ Y

        # List to store environmental impacts for each region
        all_region_impacts = []

        for region in range(len(self.regions)):
            # Determine the index range for the current region's sectors
            start = region * len(self.sectors)
            end = (region + 1) * len(self.sectors)

            # Extract the production and environmental intensity data for this region
            x_region = LY[start:end, :]       # Regional production (sectors of region x sectors)
            s_region = S[:, start:end]        # Environmental intensities (impacts x sectors of region)

            # Calculate environmental impacts for this region
            E_region = s_region @ x_region    # Resulting shape: (impacts x sectors)

            # Store the impact matrix for this region
            all_region_impacts.append(E_region)

        # Stack all regional impact matrices vertically
        # Resulting shape: (impacts * regions, sectors)
        total_impact = np.vstack(all_region_impacts)

        # Initialize a new matrix to store the reordered impacts
        total_impact_sorted = np.zeros_like(total_impact)

        # Reorder rows from grouped-by-region to grouped-by-impact-category
        for new_idx in range((len(S)*len(self.regions))):
            # Calculate the original index before reordering
            old_idx = (new_idx % len(self.regions)) * len(S) + (new_idx // len(self.regions))
            total_impact_sorted[new_idx] = total_impact[old_idx]

        # Replace the original matrix with the sorted version
        total_impact = total_impact_sorted

        # Retail impact matrix
        all_region_impacts = []
        for region in range(len(self.regions)):
            start = region * len(self.sectors)
            end = (region + 1) * len(self.sectors)
            x_region = Y[start:end, :]       # Regional production (sectors of region x sectors)
            s_region = S[:, start:end]        # Environmental intensities (impacts x sectors of region)
            E_region = s_region @ x_region    # Resulting shape: (impacts x sectors)
            all_region_impacts.append(E_region)

        retail_impact = np.vstack(all_region_impacts) # Resulting shape: (impacts * regions x sectors)
        retail_impact_sorted = np.zeros_like(retail_impact)
        for new_idx in range((len(S)*len(self.regions))):
            old_idx = (new_idx % len(self.regions)) * len(S) + (new_idx // len(self.regions))
            retail_impact_sorted[new_idx] = retail_impact[old_idx]
        retail_impact = retail_impact_sorted
        
        # Direct suppliers impact matrix
        df = A.copy()
        df[self.Index.raw_material_indices, :] = 0
        df = df @ Y
        all_region_impacts = []
        for region in range(len(self.regions)):
            start = region * len(self.sectors)
            end = (region + 1) * len(self.sectors)
            x_region = df[start:end, :]       # Regional production (sectors of region x sectors)
            s_region = S[:, start:end]        # Environmental intensities (impacts x sectors of region)
            E_region = s_region @ x_region    # Resulting shape: (impacts x sectors)
            all_region_impacts.append(E_region)

        direct_suppliers_impact = np.vstack(all_region_impacts) # Resulting shape: (impacts * regions x sectors)
        direct_suppliers_impact_sorted = np.zeros_like(direct_suppliers_impact)
        for new_idx in range((len(S)*len(self.regions))):
            old_idx = (new_idx % len(self.regions)) * len(S) + (new_idx // len(self.regions))
            direct_suppliers_impact_sorted[new_idx] = direct_suppliers_impact[old_idx]
        direct_suppliers_impact = direct_suppliers_impact_sorted
        
        # Resources extraction impact matrix
        df = (L - I)
        df[self.Index.not_raw_material_indices, :] = 0
        df = df @ Y
        all_region_impacts = []
        for region in range(len(self.regions)):
            start = region * len(self.sectors)
            end = (region + 1) * len(self.sectors)
            x_region = df[start:end, :]       # Regional production (sectors of region x sectors)
            s_region = S[:, start:end]        # Environmental intensities (impacts x sectors of region)
            E_region = s_region @ x_region    # Resulting shape: (impacts x sectors)
            all_region_impacts.append(E_region)

        resource_extraction_impact = np.vstack(all_region_impacts) # Resulting shape: (impacts * regions x sectors)
        resource_extraction_impact_sorted = np.zeros_like(resource_extraction_impact)
        for new_idx in range((len(S)*len(self.regions))):
            old_idx = (new_idx % len(self.regions)) * len(S) + (new_idx // len(self.regions))
            resource_extraction_impact_sorted[new_idx] = resource_extraction_impact[old_idx]
        resource_extraction_impact = resource_extraction_impact_sorted
        
        # Production of preliminary products impact matrix
        df = (L - I - A)
        df[self.Index.raw_material_indices, :] = 0
        df = df @ Y
        all_region_impacts = []
        for region in range(len(self.regions)):
            start = region * len(self.sectors)
            end = (region + 1) * len(self.sectors)
            x_region = df[start:end, :]       # Regional production (sectors of region x sectors)
            s_region = S[:, start:end]        # Environmental intensities (impacts x sectors of region)
            E_region = s_region @ x_region    # Resulting shape: (impacts x sectors)
            all_region_impacts.append(E_region)

        preliminary_products_impact = np.vstack(all_region_impacts) # Resulting shape: (impacts * regions x sectors)
        preliminary_products_impact_sorted = np.zeros_like(preliminary_products_impact)
        for new_idx in range((len(S)*len(self.regions))):
            old_idx = (new_idx % len(self.regions)) * len(S) + (new_idx // len(self.regions))
            preliminary_products_impact_sorted[new_idx] = preliminary_products_impact[old_idx]
        preliminary_products_impact = preliminary_products_impact_sorted
        
        # Save the calculated matrices
        logging.info("Calculations successful. Matrices are being saved...\n")
        np.save(os.path.join(self.fast_db, 'L.npy'), L)
        np.save(os.path.join(self.fast_db, 'Y.npy'), Y)
        np.save(os.path.join(self.fast_db, 'impacts', 'total.npy'), total_impact)
        np.save(os.path.join(self.fast_db, 'impacts', 'retail.npy'), retail_impact)
        np.save(os.path.join(self.fast_db, 'impacts', 'direct_suppliers.npy'), direct_suppliers_impact)
        np.save(os.path.join(self.fast_db, 'impacts', 'resource_extraction.npy'), resource_extraction_impact)
        np.save(os.path.join(self.fast_db, 'impacts', 'preliminary_products.npy'), preliminary_products_impact)
        logging.info("All matrices have been successfully saved.\n")