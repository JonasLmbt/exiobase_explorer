import os
import io
import json
import zipfile
import time
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import pandas as pd # type: ignore 
import numpy as np # type: ignore
from .Impact import Impact
from .Index import Index

class IOSystem:
    """
    This class manages the paths and parameters for loading compressed and fast-load databases
    as well as processing raw material indices for various sectors.
    """

    def __init__(self, compressed_path, fast_path=None, year=2022, language="exiobase", compressed_db=None, fast_db=None, raw_material_indices_per_sector=None):
        """
        Initializes the IOSystem with paths and parameters for the database.
        
        Args:
            compressed_path: The path to the folder containing the compressed Exiobase ZIP files.
            fast_path: (Optional) The path to the folder for fast-load databases.
            year: (Optional) The year for the database to use (default: 2022).
            language: (Optional) The language of the database (default: "exiobase").
            compressed_db: (Optional) The path to the compressed database file.
            fast_db: (Optional) The path to the fast-load database.
            raw_material_indices_per_sector: (Optional) A list of indices that define specific raw material sectors.
        """
        # Year as a string
        self.year = str(year)
        
        # Language of the database
        self.language = language

        # Impact und Index Class
        self.Impact = Impact(self)
        self.Index = Index(self)
        self.regions_exiobase = None
        self.start_time = None
        
        # Paths to the various data folders
        self.compressed_folder = compressed_path  # Path to the folder with compressed ZIP files
        self.compressed_db = compressed_db if compressed_db is not None else os.path.join(self.compressed_folder, f'IOT_{self.year}_pxp.zip')  # Default path to the compressed database
        self.fast_folder = fast_path if fast_path is not None else os.path.join(self.compressed_folder, 'Fast Load Databases')  # Path to the folder for fast-load databases
        self.fast_db = fast_db if fast_db is not None else os.path.join(self.fast_folder, f'Fast_IOT_{self.year}_pxp')  # Path to the fast-load database
        
        # Raw material indices per sector (default values)
        self.raw_material_indices_per_sector = raw_material_indices_per_sector if raw_material_indices_per_sector is not None else [
            0, 1, 2, 3, 4, 5, 6, 7,  # Agricultural products
            8, 9, 10, 11, 12, 13, 14,  # Animal products
            15, 16,  # Manure treatment
            17, 18,  # Forestry, fishing
            19, 20, 21, 22, 23, 24, 25, 26,  # Coal, peat, lignite
            27, 28, 29, 30, 31,  # Petroleum, natural gas, other hydrocarbons
            32, 33, 34, 35, 36, 37, 38, 39,  # Metal ores and minerals
            40, 41, 42,  # Stones, sand, chemical minerals
            57]  # Wood
        
        # Calculate raw material indices
        self.raw_material_indices = []
        for j in range(49):  # For each of the 49 sectors
            for i in self.raw_material_indices_per_sector:
                self.raw_material_indices.append(j * 200 + i)  # Compute the raw material indices per sector

        # Calculate indices that do not represent raw materials
        self.not_raw_material_indices = []
        for i in range(9800):  # For all 9800 indices
            if i not in self.raw_material_indices:
                self.not_raw_material_indices.append(i)  # Indices that do not correspond to raw materials

        
    def load(self, force=False, return_time=True, attempt=1): 
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

        if attempt > 2:
            raise RuntimeError("Interrupted load-function to prevent recursive actions.")
            return  
        
        if os.path.exists(self.fast_db) and not force:
            if attempt == 1:
                print("Fast database was found - Loading...")
            
            # Load the matrices and convert them to DataFrames (without labels)
            self.A = pd.DataFrame(np.load(os.path.join(self.fast_db, 'A.npy')).astype(np.float32))  # Load 'A' matrix
            self.L = pd.DataFrame(np.load(os.path.join(self.fast_db, 'L.npy')).astype(np.float32))  # Load 'L' matrix
            self.Y = pd.DataFrame(np.load(os.path.join(self.fast_db, 'Y.npy')).astype(np.float32))  # Load 'Y' matrix
            self.I = pd.DataFrame(np.identity(9800, dtype=np.float32))  # Identity matrix (9800x9800)
            
            # Load the impact matrices using the Impact class
            self.Impact.load()
            self.Index.update_multiindices()
            
            # If return_time is True, calculate and print the elapsed time
            if self.start_time is not None:
                end_time = time.time()  # Record the end time
                elapsed_time = end_time - self.start_time  # Calculate elapsed time
                print(f"\nDatabase has been loaded successfully in {round(float(elapsed_time), 2)} seconds.")
            else:
                print("\nDatabase has been loaded successfully.")
    
        else:
            # If the fast database doesn't exist or force is True, create it
            print("Creating fast database...\nLanguage was set to exiobase.")
            self.language = "exiobase"
            self.create_fast_load_database(force=force)  # Create the fast load database
            self.calc_all()  # Perform calculations on the database
            self.Index.create_excels(sheet_name="exiobase")
            self.load(attempt=attempt + 1, return_time=return_time)  # Call load again after the database is created

        
    def switch_language(self, language="exiobase"):
        """
        Switches the language for the system and updates the labels accordingly.
        
        Args:
            language: The language to switch to (default is "exiobase").
        """
        
        self.language = language  # Set the new language
        self.Index.update_multiindices()  # Update the labels based on the new language

        
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
    
        with zipfile.ZipFile(self.compressed_db, 'r') as zip_ref:  # Open the Zip archive
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
        unit_files = ["unit.txt"]
        necessary_other = []  # List of other necessary files to copy without changes
        ignored_subfolders = ["satellite"]  # Subfolders to ignore when extracting files
        
        # Retrieve the parameters from the Zip file
        header_lines_dict, indices_lines_dict = self.extract_file_parameters()
        
        # Check if self.compressed_db is a file and ends with ".zip"
        if os.path.isfile(self.compressed_db) and self.compressed_db.endswith(".zip"):         
            try:
                os.makedirs(self.fast_db, exist_ok=False)  # Create the target folder for fast load database
                print(f"Folder '{self.fast_db}' was successfully created. \n")
            except FileExistsError:
                # Handle folder existence
                if force:
                    print(f"Folder '{self.fast_db}' already exists. Its contents will be overwritten... (force-mode) \n")
                else:
                    raise ValueError(f"Custom Error: Folder '{self.fast_db}' already exists! To overwrite: force=True")
            
            # Open the ZIP archive for extraction
            with zipfile.ZipFile(self.compressed_db, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    normalized_path = os.path.normpath(file_name)  # Normalize the file path
                    path_parts = normalized_path.split(os.sep)  # Split path into components
                    if any(ignored in path_parts for ignored in ignored_subfolders):  # Skip ignored subfolders
                        continue
                    base_name = os.path.basename(file_name)   # Extract the base file name
                    relative_file_path = os.path.join(self.fast_db, *path_parts[1:])  # Create the relative path for the file
                    
                    # If the file is in necessary_other, copy it without changes
                    if base_name in necessary_other:
                        print(f"{file_name} was found and saved unchanged. \n")
                        os.makedirs(os.path.dirname(relative_file_path), exist_ok=True)
                        with zip_ref.open(file_name) as file_obj, open(relative_file_path, 'wb') as output_file:
                            output_file.write(file_obj.read())
                    
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
                            print(f"{file_name} was found and converted. Saved at: \n {output_file_path} \n")
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
        print("Diagonalizing Y matrix...")
        if Y.shape != (9800, 9800):
            Y = Y.reshape(9800, 49, 7).sum(axis=2)
            n, num_blocks = Y.shape  # (9800, 49)
            block_size = n // num_blocks  # 9800 / 49 = 200
            Y_diag = np.zeros((n, n), dtype=np.float32)
        
            for i in range(num_blocks):
                block = Y[:, i]  # Column i (size 9800)
                row_idx = np.arange(n)  # 9800 row indices
                col_idx = (row_idx % block_size) + i * block_size
                mask = col_idx < n  # If it goes out of bounds
                Y_diag[row_idx[mask], col_idx[mask]] = block[mask]
            
            Y = Y_diag
        
        # Calculate Leontief Inverse (L)
        print("Calculating Leontief Inverse...")
        L = np.linalg.inv(I - A)
        
        # Calculate impact matrices
        print("Calculating impact matrices...")
        
        # Retail impact matrix
        retail_impact = S @ Y
        
        # Direct suppliers impact matrix
        df = A.copy()
        df[self.raw_material_indices, :] = 0
        direct_suppliers_impact = S @ (df @ Y)  
        
        # Resources extraction impact matrix
        df = (L - I)
        df[self.not_raw_material_indices, :] = 0
        resource_extraction_impact = S @ (df @ Y)  
        
        # Production of preliminary products impact matrix
        df = (L - I - A)
        df[self.raw_material_indices, :] = 0
        preliminary_products_impact = S @ (df @ Y)         
        
        # Save the calculated matrices
        print("Calculations successful. Matrices are being saved...\n")
        np.save(os.path.join(self.fast_db, 'L.npy'), L)
        np.save(os.path.join(self.fast_db, 'Y.npy'), Y)
        np.save(os.path.join(self.fast_db, 'impacts', 'retail.npy'), retail_impact)
        np.save(os.path.join(self.fast_db, 'impacts', 'direct_suppliers.npy'), direct_suppliers_impact)
        np.save(os.path.join(self.fast_db, 'impacts', 'resource_extraction.npy'), resource_extraction_impact)
        np.save(os.path.join(self.fast_db, 'impacts', 'preliminary_products.npy'), preliminary_products_impact)
        print("All matrices have been successfully saved.\n")