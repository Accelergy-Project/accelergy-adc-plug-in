#!/usr/bin/env python3

import murmannsurvey
import model
from headers import *

if __name__ == '__main__':
    murmannsurvey.get_csv(ADC_LIST_DEFAULT)
    data = model.read_input_data(ADC_LIST_DEFAULT)
    model.build_model(data, MODEL_DEFAULT, False)
