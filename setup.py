from src.IOSystem import IOSystem
import os
import re

exiobase_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), 'exiobase'))
pattern = re.compile(r"IOT_(\d{4})_pxp\.zip")
for filename in os.listdir(exiobase_dir):
    match = pattern.match(filename)
    if match:
        dummy = IOSystem(year=int(match.group(1))).load()
        dummy.Index.copy_configs(output=False)
        del dummy