## **Accelergy Analog Plugin V1**

The Accelergy Analog Plugin provides area and energy estimates for analog
components. V1 supports ADC modeling, but more devices will come in later
versions.

**Currently Supported Components**

- ADC

## Cloning this Repository

Option 1:
Clone this repository, then add the directory to your `accelergy_config.yaml` file. See the
README at https://github.com/Accelergy-Project/accelergy for information on
locating this file.

Option 2:
Navigate to your shared Accelergy plugin foolder and clone there.

```
cd /usr/local/share/accelergy/estimation_plug_ins
```

## Installation

Install requirements with:

```
pip install -r requirements.txt
```


To generate ADC estimations, an ADC model must be generated. This can be done
automatically by running the following:

```
python3 run.py -g
```


This command will generate a model using the packaged ADC list from Boris
Murmann's survey [1] last refreshed 11/16/2021.
The ``run.py`` script comes with many other
options to refresh the survey from the internet, adjust modeling parameters,
and even use your own ADC list in Excel or .csv formats. Use 
``python run.py -h`` to view available options.

## References

[1] B. Murmann, "ADC Performance Survey 1997-2021," [Online]. Available: http://web.stanford.edu/~murmann/adcsurvey.html

## License
This work is licensed under the MIT license. See license.txt for details.
