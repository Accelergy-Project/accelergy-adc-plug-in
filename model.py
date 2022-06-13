from typing import Dict, Tuple
import yaml

import pandas as pd
from sklearn import linear_model
import numpy as np
from headers import *


def foms_sndr2energy(foms: float, sndr: float) -> float:
    """ Calculates the power of an ADC from its Schreier FOM and SNDR """
    return 1 / ((10 ** ((foms - sndr) / 10)) * 2)


def get_area(params: Dict, model: Dict) -> float:
    """
    Returns the energy/convert of an ADC given its design parameters.
    """
    params = params.copy()
    params[INTERCEPT] = 1  # Multiply model intercept by 1
    assert all(k in params for k in model[AREA].keys()), \
        f'Design parameters and model parameters do not match. Please ' \
        f'regenergate ADC model.'
    return math.exp(sum(params[k] * model[AREA][k] for k in model[AREA].keys()))


def get_energy(params: Dict, model: Dict, print_info: bool,
               allow_extrapolation: bool) -> float:
    """
    Returns the energy/convert of an ADC given its design parameters.
    """
    params = params.copy()
    params[INTERCEPT] = 1  # Multiply model intercept by 1
    assert allow_extrapolation or params[FREQ] <= model[FREQ][MAX], \
        f'Frequency {math.exp(params[FREQ]):2E} is greater than the maximum ' \
        f'frequency {math.exp(model[FREQ][MAX]):2E} in the model. Please ' \
        f'use a lower frequency ADC or enable extrapolation.'
    foms = sum(params[k] * model[FOMS][k] for k in [INTERCEPT, FREQ])
    foms = min(foms, model[FOMS][MAX])
    sndr = bits2sndr(params[ENOB])
    if print_info:
        print(f'\tADC with frequency {math.exp(params[FREQ]):2E} has a SNDR of '
              f'{sndr}dB and maximum Schreier FOM of {foms}')
    return foms_sndr2energy(foms, bits2sndr(params[ENOB]))


def mvgress(x: pd.DataFrame, y: pd.Series) \
        -> Tuple[pd.Series, np.ndarray, float]:
    """
    Returns the residuals, coeffs, and intercept of a multivariate linear
    regression.
    """
    if isinstance(x, pd.Series):
        x = pd.DataFrame(x)
    lm = linear_model.LinearRegression()
    x_ = x
    lm.fit(x_, y)
    print(f'Correlation: {lm.score(x_, y)}')
    return y - lm.predict(x_), lm.coef_, lm.intercept_


def get_pareto(x: pd.Series, y: pd.Series, xpos=True, ypos=True) \
        -> pd.DataFrame:
    """
    Returns the pareto set of x, y.
    """
    assert len(x) == len(y), 'x and y must be the same length'

    def more_value(a, b, pos):
        return a >= b if pos else a <= b
    chosen = []
    for i in range(len(x)):
        if all(more_value(x[i], x[j], xpos) or
               more_value(y[i], y[j], ypos) for j in range(len(x))):
            chosen.append(i)

    return x[chosen], y[chosen]


def build_model(source_data: pd.DataFrame,
                output_file: str, show_pretty_plot=False) -> Dict:
    # Ensure adc_data is valid
    print('Building model. Source adc_data:')
    print(source_data.head(5))
    for c in ALL_PARAMS:
        assert c in source_data, f'Missing adc_data column {c}!'
    for index, row in source_data.iterrows():
        for c in ALL_PARAMS:
            assert isinstance(row[c], float),\
                f'Invalid value in row {index} column {c}: {row[c]}'

    # Log columns
    logscale_data = source_data.copy()
    for c in LOGSCALE_PARAMS:
        logscale_data[c] = np.log(source_data[c])

    # ENERGY
    foms_max = logscale_data[FOMS].quantile(0.95)
    freq_max = logscale_data[FREQ].quantile(0.95)
    fr = logscale_data[FREQ]
    fs = logscale_data[FOMS]
    freq_for_pareto = fr[(fs <= fs.quantile(0.95))].reset_index(drop=True)
    foms_for_pareto = fs[(fs <= fs.quantile(0.95))].reset_index(drop=True)
    pgroup_freq, pgroup_foms = get_pareto(freq_for_pareto, foms_for_pareto)
    _, foms_coeffs, foms_intercept = mvgress(pgroup_freq, pgroup_foms)

    # AREA
    area_data = logscale_data.copy()
    ar_residual, ar_coeffs, ar_intercept = mvgress(
        area_data[AREA_CALCULATE_PARAMS], area_data[AREA])
    q = ar_residual.quantile(AREA_QUANTILE)

    if show_pretty_plot:
        import matplotlib.pyplot as plt
        plt.scatter(fr, logscale_data[FOMS])
        plt.scatter(pgroup_freq, pgroup_foms)
        plt.plot(
            [min(fr), (foms_max - foms_intercept) / foms_coeffs[0], max(fr)],
            [foms_max, foms_max, max(fr) * foms_coeffs[0] + foms_intercept])
        plt.show()

    areamodel = {a: ar_coeffs[i] for i, a in enumerate(AREA_CALCULATE_PARAMS)}
    areamodel['intercept'] = ar_intercept + q

    freqmodel = {MAX: freq_max}
    fomsmodel = {FREQ: foms_coeffs[0], MAX: foms_max, INTERCEPT: foms_intercept}

    model = {AREA: areamodel, FREQ: freqmodel, FOMS: fomsmodel,
             COMMENTS: 'Tech node, area, and frequency are log-base-e-scaled.'}

    for k in model:
        if isinstance(model[k], dict):
            m = model[k]
        else:
            m = model
        for k2 in m:
            try:
                m[k2] = float(m[k2])
            except (ValueError, TypeError):
                pass

    print(f'Writing model to "{output_file}"')
    with open(output_file, 'w') as outfile:
        yaml.dump(model, outfile, default_flow_style=False, sort_keys=False)

    return model


def read_input_data(path: str) -> pd.DataFrame:
    """ Loads input adc_data from path """
    if '.xls' == path[-4:] or '.xlsx' == path[-5:]:
        data = pd.read_excel(path)
    else:
        data = pd.read_csv(path)
    return data


if __name__ == '__main__':
    df = pd.read_csv('adc_data/adc_list.csv')
    model = build_model(df, 'adc_data/model.yaml')

    prev = 1
    prev2 = 1
    for r in range(4, 12):
        for f in [5e8, 1e9, 2e9, 3e9]:
            f_active = f
            params = {FREQ: math.log(f_active), ENOB: r, TECH: math.log(32)}
            e = get_energy(params, model, False, False)
            p = e * f_active
            print(f'{r} bit ADC running at frequency {f_active:.2E} aka '
                  f'exp({math.log(f_active):.2E}): {e:.2E}J/op, '
                  f'+{e / prev:.2f}. '
                  f'{math.exp(get_area(params, model)):.2E}um^2. '
                  f'+{math.exp(get_area(params, model)) / prev2:.2f}')
            prev = e
            prev2 = math.exp(get_area(params, model))
