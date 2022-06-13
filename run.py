#!/usr/bin/env python3

from argparse import ArgumentParser
import murmannsurvey
import model
import sys
from headers import *

if __name__ == '__main__':
    parser = ArgumentParser(
        description='Accelergy Analog Plugin provides energy/area estimations '
                    'for a variety of analog components. Supported devices:'
                    '\tADC'
    )
    parser.add_argument(
        '-g', '--generate_model', action='store_true',
        help='Generates the model used by Accelergy area/energy estimation.')
    parser.add_argument(
        '-l', '--adc_list', type=str, default=ADC_LIST_DEFAULT,
        help='Path to a user-defined list of ADCs used in model generation. '
             'By default, adc_data/adc_list.csv (populated with Murmann\'s '
             'survey data) is used. If adding your own list, ensure it follows '
             'the format given in the adc_data/adc_list.csv file.'
             '.xls files are also accpeted if the file has one sheet and '
             'column names match adc_data/adc_list.csv column names.')
    parser.add_argument(
        '-d', '--download_survey', action='store_true',
        help='Download the most recent ADC survey from Boris Murmann\'s '
             'website. Script will not download if current download is <= 6 '
             'months old; use -df to force download.\n'
             'B. Murmann, "ADC Performance Survey 1997-2021," [Online].'
             'Available: http://web.stanford.edu/~murmann/adcsurvey.html')
    parser.add_argument(
        '-df', '--download_force', action='store_true',
        help='Force download the most recent ADC survey from Boris Murmann\'s '
             'website. Please use this responsibly, and remember the survey'
             'is updated for two conferences per year.\n'
             'B. Murmann, "ADC Performance Survey 1997-2021," [Online].'
             'Available: http://web.stanford.edu/~murmann/adcsurvey.html')

    args = parser.parse_args()

    if args.download_survey or args.download_force or args.generate_model:
        xls = murmannsurvey.refresh_xls(0 if args.download_force else 183)
        murmannsurvey.xls_to_csv(xls, args.adc_list)

    if args.generate_model:
        data = model.read_input_data(args.adc_list)
        model.build_model(data, MODEL_DEFAULT, False)

    if len(sys.argv) == 1:
        parser.print_help()
