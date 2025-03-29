import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import pandas as pd # type: ignore 
import numpy as np # type: ignore

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
        - 'D_cba.npy' → `total`: Total impact matrix.
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
                "total": "D_cba.npy",
                "retail": "retail.npy",
                "direct_suppliers": "direct_suppliers.npy",
                "resource_extraction": "resource_extraction.npy",
                "preliminary_products": "preliminary_products.npy"
            }

            # Expected shape of the matrices
            expected_shape = (126, 9800)
            
            # Load the impact matrices
            for attr, filename in impact_files.items():
                file_path = os.path.join(self.IOSystem.fast_db, "impacts", filename)
                try:
                    array = np.load(file_path).astype(np.float32)

                    # Check if the loaded array has the correct shape
                    if array.shape != expected_shape:
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
            direct_suppliers[self.IOSystem.raw_material_indices, :] = 0
    
            # Resource extraction: Only consider raw material sectors
            resource_extraction = L_minus_I.copy()
            resource_extraction[self.IOSystem.not_raw_material_indices, :] = 0
    
            # Preliminary products: Exclude raw material sectors and remove direct suppliers
            preliminary_products = L_minus_I - A
            preliminary_products[self.IOSystem.raw_material_indices, :] = 0
            
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