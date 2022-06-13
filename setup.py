from setuptools import setup
import os
from os import path


def readme():
    with open('README.md') as f:
        return f.read()


ALLOWED_FILETYPES = ['.py', '.yaml', '.csv', '.xls', '.txt']


def listdir(d=''):
    d = os.path.join('./', d)
    files = [os.path.join(d, f) for f in os.listdir(d)]
    files = [f for f in files if path.isfile(f)]
    return [f for f in files if any(a in f for a in ALLOWED_FILETYPES)]


setup(
      name='accelergy-analog-plug-in',
      version='0.1',
      description='An energy estimation plug-in for Accelergy framework for analog components',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
      ],
      keywords='accelerator hardware energy estimation analog adc',
      author='Tanner Andrulis',
      author_email='Andrulis@mit.edu',
      license='MIT',
      install_requires = ['PyYAML', 'numpy', 'pandas', 'regex', 'sklearn', 'xlrd'],
      python_requires = '>=3.8',
      data_files=[
                  ('share/accelergy/estimation_plug_ins/accelergy-analog-plug-in', listdir()),
                  ('share/accelergy/estimation_plug_ins/accelergy-analog-plug-in/adc_data', listdir('adc_data')),
                  ('share/accelergy/estimation_plug_ins/accelergy-analog-plug-in/adc_data/surveys', listdir('adc_data/surveys')),
                  ('share/accelergy/primitive_component_libs/', ['analog_components.lib.yaml'])
                  ],
      include_package_data = True,
      entry_points = {},
      zip_safe = False,
    )
