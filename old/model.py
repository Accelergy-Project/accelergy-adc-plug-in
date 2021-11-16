from typing import List, Dict
import yaml

import pandas as pd
from sklearn import linear_model
import numpy as np
from headers import *


def apply_constraints(data: pd.DataFrame, constraints: Dict) -> pd.DataFrame:
    """ Removes adc_data points based on constraint values """
    keep = [True] * data.shape[0]

    for p in ALL_PARAMS:
        keep = keep & (data[p] > 0)
    if len(keep) - sum(keep):
        print(f'Removed {len(keep) - sum(keep)} ADCs'
              f' with non-positive parameters.')

    if not dict_key_true(constraints, INPUT_CONSTRAINTS_KEY):
        print(f'No input constraints found. Using all entries.')
        return data
    constraints = constraints[INPUT_CONSTRAINTS_KEY]

    for p in ALL_PARAMS:
        if not dict_key_true(constraints, p):
            continue
        param_constraints = constraints[p]

        prev_count = sum(keep)
        if MIN in param_constraints:
            keep = keep & (data[p] >= param_constraints[MIN])
        if MAX in param_constraints:
            keep = keep & (data[p] <= param_constraints[MAX])
        if MIN_PERCENTILE in param_constraints:
            keep = keep & (data[p] >= data[p].quantile(
                param_constraints[MIN_PERCENTILE] / 100))
        if MAX_PERCENTILE in param_constraints:
            keep = keep & (data[p] <= data[p].quantile(
                param_constraints[MAX_PERCENTILE] / 100))
        print(f'{prev_count - keep.sum()} ADCs excluded by {p} constraints.')

    print(f'Constrained list has {sum(keep)} ADC entries.')

    return data[keep].reset_index(drop=True)


def fit_params(data: pd.DataFrame) -> Dict:
    """ Controls design parameter effects on area/energy w/ regression """
    result = {}
    x = data.apply(lambda row: [row[p] for p in DESIGN_PARAMS], axis=1).tolist()

    for target, residual in [(AREA, AREA_RESIDUAL), (ENRG, ENRG_RESIDUAL)]:
        # Calculate regression
        y = data[target].tolist()
        lm = linear_model.LinearRegression()
        lm.fit(x, y)

        # Pack results of fit into dictionary
        result[target] = {
            k: float(lm.coef_[i]) for i, k in enumerate(DESIGN_PARAMS)
        }
        result[target][INTERCEPT] = float(lm.intercept_)
        data[residual] = [y[i] - p for i, p in enumerate(lm.predict(x))]

    return result


def group_satisfies_pareto_constraints(
        data: pd.DataFrame,
        model_constraints: Dict,
        skipped: List[int],
        chosen: List[int]) -> bool:
    """
    Checks if the list of chosen indices satisfies all pareto constraints in
    model_constraints
    """
    entries = data.iloc[chosen + skipped, :]

    # Get overall pareto percentiles needed
    min_pareto_percentile, max_pareto_percentile = 100, 100
    if MIN_PARETO_PERCENTILE in model_constraints:
        min_pareto_percentile = model_constraints[MIN_PARETO_PERCENTILE]

    # Get list of percentiles to include
    include_percentiles = {p: [] for p in DESIGN_PARAMS}
    if dict_key_true(model_constraints, INCLUDE_PERCENTILES):
        include_percentiles.update(model_constraints[INCLUDE_PERCENTILES])

    # Check we've included enough points overall
    include_to = data.shape[0] * (1 - min_pareto_percentile / 100)
    if len(skipped) + len(chosen) < include_to:
        return False

    # Check we've included needed percentiles for each parameter
    for param, percentiles in include_percentiles.items():
        if param not in data.columns or not percentiles:
            continue
        for p in percentiles:
            value = data[param].quantile(p / 100)
            if entries[param].min() > value:
                return False
            if entries[param].max() < value:
                return False

    return True


def get_energy_area_pareto(data: pd.DataFrame) -> List:
    """
    Finds area/energy pareto points and returns list of row numbers
    Data should be sorted in ascending order by area!
    """
    indices = []
    lowest_energy = None
    for i in range(data.shape[0]):
        row = data.iloc[i, :]
        if lowest_energy is None or row[ENRG_RESIDUAL] < lowest_energy:
            lowest_energy = row[ENRG_RESIDUAL]
            indices.append(i)
    return indices


def approx_pareto_group(data: pd.DataFrame, constraints: Dict) \
        -> pd.DataFrame or None:
    """
    Returns approx pareto group (set of pareto sets) that matches all
    constraints. Approximate group is made by recursively finding pareto set,
    removing that set from the adc_data, then finding the next set.
    Returns None if constraints are impossible to fit.
    """
    if not dict_key_true(constraints, MODEL_CONSTRAINTS_KEY):
        print(f'No model constraints found. Using pareto-optimal designs.')
        data = data.copy().sort_values(by=AREA_RESIDUAL).reset_index()
        return data.iloc[get_energy_area_pareto(data), :]

    model_constraints = constraints[MODEL_CONSTRAINTS_KEY]

    max_pareto_percentile = 100
    if MAX_PARETO_PERCENTILE in model_constraints:
        max_pareto_percentile = model_constraints[MAX_PARETO_PERCENTILE]

    # Put together list of pareto sets
    pareto_sets = []
    remaining = data.copy().sort_values(by=AREA_RESIDUAL).reset_index()
    while remaining.shape[0]:
        newset = get_energy_area_pareto(remaining)
        pareto_sets.append(remaining.iloc[newset, :]['index'].tolist())
        remaining = remaining.drop(newset).reset_index(drop=True)

    skipped = []
    chosen = []

    # Drop sets until we've gotten to the max percentile
    skip_to = data.shape[0] * (1 - max_pareto_percentile / 100)
    while pareto_sets and len(skipped + pareto_sets[0]) < skip_to:
        skipped += pareto_sets.pop(0)

    # Add sets until other requirements are satisfying
    while pareto_sets:
        chosen += pareto_sets.pop(0)
        if group_satisfies_pareto_constraints(
                data, model_constraints, skipped, chosen):
            return data.iloc[chosen, :]
    return None


def pareto_group(data: pd.DataFrame, constraints: Dict) -> pd.DataFrame or None:
    """
    Returns pareto group (set of pareto sets) that matches all constraints.
    Returns None if constraints are impossible to fit.
    """
    # Get approximate pareto group
    approx = approx_pareto_group(data, constraints)
    if approx is None or not dict_key_true(constraints, MODEL_CONSTRAINTS_KEY):
        return approx

    # Use tradeoff line from this group as a metric for rating new group
    lm = linear_model.LinearRegression()
    x = approx[AREA_RESIDUAL]
    y = approx[ENRG_RESIDUAL].tolist()
    lm.fit([[v] for v in x], y)

    # Rate points based on approx tradeoff line
    data = data.copy()
    rise, run = 1, - lm.coef_[0]  # rise and run of perpendicular line
    data['QUALITY'] = data.apply(
        lambda r: r[AREA_RESIDUAL] * run + r[ENRG_RESIDUAL] * rise, axis=1)
    data = data.sort_values(by='QUALITY').reset_index(drop=True)

    # Now build real set
    model_constraints = constraints[MODEL_CONSTRAINTS_KEY]
    max_pareto_percentile = model_constraints[MAX_PARETO_PERCENTILE] \
        if MAX_PARETO_PERCENTILE in model_constraints else 100

    skipped = [
        x for x in range(int(data.shape[0] * (1 - max_pareto_percentile / 100)))
    ]
    chosen = [skipped[-1] + 1 if skipped else 0]
    while len(skipped) + len(chosen) < data.shape[0]:
        if group_satisfies_pareto_constraints(
                data, model_constraints, skipped, chosen):
            print(f'Pareto group found with {len(chosen)} entries.')
            return data.iloc[chosen, :]
        chosen.append(chosen[-1] + 1)
    return None


def model_from_pareto(
        pareto_group: pd.DataFrame,
        param_fit: Dict,
) -> Dict:
    """ Constructs the final model and packs into a dictionary """
    model = {}

    # Build area/energy tradeoff linear model
    lm = linear_model.LinearRegression()
    x = pareto_group[AREA_RESIDUAL]
    y = pareto_group[ENRG_RESIDUAL].tolist()
    lm.fit([[v] for v in x], y)
    model[AREA_ENRG_TRADEOFF] = {}
    model[AREA_ENRG_TRADEOFF][AREA_ENRG_MODEL] = {
        AREA_COEFF: float(lm.coef_[0]),
        INTERCEPT: float(lm.intercept_)
    }

    assert model[AREA_ENRG_TRADEOFF][AREA_ENRG_MODEL][AREA_COEFF] < 0, \
        'Pareto group has a positively correlated energy/op and area. Please ' \
        'add adc_data or modify constraints for a representative Pareto group.' \
        'This may occur if you require too many points in your Pareto group.'

    # Get min/max values
    model_min_area = min(pareto_group[AREA_RESIDUAL])
    model_max_area = max(pareto_group[AREA_RESIDUAL])
    model_min_enrg = min(pareto_group[ENRG_RESIDUAL])
    model_max_enrg = max(pareto_group[ENRG_RESIDUAL])

    model_min_area = max(model_min_area,
                         (model_max_enrg - lm.intercept_) / lm.coef_[0])
    model_max_area = min(model_max_area,
                         (model_min_enrg - lm.intercept_) / lm.coef_[0])
    model_max_enrg = lm.intercept_ + model_min_area * lm.coef_[0]
    model_min_enrg = lm.intercept_ + model_max_area * lm.coef_[0]

    model[AREA_ENRG_TRADEOFF][CONSTRAINTS] = {
        AREA: {MIN: float(model_min_area), MAX: float(model_max_area)},
        ENRG: {MIN: float(model_min_enrg), MAX: float(model_max_enrg)}
    }
    model[AREA_ENRG_TRADEOFF][COMMENTS] = (
        'This area/energy tradeoff linear model operates on log scaled adc_data '
        'after values have been scaled for tech node, # bits, and frequency.'
    )

    model[DESIGN_PARAM_MODEL] = param_fit
    model[DESIGN_PARAM_MODEL][COMMENTS] = (
        'This model scales energy/area of ADCs based on tech node, # bits, and '
        'frequency. All values are log scaled except # bits.'
    )

    model[CONSTRAINTS] = {}
    for p in DESIGN_PARAMS:
        model[CONSTRAINTS][p] = {
            MIN: float(pareto_group[p].min()),
            MAX: float(pareto_group[p].max())
        }
    model[CONSTRAINTS][COMMENTS] = (
        'Ranges for which this model is valid. All values are log scaled '
        'except # bits.'
    )

    return model


def build_model(source_data: pd.DataFrame, constraints: Dict, output_file: str):
    # Ensure adc_data is valid
    for c in ALL_PARAMS:
        assert c in source_data, f'Missing adc_data column {c}!'
    for index, row in source_data.iterrows():
        for c in ALL_PARAMS:
            assert isinstance(row[c], float),\
                f'Invalid value in row {index} column {c}: {row[c]}'

    # Apply constraints
    source_data = apply_constraints(source_data, constraints)
    assert source_data.shape[0] >= 2, 'Insufficient adc_data points!'

    # Log columns
    logscale_data = source_data.copy()
    for c in LOGSCALE_PARAMS:
        logscale_data[c] = np.log(source_data[c])

    # Control for frequency, technology, area with linear model
    fitted_model = fit_params(logscale_data)

    # Get pareto group
    pareto = pareto_group(logscale_data, constraints)
    assert pareto is not None, 'Model could not be built under ' \
                               'modeling constraints. Please check ' \
                               'modeling constraints file and relax ' \
                               'parameters.'

    # Construct final model
    model = model_from_pareto(pareto, fitted_model)
    print(f'Writing model to "{output_file}"')
    with open(output_file, 'w') as outfile:
        yaml.dump(model, outfile, default_flow_style=False, sort_keys=False)


if __name__ == '__main__':
    with open('constraints.yaml') as f:
        abc = yaml.load(f.read(), Loader=yaml.FullLoader)
    df = pd.read_csv('adc_list.csv')
    build_model(df, abc, 'model.yml')
