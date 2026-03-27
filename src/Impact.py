"""
Impact.py

Contains the `Impact` class (extracted from IOSystem.py).

The Impact class handles loading/storing impact matrices and provides helpers
for colors/units and regional impact reassignment.
"""

from __future__ import annotations

import logging
import os
from typing import List

import numpy as np
import pandas as pd


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

    def load(self, file_ids: List[str] | None = None) -> None:
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
            "preliminary_products": ("preliminary_products.npy", (6174, 9800)),
        }

        selected_ids = set(file_ids or file_mapping.keys())

        for file_id, (filename, expected_shape) in file_mapping.items():
            if file_id not in selected_ids:
                continue
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
            # Use level-0 column (first after reversal) — same level .loc[impact] searches.
            impact_list = self.iosystem.index.impacts_df.iloc[:, 0].tolist()

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
            unit_formatter = getattr(self.iosystem.index, "unit_formatter", None)
            if unit_formatter is not None:
                impact_key = self.iosystem.index.impact_key_from_label(str(impact))
                meta = unit_formatter.format_value(str(impact_key), 0.0, self.iosystem.language, style="short")
                unit = str(meta.get("unit_short") or "").strip()
                if unit:
                    return unit
        except Exception:
            pass

        try:
            impact_list = list(getattr(self.iosystem, "impacts", []) or [])
            idx = impact_list.index(impact)
            units = list(getattr(self.iosystem, "units", []) or [])
            if idx < len(units):
                unit = str(units[idx]).strip()
                if unit:
                    return unit
        except Exception:
            pass

        try:
            impact_list = self.iosystem.index.impacts_df.iloc[:, 0].tolist()
            idx = impact_list.index(impact)
            units_df = getattr(self.iosystem.index, "units_df", None)
            if units_df is not None:
                return str(units_df.iloc[idx].iloc[4]).strip()
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

            # Use the same decomposition as the non-regional pipeline so the four
            # stage shares remain additive and sum to the total.
            self._calculate_supply_chain_matrices(A, L_minus_I, I, S, Y)

            # Step 3: Update labels for DataFrames
            self.iosystem.index.update_multiindices()

            logging.info("Calculations successful.\n")

    def _calculate_supply_chain_matrices(
        self,
        A: np.ndarray,
        L_minus_I: np.ndarray,
        I: np.ndarray,
        S: np.ndarray,
        Y: np.ndarray,
    ) -> None:
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
            direct_suppliers[self.region_indices, :]
            + resource_extraction[self.region_indices, :]
            + preliminary_products[self.region_indices, :]
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

