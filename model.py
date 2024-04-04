from typing import Dict, Tuple
import yaml

from headers import *
import logging
import math

logger = logging.getLogger(__name__)


def foms_sndr2energy(foms: float, sndr: float) -> float:
    """Calculates the energy of an ADC from its Schreier FOM and SNDR"""
    return 1 / ((10 ** ((foms - sndr) / 10)) * 2)


def get_area(params: Dict, model: Dict) -> float:
    """
    Returns the energy/convert of an ADC given its design parameters.
    """
    params = params.copy()
    params[INTERCEPT] = 1  # Multiply model intercept by 1
    assert all(k in params for k in model[AREA].keys()), (
        f"Design parameters and model parameters do not match. Please "
        f"regenergate ADC model."
    )
    return math.exp(sum(params[k] * model[AREA][k] for k in model[AREA].keys()))


def get_energy(params: Dict, model: Dict, allow_extrapolation: bool) -> float:
    """
    Returns the energy/convert of an ADC given its design parameters.
    """
    params = params.copy()
    params[INTERCEPT] = 1  # Multiply model intercept by 1
    warning_txt = (
        f"Frequency {math.exp(params[FREQ]):2E} is greater than the maximum "
        f"frequency {math.exp(model[FREQ][MAX]):2E} in the model."
    )
    err_txt = warning_txt + " Please use a lower frequency ADC or enable extrapolation."
    if not allow_extrapolation:
        assert params[FREQ] <= model[FREQ][MAX], err_txt
    elif params[FREQ] > model[FREQ][MAX]:
        logger.warning(warning_txt)

    foms = sum(params[k] * model[FOMS][k] for k in [INTERCEPT, FREQ])
    foms_max_by_enob = model[FOMS][MAX_BY_ENOB]
    foms_max = foms_max_by_enob[
        max(min(math.ceil(params[ENOB]), len(foms_max_by_enob) - 1), 0)
    ]
    foms = min(foms, foms_max)
    energy = foms_sndr2energy(foms, bits2sndr(params[ENOB]))

    return energy * math.exp(
        model[FOMS][TECH_INTERCEPT]
        + model[FOMS][TECH_SLOPE] * (params[TECH])
        + model[FOMS][ENOB_SLOPE] * math.log(params[ENOB])
        + model[FOMS][ENRG_RESIDUAL]
    )


def mvgress(
    x: "pd.DataFrame", y: "pd.Series"
) -> Tuple["pd.Series", "np.ndarray", float]:
    """
    Returns the residuals, coeffs, and intercept of a multivariate linear
    regression.
    """
    from sklearn import linear_model
    import pandas as pd

    if isinstance(x, pd.Series):
        x = pd.DataFrame(x)
    lm = linear_model.LinearRegression()
    x_ = x
    lm.fit(x_, y)
    logger.info(f"Correlation: {lm.score(x_, y)}")
    return y - lm.predict(x_), lm.coef_, lm.intercept_


def get_pareto(
    x: "pd.Series",
    y: "pd.Series",
    x_positive=True,
    y_positive=True,
    allow_interior_points: int = 1,
) -> "pd.DataFrame":
    """
    Returns the pareto set of x, y.
    """
    assert len(x) == len(y), "x and y must be the same length"

    def more_value(a, b, pos):
        return a >= b if pos else a <= b

    chosen = []
    for i in range(len(x)):
        if (
            len(x)
            - sum(
                more_value(x[i], x[j], x_positive) or more_value(y[i], y[j], y_positive)
                for j in range(len(x))
            )
            < allow_interior_points
        ):
            chosen.append(i)

    return x[chosen], y[chosen]


def build_model(
    source_data: "pd.DataFrame", output_file: str, show_pretty_plot=False
) -> Dict:
    import numpy as np
    import pandas as pd

    # Ensure adc_data is valid
    logger.info("Building model. Source adc_data:")
    logger.info(source_data.head(5))
    for c in ALL_PARAMS:
        assert c in source_data, f"Missing adc_data column {c}!"
    for index, row in source_data.iterrows():
        for c in ALL_PARAMS:
            assert isinstance(
                row[c], float
            ), f"Invalid value in row {index} column {c}: {row[c]}"

    # Log columns
    logscale_data = source_data.copy()
    for c in LOGSCALE_PARAMS:
        logscale_data[c] = np.log(source_data[c])

    # Remove outliers
    OUTLIER_THRESHOLD = 0.8

    # Adjust the FOMS by tech node
    residual, coeffs, intercept = mvgress(logscale_data[ENOB], logscale_data[TECH])
    logscale_data["FOMS_ADJUSTED"] = (
        logscale_data[FOMS] - coeffs[0] * logscale_data[TECH] - intercept
    )
    logscale_data["log ENOB"] = np.log(logscale_data[ENOB])
    logscale_data = logscale_data.dropna().reset_index(drop=True)

    # ENERGY
    foms_max = logscale_data["FOMS_ADJUSTED"].quantile(OUTLIER_THRESHOLD)
    print(f"Maximum FOMS: {foms_max}")

    residuals, coeffs, intercept = mvgress(
        logscale_data[ENOB], logscale_data["FOMS_ADJUSTED"]
    )
    intercept += pd.Series(residuals).quantile(OUTLIER_THRESHOLD)
    foms_max_by_enob_x = np.arange(math.ceil(np.max(logscale_data[ENOB]) + 1)).reshape(
        -1, 1
    )
    foms_max_by_enob = [float(intercept + coeffs[0] * x) for x in foms_max_by_enob_x]

    freq_max = np.log(1e10)  # logscale_data[FREQ].quantile(TH3)
    fr = logscale_data[FREQ]
    fs = logscale_data["FOMS_ADJUSTED"]
    freq_for_pareto = fr[(fs <= fs.quantile(OUTLIER_THRESHOLD))].reset_index(drop=True)
    foms_for_pareto = fs[(fs <= fs.quantile(OUTLIER_THRESHOLD))].reset_index(drop=True)
    pgroup_freq, pgroup_foms = get_pareto(
        freq_for_pareto,
        foms_for_pareto,
        allow_interior_points=round(len(freq_for_pareto) * 0.05),
    )
    _, foms_coeffs, foms_intercept = mvgress(pgroup_freq, pgroup_foms)

    def get_max_foms(enob, freq):
        max_by_enob = foms_max_by_enob[round(enob)]
        max_by_freq = foms_coeffs[0] * freq + foms_intercept
        return min(max_by_enob, max_by_freq)

    max_foms = logscale_data.apply(lambda x: get_max_foms(x[ENOB], x[FREQ]), axis=1)
    pred_energy = foms_sndr2energy(max_foms, bits2sndr(logscale_data[ENOB]))
    error = np.log(np.exp(logscale_data[ENRG]) / pred_energy)
    logscale_data["log ENOB"] = np.log(logscale_data[ENOB])
    tech_energy_residuals, tech_energy_coeffs, tech_energy_intercept = mvgress(
        logscale_data[[TECH, "log ENOB"]], error
    )
    print(
        f"Residuals-tech correlation: {np.corrcoef(logscale_data[TECH], tech_energy_residuals)[0, 1]}"
    )
    print(
        f"Predicted-actual energy correlation: {np.corrcoef(logscale_data[ENRG], np.log(pred_energy))[0, 1]}"
    )
    pred_energy = pred_energy * np.exp(
        tech_energy_intercept
        + tech_energy_coeffs[0] * logscale_data[TECH]
        + tech_energy_coeffs[1] * logscale_data["log ENOB"]
    )
    print(
        f"Predicted-actual energy correlation: {np.corrcoef(logscale_data[ENRG], np.log(pred_energy))[0, 1]}"
    )
    with open("energy_correlation.csv", "w") as f:
        f.write("Actual energy (pJ/op),Predicted energy (pJ/op)\n")
        for i in range(len(pred_energy)):
            f.write(f"{np.exp(logscale_data[ENRG].iloc[i])},{pred_energy.iloc[i]}\n")
    energy_residual = tech_energy_residuals.quantile(1 - OUTLIER_THRESHOLD)

    freqmodel = {MAX: freq_max}
    fomsmodel = {
        FREQ: foms_coeffs[0],
        MAX: foms_max,
        INTERCEPT: foms_intercept,
        MAX_BY_ENOB: foms_max_by_enob,
        TECH_INTERCEPT: tech_energy_intercept,
        TECH_SLOPE: tech_energy_coeffs[0],
        ENOB_SLOPE: tech_energy_coeffs[1],
        ENRG_RESIDUAL: energy_residual,
    }
    model = {
        FREQ: freqmodel,
        FOMS: fomsmodel,
        COMMENTS: "Tech node, area, and frequency are log-base-e-scaled. "
        "max_by_enob was also considered for limiting the frequency of "
        "ADCs, but max ADC frequency was plenty for realistic PIM "
        "settings at reasonable ADC resolutions.",
    }
    # AREA
    area_data = logscale_data.copy()
    ar_residual, ar_coeffs, ar_intercept = mvgress(
        area_data[AREA_CALCULATE_PARAMS], area_data[AREA]
    )
    ar_intercept -= ar_residual.quantile(1 - AREA_QUANTILE)

    areamodel = {a: ar_coeffs[i] for i, a in enumerate(AREA_CALCULATE_PARAMS)}
    areamodel["intercept"] = ar_intercept
    model[AREA] = areamodel

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

    logger.info(f'Writing model to "{output_file}"')
    with open(output_file, "w") as outfile:
        yaml.dump(model, outfile, default_flow_style=False, sort_keys=False)

    return model


def read_input_data(path: str) -> "pd.DataFrame":
    """Loads input adc_data from path"""
    import pandas as pd

    if ".xls" == path[-4:] or ".xlsx" == path[-5:]:
        data = pd.read_excel(path)
    else:
        data = pd.read_csv(path)
    return data


if __name__ == "__main__":
    with open("./adc_data/model.yaml", "r") as f:
        model = yaml.safe_load(f)

    prev = 1
    prev2 = 1
    for r in range(4, 12):
        for f in [1e8, 2.5e8, 5e8, 1e9, 2e9]:
            f_active = f
            params = {FREQ: math.log(f_active), ENOB: r, TECH: math.log(32)}
            e = get_energy(params, model, True)
            params[ENRG] = e
            a = get_area(params, model)
            p = e * f_active
            print(f"{r}, {f_active:.2E}, {a:.2E}")
            prev = e
            prev2 = get_area(params, model)

    resolutions = [x for x in range(4, 12)]
    frequencies = [1e7] + [5e7] + [1e8 * x for x in range(1, 21)]
    print("," + ",".join([f"{x/1e6}" for x in frequencies]))
    for r in resolutions:
        energies = []
        areas = []
        for f in frequencies:
            params = {FREQ: math.log(f), ENOB: r, TECH: math.log(32)}
            params[ENRG] = math.log(get_energy(params, model, True) * 1e12)
            energies.append(math.exp(params[ENRG]))
            areas.append(get_area(params, model))

        print(f"{r}," + ",".join([f"{e:.2E}" for e in areas]))
