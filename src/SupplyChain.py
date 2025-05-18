import pandas as pd 
import matplotlib.pyplot as plt 
import matplotlib.colors as mcolors 
import tkinter as tk
from tkinter import ttk

class SupplyChain:

    def __init__(self, database, select=False, indices=None, **kwargs):
        # Parameter setzen
        self.database = database
        self.language = self.database.language
        self.regional = False
        self.inputByIndices = False

        # 🛠 Hier sicher initialisieren:
        self.hierarchy_levels = {}

        if indices is not None:
            self.indices = indices
            self.inputByIndices = True
            
        else:         
            if select == True:
                kwargs = {**self.get_multiindex_selection(self.database.Index.region_multiindex), 
                          **self.get_multiindex_selection(self.database.Index.sector_multiindex_per_region)}

            for attr in self.database.Index.region_classification + self.database.Index.sector_classification:
                value = kwargs.get(attr, None)
                setattr(self, attr, value)
                self.hierarchy_levels[attr] = value
            
            df = self.database.I.copy()
            idx = pd.IndexSlice
        
            subset = df.loc[idx[
                *(slice(None) if self.hierarchy_levels[level] is None else self.hierarchy_levels[level]
                  for level in self.database.Index.region_classification + self.database.Index.sector_classification)
            ], :]

            self.indices = df.index.get_indexer(subset.index).tolist()
        
            if any(self.hierarchy_levels[level] for level in self.database.Index.region_classification) and \
               not any(self.hierarchy_levels[level] for level in self.database.Index.sector_classification):
                self.regional = True
                self.database.Impact.get_regional_impacts(region_indices=self.indices)

    def get_multiindex_selection(self, index):
        """
        Funktion zur Darstellung eines MultiIndex in einer interaktiven Baumstruktur.
        Gibt das ausgewählte Schema als Dictionary zurück.
        
        :param index: pd.MultiIndex - Der MultiIndex, der im TreeView angezeigt wird
        :return: dict - Das ausgewählte Schema im Dictionary-Format
        """
        
        # Tkinter Fenster erstellen
        root = tk.Tk()
        root.title("MultiIndex GUI")

        # Fenstergröße anpassen (breiter machen)
        root.geometry("600x400")  # Breiter machen, z.B. 600px Breite, 400px Höhe

        # Treeview erstellen (größer machen) - Nur eine Textspalte
        tree = ttk.Treeview(root, height=15, columns=("text"))  # Eine Spalte 'text'
        tree.heading("#1", text="Bezeichnung")  # Überschrift für die Spalte
        tree.column("#1", width=300)  # Breite der Textspalte einstellen
        tree.pack(fill="both", expand=True)

        # Label zum Anzeigen des Pfades als Dictionary
        path_label = tk.Label(root, text="Auswahl als Dictionary: ", font=("Arial", 12))
        path_label.pack(pady=10)

        # Variable zum Speichern des Pfades
        selected_path = {}

        # Funktion, um die Baumstruktur aus dem MultiIndex zu erstellen
        def create_treeview_from_index(parent, index, level=0, path=""):
            if level < len(index.names):
                unique_values = index.get_level_values(level).unique()
                for value in unique_values:
                    node_name = value
                    node_id = f"{path}-{value}"
                    new_parent = tree.insert(parent, 'end', node_id, text=node_name)
                    subset = index[index.get_level_values(level) == value]
                    create_treeview_from_index(new_parent, subset, level + 1, node_id)

        # Baumstruktur aus dem MultiIndex erstellen
        create_treeview_from_index('', index)

        # Funktion zum Anzeigen des gesamten Pfades der ausgewählten Knoten als Dictionary
        def show_selection(event):
            selected_item = tree.selection()[0]
            path = [tree.item(selected_item)['text']]
            
            # Sammle den Pfad von den Elternknoten
            while tree.parent(selected_item):
                parent_item = tree.parent(selected_item)
                path.insert(0, tree.item(parent_item)['text'])
                selected_item = parent_item
            
            # Erstelle das Dictionary mit dem letzten Wert der Auswahl
            nonlocal selected_path
            selected_path = {}

            # Füge nur das letzte Element (die ausgewählte Ebene) in das Dictionary ein
            selected_path[index.names[len(path) - 1]] = path[-1]

            # Zeige das Dictionary mit der letzten Auswahl an
            path_label.config(text="Auswahl als Dictionary: " + str(selected_path))


        # Ereignisbindung zum Auswählen von Knoten
        tree.bind("<<TreeviewSelect>>", show_selection)

        # Funktion zum Speichern der Auswahl und Schließen des Fensters
        def on_close():
            root.destroy()  # Verwende destroy(), um das Fenster zu schließen

        # Ereignis für das Schließen des Fensters
        root.protocol("WM_DELETE_WINDOW", on_close)

        root.mainloop()
        
        return selected_path

    def __repr__(self):
        """
        Returns a string representation of the SupplyChain object, useful for debugging or displaying in the program.    
        This representation is especially helpful when inspecting objects during debugging.
        """
        if self.inputByIndices:
            return f"SupplyChain(Number of Indices: {len(self.indices)}, input was given by indices)"
        else:
            return f"SupplyChain(Number of Indices: {len(self.indices)}, Hierarchy levels: {self.hierarchy_levels})"

    def transform_unit(self, value, impact):
        """
        Transforms the given value based on the unit for the specified impact.
        """
        impact_row_idx = self.database.Index.units_df[self.database.Index.units_df.iloc[:, 0] == impact].index
        impact_row = self.database.Index.units_df.iloc[impact_row_idx[0]].tolist()
        unit = impact_row[4]
        value = value / impact_row[2]
        #if round(value, impact_row[3]) != 0:
        #    value = round(value, impact_row[3])

        return (value, unit)
    
    def total(self, impact):
        """
        Calculates the total environmental impact along the entire supply chain (Leontief Inverse) for a given impact.
        
        The method computes the total environmental impact for a specified "impact" across the supply chain.
        It uses data from the `Impact` object in the database and applies a unit transformation to return the result.
        
        :param impact: str: The name of the environmental impact to calculate (e.g., "CO2 Emissions").
        
        :return: The total impact value after transformation into the correct unit.
        """
        # Summing the impact for the specified sector-region combination (using indices) 
        # and then transforming the unit based on the calculated value.
        return self.transform_unit(value=self.database.Impact.total.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)
            
    def resource_extraction(self, impact):
        """
        Calculates the environmental impact of resource extraction for a given impact type.
    
        The method sums the environmental impact values for resource extraction along the supply chain for the specified impact.
    
        :param impact: str: The environmental impact type (e.g., "CO2 Emissions").
    
        :return: The total impact value after transformation into the correct unit.
        """
        # Summing the impact for the resource extraction data using the given indices and then transforming the unit
        if not self.regional:
            return self.transform_unit(value=self.database.Impact.resource_extraction.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)
        else:
            return self.transform_unit(value=self.database.Impact.resource_extraction_regional.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)

    def preliminary_products(self, impact):
        """
        Calculates the environmental impact of preliminary products for a given impact type.
    
        The method sums the environmental impact values for preliminary products along the supply chain for the specified impact.
    
        :param impact: str: The environmental impact type (e.g., "CO2 Emissions").
    
        :return: The total impact value after transformation into the correct unit.
        """
        # Summing the impact for preliminary products using the given indices and then transforming the unit
        if not self.regional:
            return self.transform_unit(value=self.database.Impact.preliminary_products.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)
        else:
            return self.transform_unit(value=self.database.Impact.preliminary_products_regional.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)
    
    def direct_suppliers(self, impact):
        """
        Calculates the environmental impact of direct suppliers (A-Matrix) for a given impact type.
        Raw materials, whose indices are stored in raw_material_indices, are filtered out.
    
        :param impact: str: The environmental impact type (e.g., "CO2 Emissions").
    
        :return: The total impact value after transformation into the correct unit.
        """
        # Summing the impact for direct suppliers (excluding raw materials) using the given indices and then transforming the unit
        if not self.regional:
            return self.transform_unit(value=self.database.Impact.direct_suppliers.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)
        else:
            return self.transform_unit(value=self.database.Impact.direct_suppliers_regional.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)
      
    def retail(self, impact):
        """
        Calculates the environmental impact directly at the production site (identity matrix) for a given impact type.
    
        The method sums the environmental impact values directly at the production site for the specified impact.
    
        :param impact: str: The environmental impact type (e.g., "CO2 Emissions").
    
        :return: The total impact value after transformation into the correct unit.
        """
        # Summing the impact for retail data using the given indices and then transforming the unit
        if not self.regional:
            return self.transform_unit(value=self.database.Impact.retail.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)
        else:
            return self.transform_unit(value=self.database.Impact.retail_regional.loc[impact].iloc[:, self.indices].sum().sum().item(), impact=impact)

    def calculate_all(self, impacts, relative=True, decimal_places=2, row_length=35):
        """
        Calculates the environmental impacts across the supply chain and returns the results as a DataFrame.
    
        :param impacts: list: A list of environmental impacts to calculate (e.g., ["CO2 Emissions", "Water Usage"]).
        :param relative: bool: If True, the values are given as a relative proportion of the total environmental impact.
                              If False, absolute values are returned.
        :param decimal_places: int: Number of decimal places to round the results to.
    
        :return: pd.DataFrame: A DataFrame containing the calculated impacts for each impact type.
        """
        data = []  # List to store calculated values for each impact
    
        for impact in impacts:
            # Calculate the total impact and unit for the specified impact
            total, unit = self.total(impact)
            
            # Calculate environmental impacts for resource extraction, preliminary products, direct suppliers, and retail
            res, _ = self.resource_extraction(impact)
            pre, _ = self.preliminary_products(impact)
            direct, _ = self.direct_suppliers(impact)
            ret, _ = self.retail(impact)
    
            # Get the color associated with the impact (for visual representation)
            color = self.database.Impact.get_color(impact)
    
            # If relative is True, normalize all values by dividing them by the total impact
            if relative:
                res /= total
                pre /= total
                direct /= total
                ret /= total
    
            # Append the calculated values for this impact type
            data.append([
                round(res, decimal_places), 
                round(pre, decimal_places), 
                round(direct, decimal_places), 
                round(ret, decimal_places), 
                round(total, decimal_places), 
                unit, 
                color
            ])
    
        # Define column names for the DataFrame
        columns = [
            self.database.Index.general_dict["Resource Extraction"], 
            self.database.Index.general_dict["Preliminary Products"], 
            self.database.Index.general_dict["Direct Suppliers"], 
            self.database.Index.general_dict["Retail"], 
            self.database.Index.general_dict["Total"], 
            self.database.Index.general_dict["Unit"], 
            self.database.Index.general_dict["Color"]
        ]

        def wrap_text(text, max_length=row_length):
            """
            Wraps a string so that no line exceeds `max_length` characters.
            Line breaks are inserted preferably at spaces; if a single word 
            is longer than `max_length`, it will be split at the limit.

            Parameters:
                text (str): The input string to wrap.
                max_length (int): The maximum number of characters per line.

            Returns:
                str: The wrapped string with line breaks (\n).
            """
            words = text.split()  # Split the text into words
            result = ""
            line = ""

            for word in words:
                # If adding the next word keeps the line within the limit
                if len(line) + len(word) + (1 if line else 0) <= max_length:
                    line += (" " if line else "") + word  # Add word with space if needed
                else:
                    result += line + "\n"  # Add completed line to result
                    line = word  # Start new line with the current word

            # Add the last line if it's not empty
            if line:
                result += line

            # Post-processing: force breaks if any line is still too long (e.g., from long words)
            final_result = ""
            for line in result.split("\n"):
                while len(line) > max_length:
                    final_result += line[:max_length] + "\n"  # Hard wrap at max_length
                    line = line[max_length:]
                final_result += line + "\n"

            return final_result.rstrip()  # Remove trailing newline


        impacts = [wrap_text(impact) for impact in impacts]

        # Create the DataFrame from the collected data
        df = pd.DataFrame(data, index=impacts, columns=columns)
    
        return df
 
    def plot_supplychain_diagram(self, impacts, title=None, size=1, lines=True, line_width=1, line_color="gray", text_position="center"):
        """
        Visualizes the environmental impacts along a supply chain in a clear plot.
        
        This function creates a graphical representation of the environmental impacts at various stages of the supply chain 
        (e.g., resource extraction, production, direct suppliers, retail) for a range of environmental indicators (e.g., CO2 emissions, water use). 
        The relative environmental impacts are displayed as bubbles, with their size proportional to the respective share of the total impact.
        The plot allows for a quick visual analysis of the environmental impacts and provides a clear separation of the different supply chain stages.
        
        Parameters:
        - impacts: List of environmental impacts (e.g., CO2, water usage, etc.) to be plotted.
        - title: The title of the plot (default is "Supply Chain Analysis").
        - size: The scale factor for the plot's size (default is 3).
        - lines: Boolean flag indicating whether to include lines separating the grid (default is True).
        - line_width: The width of the lines separating the grid (default is 1).
        - line_color: The color of the grid lines (default is "gray").
        - text_position: The position of the text labels relative to the bubbles ("center", "top", or "bottom").
        
        Returns:
        - A plot displaying the environmental impacts in a supply chain, with bubbles sized according to the relative environmental impacts 
        at each stage (resource extraction, production, direct suppliers, retail) for each environmental indicator.
        """

        if not impacts:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title("No impacts selected", fontsize=14, fontweight="bold", pad=20)
            ax.axis('off')  # Deaktiviert die Achsen für einen leeren Plot
            return fig

        LINE_WIDTH = line_width  # Line width for grid lines
        LINE_COLOR = line_color  # Color of the grid lines (default: gray)
        
        # Default title if none is provided
        title = title if title is not None else f'{self.database.Index.general_dict["Supply Chain Analysis"]} ' + self.get_title()
        
        # Get the relative environmental impact data as a DataFrame
        df_rel = self.calculate_all(impacts=impacts, relative=True, decimal_places=5)

        # Column and row labels for the plot
        col_labels = [df_rel.columns[0], df_rel.columns[1], 
                    df_rel.columns[2], df_rel.columns[3], df_rel.columns[4]]
        row_labels = df_rel.index.tolist()  # Impact names (e.g., CO2, Water Usage)

        # Create the figure and axis for the plot
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.set_dpi(size * 100)

        # Set the title of the plot
        ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

        # Get the number of rows and columns for the grid
        n_rows, n_cols = len(row_labels), 5

        # Set axis limits and labels
        ax.set_xlim(-0.5, n_cols - 0.5)
        ax.set_ylim(-0.5, n_rows - 0.5)
        ax.set_xticks(range(n_cols))
        ax.set_yticks(range(n_rows))
        ax.set_xticklabels(col_labels, fontsize=10, fontweight="bold")
        ax.set_yticklabels(row_labels, fontsize=10, fontweight="bold")
        ax.invert_yaxis()  # Invert y-axis so the first row is at the top
        ax.grid(False)

        # Hide the spines (border lines)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Bubble scale factor for visualizing relative impacts
        bubble_scale = 3000

        # Draw the grid lines if 'lines' is True
        if lines:
            for i in range(n_rows + 1):  # Horizontal lines
                ax.axhline(i - 0.5, color=LINE_COLOR, linewidth=LINE_WIDTH)
            for j in range(n_cols + 1):  # Vertical lines
                ax.axvline(j - 0.5, color=LINE_COLOR, linewidth=LINE_WIDTH)

            ax.axhline(n_rows - 0.5, color=LINE_COLOR, linewidth=LINE_WIDTH * 1.5)  # Bottom border line
            ax.axvline(n_cols - 0.5, color=LINE_COLOR, linewidth=LINE_WIDTH * 1.5)  # Right border line

        # Plot the data for each row (impact)
        for i, impact_name in enumerate(row_labels):
            row_values = df_rel.loc[impact_name]
            color = df_rel.loc[impact_name, self.database.Index.general_dict["Color"]]

            # Plot each stage of the supply chain (columns 0 to 3)
            for col in range(4):
                val_rel = row_values.iloc[col]
                size = val_rel * bubble_scale  # Size of the bubble based on relative impact
                ax.scatter(col, i, s=size, color=color, alpha=0.7, edgecolors="black", linewidths=0.6)  # Scatter plot
                ax.text(col, i, f"{val_rel * 100:.1f} %", va=text_position, ha="center", fontsize=9, color="black")  # Text inside bubbles

            # Total impact (column 4)
            total_val = row_values[self.database.Index.general_dict["Total"]]
            einheit = row_values[self.database.Index.general_dict["Unit"]] if self.database.Index.general_dict["Unit"] in df_rel.columns else ""
            text_str = f"{total_val} \n {einheit}"
            ax.text(4, i, text_str, ha="center", va="center", fontsize=9, color="black", fontweight="bold")

        # Adjust layout to avoid clipping and show the plot
        fig.tight_layout()

        plt.close(fig)
        return fig

    def plot_worldmap_by_subcontractors(self, color="Blues", title=None, relative=True, show_legend=False, return_data=False):
        values = list(self.database.L.iloc[:, self.indices]
                    .groupby(level=self.database.Index.region_classification[-1], sort=False)
                    .sum().sum(axis=1).values)

        df = pd.DataFrame(values, index=self.database.regions_exiobase)
        title = title if title is not None else f'{self.database.Index.general_dict["Subcontractors"]} ' + self.get_title()

        units = [""] * 48

        return self.plot_worldmap_by_data(df=df, units=units, color_map=color, relative=relative, title=title, show_legend=show_legend, return_data=return_data)
    
    def plot_worldmap_by_impact(self, impact, color="Blues", title=None, relative=True, show_legend=False, return_data=False):
        values = self.database.Impact.total.loc[impact].iloc[:, self.indices].sum(axis=1).values.tolist()

        values = [self.transform_unit(value=value, impact=impact)[0] for value in values]

        df = pd.DataFrame({'Impact': values}, index=self.database.regions_exiobase)
        title = title if title is not None else f'{self.database.Index.general_dict["Global"]} {impact} ' + self.get_title()

        units = [self.database.Impact.get_unit(impact)] * 48

        return self.plot_worldmap_by_data(df=df, units=units, color_map=color, relative=relative, title=title, show_legend=show_legend, return_data=return_data)

    def plot_worldmap_by_data(self, df, units=None, column=None, color_map="Blues", relative=False, title="", show_legend=False, return_data=False):
        """
        Plots a choropleth map of the given dataframe's column.

        Parameters:
            df (pd.DataFrame): DataFrame with regions as index (Two-letter codes) and a numerical column.
            column (str): The name of the column to be plotted.
            color_map (str): The color map to use for shading.
            relative (bool): If True, convert values to percentages of the total sum.
            title (str): Title of the plot.
            show_legend (bool): Whether to display the color bar legend.
        """ 
        world = self.database.Index.get_map()
        column = column if column is not None else df.columns[0]
        df = df.drop(index="MT", errors="ignore")  # Falls "MT" nicht existiert, keinen Fehler werfen
        
        # Werte ggf. als Prozent
        values = df[column].copy()
        percentages = (values / values.sum()) * 100
        
        # Reihenfolge sichern
        world = world.loc[df.index]
        world["region"] = self.database.regions[:19] + self.database.regions[20:]
        world["exiobase"] = self.database.regions_exiobase[:19] + self.database.regions_exiobase[20:]
        world["value"] = values
        world["percentage"] =  percentages
        if units:
            world["unit"] = units
        
        world["data"] = percentages if relative else values
        

        # Plot
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        world.plot(column="data", cmap=color_map, legend=False, scheme="quantiles",
                classification_kwds={'k': 5}, ax=ax, edgecolor="gray", linewidth=0.6, alpha=0.9)

        # Nur Legende, wenn aktiviert
        if show_legend:
            norm = mcolors.Normalize(vmin=world["data"].min(), vmax=world["data"].max())
            sm = plt.cm.ScalarMappable(cmap=color_map, norm=norm)
            sm._A = []
            cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)

            if relative:
                cbar.set_label(f"{column} (%)")
                cbar.ax.set_yticklabels([f"{int(tick)}%" for tick in cbar.get_ticks()])
            else:
                cbar.set_label(column)

        # Achsen & Rahmen ausblenden
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)

        # Titel
        ax.set_title(title)
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        plt.close(fig)
        if return_data:
            return fig, world
        else:
            return fig

    def get_title(self, **kwargs):
        """
        Generates a dynamic title based on the provided hierarchy levels and their translations.
        
        :param kwargs: Keyword arguments for sector and region classifications.
        :return: A string title that reflects the provided hierarchy levels.
        """    
        # Erstellen des Titels basierend auf den angegebenen Hierarchieebenen

        if self.inputByIndices:
            return f'{self.database.Index.general_dict["of a"]} {self.database.Index.general_dict["specific selection of sectors"]} ({self.database.year})'
        else:
            title_parts = []

            # Iteriere über alle möglichen Hierarchieebenen, die in der Index-Klassifikation definiert sind
            for level in self.hierarchy_levels:
                value = self.hierarchy_levels[level]
                
                # Falls der Wert nicht None ist, füge ihn dem Titel hinzu
                if value is not None:
                    title_parts.append(f"{level}: {value}")
        
            # Falls keine Teile im Titel sind, gib eine Standardeinstellung zurück
            if not title_parts:
                return self.database.Index.general_dict["of the World"]
        
            # Rückgabe des zusammengefügten Titels
            return f'{self.database.Index.general_dict["of"]} ' + " | ".join(title_parts) + f" ({self.database.year})"