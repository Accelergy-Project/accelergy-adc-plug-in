import sys
import os
import re
from typing import Dict

# Need to add this directory to path for proper imports
import yaml

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(SCRIPT_DIR)
from optimizer import ADCRequest
from headers import *

MODEL_FILE = os.path.join(SCRIPT_DIR, 'adc_data/model.yaml')
AREA_ACCURACY = 75
ENERGY_ACCURACY = 75


# ==============================================================================
# Input Parsing
# ==============================================================================
def unit_check(key, attributes, default, my_scale, accelergy_scale):
    """ Checks for a key in attributes & does unit conversions """
    if key not in attributes:
        return default
    try:
        return float(attributes[key]) / my_scale * accelergy_scale
    except ValueError:
        pass

    v = re.findall(r'(\d*\.?\d+|\d+\.?\d*)', attributes[key])
    if not v:
        return default
    v = float(v[0]) / my_scale

    nounit = True
    for index, postfix in enumerate(['', 'm', 'u', 'n', 'p', 'f']):
        if postfix in attributes[key]:
            nounit = False
            v /= (1000 ** index)
    if nounit:
        v *= accelergy_scale
    return v


def adc_attr_to_request(attributes):
    """ Creates an ADC Request from a list of attributes """

    def checkerr(attr, numeric):
        assert attr in attributes, f'No attribute found: {attr}'
        if numeric and isinstance(attributes[attr], str):
            v = re.findall(r'(\d*\.?\d+|\d+\.?\d*)', attributes[attr])
            assert v, f'No numeric found for attribute: {attr}'
            return float(v[0])
        return attributes[attr]

    try:
        n_adc = int(  checkerr('n_adc', numeric=True))
    except AssertionError:
        n_adc = int(  checkerr('n_components', numeric=True))

    r = ADCRequest(
        bits                 =float(checkerr('resolution', numeric=True)),
        tech                 =float(checkerr('technology', numeric=True)),
        throughput           =float(checkerr('throughput', numeric=True)),
        n_adc                =n_adc,
    )
    return r


def dict_to_str(attributes: Dict) -> str:
    """ Converts a dictionary into a multi-line string representation """
    s = '\n'
    for k, v in attributes.items():
        s += f'\t{k}: {v}\n'
    return s


# ==============================================================================
# Wrapper Class
# ==============================================================================
class AnalogEstimator:
    def __init__(self):
        self.estimator_name = 'Analog Estimator'
        if not os.path.exists(MODEL_FILE):
            print(f'python3 {os.path.join(SCRIPT_DIR, "run.py")} -g')
            os.system(f'python3 {os.path.join(SCRIPT_DIR, "run.py")} -g')
        if not os.path.exists(MODEL_FILE):
            print(f'ERROR: Could not find model file: {MODEL_FILE}')
            print(f'Try running: "python3 {os.path.join(SCRIPT_DIR, "run.py")} '
                  f'-g" to generate a model.')
            sys.exit(1)
        with open(MODEL_FILE, 'r') as f:
            self.model = yaml.safe_load(f)

    def primitive_action_supported(self, interface):
        """
        :param interface:
        - contains four keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        3. action_name: string
        4. arguments: dictionary of name: value
        :type interface: dict
        :return return the accuracy if supported, return 0 if not
        :rtype: int
        """
        class_name = interface['class_name']
        attributes = interface['attributes']
        action_name = interface['action_name']

        if str(class_name).lower() == 'adc' \
                and str(action_name).lower() == 'convert':
            try:
                adc_attr_to_request(attributes)  # Errors if no match
                return ENERGY_ACCURACY
            except AssertionError as e:
                print(f'Warn: Analog Plug-in could not generate ADC. {e}')
                print(f'Warn: Attributes given: {attributes}')

        return 0  # if not supported, accuracy is 0

    def estimate_energy(self, interface):
        """
        :param interface:
        - contains four keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        3. action_name: string
        4. arguments: dictionary of name: value
       :return the estimated energy
       :rtype float
        """
        class_name = interface['class_name']
        attributes = interface['attributes']
        action_name = interface['action_name']

        if str(class_name).lower() == 'adc' \
                and str(action_name).lower() == 'convert':
            try:
                r = adc_attr_to_request(attributes)  # Errors if no match
                print(f'Info: Analog Plug-in... Accelergy requested ADC energy'
                      f' estimation with attributes: {dict_to_str(attributes)}')
                energy_per_op = r.energy_per_op(self.model) * 1e12  # J to pJ
                assert energy_per_op, 'Could not find ADC for request.'
                print(f'Info: Generated model uses {energy_per_op:2E} pJ/op.')
                return energy_per_op
            except AssertionError as e:
                print(f'Warn: Analog Plug-in could not generate ADC. {e}')
                print(f'Warn: Attributes given: {dict_to_str(attributes)}')

        return 0  # if not supported, accuracy is 0

    def primitive_area_supported(self, interface):
        """
        :param interface:
        - contains two keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        :type interface: dict
        :return return the accuracy if supported, return 0 if not
        :rtype: int
        """
        class_name = interface['class_name']
        attributes = interface['attributes']

        if str(class_name).lower() == 'adc':
            try:
                adc_attr_to_request(attributes)  # Errors if no match
                return AREA_ACCURACY
            except AssertionError as e:
                print(f'Warn: Analog Plug-in could not generate ADC. {e}')
                print(f'Warn: Attributes given: {dict_to_str(attributes)}')

        return 0  # if not supported, accuracy is 0

    def estimate_area(self, interface):
        """
        :param interface:
        - contains two keys:
        1. class_name : string
        2. attributes: dictionary of name: value
        :type interface: dict
        :return the estimated area
        :rtype: float
        """
        class_name = interface['class_name']
        attributes = interface['attributes']

        if str(class_name).lower() == 'adc':
            try:
                r = adc_attr_to_request(attributes)  # Errors if no match
                print(f'Info: Analog Plug-in... Accelergy requested ADC energy'
                      f' estimation with attributes: {dict_to_str(attributes)}')
                area = r.area(self.model) # um^2 -> mm^2
                print(f'Info: Generated model uses {area:2E} um^2 total.')
                return area
            except AssertionError as e:
                print(f'Warn: Analog Plug-in could not generate ADC. {e}')
                print(f'Warn: Attributes given: {dict_to_str(attributes)}')

        return 0  # if not supported, accuracy is 0


if __name__ == '__main__':
    bits = 8
    technode = 16
    throughput = 512e7
    n_adc = 32
    attrs = {
        'class_name': 'ADC',
        'action_name': 'convert',
        'attributes': {
            'resolution': bits,
            'technology': technode,
            'throughput': throughput,
            'n_adc': n_adc
        }
    }
    e = AnalogEstimator()
    e.estimate_energy(attrs)
    e.estimate_area(attrs)
