from setuptools import setup
import os

def readme():
      with open('README.md') as f:
            return f.read()

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
      install_requires = ['PyYAML', 'numpy', 'pandas', 'regex', 'sklearn'],
      python_requires = '>=3.8',
      data_files=[
                  ('share/accelergy/estimation_plug_ins/accelergy-analog-plug-in', ['*.yaml', *.py])
                  ('share/accelergy/estimation_plug_ins/accelergy-analog-plug-in/adc_data', ['adc_data/*])
                  ('share/accelergy/estimation_plug_ins/accelergy-analog-plug-in/adc_data/surveys', ['adc_data/surveys*])
                  ('share/accelergy/estimation_plug_ins/accelergy-analog-plug-in/adc_data/surveys', ['adc_data/surveys*])
                  ('share/accelergy/primitive_component_libs/', ['analog_components.lib.yaml*])
                  ],
      include_package_data = True,
      entry_points = {},
      zip_safe = False,
    )
