from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain

import matplotlib.pyplot as plt

io_system_instance = IOSystem(year=2022, language="Deutsch")
io_system_instance.load()

supplychain = SupplyChain(iosystem=io_system_instance, Region="Deutschland", Sektor="Textilien")

# supplychain.plot_worldmap_by_impact(impact="Treibhausgasemissionen")
# supplychain.plot_worldmap_by_subcontractors(color="Blues")
# fig = supplychain.plot_supplychain_diagram(impacts=["Treibhausgasemissionen", "Wasserverbrauch", "Landnutzung", "Wertschöpfung", "Arbeitszeit"])
# supplychain.calculate_all(impacts=["Treibhausgasemissionen", "Wasserverbrauch", "Landnutzung", "Wertschöpfung", "Arbeitszeit"], relative=False, decimal_places=5)

plt.show()