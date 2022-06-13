from typing import Dict
from headers import *
from model import get_energy, get_area


class ADCRequest:
    def __init__(
            self,
            bits: float,  # Resolution (bits)
            tech: float,  # Tech node (nm)
            throughput: float = 0,  # ops/channel/second
            n_adc: int = 1,  # Number of ADCs. Fractions allowed
    ):
        self.bits = bits
        self.tech = tech
        self.throughput = throughput
        self.n_adc = n_adc

    def energy_per_op(self, model: Dict) -> float:
        """ Returns energy per operation in Joules. """
        design_params = {ENOB: self.bits, TECH: math.log(self.tech),
                         FREQ: math.log(self.throughput / self.n_adc)}
        e_per_op = get_energy(design_params, model, True, False)

        print('\tAlternative designs:')
        for n_adc in range(max(self.n_adc - 5, 1), self.n_adc + 5):
            f = self.throughput / n_adc
            design_params[FREQ] = math.log(f)
            try:
                e = get_energy(design_params, model, False, False)
                a = self.area(model, n_adc)
                l = '\tCHOSEN > ' if n_adc == self.n_adc else '\t         '
                print(f'{l}{n_adc:2f} ADCs running at {f:2E}Hz: '
                      f'{e*1e12:2E}pJ/op, {a/1e6:2E}mm^2')
            except AssertionError:
                pass
        print('')
        return e_per_op

    def area(self, model: Dict, n_adc_override=-1) -> float:
        """ Returns area in um^2. """
        n_adc = self.n_adc if n_adc_override == -1 else n_adc_override
        design_params = {ENOB: self.bits, TECH: math.log(self.tech),
                         FREQ: math.log(self.throughput / n_adc)}
        design_params[ENRG] = get_energy(design_params, model, False, False)
        return get_area(design_params, model) * n_adc
