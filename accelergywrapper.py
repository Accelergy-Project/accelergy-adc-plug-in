import sys
import os
import re
from typing import Dict

# Need to add this directory to path for proper imports
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(SCRIPT_DIR)
from optimizer import ADCRequest, Model

MODEL_FILE = os.path.join(SCRIPT_DIR, 'adc_data/model.yaml')
# Accuracy values are from correlation coeffs. of actual vs. predicted ADC
# characteristics at the time of writing this script.
AREA_ACCURACY = 69
ENERGY_ACCURACY = 82


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

    def check(attr, default):
        return default if attr not in attributes else attributes[attr]

    def checkerr(attr, numeric):
        assert attr in attributes, f'No attribute found: {attr}'
        if numeric and isinstance(attributes[attr], str):
            v = re.findall(r'(\d*\.?\d+|\d+\.?\d*)', attributes[attr])
            assert v, f'No numeric found for attribute: {attr}'
            return float(v[0])
        return attributes[attr]

    r = ADCRequest(
        bits                 =float(checkerr('resolution', numeric=True)),
        tech                 =float(checkerr('technology', numeric=True)),
        channel_count        =int(  check('channels', 1)),
        energy_area_tradeoff =float(check('energy_area_tradeoff', .5)),
        max_share_count      =int(  check('max_share_count', 0)),
        adc_per_channel      =int(  check('adc_per_channel', 0)),
        channel_per_adc      =int(  check('channel_per_adc', 0)),
        latency              =float(unit_check('adc_latency', attributes, 0, 1, 10 ** -9)), # We use seconds, accelergy uses nanoseconds
        throughput           =float(check('adc_throughput', 0)),
        area_budget          =      unit_check('area_budget', attributes, None, 10 ** -12, 10 ** -12),  # We use um^2, accelergy uses um^2
        energy_budget        =      unit_check('energy_budget', attributes, None, 10 ** -12, 10 ** -12),  # We use pJ, accelergy uses pJ
        allow_extrapolation  =      check('allow_extrapolation', True),
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
        self.model = Model(MODEL_FILE)

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
                r.optimize(self.model)
                energy_per_op = r.energy_per_op
                assert r.energy_per_op, 'Could not find ADC for request.'
                print(f'Info: Analog Plug-in... Accelergy requested ADC energy'
                      f' estimation with attributes: {dict_to_str(attributes)}')
                print(f'Info: Generated model uses {r.adc_count} ADCs at '
                      f'{energy_per_op} pJ/op.')
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
                r.optimize(self.model)
                assert r.area_per_channnel, 'Could not find ADC for request.'
                print(f'Info: Analog Plug-in... Accelergy requested ADC energy'
                      f' estimation with attributes: {dict_to_str(attributes)}')
                print(f'Info: Generated model uses {r.adc_count} ADCs at '
                      f'{r.area_per_channnel * r.channel_count:.3} um^2 total.')
                return r.area_per_channnel * r.channel_count  # mm^2 -> um^2
            except AssertionError as e:
                print(f'Warn: Analog Plug-in could not generate ADC. {e}')
                print(f'Warn: Attributes given: {dict_to_str(attributes)}')

        return 0  # if not supported, accuracy is 0
