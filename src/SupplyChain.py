"""
SupplyChain.py

This module provides the SupplyChain class for analyzing environmental impacts along supply chains.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional, Tuple, Union, Any

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd


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

    def plot_supplychain_diagram(
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
            title = f'{general_dict["Supply Chain Analysis"]} {self.get_title()}'

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
        self._plot_supply_chain_data(
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

    def _plot_supply_chain_data(
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

    def plot_worldmap_by_subcontractors(
            self,
            color: str = "Blues",
            title: Optional[str] = None,
            relative: bool = True,
            show_legend: bool = False,
            return_data: bool = False
    ) -> Union[plt.Figure, Tuple[plt.Figure, pd.DataFrame]]:
        """
        Plot world map showing subcontractor distribution.

        Args:
            color: Color map for visualization
            title: Plot title
            relative: Whether to show relative values
            show_legend: Whether to display color bar legend
            return_data: Whether to return data along with figure

        Returns:
            Figure or tuple of figure and data
        """
        values = list(
            self.iosystem.L.iloc[:, self.indices]
            .groupby(level=self.iosystem.index.region_classification[-1], sort=False)
            .sum()
            .sum(axis=1)
            .values
        )

        df = pd.DataFrame(values, index=self.iosystem.regions_exiobase)

        if title is None:
            general_dict = self.iosystem.index.general_dict
            title = f'{general_dict["Subcontractors"]} {self.get_title()}'

        units = [""] * 48

        return self.plot_worldmap_by_data(
            df=df,
            units=units,
            color_map=color,
            relative=relative,
            title=title,
            show_legend=show_legend,
            return_data=return_data
        )

    def plot_worldmap_by_impact(
            self,
            impact: str,
            color: str = "Blues",
            title: Optional[str] = None,
            relative: bool = True,
            show_legend: bool = False,
            return_data: bool = False
    ) -> Union[plt.Figure, Tuple[plt.Figure, pd.DataFrame]]:
        """
        Plot world map showing impact distribution.

        Args:
            impact: Environmental impact to visualize
            color: Color map for visualization
            title: Plot title
            relative: Whether to show relative values
            show_legend: Whether to display color bar legend
            return_data: Whether to return data along with figure

        Returns:
            Figure or tuple of figure and data
        """
        values = (
            self.iosystem.impact.total.loc[impact]
            .iloc[:, self.indices]
            .sum(axis=1)
            .values
            .tolist()
        )

        # Transform values using unit conversion
        values = [
            self.transform_unit(value=value, impact=impact)[0]
            for value in values
        ]

        df = pd.DataFrame({'Impact': values}, index=self.iosystem.regions_exiobase)

        if title is None:
            general_dict = self.iosystem.index.general_dict
            title = f'{general_dict["Global"]} {impact} {self.get_title()}'

        units = [self.iosystem.impact.get_unit(impact)] * 48

        return self.plot_worldmap_by_data(
            df=df,
            units=units,
            color_map=color,
            relative=relative,
            title=title,
            show_legend=show_legend,
            return_data=return_data
        )

    def plot_worldmap_by_data(
            self,
            df: pd.DataFrame,
            units: Optional[List[str]] = None,
            column: Optional[str] = None,
            color_map: str = "Blues",
            relative: bool = False,
            title: str = "",
            show_legend: bool = False,
            return_data: bool = False
    ) -> Union[plt.Figure, Tuple[plt.Figure, pd.DataFrame]]:
        """
        Plot a choropleth map of the given DataFrame's column.

        Args:
            df: DataFrame with regions as index and numerical column
            units: List of units for each region
            column: Column name to plot (uses first column if None)
            color_map: Color map for shading
            relative: Whether to convert values to percentages
            title: Plot title
            show_legend: Whether to display color bar legend
            return_data: Whether to return data along with figure

        Returns:
            Figure or tuple of figure and data
        """
        world = self.iosystem.index.get_map()
        column = column if column is not None else df.columns[0]

        # Remove Malta if present (special case)
        df = df.drop(index="MT", errors="ignore")

        # Calculate values and percentages
        values = df[column].copy()
        total_sum = values.sum()
        percentages = (values / total_sum * 100) if total_sum != 0 else values * 0

        # Ensure proper ordering and add metadata
        world = world.loc[df.index]
        world = self._add_world_metadata(world, values, percentages, units)

        # Set data column based on relative flag
        world["data"] = percentages if relative else values

        # Create the plot
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))

        world.plot(
            column="data",
            cmap=color_map,
            legend=False,
            scheme="quantiles",
            classification_kwds={'k': 5},
            ax=ax,
            edgecolor="gray",
            linewidth=0.6,
            alpha=0.9
        )

        # Add legend if requested
        if show_legend:
            self._add_map_legend(fig, ax, world["data"], column, color_map, relative)

        # Configure plot appearance
        self._configure_map_appearance(ax, title)

        plt.close(fig)

        return (fig, world) if return_data else fig

    def _add_world_metadata(
            self,
            world: pd.DataFrame,
            values: pd.Series,
            percentages: pd.Series,
            units: Optional[List[str]]
    ) -> pd.DataFrame:
        """
        Add metadata to the world DataFrame for mapping.
        """
        # Handle region names (skip Malta at index 19)
        regions = self.iosystem.regions[:19] + self.iosystem.regions[20:]
        regions_exiobase = self.iosystem.regions_exiobase[:19] + self.iosystem.regions_exiobase[20:]

        world["region"] = regions
        world["exiobase"] = regions_exiobase
        world["value"] = values
        world["percentage"] = percentages

        if units:
            world["unit"] = units

        return world

    def _add_map_legend(
            self,
            fig: plt.Figure,
            ax: plt.Axes,
            data: pd.Series,
            column: str,
            color_map: str,
            relative: bool
    ) -> None:
        """
        Add color bar legend to the map.
        """
        norm = mcolors.Normalize(vmin=data.min(), vmax=data.max())
        sm = plt.cm.ScalarMappable(cmap=color_map, norm=norm)
        sm._A = []
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)

        if relative:
            cbar.set_label(f"{column} (%)")
            cbar.ax.set_yticklabels([f"{int(tick)}%" for tick in cbar.get_ticks()])
        else:
            cbar.set_label(column)

    def _configure_map_appearance(self, ax: plt.Axes, title: str) -> None:
        """
        onfigure the visual appearance of the map.
        """
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)
        # ax.set_title(title)
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
        plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0)

    def get_title(self, **kwargs) -> str:
        """
        Generate a dynamic title based on hierarchy levels and their translations.

        Args:
            **kwargs: Additional keyword arguments (currently unused)

        Returns:
            String title reflecting the provided hierarchy levels
        """
        general_dict = self.iosystem.index.general_dict

        if self.inputByIndices:
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
