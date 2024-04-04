"""
This file includes constants and headers that are used across the different
scripts in this plugin.
"""

import math
import os

# ==============================================================================
# Design parameters
# ==============================================================================
FREQ = "frequency (Hz)"  # Hz
TECH = "tech node (nm)"  # nm
ENOB = "number of bits"  # bits
DESIGN_PARAMS = [FREQ, TECH, ENOB]
AREA = "area (um^2)"  # ln(um^2)
ENRG = "energy (pJ/op)"  # pJ / op
FOMS = "FOMS_hf [dB]"
SNDR = "SNDR_plot [dB]"
ALL_PARAMS = DESIGN_PARAMS + [AREA, ENRG, FOMS]
AREA_CALCULATE_PARAMS = [TECH, FREQ, ENRG]
LOGSCALE_PARAMS = [FREQ, TECH, AREA, ENRG]

# For fitted energy / area
ENRG_RESIDUAL = f"{ENRG} res"
INTERCEPT = "intercept"  # Constant factor for fitting
TECH_INTERCEPT = "tech intercept"
TECH_SLOPE = "tech slope"
ENOB_SLOPE = "enob slope"

# ==============================================================================
# Model file
# ==============================================================================
MIN = "min value"
MAX = "max value"
MAX_BY_ENOB = "max_by_enob"
AREA_ENRG_TRADEOFF = "area/energy tradeoff"
AREA_ENRG_MODEL = "model"
AREA_COEFF = "area coeff"
CONSTRAINTS = "constraints"
DESIGN_PARAM_MODEL = "design param model"
COMMENTS = "comments"
AREA_QUANTILE = 0.1  # Use bottom 10% of area

# ==============================================================================
# Paths
# ==============================================================================
CURRENT_DIR = os.path.dirname(__file__)
ADC_LIST_DEFAULT = os.path.join(CURRENT_DIR, "adc_data/adc_list.csv")
MODEL_DEFAULT = os.path.join(CURRENT_DIR, "adc_data/model.yaml")


# ==============================================================================
# Helper functions
# ==============================================================================
def dict_key_true(dict_to_check: dict, key: str) -> bool:
    """Returns true if key in is dict and is not none"""
    return dict_to_check and key in dict_to_check and dict_to_check[key]


def bits2sndr(bits: int) -> float:
    """Calculates the SNDR of an ADC from its resolution"""
    return bits * 20 * math.log(2, 10) + 10 * math.log(1.5, 10)


def sndr2bits(sndr: float) -> float:
    """Calculates the resolution of an ADC from its sndr"""
    return (sndr - 10 * math.log(1.5, 10)) / (20 * math.log(2, 10))
