"""
SupplyChain.py

This module provides the SupplyChain class for analyzing environmental impacts along supply chains.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional, Tuple, Union, Any
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
import matplotlib.colors as mcolors
from matplotlib.cm import get_cmap
import re
from matplotlib.colors import Normalize, BoundaryNorm


class SupplyChain:
    """
    A class for analyzing environmental impacts along supply chains using input-output analysis.

    This class provides methods to calculate environmental impacts at different stages of the
    supply chain including resource extraction, preliminary products, direct suppliers, and retail.
    It also offers visualization capabilities through plots and world maps.

    Attributes:
        iosystem: The main database containing all economic and environmental data
        language: Language setting for the analysis
        regional: Boolean indicating if regional analysis is performed
        inputByIndices: Boolean indicating if input was provided by indices
        indices: List of indices for the selected sectors/regions
        hierarchy_levels: Dictionary containing the hierarchy levels and their values
    """

    def __init__(
            self,
            iosystem: Any,
            select: bool = False,
            indices: Optional[List[int]] = None,
            **kwargs
    ) -> None:
        """
        Initialize the SupplyChain object.

        Args:
            iosystem: The database containing economic and environmental data
            select: If True, opens GUI for interactive selection
            indices: Optional list of specific indices to analyze
            **kwargs: Additional keyword arguments for sector/region classification
        """
        # Set core parameters
        self.iosystem = iosystem
        self.language = self.iosystem.language
        self.regional = False
        self.inputByIndices = False

        # Initialize hierarchy levels safely
        self.hierarchy_levels: Dict[str, Optional[str]] = {}

        if indices is not None:
            self.indices = indices
            self.inputByIndices = True
        else:
            self._setup_hierarchy_selection(select, kwargs)

    def _setup_hierarchy_selection(self, select: bool, kwargs: Dict[str, Any]) -> None:
        """
        Set up hierarchy selection based on user input.

        Args:
            select: Whether to use GUI selection
            kwargs: Keyword arguments for selection
        """
        if select:
            region_selection = self.get_multiindex_selection(
                self.iosystem.index.region_multiindex
            )
            sector_selection = self.get_multiindex_selection(
                self.iosystem.index.sector_multiindex_per_region
            )
            kwargs = {**region_selection, **sector_selection}

        # Set hierarchy levels from all classification attributes
        all_classifications = (
                self.iosystem.index.region_classification +
                self.iosystem.index.sector_classification
        )

        for attr in all_classifications:
            value = kwargs.get(attr, None)
            setattr(self, attr, value)
            self.hierarchy_levels[attr] = value

        # Calculate indices based on hierarchy levels
        self._calculate_indices()

        # Check if regional analysis is needed
        self._check_regional_analysis()

    def _calculate_indices(self) -> None:
        """
        Calculate indices based on hierarchy levels.
        """
        df = self.iosystem.I.copy()
        idx = pd.IndexSlice

        # Create slice for each classification level
        slice_list = []
        all_classifications = (
                self.iosystem.index.region_classification +
                self.iosystem.index.sector_classification
        )

        for level in all_classifications:
            level_value = self.hierarchy_levels[level]
            slice_list.append(
                slice(None) if level_value is None else level_value
            )

        subset = df.loc[idx[*slice_list], :]
        self.indices = df.index.get_indexer(subset.index).tolist()

    def _check_regional_analysis(self) -> None:
        """
        Check if regional analysis should be performed.
        """
        region_selected = any(
            self.hierarchy_levels[level]
            for level in self.iosystem.index.region_classification
        )
        sector_selected = any(
            self.hierarchy_levels[level]
            for level in self.iosystem.index.sector_classification
        )

        if region_selected and not sector_selected:
            self.regional = True
            self.iosystem.impact.get_regional_impacts(region_indices=self.indices)

    def get_multiindex_selection(self, index: pd.MultiIndex) -> Dict[str, str]:
        """
        Create an interactive tree structure to display a MultiIndex.
        Returns the selected schema as a dictionary.

        Args:
            index: The MultiIndex to be displayed in the TreeView

        Returns:
            Dictionary containing the selected schema
        """
        # Create Tkinter window
        root = tk.Tk()
        root.title("MultiIndex Selection")
        root.geometry("600x400")

        # Create TreeView with proper configuration
        tree = ttk.Treeview(root, height=15, columns=("text",))
        tree.heading("#1", text="Description")
        tree.column("#1", width=300)
        tree.pack(fill="both", expand=True)

        # Label to display the path as dictionary
        path_label = tk.Label(
            root,
            text="Selection as Dictionary: ",
            font=("Arial", 12)
        )
        path_label.pack(pady=10)

        # Variable to store the selected path
        selected_path: Dict[str, str] = {}

        def create_treeview_from_index(
                parent: str,
                index: pd.MultiIndex,
                level: int = 0,
                path: str = ""
        ) -> None:
            """
            Recursively create tree structure from MultiIndex.

            Args:
                parent: Parent node ID
                index: MultiIndex to process
                level: Current level in the hierarchy
                path: Current path string
            """
            if level < len(index.names):
                unique_values = index.get_level_values(level).unique()
                for value in unique_values:
                    node_id = f"{path}-{value}"
                    new_parent = tree.insert(parent, 'end', node_id, text=str(value))
                    subset = index[index.get_level_values(level) == value]
                    create_treeview_from_index(new_parent, subset, level + 1, node_id)

        def show_selection(event: tk.Event) -> None:
            """
            Handle selection event and update the path display.

            Args:
                event: Tkinter event object
            """
            if not tree.selection():
                return

            selected_item = tree.selection()[0]
            path = [tree.item(selected_item)['text']]

            # Collect path from parent nodes
            while tree.parent(selected_item):
                parent_item = tree.parent(selected_item)
                path.insert(0, tree.item(parent_item)['text'])
                selected_item = parent_item

            # Create dictionary with the last selected value
            nonlocal selected_path
            selected_path = {}

            if len(path) <= len(index.names):
                level_name = index.names[len(path) - 1]
                selected_path[level_name] = path[-1]

            # Update label with selection
            path_label.config(
                text=f"Selection as Dictionary: {selected_path}"
            )

        # Create tree structure from MultiIndex
        create_treeview_from_index('', index)

        # Bind selection event
        tree.bind("<<TreeviewSelect>>", show_selection)

        # Handle window closing
        def on_close() -> None:
            """
            Handle window close event.
            """
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()

        return selected_path

    def __repr__(self) -> str:
        """
        Return a string representation of the SupplyChain object.

        Returns:
            String representation useful for debugging
        """
        if self.inputByIndices:
            return (
                f"SupplyChain(Number of Indices: {len(self.indices)}, "
                f"input was given by indices)"
            )
        else:
            return (
                f"SupplyChain(Number of Indices: {len(self.indices)}, "
                f"Hierarchy levels: {self.hierarchy_levels})"
            )

    def transform_unit(self, value: float, impact: str) -> Tuple[float, str]:
        """
        Transform the given value based on the unit for the specified impact.

        Args:
            value: The raw impact value
            impact: The impact category name

        Returns:
            Tuple containing the transformed value and its unit
        """
        units_df = self.iosystem.index.units_df
        impact_mask = units_df.iloc[:, 0] == impact

        if not impact_mask.any():
            raise ValueError(f"Impact '{impact}' not found in units iosystem")

        impact_row_idx = units_df[impact_mask].index[0]
        impact_row = units_df.iloc[impact_row_idx].tolist()

        unit = impact_row[4]
        transformed_value = value / impact_row[2]

        return transformed_value, unit

    def total(self, impact: str) -> Tuple[float, str]:
        """
        Calculate the total environmental impact along the entire supply chain.

        Uses the Leontief Inverse to compute total environmental impact for a given
        impact category across the entire supply chain.

        Args:
            impact: The name of the environmental impact to calculate

        Returns:
            Tuple containing the total impact value and its unit
        """
        total_impact = (
            self.iosystem.impact.total.loc[impact]
            .iloc[:, self.indices]
            .sum()
            .sum()
        )

        return self.transform_unit(value=total_impact, impact=impact)

    def resource_extraction(self, impact: str) -> Tuple[float, str]:
        """
        Calculate the environmental impact of resource extraction.

        Args:
            impact: The environmental impact type

        Returns:
            Tuple containing the impact value and its unit
        """
        if self.regional:
            impact_data = self.iosystem.impact.resource_extraction_regional
        else:
            impact_data = self.iosystem.impact.resource_extraction

        extraction_impact = (
            impact_data.loc[impact]
            .iloc[:, self.indices]
            .sum()
            .sum()
        )

        return self.transform_unit(value=extraction_impact, impact=impact)

    def preliminary_products(self, impact: str) -> Tuple[float, str]:
        """
        Calculate the environmental impact of preliminary products.

        Args:
            impact: The environmental impact type

        Returns:
            Tuple containing the impact value and its unit
        """
        if self.regional:
            impact_data = self.iosystem.impact.preliminary_products_regional
        else:
            impact_data = self.iosystem.impact.preliminary_products

        preliminary_impact = (
            impact_data.loc[impact]
            .iloc[:, self.indices]
            .sum()
            .sum()
        )

        return self.transform_unit(value=preliminary_impact, impact=impact)

    def direct_suppliers(self, impact: str) -> Tuple[float, str]:
        """
        Calculate the environmental impact of direct suppliers (A-Matrix).

        Raw materials are filtered out based on raw_material_indices.

        Args:
            impact: The environmental impact type

        Returns:
            Tuple containing the impact value and its unit
        """
        if self.regional:
            impact_data = self.iosystem.impact.direct_suppliers_regional
        else:
            impact_data = self.iosystem.impact.direct_suppliers

        suppliers_impact = (
            impact_data.loc[impact]
            .iloc[:, self.indices]
            .sum()
            .sum()
        )

        return self.transform_unit(value=suppliers_impact, impact=impact)

    def retail(self, impact: str) -> Tuple[float, str]:
        """
        Calculate the environmental impact directly at the production site.

        Uses the identity matrix approach for direct production impacts.

        Args:
            impact: The environmental impact type

        Returns:
            Tuple containing the impact value and its unit
        """
        if self.regional:
            impact_data = self.iosystem.impact.retail_regional
        else:
            impact_data = self.iosystem.impact.retail

        retail_impact = (
            impact_data.loc[impact]
            .iloc[:, self.indices]
            .sum()
            .sum()
        )

        return self.transform_unit(value=retail_impact, impact=impact)

    def calculate_all(
            self,
            impacts: List[str],
            relative: bool = True,
            decimal_places: int = 2,
            row_length: int = 35
    ) -> pd.DataFrame:
        """
        Calculate environmental impacts across the supply chain.

        Returns results as a comprehensive DataFrame with all supply chain stages.

        Args:
            impacts: List of environmental impacts to calculate
            relative: If True, returns relative proportions; if False, absolute values
            decimal_places: Number of decimal places for rounding
            row_length: Maximum length for text wrapping

        Returns:
            DataFrame containing calculated impacts for each stage
        """
        if not impacts:
            raise ValueError("At least one impact must be specified")

        data = []

        for impact in impacts:
            try:
                # Calculate impacts for all supply chain stages
                total_val, unit = self.total(impact)
                res_val, _ = self.resource_extraction(impact)
                pre_val, _ = self.preliminary_products(impact)
                direct_val, _ = self.direct_suppliers(impact)
                ret_val, _ = self.retail(impact)

                # Get color for visualization
                color = self.iosystem.impact.get_color(impact)

                # Convert to relative values if requested
                if relative and total_val != 0:
                    res_val /= total_val
                    pre_val /= total_val
                    direct_val /= total_val
                    ret_val /= total_val

                # Append calculated values
                data.append([
                    round(res_val, decimal_places),
                    round(pre_val, decimal_places),
                    round(direct_val, decimal_places),
                    round(ret_val, decimal_places),
                    round(total_val, decimal_places),
                    unit,
                    color
                ])

            except Exception as e:
                print(f"Error calculating impact '{impact}': {e}")
                # Add empty row for failed calculations
                data.append([0, 0, 0, 0, 0, "", "gray"])

        # Define column names using general dictionary
        general_dict = self.iosystem.index.general_dict
        columns = [
            general_dict["Resource Extraction"],
            general_dict["Preliminary Products"],
            general_dict["Direct Suppliers"],
            general_dict["Retail"],
            general_dict["Total"],
            general_dict["Unit"],
            general_dict["Color"]
        ]

        # Apply text wrapping to impact names
        wrapped_impacts = [self._wrap_text(impact, row_length) for impact in impacts]

        return pd.DataFrame(data, index=wrapped_impacts, columns=columns)

    def _wrap_text(self, text: str, max_length: int = 35) -> str:
        """
        Wrap text to ensure no line exceeds the maximum length.

        Line breaks are inserted preferably at spaces. If a single word
        is longer than max_length, it will be split at the limit.

        Args:
            text: The input string to wrap
            max_length: Maximum number of characters per line

        Returns:
            Wrapped string with line breaks
        """
        if len(text) <= max_length:
            return text

        words = text.split()
        result = ""
        line = ""

        for word in words:
            # Check if adding the next word keeps the line within the limit
            test_line = f"{line} {word}" if line else word

            if len(test_line) <= max_length:
                line = test_line
            else:
                if line:  # If we have content in the current line, start a new one
                    result += line + "\n"
                    line = word
                else:  # Single word is too long, force break
                    line = word

        # Add the last line if it's not empty
        if line:
            result += line

        # Post-processing: force breaks for words longer than max_length
        final_result = ""
        for line in result.split("\n"):
            while len(line) > max_length:
                final_result += line[:max_length] + "\n"
                line = line[max_length:]
            final_result += line + "\n"

        return final_result.rstrip()

    def plot_bubble_diagram(
            self,
            impacts: List[str],
            title: Optional[str] = None,
            size: float = 1,
            lines: bool = True,
            line_width: float = 1,
            line_color: str = "gray",
            text_position: str = "center"
    ) -> plt.Figure:
        """
        Visualize environmental impacts along the supply chain.

        Creates a bubble plot showing relative environmental impacts at various
        supply chain stages. Bubble sizes are proportional to the impact share.

        Args:
            impacts: List of environmental impacts to plot
            title: Plot title (auto-generated if None)
            size: Scale factor for plot size
            lines: Whether to include grid lines
            line_width: Width of grid lines
            line_color: Color of grid lines
            text_position: Position of text labels ("center", "top", "bottom")

        Returns:
            Matplotlib figure object
        """
        if not impacts:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title("No impacts selected", fontsize=14, fontweight="bold", pad=20)
            ax.axis('off')
            return fig

        # Set default title if none provided
        if title is None:
            general_dict = self.iosystem.index.general_dict
            title = f'{general_dict["Supply Chain Analysis"]} {self._get_title()}'

        # Get relative environmental impact data
        df_rel = self.calculate_all(impacts=impacts, relative=True, decimal_places=5)

        # Extract labels and data
        col_labels = df_rel.columns[:5].tolist()
        row_labels = df_rel.index.tolist()

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.set_dpi(size * 100)

        # Set plot title
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        # Configure plot dimensions
        n_rows, n_cols = len(row_labels), 5
        ax.set_xlim(-0.5, n_cols - 0.5)
        ax.set_ylim(-0.5, n_rows - 0.5)
        ax.set_xticks(range(n_cols))
        ax.set_yticks(range(n_rows))
        ax.set_xticklabels(col_labels, fontsize=10, fontweight="bold")
        ax.set_yticklabels(row_labels, fontsize=10, fontweight="bold")
        ax.invert_yaxis()
        ax.grid(False)

        # Hide spines
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Draw grid lines if requested
        if lines:
            self._draw_grid_lines(ax, n_rows, n_cols, line_color, line_width)

        # Plot data points
        self._plot_bubble_data(
            ax, df_rel, row_labels, text_position
        )

        fig.tight_layout()
        plt.close(fig)  # PREVENTS DISPLAY IN WINDOW DURING USE
        return fig

    def _draw_grid_lines(
            self,
            ax: plt.Axes,
            n_rows: int,
            n_cols: int,
            line_color: str,
            line_width: float
    ) -> None:
        """
        Draw grid lines on the supply chain plot.
        """
        # Horizontal lines
        for i in range(n_rows + 1):
            ax.axhline(i - 0.5, color=line_color, linewidth=line_width)

        # Vertical lines
        for j in range(n_cols + 1):
            ax.axvline(j - 0.5, color=line_color, linewidth=line_width)

        # Enhanced border lines
        ax.axhline(n_rows - 0.5, color=line_color, linewidth=line_width * 1.5)
        ax.axvline(n_cols - 0.5, color=line_color, linewidth=line_width * 1.5)

    def _plot_bubble_data(
            self,
            ax: plt.Axes,
            df_rel: pd.DataFrame,
            row_labels: List[str],
            text_position: str
    ) -> None:
        """
        Plot the actual data points and labels on the supply chain diagram.
        """
        bubble_scale = 3000
        general_dict = self.iosystem.index.general_dict

        for i, impact_name in enumerate(row_labels):
            row_values = df_rel.loc[impact_name]
            color = row_values[general_dict["Color"]]

            # Plot supply chain stages (columns 0 to 3)
            for col in range(4):
                val_rel = row_values.iloc[col]
                bubble_size = val_rel * bubble_scale

                ax.scatter(
                    col, i,
                    s=bubble_size,
                    color=color,
                    alpha=0.7,
                    edgecolors="black",
                    linewidths=0.6
                )

                ax.text(
                    col, i,
                    f"{val_rel * 100:.1f}%",
                    va=text_position,
                    ha="center",
                    fontsize=9,
                    color="black"
                )

            # Total impact (column 4)
            total_val = row_values[general_dict["Total"]]
            unit = row_values.get(general_dict["Unit"], "")
            text_str = f"{total_val}\n{unit}"

            ax.text(
                4, i,
                text_str,
                ha="center",
                va="center",
                fontsize=9,
                color="black",
                fontweight="bold"
            )

    def return_impact_per_region_data(self, impact, save_to_excel: str | None = None):
        # Remove function? Same as impact_per_region_df with different return type
        """
        Returns a DataFrame (index: EXIOBASE regions) with one column per impact.
        The column name includes the unit in parentheses, e.g. "Water consumption (m³)".

        If 'save_to_excel' is provided, writes the file and returns None.
        """
        res = self.impact_per_region_df(
            impacts=impact,
            relative=False,
            include_units_in_cols=True,
            localize_cols=True,
            save_to_excel=save_to_excel,
        )
        if save_to_excel:
            return None
        df, _units = res
        return df

    def plot_worldmap_by_subcontractors(
            self,
            color: str = "Blues",
            title: Optional[str] = None,
            relative: bool = True,
            show_legend: bool = False,
            return_data: bool = False,
            # pass-through to map function for consistent behavior
            mode: str = "binned",                 # "continuous" or "binned"
            k: int = 7,                           # classes if no custom_bins
            custom_bins: Optional[List[float]] = None,  # explicit breakpoints
            norm_mode: str = "linear",            # "linear" | "log" | "power" (continuous only)
            robust: float = 2.0,                  # quantile clipping in % (continuous only)
            gamma: float = 0.7                    # for PowerNorm (continuous only)
    ) -> Union[plt.Figure, Tuple[plt.Figure, pd.DataFrame]]:
        """
        Plot world map showing subcontractor distribution.

        Notes
        -----
        - In continuous mode we color and label by ABSOLUTE values (unit shown in legend).
        - In binned mode, `relative=True` bins by percentage share; `relative=False` by absolute values.
        """
        # Aggregate subcontractor intensity by EXIOBASE region
        values = list(
            self.iosystem.L.iloc[:, self.indices]
            .groupby(level=self.iosystem.index.region_classification[-1], sort=False)
            .sum()
            .sum(axis=1)
            .values
        )

        # Build DataFrame with a clear column name
        df = pd.DataFrame({f"{self.iosystem.index.general_dict['Subcontractors']}": values}, index=self.iosystem.regions_exiobase)

        # Title
        if title is None:
            general_dict = self.iosystem.index.general_dict
            title = f'{general_dict["Subcontractors"]} {self._get_title()}'

        # IMPORTANT: scalar unit to avoid length mismatch after filtering (e.g., Malta drop)
        unit_scalar = ""  # no specific unit known; keep empty string

        return self._plot_worldmap_by_data(
            df=df,
            units=unit_scalar,              # scalar unit
            column=f"{self.iosystem.index.general_dict['Subcontractors']}",
            color_map=color,
            relative=relative,
            title=title,
            show_legend=show_legend,
            return_data=return_data,
            mode=mode,
            k=k,
            custom_bins=custom_bins,
            norm_mode=norm_mode,
            robust=robust,
            gamma=gamma
        )

    def plot_worldmap_by_impact(
            self,
            impact: str,
            color: str = "Blues",
            title: Optional[str] = None,
            relative: bool = True,
            show_legend: bool = False,
            return_data: bool = False,
            # pass-through to map function
            mode: str = "binned",                 # "continuous" or "binned"
            k: int = 7,                           # classes if no custom_bins
            custom_bins: Optional[List[float]] = None,  # explicit breakpoints
            norm_mode: str = "linear",            # "linear" | "log" | "power"
            robust: float = 2.0,                  # quantile clipping in %, e.g. 2 -> [2%,98%]
            gamma: float = 0.7                    # for PowerNorm
    ) -> Union[plt.Figure, Tuple[plt.Figure, pd.DataFrame]]:
        """
        Plot world map showing impact distribution with clear legend.
        """
        values = (
            self.iosystem.impact.total.loc[impact]
            .iloc[:, self.indices]
            .sum(axis=1)
            .values
            .tolist()
        )

        # Unit transformation
        values = [self.transform_unit(value=value, impact=impact)[0] for value in values]

        df = pd.DataFrame({impact: values}, index=self.iosystem.regions_exiobase)

        if title is None:
            general_dict = self.iosystem.index.general_dict
            title = f'{general_dict["Global"]} {impact} {self._get_title()}'

        # IMPORTANT: pass unit as scalar, not a list (avoids length mismatch after drops)
        unit_scalar = self.iosystem.impact.get_unit(impact)

        return self._plot_worldmap_by_data(
            df=df,
            units=unit_scalar,              # scalar unit
            color_map=color,
            relative=relative,
            title=title,
            show_legend=show_legend,
            return_data=return_data,
            mode=mode,
            k=k,
            custom_bins=custom_bins,
            norm_mode=norm_mode,
            robust=robust,
            gamma=gamma
        )

    def _plot_worldmap_by_data(
            self,
            df: pd.DataFrame,
            units: Optional[Union[str, List[str]]] = None,
            column: Optional[str] = None,
            color_map: str = "Blues",
            relative: bool = False,
            title: str = "",
            show_legend: bool = True,
            return_data: bool = False,
            mode: str = "binned",          # "continuous" or "binned"
            k: int = 7,                    # classes if mode="binned" and no custom_bins
            custom_bins: Optional[List[float]] = None,
            # NEW: continuous contrast controls
            norm_mode: str = "linear",     # "linear" | "log" | "power"
            robust: float = 2.0,           # quantile clipping in %
            gamma: float = 0.7             # for PowerNorm
    ) -> Union[plt.Figure, Tuple[plt.Figure, pd.DataFrame]]:
        """
        Plot a choropleth map with a clear legend showing numeric ranges.

        Continuous mode:
            - Colors and legend are based on ABSOLUTE values (with unit),
            regardless of `relative`. This keeps the scale interpretable.
            - `norm_mode` + `robust` + `gamma` control contrast.

        Binned mode:
            - Behaves like before; `relative=True` means bins on percentages,
            `relative=False` means bins on absolute values.
        """

        # Helper for binned legend range labels (raw numbers)
        def _fmt_range(lo: float, hi: float) -> str:
            if lo is None and hi is None:
                return ""
            if lo is None:
                return f"≤ {hi:.2f}"
            elif hi is None:
                return f"≥ {lo:.2f}"
            else:
                return f"{lo:.2f} – {hi:.2f}"

        world = self.iosystem.index.get_map()
        column = column if column is not None else df.columns[0]

        # Drop Malta if present (special case in EXIOBASE)
        df = df.drop(index="MT", errors="ignore")

        values = df[column].copy()
        total_sum = values.sum()
        percentages = (values / total_sum * 100.0) if total_sum != 0 else values * 0.0

        # Align shapes and attach metadata
        world = world.loc[df.index]
        world = self._add_world_metadata(world, values, percentages, units)

        # Data columns:
        # - absolute values: world["value"]
        # - percentage share: world["percentage"]
        # For continuous we force absolute; for binned we honor `relative`.
        if mode == "continuous":
            world["data"] = world["value"].astype(float)       # FORCE absolute
        else:
            world["data"] = (world["percentage"] if relative else world["value"]).astype(float)

        data = world["data"].astype(float)
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))

        if mode == "continuous":
            # Robust quantile clipping for better contrast
            finite = data[np.isfinite(data)]
            if finite.empty:
                vmin, vmax = 0.0, 1.0
            else:
                lo_q, hi_q = np.nanpercentile(finite, [robust, 100.0 - robust])
                vmin, vmax = float(lo_q), float(hi_q)
                if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
                    vmin, vmax = float(finite.min()), float(finite.max())
                    if vmin == vmax:
                        vmin, vmax = vmin - 0.5, vmax + 0.5

            # Choose normalization
            if norm_mode == "log":
                eps = 1e-12
                vmin = max(vmin, eps)
                norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
            elif norm_mode == "power":
                norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)
            else:
                norm = Normalize(vmin=vmin, vmax=vmax)

            cmap = get_cmap(color_map)

            world.plot(
                column="data",
                cmap=cmap,
                legend=False,
                ax=ax,
                edgecolor="gray",
                linewidth=0.6,
                alpha=0.95,
                norm=norm
            )

            if show_legend:
                # Absolute-value legend with unit
                unit = None
                if isinstance(units, str):
                    unit = units
                elif hasattr(units, "__len__") and len(units) > 0:
                    # if heterogeneous, we don't try to synthesize; else take single
                    unit = units if isinstance(units, str) else (list(set(units))[0] if len(set(units)) == 1 else None)

                self._add_map_legend(
                    fig=fig, ax=ax, data=data, column=column, color_map=color_map,
                    relative=relative,
                    mode="continuous",
                    edges=None,
                    norm_mode=norm_mode,
                    vmin=vmin, vmax=vmax, gamma=gamma,
                    unit=unit
                )

        elif mode == "binned":
            # Discrete classes with numeric ranges in legend
            finite = data[np.isfinite(data)]
            if finite.empty:
                world.plot(color="#dddddd", ax=ax, edgecolor="gray", linewidth=0.6)
                self._configure_map_appearance(ax, title)
                plt.close(fig)
                return (fig, world) if return_data else fig

            dmin, dmax = float(finite.min()), float(finite.max())

            # Determine bin edges
            if custom_bins is not None and len(custom_bins) > 0:
                edges = np.array([dmin] + list(custom_bins) + [dmax], dtype=float)
                edges = np.unique(edges)
            else:
                edges = np.linspace(dmin, dmax, num=max(2, int(k) + 1))

            if np.allclose(edges.min(), edges.max()):
                edges = np.array([dmin - 0.5, dmax + 0.5])

            n_classes = len(edges) - 1
            cmap = get_cmap(color_map, n_classes)
            norm = BoundaryNorm(edges, ncolors=cmap.N, clip=True)

            world.plot(
                column="data",
                cmap=cmap,
                ax=ax,
                edgecolor="gray",
                linewidth=0.6,
                alpha=0.9,
                norm=norm
            )

            if show_legend:
                sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
                sm.set_array([])
                cbar = fig.colorbar(
                    sm,
                    ax=ax,
                    fraction=0.03,
                    pad=0.02,
                    ticks=[(edges[i] + edges[i+1]) / 2 for i in range(n_classes)]
                )
                tick_labels = [_fmt_range(edges[i], edges[i+1]) for i in range(n_classes)]
                cbar.ax.set_yticklabels(tick_labels)
                # If we have a single unit, display it in the label
                label = column
                if isinstance(units, str):
                    label = f"{column} [{units}]"
                elif hasattr(units, "__len__") and len(set(units)) == 1:
                    label = f"{column} [{list(set(units))[0]}]"
                cbar.set_label(f"{label}")

        else:
            raise ValueError('mode must be "continuous" or "binned"')

        self._configure_map_appearance(ax, title)
        plt.close(fig)
        return (fig, world) if return_data else fig

    def plot_pie_by_impact(
        self,
        impact: str,
        *,
        top_slices: int = 10,
        min_pct: float | None = None,             # when set, ignores top_slices
        sort_slices: str = "desc",                # "desc" | "asc" | "original"
        title: str | None = None,
        start_angle: int = 90,
        counterclockwise: bool = True,
        color_map: str = "tab20",                 # e.g., "tab20", "tab20_r", "viridis"
        relative: bool = True,                    
        return_data: bool = False
    ) -> plt.Figure | tuple[plt.Figure, pd.DataFrame]:
        """Render a pie chart for a single impact across regions.

        Pulls the same world data used by the choropleth, then aggregates and plots
        the top slices (or those above a percentage threshold), with the remainder
        grouped as "Others". Colors are drawn from a matplotlib colormap.

        Args:
            impact (str): Canonical impact key (or localized, handled upstream).
            top_slices (int): Max number of slices to show (if `min_pct` is None).
            min_pct (float | None): Minimum share (%) to include as its own slice.
            sort_slices (str): Sorting strategy for slices ("desc", "asc", "original").
            title (str | None): Optional figure title.
            start_angle (int): Starting angle for the first slice.
            counterclockwise (bool): Draw wedges counterclockwise if True.
            color_map (str): Matplotlib colormap name (supports *_r reversal).
            relative (bool): Use relative values for data fetch (percent-based).
            return_data (bool): If True, return (fig, pie_df) with 'label', 'value', 'unit'.

        Returns:
            Figure | (Figure, DataFrame): The rendered figure, optionally with data.
        """
        # 1) Fetch base data (same provider as world map)
        df, unit = self._sc__world_df(
            impact,
            relative=relative,
            color="Reds", title=None,
            mode="binned", k=7, custom_bins=None, norm_mode="linear", robust=2.0, gamma=0.7
        )

        s = pd.to_numeric(df["value"], errors="coerce").fillna(0.0)
        base = pd.DataFrame({"region": df["region"], "value": s})

        # 2) Sorting
        if sort_slices == "asc":
            base = base.sort_values("value", ascending=True, kind="mergesort")
        elif sort_slices == "original":
            pass  # keep provider order
        else:  # default: "desc"
            base = base.sort_values("value", ascending=False, kind="mergesort")

        total = float(base["value"].sum())
        if total <= 0:
            # Graceful empty-state fallback
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, self.iosystem.index.general_dict.get("No data", "No data"),
                    ha="center", va="center", transform=ax.transAxes)
            ax.axis("off")
            return (fig, base.assign(unit=unit)) if return_data else fig

        # 3) Slice selection (+ 'Others')
        others_label = self.iosystem.index.general_dict.get("Others", "Others")

        if min_pct is not None:
            thr = total * (float(min_pct) / 100.0)
            top = base[base["value"] >= thr].copy()
            others_val = total - float(top["value"].sum())
        else:
            k = max(1, int(top_slices))
            top = base.head(k).copy()
            others_val = base["value"].iloc[k:].sum()

        pie_df = top.rename(columns={"region": "label"})[["label", "value"]]
        if others_val > 0:
            pie_df = pd.concat(
                [pie_df, pd.DataFrame([{"label": others_label, "value": float(others_val)}])],
                ignore_index=True
            )

        # 4) Colors: ensure "Others" is visually distinct from the largest slice
        cmap = get_cmap(color_map)
        n = len(pie_df)
        # Evenly sample colors from the colormap
        if n == 1:
            cols = [cmap(0.15)]
        else:
            cols = [cmap(i / max(n - 1, 1)) for i in range(n)]

        # If the last slice is "Others", assign a neutral-ish color
        if pie_df.iloc[-1]["label"] == others_label:
            others_color = cmap(0.85)
            # Rare: if equal to the first color (discrete maps), switch to gray
            if n >= 1 and np.allclose(others_color, cols[0]):
                others_color = (0.7, 0.7, 0.7, 1.0)
            cols[-1] = others_color

        # 5) Plot
        fig = plt.figure()
        ax = fig.add_subplot(111)
        wedges, _texts, autotexts = ax.pie(
            pie_df["value"].to_numpy(),
            labels=None,
            startangle=int(start_angle),
            counterclock=bool(counterclockwise),
            autopct="%1.1f%%"
        )
        for w, c in zip(wedges, cols):
            w.set_facecolor(c)

        # Legend placed outside on the left for readability
        ax.legend(wedges, pie_df["label"].tolist(), loc="center left", bbox_to_anchor=(1.0, 0.5))
        if title:
            ax.set_title(title)
        ax.axis("equal")
        fig.tight_layout()

        pie_df["unit"] = unit
        return (fig, pie_df) if return_data else fig

    def _canon_impact(self, impact: str) -> str:
        """
        Map localized impact names to canonical keys.

        Example:
            "Zulieferer" -> "Subcontractors"

        If no mapping is needed, return the input unchanged.
        """
        if not isinstance(impact, str):
            return impact
        key = impact.strip()
        low = key.casefold()

        gd = getattr(self.iosystem.index, "general_dict", {}) or {}
        sub_local = [gd.get("Subcontractors", ""), gd.get("Zulieferer", "")]
        sub_local = [s.casefold() for s in sub_local if s]

        if low == "subcontractors" or low in sub_local:
            return "Subcontractors"
        return key

    def impact_per_region_df(
        self,
        impacts,
        *,
        relative: bool = False,
        include_units_in_cols: bool = True,
        localize_cols: bool = True,
        save_to_excel: str | None = None,
    ):
        """
        Unified data source: values per EXIOBASE-region for 1..n impacts.

        Parameters
        ----------
        impacts : str | list[str]
            Single impact or a list (e.g., ["Value added", "Labour time", "Subcontractors"]).
        relative : bool
            If True, return percentage shares per impact (sum = 100). Otherwise absolute values.
        include_units_in_cols : bool
            Include the unit in column names (e.g., "Water (m³)").
        localize_cols : bool
            Use localized display names for columns when available.
        save_to_excel : str | None
            If provided, write to this path and return None.

        Returns
        -------
        (df, units_map) | None
            df: DataFrame indexed by EXIOBASE regions (self.iosystem.regions),
                columns are impact names (optionally with units).
            units_map: Mapping {column_name -> unit_string}.
        """
        imp_list = [impacts] if isinstance(impacts, str) else list(impacts)
        imp_list = [self._canon_impact(i) for i in imp_list if i]

        gd = getattr(self.iosystem.index, "general_dict", {}) or {}
        regions = self.iosystem.regions

        data = {}
        units_map = {}

        for imp in imp_list:
            if imp == "Subcontractors":
                # Aggregate subcontractor values by region (unitless)
                vals = (
                    self.iosystem.L.iloc[:, self.indices]
                    .groupby(level=self.iosystem.index.region_classification[-1], sort=False)
                    .sum()
                    .sum(axis=1)
                ).to_numpy(dtype="float64")
                unit = ""  
                display = gd.get("Subcontractors", "Subcontractors")
            else:
                # Sum impact across selected indices and convert unit per row
                vals = (
                    self.iosystem.impact.total.loc[imp]
                    .iloc[:, self.indices]
                    .sum(axis=1)
                    .to_numpy(dtype="float64")
                )
                vals = [self.transform_unit(value=v, impact=imp)[0] for v in vals]
                try:
                    unit = self.iosystem.impact.get_unit(imp) or ""
                except Exception:
                    # Fallback: query transform_unit for the unit
                    try:
                        _tmp, unit = self.transform_unit(value=0.0, impact=imp)
                    except Exception:
                        unit = ""
                display = gd.get(imp, imp) if localize_cols else imp

            if relative:
                s = float(np.nansum(vals))
                vals = (np.array(vals, dtype="float64") / s * 100.0) if s != 0.0 else np.zeros_like(vals)
                unit_for_col = "%"  
            else:
                unit_for_col = unit

            colname = f"{display} ({unit_for_col})" if (include_units_in_cols and unit_for_col) else str(display)
            data[colname] = vals
            units_map[colname] = unit_for_col

        df = pd.DataFrame(data, index=regions)

        if save_to_excel:
            df.to_excel(save_to_excel)
            return None

        return df, units_map
    
    def plot_topn_by_impacts(
        self,
        impacts: list,
        n: int = 10,
        *,
        relative: bool = True,
        orientation: str = "vertical",
        bar_color: str = "tab10",
        bar_width: float = 0.8,
        title: str = "",
        return_data: bool = False,
        ascending: bool = False,  
    ):
        """
        Render a grouped bar chart of Top/Flop regions across 1..3 impacts.

        The first impact acts as the ranking key; up to two additional impacts
        are plotted side-by-side for comparison. When `ascending=True`, this
        effectively draws a "Flop n" chart (lowest values first).

        Args:
            impacts (list): Primary impact first (sort key), plus up to two comparators.
            n (int): Number of regions to include.
            relative (bool): If True, plot percentages; otherwise absolute values.
            orientation (str): "vertical" or "horizontal".
            bar_color (str): Matplotlib colormap name or a single color.
            bar_width (float): Total width of each region's group (distributed across impacts).
            title (str): Optional custom title; empty lets the backend auto-title.
            return_data (bool): If True, return (fig, DataFrame) instead of just the figure.
            ascending (bool): False -> Top n (largest first), True -> Flop n (smallest first).

        Returns:
            Figure | (Figure, DataFrame): The chart (and underlying matrix if requested).
        """
        gd = getattr(self.iosystem.index, "general_dict", {}) or {}

        def _canon(imp: str) -> str:
            try:
                return self._canon_impact(imp)
            except Exception:
                return imp

        def _disp(imp: str) -> str:
            ci = _canon(imp)
            return gd.get("Subcontractors", "Subcontractors") if ci == "Subcontractors" else gd.get(ci, ci)

        def _strip_unit(col: str) -> str:
            return re.sub(r"\s*\([^)]*\)\s*$", "", str(col)).strip()

        def _resolve_col(df: pd.DataFrame, imp: str) -> str:
            """Resolve a column name in df for the given impact (robust to localization/units)."""
            ci, li = _canon(imp), _disp(imp)
            for key in (ci, li):
                if key in df.columns:
                    return key
            stripped = {_strip_unit(c).casefold(): c for c in df.columns}
            for key in (ci, li):
                c = stripped.get(key.casefold())
                if c:
                    return c
            for c in df.columns:
                if str(c).casefold().startswith(ci.casefold()) or str(c).casefold().startswith(li.casefold()):
                    return c
            raise KeyError(ci)

        if isinstance(impacts, str):
            impacts = [impacts]
        impacts = [i for i in impacts if i]

        # Pull per-region data for all requested impacts (unlocalized, no units in col names)
        try:
            df_vals, units_map = self.impact_per_region_df(
                impacts=impacts, relative=relative,
                include_units_in_cols=False, localize_cols=False
            )
        except Exception:
            # Fallback: project-specific retrieval
            df_vals = self.return_impact_per_region_data(impacts)
            units_map = {}

        primary = impacts[0]
        col_primary = _resolve_col(df_vals, primary)

        # Rank by primary, then take top/flop n indices
        s_primary = pd.to_numeric(df_vals[col_primary], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        n = max(1, int(n))
        take_idx = s_primary.sort_values(ascending=ascending).head(n).index

        # Assemble the plotting matrix (rows: regions, cols: impacts)
        cols = [_resolve_col(df_vals, imp) for imp in impacts]
        mat = df_vals.loc[take_idx, cols].astype(float)
        legend_labels = [_disp(imp) for imp in impacts]

        def _color_list(name: str, k: int):
            try:
                cmap = get_cmap(name)
                return [cmap(t) for t in np.linspace(0.15, 0.85, k)]
            except Exception:
                return [name] * k

        colors = _color_list(bar_color, len(impacts))
        fig, ax = plt.subplots(figsize=(12, 6))

        idx = np.arange(len(take_idx))
        m = len(impacts)
        width = (bar_width / m)
        code2name = dict(zip(self.iosystem.regions_exiobase, self.iosystem.regions))

        # Draw bars
        if orientation == "horizontal":
            for j in range(m):
                offs = (-bar_width/2) + (j + 0.5) * width
                ax.barh(idx + offs, mat.iloc[:, j].values, height=width, label=legend_labels[j], color=colors[j])
            ax.set_yticks(idx)
            ax.set_yticklabels([code2name.get(code, code) for code in take_idx])
            ax.set_xlabel("%" if relative else units_map.get(cols[0], gd.get("Value", "Value")))
            ax.grid(axis='x', alpha=0.2)
        else:
            for j in range(m):
                offs = (-bar_width/2) + (j + 0.5) * width
                ax.bar(idx + offs, mat.iloc[:, j].values, width=width, label=legend_labels[j], color=colors[j])
            ax.set_xticks(idx)
            ax.set_xticklabels([code2name.get(code, code) for code in take_idx], rotation=45, ha="right")
            ax.set_ylabel("%" if relative else units_map.get(cols[0], gd.get("Value", "Value")))
            ax.grid(axis='y', alpha=0.2)

        # Title: auto-generate if none provided
        if not title:
            rank_word = gd.get("Flop", "Flop") if ascending else gd.get("Top", "Top")
            ax.set_title(f"{rank_word} {n} – {_disp(primary)}")
        else:
            ax.set_title(title)

        ax.legend(title=gd.get("Impacts", "Impacts"), loc="best")
        fig.tight_layout()

        return (fig, mat) if return_data else fig

    def plot_flopn_by_impacts(
        self,
        impacts: list,
        n: int = 10,
        *,
        relative: bool = True,
        orientation: str = "vertical",
        bar_color: str = "tab10",
        bar_width: float = 0.8,
        title: str = "",
        return_data: bool = False,
    ):
        """
        Convenience wrapper for Flop-n (smallest values first).

        Delegates to `plot_topn_by_impacts(..., ascending=True)`.
        """
        return self.plot_topn_by_impacts(
            impacts=impacts,
            n=n,
            relative=relative,
            orientation=orientation,
            bar_color=bar_color,
            bar_width=bar_width,
            title=title,
            return_data=return_data,
            ascending=True, 
        )

    def _add_world_metadata(
            self,
            world: pd.DataFrame,
            values: pd.Series,
            percentages: pd.Series,
            units: Optional[Union[str, List[str]]]
    ) -> pd.DataFrame:
        """
        Attach region labels, EXIOBASE codes, values, percentages, and units to the map dataframe.

        Note:
            The implementation drops Malta (index 19) from both region lists to match
            a world geometry source that excludes it. Lengths must match post-filter.

        Args:
            world (pd.DataFrame): GeoDataFrame-like with geometries aligned to EXIOBASE order.
            values (pd.Series): Absolute values per country.
            percentages (pd.Series): Share per country (sum = 100).
            units (str | list | None): A scalar unit or a list aligned with the rows.

        Returns:
            pd.DataFrame: Input `world` with extra columns:
                          ['region', 'exiobase', 'value', 'percentage', 'unit'].
        """
        # Construct region name lists (skipping Malta at position 19)
        regions = self.iosystem.regions[:19] + self.iosystem.regions[20:]
        regions_exiobase = self.iosystem.regions_exiobase[:19] + self.iosystem.regions_exiobase[20:]

        # Ensure length match after potential Malta drop
        if len(world) != len(regions):
            raise ValueError(
                f"Length mismatch: world has {len(world)} rows, "
                f"but regions has {len(regions)} entries. "
                "Check if filtering is consistent."
            )

        world["region"] = regions
        world["exiobase"] = regions_exiobase
        world["value"] = values
        world["percentage"] = percentages

        # Unit handling: broadcast scalar or check list length
        if units is not None:
            if isinstance(units, str):
                world["unit"] = units
            elif hasattr(units, "__len__"):
                if len(units) == len(world):
                    world["unit"] = units
                elif len(set(units)) == 1:
                    # All entries equal → broadcast single value
                    world["unit"] = list(units)[0]
                else:
                    raise ValueError(
                        f"Unit list length ({len(units)}) does not match number of rows ({len(world)})."
                    )

        return world

    def _add_map_legend(
            self,
            fig: plt.Figure,
            ax: plt.Axes,
            data: pd.Series,
            column: str,
            color_map: str,
            relative: bool,
            *,
            mode: str = "continuous",               # "continuous" or "binned"
            edges: Optional[List[float]] = None,    # for binned (unused here)
            # Normalization parameters for continuous (kept consistent with the map)
            norm_mode: str = "linear",
            vmin: Optional[float] = None,
            vmax: Optional[float] = None,
            gamma: float = 0.7,
            unit: Optional[str] = None
    ) -> None:
        """
        Add a colorbar legend to the map.

        Behavior:
          - Continuous mode: uses vmin/vmax and normalization to match the map,
            labeling with absolute units when available.
          - Binned mode: colorbar/legend is handled elsewhere; this helper raises.

        Args:
            fig (Figure): Parent figure.
            ax (Axes): Axes the colorbar should be associated with.
            data (Series): Underlying numeric data (used for robust min/max).
            column (str): Legend label (e.g., impact/metric name).
            color_map (str): Matplotlib colormap name.
            relative (bool): Unused here (legend uses absolute values label when unit provided).
            mode (str): "continuous" supported here; "binned" is not.
            edges (list[float] | None): Unused for continuous.
            norm_mode (str): "linear" | "log" | "power".
            vmin, vmax (float | None): Explicit bounds; inferred if None.
            gamma (float): Gamma for PowerNorm.
            unit (str | None): Unit string appended to the legend label.

        Raises:
            ValueError: If called with mode != "continuous".
        """
        cmap = plt.get_cmap(color_map)

        finite = data[np.isfinite(data)]
        if finite.empty:
            norm = mcolors.Normalize(vmin=0.0, vmax=1.0)
            sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
            return

        if mode == "continuous":
            # Use provided vmin/vmax to ensure consistency with the map
            if vmin is None or vmax is None:
                vmin, vmax = float(finite.min()), float(finite.max())
                if vmin == vmax:
                    vmin, vmax = vmin - 0.5, vmax + 0.5

            if norm_mode == "log":
                eps = 1e-12
                vmin = max(vmin, eps)
                norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
            elif norm_mode == "power":
                norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)
            else:
                norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

            sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)

            # Absolute-value legend label with unit if available
            cbar.set_label(f"{column} [{unit}]" if unit not in (None, "") else f"{column}")
        else:
            raise ValueError('Legend helper is meant for mode="continuous" here.')
    
    def _configure_map_appearance(self, ax: plt.Axes, title: str) -> None:
        """
        Configure basic visual appearance of the map axes.

        - Removes ticks and frame for a clean, figure-centric look.
        - Sets a bold title with modest padding.
        - Leaves global layout to the caller; applies only minimal subplot padding.
        """
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        # Leave tight layout control to the caller; minimal padding here:
        plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0.0)

    def _get_title(self, **kwargs) -> str:
        """
        Build a dynamic map title based on the current hierarchy selection.

        If `inputByIndices` is active, returns a specific-selection title.
        Otherwise, concatenates available hierarchy levels as "Level: Value" parts.
        Falls back to "of the World" when nothing is selected.

        Args:
            **kwargs: Reserved for future expansion (unused).

        Returns:
            str: Localized title string including the current EXIO year.
        """
        general_dict = self.iosystem.index.general_dict

        if self.inputByIndices:
            if len(self.indices) == (len(self.iosystem.regions)*len(self.iosystem.sectors)):
                return f'{general_dict["of the World"]} ({self.iosystem.year})'
            return (
                f'{general_dict["of a"]} '
                f'{general_dict["specific selection of sectors"]} '
                f'({self.iosystem.year})'
            )

        # Collect non-None hierarchy levels
        title_parts = []
        for level, value in self.hierarchy_levels.items():
            if value is not None:
                title_parts.append(f"{level}: {value}")

        # Return appropriate title based on content
        if not title_parts:
            return f'{general_dict["of the World"]} ({self.iosystem.year})'

        return (
            f'{general_dict["of"]} ' +
            " | ".join(title_parts) +
            f' ({self.iosystem.year})'
        )
    
    def _sc__extract_unit(self, world) -> str:
        """
        Robustly extract a scalar unit string from various world objects.

        Accepts DataFrame/GeoDataFrame (prefers a 'unit' column), dict-like (uses
        'unit' key), or plain objects (reads a 'unit' attribute). Returns empty
        string if no unit can be determined.
        """
        try:
            if isinstance(world, pd.DataFrame):
                return str(world["unit"].iloc[0]) if "unit" in world.columns and len(world) else ""
            if isinstance(world, dict) and "unit" in world:
                return str(world["unit"])
            u = getattr(world, "unit", "")
            return "" if u is None else str(u)
        except Exception:
            return ""

    def _sc__world_df(
        self,
        impact: str,
        *,
        relative: bool = True,
        color: str = "Reds",
        title: Optional[str] = None,
        show_legend: bool = False,
        mode: str = "binned",
        k: int = 7,
        custom_bins: Optional[List[float]] = None,
        norm_mode: str = "linear",
        robust: float = 2.0,
        gamma: float = 0.7
    ) -> Tuple[pd.DataFrame, str]:
        """
        Retrieve the same data structure used by the world map—without rendering.

        Tries pure data endpoints (if available), otherwise falls back to the
        existing plotting functions with `return_data=True`.

        Guarantees columns: ['region', 'value', 'percentage', 'unit'].
        Geometry may be present when the upstream provider returns it.

        Args:
            impact (str): Canonical impact key (or 'Subcontractors').
            relative (bool): If True, compute percentages; else absolute values.
            color (str): Colormap name passed through to the fallback plot call.
            title (str | None): Optional title for fallback plotting.
            show_legend (bool): Whether to display legend in fallback plotting.
            mode (str): "binned" | "continuous" (passed to fallback).
            k (int): Number of classes (binned mode).
            custom_bins (list[float] | None): Overrides `k` when provided.
            norm_mode (str): "linear" | "log" | "power" for continuous mode.
            robust (float): Robust clipping percentile for continuous mode.
            gamma (float): Gamma for PowerNorm in continuous mode.

        Returns:
            Tuple[pd.DataFrame, str]: (DataFrame, unit string)
        """
        # 1) Prefer data-only endpoints (if implemented later)
        try:
            if impact.strip().lower() == "subcontractors" and hasattr(self, "worldmap_data_by_subcontractors"):
                df = self.worldmap_data_by_subcontractors(relative=relative)
                unit = str(df["unit"].iloc[0]) if "unit" in df.columns and len(df) else ""
                return df.copy(), unit
            if impact.strip().lower() != "subcontractors" and hasattr(self, "worldmap_data_by_impact"):
                df = self.worldmap_data_by_impact(impact, relative=relative)
                unit = str(df["unit"].iloc[0]) if "unit" in df.columns and len(df) else ""
                return df.copy(), unit
        except Exception:
            # Fall back to plot-based data retrieval below
            pass

        # 2) Fallback: use existing plot functions with return_data=True
        kw = dict(
            color=color, title=title, relative=relative, show_legend=show_legend,
            return_data=True, mode=mode, k=k, custom_bins=custom_bins,
            norm_mode=norm_mode, robust=robust, gamma=gamma
        )

        if impact.strip().lower() == "subcontractors":
            _fig, world = self.plot_worldmap_by_subcontractors(**kw)
        else:
            _fig, world = self.plot_worldmap_by_impact(impact, **kw)

        unit = self._sc__extract_unit(world)
        df = pd.DataFrame(world).copy()

        # Ensure minimum columns exist
        for col in ["region", "value", "percentage"]:
            if col not in df.columns:
                df[col] = None
        if "unit" not in df.columns:
            df["unit"] = unit

        return df, unit
