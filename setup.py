"""
setup.py

This script is used to set up the Exiobase database for the IOSystem.
"""

import logging
import os
import re
import sys

from src.IOSystem import IOSystem

# Configure logging for clear output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    stream=sys.stdout  # Hier wird der Ausgabestrom explizit gesetzt
)

databases_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), 'exiobase'))
logging.info(f"databases_dir: {databases_dir} \n")

pattern = re.compile(r"IOT_(\d{4})_pxp\.zip")
for filename in os.listdir(databases_dir):
    match = pattern.match(filename)
    if match:
        dummy = IOSystem(year=int(match.group(1)))
        dummy.load()
        dummy.index.copy_configs(output=False)
        del dummy