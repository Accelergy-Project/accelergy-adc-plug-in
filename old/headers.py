# ==============================================================================
# Design parameters
# ==============================================================================
FREQ = 'frequency (Hz)'  # Hz
TECH = 'tech node (nm)'  # nm
ENOB = 'number of bits'  # bits
DESIGN_PARAMS = [FREQ, TECH, ENOB]
AREA = 'area (um^2)'  # ln(um^2)
ENRG = 'energy (pJ/op)'  # pJ / op
ALL_PARAMS = DESIGN_PARAMS + [AREA, ENRG]
LOGSCALE_PARAMS = [FREQ, TECH, AREA, ENRG]

# For fitted energy / area
RESIDUALS = f'residuals'
AREA_RESIDUAL = f'{AREA} res'
ENRG_RESIDUAL = f'{ENRG} res'
INTERCEPT = 'intercept'  # Constant factor for fitting

# ==============================================================================
# YAML keys
# ==============================================================================
# Modeling constraints file
INPUT_CONSTRAINTS_KEY = 'input constraints'
MODEL_CONSTRAINTS_KEY = 'model constraints'
MIN_PARETO_PERCENTILE = 'min pareto percentile'
MAX_PARETO_PERCENTILE = 'max pareto percentile'
INCLUDE_PERCENTILES = 'include percentiles'
MIN = 'min value'
MAX = 'max value'
MIN_PERCENTILE = 'min percentile'
MAX_PERCENTILE = 'max percentile'

# ==============================================================================
# Model file
# ==============================================================================
AREA_ENRG_TRADEOFF = 'area/energy tradeoff'
AREA_ENRG_MODEL = 'model'
AREA_COEFF = 'area coeff'
CONSTRAINTS = 'constraints'
DESIGN_PARAM_MODEL = 'design param model'
COMMENTS = 'comments'


def dict_key_true(dict_to_check: dict, key: str) -> bool:
    """ Returns true if key in dict and is not none """
    return dict_to_check and key in dict_to_check and dict_to_check[key]
