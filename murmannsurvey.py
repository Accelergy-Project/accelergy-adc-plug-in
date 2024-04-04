"""
This script downloads Boris Murmann's ADC survey and packages it into a .CSV
ADC list for user use.
"""

# Data source:
# B. Murmann, "ADC Performance Survey 1997-2023," [Online].
# Available: https://github.com/bmurmann/ADC-survey.

import logging

import pandas as pd

from headers import *

logger = logging.getLogger(__name__)


XLS_FILE = "adc_data/ADC-survey/xls/ADCsurvey_latest.xls"


def get_csv(outfile: str):
    """Converts survey adc_data to a CSV file"""
    xls_path = os.path.join(os.path.dirname(__file__), XLS_FILE)
    if not os.path.exists(xls_path):
        xls_path += "x"
    isscc = pd.read_excel(xls_path, sheet_name="ISSCC")
    vsli = pd.read_excel(xls_path, sheet_name="VLSI")
    xls = pd.concat([isscc, vsli])

    csv = pd.DataFrame()
    numeric_cols = [
        "fs [Hz]",
        "AREA [mm^2]",
        "TECHNOLOGY",
        "P [W]",
        "P/fsnyq [pJ]",
        FOMS,
        SNDR,
    ]
    for c in numeric_cols:
        xls = xls[pd.to_numeric(xls[c], errors="coerce").notnull()]
    csv[FREQ] = xls["fs [Hz]"]
    csv[TECH] = xls["TECHNOLOGY"] * 10**3  # um >> nm
    csv[AREA] = xls["AREA [mm^2]"] * 10**6  # mm^2 -> um^2
    csv[ENRG] = xls["P/fsnyq [pJ]"]
    csv[SNDR] = xls[SNDR]
    csv[ENOB] = xls[SNDR].apply(sndr2bits)
    csv[FOMS] = xls[FOMS]
    csv.reset_index(inplace=True, drop=True)
    if os.path.exists(outfile):
        os.remove(outfile)
    csv.to_csv(outfile)
