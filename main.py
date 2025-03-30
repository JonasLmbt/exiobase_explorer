from exiobase_explorer.IOSystem import IOSystem
from exiobase_explorer.SupplyChain import SupplyChain

database = IOSystem(year=2022, language="german").load()

supplychain = SupplyChain(database=database, select=True)
print(supplychain)

supplychain.plot_supply_chain(impacts=["Treibhausgasemissionen", "Wasserverbrauch", "Landnutzung", "Wertschöpfung", "Arbeitszeit"])

supplychain.plot_subcontractors(color="Greens")