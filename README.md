## Accelergy ADC Plug-In
The Accelergy ADC Plug-In provides estimates for the area and energy of
Analog-Digital Converters (ADCs) for use in analog & mixed-signal accelerator
design space exploration.

Models are based on statistical analysis of published ADC performance data in
Boris Murmann's ADC Performance Survey [1]. The energy model is based on the
observation that the maximum efficiency of an ADC is bounded by the sampling
rate and the resolution [1], and the area model is based on regression
analysis. Estimations are optimistic; they answer the question "what is the
best possible ADC design for the given parameters?".

## Quick Install
Clone the repository and install the plug-in using pip:

```
git clone https://github.com/Accelergy-Project/accelergy-adc-plug-in.git
cd accelergy-adc-plug-in
pip install .
```

## Usage
### Accelergy Interface
ADCs take the following parameters:
- `adc_resolution`: the number of bits in the ADC
- `technology`: the technology node in nm
- `n_adcs`: the number of ADCs working together, in the case of alternating
  ADCs
- `throughput`: the aggregate throughput of the ADCs, in samples per second

ADCs support the following actions:
- `read` or `convert`: Convert a single value from analog to digital. Note: if
  there are multiple ADCs, this is a single sample from a single ADC.

### Exploring Tradeoffs
There are several tradeoffs available around ADC design:
- Lower-resolution ADCs are smaller and more energy-efficient.
- Using more ADCs in parallel allows for a lower frequency, but increases the
  area.
- Using fewer ADCs in parallel allows for a higher frequency. Up to a point,
  this will not increase the area or energy/area of the ADCs. However, at some
  this will result in an exponential increase in energy/area.
- Lower-resolution ADCs can run at higher frequencies before the exponential
  increase in energy/area occurs.

When the ADC plug-in runs, it will output a list of alternative design options.
Each will report a number of ADCs and frequency needed to achieve the desired
throughput, as well as the area and energy of the ADCs. You can then use this
information to make tradeoffs between ADC resolution, frequency, and number of
ADCs.

This is plug-in is the work of Tanner Andrulis & Ruicong Chen.

## Updating the ADC Model
The generated ADC model is based on the data in Boris Murmann's survey [1],
included in the submodule. This survey is updated periodically. The model can
be update to reflect the most recent data by running the following:


```bash
pip3 install sklearn
pip3 install pandas
pip3 install numpy
git submodule update --init --recursive --remote
python3 update_model.py
```

This is only necessary if more recent data is published. If the data here is
out of date, please open an issue or pull request.

## References
[1] B. Murmann, "ADC Performance Survey 1997-2023," [Online]. Available:
https://github.com/bmurmann/ADC-survey

## License
This work is licensed under the MIT license. See license.txt for details.
