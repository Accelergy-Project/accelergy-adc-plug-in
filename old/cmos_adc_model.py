"""
Area scaling analysis of CMOS ADCs
M. Verhelst and B. Murmann

Uses current adc_data
"""

import pandas as pd

from murmannsurvey import *


def xls_to_csv(xls: str, outfile: str):
    """ Converts survey adc_data to a CSV file """
    isscc = pd.read_excel(xls, sheet_name='ISSCC')
    vsli = pd.read_excel(xls, sheet_name='VLSI')
    xls = pd.concat([isscc, vsli])

    csv = pd.DataFrame()

    xls = xls[xls['ARCHITECTURE'].str.contains('SAR')]
    xls[ENOB] = xls.apply(infer_bits, axis=1)

    numeric_cols = [
        'fs [Hz]', 'AREA [mm^2]', 'TECHNOLOGY', 'P [W]', ENOB
    ]
    for c in numeric_cols:
        xls = xls[pd.to_numeric(xls[c], errors='coerce').notnull()]
    csv[FREQ] = xls['fs [Hz]']
    csv[ENOB] = xls[ENOB]
    csv[TECH] = xls['TECHNOLOGY'] * 1000
    csv[AREA] = xls['AREA [mm^2]']
    csv[ENRG] = xls['P/fsnyq [pJ]']
    csv.reset_index(inplace=True, drop=True)

    data = csv

    A = (e^a) * (T ^ b) * (e ^ cR) * (e ^ dF)
    log A = a + blog(T) + cR + dlog(F)










