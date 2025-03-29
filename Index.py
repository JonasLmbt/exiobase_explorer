import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import pandas as pd # type: ignore 
import numpy as np # type: ignore
import geopandas as gpd

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
        read_excels(): Reads sector, region, and impact data from Excel files 
                       and constructs MultiIndex structures.
        update_multiindices(): Updates all matrices within the IOSystem to use 
                               the correct hierarchical indices.
        create_excels(language=None): Generates and saves sector, region, impact, 
                                      and unit classification data into Excel files.
    """
    
    def __init__(self, IOSystem):
        """
        Initializes the Index object.
        """
        self.IOSystem = IOSystem
        self.world = None

        self.exiobase_to_map_dict = { # Can later be changed in excel
            'Afghanistan': 'WA', 'Albania': 'WE', 'Algeria': 'WF', 'Angola': 'WF', 'Antarctica': None,
            'Argentina': 'WL', 'Armenia': 'WA', 'Australia': 'AU', 'Austria': 'AT', 'Azerbaijan': 'WA',
            'Bahamas': 'WL', 'Bangladesh': 'WA', 'Belarus': 'WE', 'Belgium': 'BE', 'Belize': 'WL',
            'Benin': 'WF', 'Bhutan': 'WA', 'Bolivia': 'WL', 'Bosnia and Herz.': 'WE', 'Botswana': 'WF',
            'Brazil': 'BR', 'Brunei': 'WA', 'Bulgaria': 'BG', 'Burkina Faso': 'WF', 'Burundi': 'WF',
            'Cambodia': 'WA', 'Cameroon': 'WF', 'Canada': 'CA', 'Central African Rep.': 'WF', 'Chad': 'WF',
            'Chile': 'WL', 'China': 'CN', 'Colombia': 'WL', 'Congo': 'WF', 'Costa Rica': 'WL',
            'Croatia': 'HR', 'Cuba': 'WL', 'Cyprus': 'CY', 'Czechia': 'CZ', "Côte d'Ivoire": 'WF',
            'Dem. Rep. Congo': 'WF', 'Denmark': 'DK', 'Djibouti': 'WF', 'Dominican Rep.': 'WL',
            'Ecuador': 'WL', 'Egypt': 'WF', 'El Salvador': 'WL', 'Eq. Guinea': 'WF', 'Eritrea': 'WF',
            'Estonia': 'EE', 'Ethiopia': 'WF', 'Falkland Is.': 'WL', 'Fiji': 'WA', 'Finland': 'FI',
            'Fr. S. Antarctic Lands': 'WA', 'France': 'FR', 'Gabon': 'WF', 'Gambia': 'WF', 'Georgia': 'WA',
            'Germany': 'DE', 'Ghana': 'WF', 'Greece': 'GR', 'Greenland': 'DK', 'Guatemala': 'WL',
            'Guinea': 'WF', 'Guinea-Bissau': 'WF', 'Guyana': 'WL', 'Haiti': 'WL', 'Honduras': 'WL',
            'Hungary': 'HU', 'Iceland': 'WE', 'India': 'IN', 'Indonesia': 'ID', 'Iran': 'WM',
            'Iraq': 'WM', 'Ireland': 'IE', 'Israel': 'WM', 'Italy': 'IT', 'Jamaica': 'WL', 'Japan': 'JP',
            'Jordan': 'WM', 'Kazakhstan': 'WA', 'Kenya': 'WF', 'Kosovo': 'WE', 'Kuwait': 'WM',
            'Kyrgyzstan': 'WA', 'Laos': 'WA', 'Latvia': 'LV', 'Lebanon': 'WM', 'Lesotho': 'WF',
            'Liberia': 'WF', 'Libya': 'WF', 'Lithuania': 'LT', 'Luxembourg': 'LU', 'Madagascar': 'WF',
            'Malawi': 'WF', 'Malaysia': 'WA', 'Mali': 'WF', 'Malta': None, 'Mauritania': 'WF',
            'Mexico': 'MX', 'Moldova': 'WE', 'Mongolia': 'WA', 'Montenegro': 'WE', 'Morocco': 'WF',
            'Mozambique': 'WF', 'Myanmar': 'WA', 'N. Cyprus': 'CY', 'Namibia': 'WF', 'Nepal': 'WA',
            'Netherlands': 'NL', 'New Caledonia': 'WA', 'New Zealand': 'WA', 'Nicaragua': 'WL',
            'Niger': 'WF', 'Nigeria': 'WF', 'North Korea': 'WA', 'North Macedonia': 'WE', 'Norway': 'NO',
            'Oman': 'WM', 'Pakistan': 'WA', 'Palestine': 'WM', 'Panama': 'WL', 'Papua New Guinea': 'WA',
            'Paraguay': 'WL', 'Peru': 'WL', 'Philippines': 'WA', 'Poland': 'PL', 'Portugal': 'PT',
            'Puerto Rico': 'WL', 'Qatar': 'WM', 'Romania': 'RO', 'Russia': 'RU', 'Rwanda': 'WF',
            'S. Sudan': 'WF', 'Saudi Arabia': 'WM', 'Senegal': 'WF', 'Serbia': 'WE', 'Sierra Leone': 'WF',
            'Slovakia': 'SK', 'Slovenia': 'SI', 'Solomon Is.': 'WA', 'Somalia': 'WF', 'Somaliland': 'WF',
            'South Africa': 'ZA', 'South Korea': 'KR', 'Spain': 'ES', 'Sri Lanka': 'WA', 'Sudan': 'WF',
            'Suriname': 'WL', 'Sweden': 'SE', 'Switzerland': 'CH', 'Syria': 'WM', 'Taiwan': 'TW',
            'Tajikistan': 'WA', 'Tanzania': 'WF', 'Thailand': 'WA', 'Timor-Leste': 'WA', 'Togo': 'WF',
            'Trinidad and Tobago': 'WL', 'Tunisia': 'WF', 'Turkey': 'TR', 'Turkmenistan': 'WA',
            'Uganda': 'WF', 'Ukraine': 'WE', 'United Arab Emirates': 'WM', 'United Kingdom': 'GB',
            'United States of America': 'US', 'Uruguay': 'WL', 'Uzbekistan': 'WA', 'Vanuatu': 'WA',
            'Venezuela': 'WL', 'Vietnam': 'WA', 'W. Sahara': 'WF', 'Yemen': 'WM', 'Zambia': 'WF',
            'Zimbabwe': 'WF', 'eSwatini': 'WF'}

        self.general_dict = {'Supply Chain Analysis': 'Supply Chain Analysis', 'Total': 'Total', 'Unit': 'Unit', 'Color': 'Color', 'Retail': 'Retail',
                        'Direct Suppliers': 'Direct Suppliers', 'Preliminary Products': 'Preliminary Products', 'Resource Extraction': 'Resource Extraction',
                            'Subcontractors': 'Subcontractors', 'World': 'World', 'of': 'of'}


    def read_excels(self):
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
                'regions_df': 49,
                'exiobase_to_map_df': len(self.exiobase_to_map_dict),
                'impacts_df': 126,
                'impact_color_df': 126,
                'units_df': 126,
                'general_df': len(self.general_dict)
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
                    if amount != expected_lengths.get(attr, 0):
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
        # Load the latest Excel data and update sector and impact multiindices
        self.read_excels()
        self.create_multiindices()
        self.create_map()

        # Extract unique names for system-wide reference
        self.IOSystem.sectors = self.sectors_df.iloc[:, -1].unique().tolist()
        self.IOSystem.regions = self.regions_df.iloc[:, -1].unique().tolist()
        self.IOSystem.impacts = self.impacts_df.iloc[:, -1].unique().tolist()
        self.IOSystem.units = self.units_df.iloc[:, -1].tolist()

        # Load 'regions_exiobase' data
        regions_exiobase_df = pd.read_excel(os.path.join(self.IOSystem.fast_db, 'regions.xlsx'), sheet_name="exiobase")
        self.IOSystem.regions_exiobase = regions_exiobase_df.iloc[:, -1].unique().tolist()

        # Update impact units DataFrame
        self.IOSystem.Impact.unit = pd.DataFrame({"unit": self.IOSystem.units}, index=self.IOSystem.impacts)

        # Define matrices that need their MultiIndex updated (both sector and impact matrices)
        matrix_mappings = {
            "standard_matrices": ["A", "L", "Y", "I"],
            "impact_matrices": ["S", "total", "retail", "direct_suppliers", "resource_extraction", "preliminary_products"],
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
                

    def create_excels(self, sheet_name=None):
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
        # Set sheet_name to the specified one, or use the default language if None
        sheet_name = sheet_name if sheet_name is not None else self.IOSystem.language

        # Create DataFrames for the main data
        if sheet_name == "exiobase":  # Create DataFrames for exiobase
            self.sectors_df = pd.DataFrame(self.IOSystem.sectors, columns=["sector"])
            self.regions_df = pd.DataFrame(self.IOSystem.regions, columns=["region"])
            self.impacts_df = pd.DataFrame(self.IOSystem.impacts, columns=["impact"])
            self.impact_color_df = pd.DataFrame(["#ffffff"] * len(self.IOSystem.impacts), columns=["color"])
            self.units_df = pd.DataFrame({
                "impact": self.IOSystem.impacts,
                "exiobase unit": self.IOSystem.units, 
                "divisor": [1] * len(self.IOSystem.impacts),
                "decimal places": [3] * len(self.IOSystem.impacts),
                "new unit": self.IOSystem.units
            })

        # Create DataFrames for the additional files
        self.exiobase_to_map_df = pd.DataFrame(list(self.exiobase_to_map_dict.items()), columns=["NAME", "region"]).iloc[:, ::-1]
        self.general_df = pd.DataFrame(list(self.general_dict.items()), columns=["exiobase", "translation"])

        # List of file paths and corresponding DataFrames
        file_data = {
            "sectors.xlsx": [(self.sectors_df.iloc[:, ::-1], sheet_name)],
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

    
    def create_map(self, naturalearth_path="ne_110m_admin_0_countries.zip", force=False):
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
        if self.world is None or force:
            self.world = world = gpd.read_file(naturalearth_path if naturalearth_path is not None else "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip")
    
            self.exiobase_to_map_dict = dict(zip(self.exiobase_to_map_df['NAME'], self.exiobase_to_map_df['region']))
            
            # Neue Spalte für Regionen basierend auf dem Mapping
            self.world["region"] = self.world["NAME"].map(self.exiobase_to_map_dict)
            
            self.world = self.world[["region", "geometry"]]
            
            self.world = self.world.dissolve(by="region") 

        return self.world.copy()