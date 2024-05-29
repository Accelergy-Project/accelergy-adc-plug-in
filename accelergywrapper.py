import logging
import sys
import os
import re
from typing import Dict, List
import yaml
from accelergy.plug_in_interface.interface import *
from accelergy.plug_in_interface.estimator_wrapper import (
    SupportedComponent,
    PrintableCall,
)

# Need to add this directory to path for proper imports
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(SCRIPT_DIR)
# fmt: off
from headers import *
from optimizer import ADCRequest
import optimizer
import model
# fmt: on

MODEL_FILE = os.path.join(SCRIPT_DIR, "adc_data/model.yaml")
AREA_ACCURACY = 75
ENERGY_ACCURACY = 75

CLASS_NAMES = [
    "adc",
    "pim_adc",
    "sar_adc",
    "array_adc",
    "pim_array_adc",
    "cim_array_adc",
    "cim_adc",
]
ACTION_NAMES = ["convert", "drive", "read", "sample", "leak", "activate"]

# ==============================================================================
# Input Parsing
# ==============================================================================


def unit_check(key, attributes, default, my_scale, accelergy_scale):
    """Checks for a key in attributes & does unit conversions"""
    if key not in attributes:
        return default
    try:
        return float(attributes[key]) / my_scale * accelergy_scale
    except ValueError:
        pass

    v = re.findall(r"(\d*\.?\d+|\d+\.?\d*)", attributes[key])
    if not v:
        return default
    v = float(v[0]) / my_scale

    nounit = True
    for index, postfix in enumerate(["", "m", "u", "n", "p", "f"]):
        if postfix in attributes[key]:
            nounit = False
            v /= 1000**index
    if nounit:
        v *= accelergy_scale
    return v


def adc_attr_to_request(attributes: Dict, logger: logging.Logger) -> ADCRequest:
    """Creates an ADC Request from a list of attributes"""

    def checkerr(attr, numeric):
        assert attr in attributes, f"No attribute found: {attr}"
        if numeric and isinstance(attributes[attr], str):
            v = re.findall(r"(\d*\.?\d+|\d+\.?\d*)", attributes[attr])
            assert v, f"No numeric found for attribute: {attr}"
            return float(v[0])
        return attributes[attr]

    try:
        n_adcs = int(checkerr("n_adcs", numeric=True))
    except AssertionError:
        n_adcs = 1

    def try_check(keys, numeric):
        for k in keys[:-1]:
            try:
                return checkerr(k, numeric)
            except AssertionError:
                pass
        return checkerr(keys[-1], numeric)

    resolution_names = []
    for x0 in ["adc", ""]:
        for x1 in ["resolution", "bits", "n_bits"]:
            for x2 in ["adc", ""]:
                x = "_".join([x for x in [x0, x1, x2] if x != ""])
                resolution_names.append(x)
    resolution_names.append("resolution")

    r = ADCRequest(
        bits=try_check(resolution_names, numeric=True),
        tech=float(checkerr("technology", numeric=True)),
        throughput=float(checkerr("throughput", numeric=True)),
        n_adcs=n_adcs,
        logger=logger,
    )
    return r


def dict_to_str(attributes: Dict) -> str:
    """Converts a dictionary into a multi-line string representation"""
    s = "\n"
    for k, v in attributes.items():
        s += f"\t{k}: {v}\n"
    return s


# ==============================================================================
# Wrapper Class
# ==============================================================================
class ADCEstimator(AccelergyPlugIn):
    def __init__(self):
        super().__init__()
        model.logger = self.logger
        optimizer.logger = self.logger

        if not os.path.exists(MODEL_FILE):
            self.logger.info(f'python3 {os.path.join(SCRIPT_DIR, "run.py")} -g')
            os.system(f'python3 {os.path.join(SCRIPT_DIR, "run.py")} -g')
        if not os.path.exists(MODEL_FILE):
            self.logger.error(f"ERROR: Could not find model file: {MODEL_FILE}")
            self.logger.error(
                f'Try running: "python3 {os.path.join(SCRIPT_DIR, "run.py")} '
                f'-g" to generate a model.'
            )
        with open(MODEL_FILE, "r") as f:
            self.model = yaml.safe_load(f)

    def get_name(self) -> str:
        return "ADC Plug-In"

    def primitive_action_supported(self, query: AccelergyQuery) -> AccuracyEstimation:
        class_name = query.class_name
        attributes = query.class_attrs
        action_name = query.action_name
        arguments = query.action_args

        if (
            str(class_name).lower() in CLASS_NAMES
            and str(action_name).lower() in ACTION_NAMES
        ):
            adc_attr_to_request(attributes, self.logger)  # Errors if no match
            return AccuracyEstimation(ENERGY_ACCURACY)
        self.logger.info(
            f"ADC Plug-In does not support {class_name}.{action_name}. "
            f"Supported classes: {CLASS_NAMES}, supported actions: {ACTION_NAMES}"
        )
        return AccuracyEstimation(0)  # if not supported, accuracy is 0

    def estimate_energy(self, query: AccelergyQuery) -> Estimation:
        class_name = query.class_name
        attributes = query.class_attrs
        action_name = query.action_name
        arguments = query.action_args

        if (
            str(class_name).lower() not in CLASS_NAMES
            or str(action_name).lower() not in ACTION_NAMES
        ):
            raise NotImplementedError(
                f"Energy estimation for {class_name}.{action_name}" f"is not supported."
            )

        r = adc_attr_to_request(attributes, self.logger)  # Errors if no match
        if "leak" in str(action_name).lower():
            return Estimation(0, "p")
        self.logger.info(
            f"Accelergy requested ADC energy"
            f" estimation with attributes: {dict_to_str(attributes)}"
        )
        energy_per_op = r.energy_per_op(self.model)
        assert energy_per_op, "Could not find ADC for request."
        self.logger.info(f"Generated model uses {energy_per_op:2E} pJ/op.")
        return Estimation(energy_per_op, "p")  # energy is in pJ)

    def primitive_area_supported(self, query: AccelergyQuery) -> AccuracyEstimation:
        class_name = query.class_name
        attributes = query.class_attrs
        action_name = query.action_name
        arguments = query.action_args

        if str(class_name).lower() in CLASS_NAMES:
            adc_attr_to_request(attributes, self.logger)  # Errors if no match
            return AccuracyEstimation(AREA_ACCURACY)
        self.logger.info(
            f"ADC Plug-In does not support {class_name}.{action_name}. "
            f"Supported classes: {CLASS_NAMES}."
        )

        return AccuracyEstimation(0)  # if not supported, accuracy is 0

    def estimate_area(self, query: AccelergyQuery) -> Estimation:
        class_name = query.class_name
        attributes = query.class_attrs
        action_name = query.action_name
        arguments = query.action_args

        if str(class_name).lower() not in CLASS_NAMES:
            raise NotImplementedError(
                f"Area estimation for {class_name} is not supported."
            )

        r = adc_attr_to_request(attributes, self.logger)  # Errors if no match
        self.logger.info(
            f"Accelergy requested ADC energy"
            f" estimation with attributes: {dict_to_str(attributes)}"
        )
        area = r.area(self.model)  # um^2 -> mm^2
        self.logger.info(f"Generated model uses {area:2E} um^2 total.")
        return Estimation(area, "u^2")  # area is in um^2

    def get_supported_components(self) -> List[SupportedComponent]:
        return [
            SupportedComponent(
                CLASS_NAMES,
                PrintableCall("", ["resolution", "technology", "throughput", "n_adcs"]),
                [PrintableCall(a) for a in ACTION_NAMES],
            )
        ]


if __name__ == "__main__":
    bits = 8
    technode = 16
    throughput = 512e7
    n_adcs = 32
    e = ADCEstimator()
    query = AccelergyQuery(
        class_name="ADC",
        action_name="convert",
        class_attrs={
            "resolution": bits,
            "technology": technode,
            "throughput": throughput,
            "n_adcs": n_adcs,
        },
    )
    print(e.estimate_energy(query))
    print(e.estimate_area(query))
