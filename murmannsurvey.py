
"""
This script downloads Boris Murmann's ADC survey and packages it into a .CSV
ADC list for user use.
"""


# B. Murmann, "ADC Performance Survey 1997-2021," [Online].
# Available: http://web.stanford.edu/~murmann/adcsurvey.html.

from urllib import request, error
import regex as re
import os
from typing import List
from datetime import datetime, timedelta
import math

import pandas as pd

from headers import *

MURMANN_URL = 'http://web.stanford.edu/~murmann/'
LINK_PAGE = 'adcsurvey.html'
XLS_PAGES = ['ISSCC', 'VLSI']


CURRENT_DIR = os.path.dirname(__file__)
SURVEY_DIR = os.path.join(CURRENT_DIR, 'adc_data/surveys')
SURVEY_NAME_FORMAT = '%Y_%m_%d-%H_%M_%S_%f'

TITLE_COLUMN = 'TITLE'
BIT_INFERENCE_COLUMNS = ['COMMENTS', 'TITLE', 'ABSTRACT']  # Where to bit info
BIT_INFERENCE_REGEX = r'(?:^|[^.\d])(\d+)[^\w\.]*b(?:it)?(?!\w)'
SNR_COLUMNS = ['SFDR [dB]', 'DR [dB]', 'SNDR_hf [dB]',	'SNR [dB]', '-THD [dB]']


def infer_bits(row: pd.DataFrame) -> float or None:
    """
    Finds a number of bits mentioned, or refers to design specifications if
    none present.
    :param row: Dataframe row with ADC info
    :return: Inferred voltage value
    """
    v = None
    for col in SNR_COLUMNS:
        if not row[col] or pd.isna(row[col]):
            continue
        f = (float(row[col]) - 10 * math.log(1.5, 10)) / (20 * math.log(2, 10))
        v = max(v, f) if v is not None else f
    return v


def fetch_xls() -> List:
    """ Downloads Murmann's ADC Survey from internet. Returns list of files
        storing any new downloads if successful.
    """
    # Parse excel links from Murmann's website
    try:
        print(f'Parsing {MURMANN_URL}{LINK_PAGE} for links to MS Excel files.')
        with request.urlopen(f'{MURMANN_URL}{LINK_PAGE}') as response:
            http = response.read().decode('ascii')
        xls_links = re.findall(r'href="([^"]*\.xls)"', http)
        if not xls_links:
            print(f'No link found! Please check page {MURMANN_URL}{LINK_PAGE} '
                  f' or change addresses in this file.')
            return []
    except error.HTTPError as e:
        print(f'Error! Failed to read adc_data from internet: {e}')
        return []

    # Fetch excel files using link
    downloaded = []
    for x in xls_links:
        try:
            print(f'Parsing .xls link: {MURMANN_URL}{x}')
            file = os.path.join(
                SURVEY_DIR,
                f'{datetime.now().strftime(SURVEY_NAME_FORMAT)}.xls')
            request.urlretrieve(f'{MURMANN_URL}{x}', file)
            downloaded.append(file)
        except (error.URLError, error.ContentTooShortError) as e:
            print(f'Error! Failed to read file from internet: {e}')

    return downloaded


def refresh_xls(interval: int) -> List:
    """ If current survey is >= interval days old, tries to redownload. """
    latest = None
    latest_str = None
    saved = os.listdir(SURVEY_DIR)
    for s in saved:
        if s[-4:] != '.xls':
            continue
        date = datetime.strptime(s[:-4], SURVEY_NAME_FORMAT)
        if latest:
            latest = max(date, latest)
        else:
            latest = date
            latest_str = s[:-4]

    if latest:
        print(f'Most recent survey found downloaded {latest}')
    else:
        print(f'No saved survey found.')

    if not latest or latest < datetime.now() - timedelta(days=interval):
        print('Downloading new survey.')
        return fetch_xls()

    else:
        return [os.path.join(f'{SURVEY_DIR}', f'{latest_str}.xls')]


def xls_to_csv(xls: str, outfile: str):
    """ Converts survey adc_data to a CSV file """
    isscc = pd.read_excel(xls, sheet_name='ISSCC')
    vsli = pd.read_excel(xls, sheet_name='VLSI')
    xls = pd.concat([isscc, vsli])

    csv = pd.DataFrame()
    xls[ENOB] = xls.apply(infer_bits, axis=1)
    numeric_cols = [
        'fs [Hz]', 'AREA [mm^2]', 'TECHNOLOGY', 'P [W]', ENOB, 'P/fsnyq [pJ]',
    ]
    for c in numeric_cols:
        xls = xls[pd.to_numeric(xls[c], errors='coerce').notnull()]
    csv[FREQ] = xls['fs [Hz]']
    csv[ENOB] = xls[ENOB]
    csv[TECH] = xls['TECHNOLOGY'] * 10 ** 3  # um >> nm
    csv[AREA] = xls['AREA [mm^2]'] * 10 ** 6  # mm^2 -> um^2
    csv[ENRG] = xls['P/fsnyq [pJ]']
    csv.reset_index(inplace=True, drop=True)
    if os.path.exists(outfile):
        os.remove(outfile)
    csv.to_csv(outfile)
