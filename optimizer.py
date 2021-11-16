from typing import Tuple

import math
import yaml
from headers import *


class Model:
    """ Models a single ADC """
    def __init__(self, model_file: str):
        with open(model_file) as f:
            self._model_dict = yaml.load(f.read(), Loader=yaml.FullLoader)

        # Slope is design invariant; others need design params for calculation.
        self._tradeoff_slope = \
            self._model_dict[AREA_ENRG_TRADEOFF][AREA_ENRG_MODEL][AREA_COEFF]
        self._tradeoff_intercept = None
        self._min_area = None
        self._max_area = None
        self._min_energy = None
        self._max_energy = None
        self._bits = None
        self._tech = None
        self._freq = None

    def _get_area_offset(self) -> float:
        """ Calculates design-param-adjusted area offset """
        coeffs = self._model_dict[DESIGN_PARAM_MODEL][AREA]
        offset = \
            coeffs[ENOB] * self._bits \
            + coeffs[TECH] * self._tech \
            + coeffs[FREQ] * self._freq \
            + coeffs[INTERCEPT]
        return offset

    def _get_energy_offset(self) -> float:
        """ Calculates design-param-adjusted energy offset """
        coeffs = self._model_dict[DESIGN_PARAM_MODEL][ENRG]
        offset = \
            coeffs[ENOB] * self._bits \
            + coeffs[TECH] * self._tech \
            + coeffs[FREQ] * self._freq \
            + coeffs[INTERCEPT]
        return offset

    def set_design_params(self,
                          bits: float or None = None,
                          tech: float or None = None,
                          freq: float or None = None,
                          allow_extrapolation: bool = False):
        """ Sets internal model to use given design parameters """
        self._bits = bits if bits is not None else self._bits
        self._tech = math.log(tech) if tech is not None else self._tech
        self._freq = math.log(freq) if freq is not None else self._freq

        # Check that values are within allowed parameters
        for val, check, include in [
            (self._bits, ENOB, bits),
            (self._tech, TECH, tech),
            (self._freq, FREQ, freq)
        ]:
            if include is None:
                continue
            constraints = self._model_dict[CONSTRAINTS][check]
            assert allow_extrapolation or val >= constraints[MIN], \
                f'{val} below minimum {constraints[MIN]} for {check}.'
            assert allow_extrapolation or val <= constraints[MAX], \
                f'{val} above maximum {constraints[MAX]} for {check}.'

        if any(p is None for p in [self._bits, self._tech, self._freq]):
            return

        # Adjust min/max area/energy
        constraints = self._model_dict[AREA_ENRG_TRADEOFF][CONSTRAINTS]
        self._min_area = constraints[AREA][MIN] + self._get_area_offset()
        self._max_area = constraints[AREA][MAX] + self._get_area_offset()
        self._min_energy = constraints[ENRG][MIN] + self._get_energy_offset()
        self._max_energy = constraints[ENRG][MAX] + self._get_energy_offset()

        # Adjust tradeoff intercept
        icpt = self._model_dict[AREA_ENRG_TRADEOFF][AREA_ENRG_MODEL][INTERCEPT]
        self._tradeoff_intercept = \
            icpt + self._get_energy_offset() \
            - self._get_area_offset() * self._tradeoff_slope

    def design_minmax_area(self,
                           bits: float or None = None,
                           tech: float or None = None,
                           freq: float or None = None,
                           allow_extrapolation: bool = False
                           ) -> Tuple[float, float]:
        """ Returns log min/max area for given design parameters """
        self.set_design_params(bits, tech, freq, allow_extrapolation)
        return math.exp(self._min_area), math.exp(self._max_area)

    def pick_design(self,
                    area_budget: float or None = None,
                    energy_budget: float or None = None,
                    ) -> Tuple[float, float]:
        """
        Picks optimal design for given design parameters and returns
        (area, energy) tuple.
        """
        max_area, max_energy = self._max_area, self._max_energy
        if area_budget:
            area_budget = math.log(area_budget)
            max_area = min(max_area, area_budget)
        if energy_budget:
            energy_budget = math.log(energy_budget)
            max_energy = min(max_energy, energy_budget)

        # Assuming if min_area is set, the rest will be by set_design_params
        assert self._min_area is not None, \
            'Set design parameters before picking ADCs'

        # Calculate area
        area = min(max_area, max(area_budget, self._min_area))
        # Calculate energy
        energy = self._tradeoff_intercept + self._tradeoff_slope * area
        energy = min(max_energy, max(energy, self._min_energy))
        # Calculate area again in case the binding of energy changed it
        area = (energy - self._tradeoff_intercept) / self._tradeoff_slope

        assert (area < max_area or math.isclose(max_area, area)) and \
               (self._min_area < area or math.isclose(self._min_area, area)), \
               'Design can not be realized. Area and energy budgets too tight.'

        return math.exp(area), math.exp(energy)


class ADCRequest:
    def __init__(
            self,
            bits: float,  # Resolution (bits)
            tech: float,  # Tech node (nm)
            channel_count: float,  # Channel count
            energy_area_tradeoff: float,  # 0 for min area, 1 for min energy
            max_share_count: int = 0,  # max adc/channel or channel/adc
            adc_per_channel: int = 0,  # max adc/channel
            channel_per_adc: int = 0,  # max channel/adc
            latency: float = 0,  # Seconds
            throughput: float = 0,  # ops/channel/second
            area_budget: float or None = None,  # um^2 per channel
            energy_budget: float or None = None,  # pJ per channel per op
            allow_extrapolation: bool = False  # Whether to exceed model limits
    ):
        assert latency or throughput, 'Please provide a latency or ' \
                                      'throughput requirement for ADC ' \
                                      'optimization.'
        self.bits = bits
        self.tech = tech
        self.channel_count = channel_count
        self.energy_area_tradeoff = energy_area_tradeoff
        self.max_share_count = max_share_count
        self.adc_per_channel = adc_per_channel
        self.channel_per_adc = channel_per_adc
        self.latency = latency
        self.throughput = throughput
        self.area_budget = area_budget
        self.energy_budget = energy_budget
        self.allow_extrapolation = allow_extrapolation

        self.area_per_channnel = None
        self.energy_per_op = None
        self.adc_count = None

        assert sum(
            x == 0 for x in [max_share_count, adc_per_channel, channel_per_adc]
        ) == 2, 'Give nonzero values for exactly 1 of the following: ' \
                'max_share_count, adc_per_channel, channel_per_adc.'

    def optimize(self, model: Model):
        """
        Optimizes ADC model and sets area_per_channel, energy_per_op, and
        adc_count attributes.
        """
        self.adc_count = None
        self.energy_per_op = None
        self.area_per_channnel = None

        throughput = self.throughput
        if self.latency > 0:
            throughput = max(throughput, 1 / self.latency)
        model.set_design_params(
            bits=self.bits,
            tech=self.tech,
            allow_extrapolation=self.allow_extrapolation
        )
        # Get list of design points to try
        n_adc_to_try = []
        for share in range(1, self.max_share_count + 1):
            n_adc_to_try.append(self.channel_count * share)
            n_adc_to_try.append(math.ceil(self.channel_count / share))
        if self.adc_per_channel:
            n_adc_to_try.append(self.channel_count * self.adc_per_channel)
        if self.channel_per_adc:
            n_adc_to_try.append(self.channel_count * self.channel_per_adc)

        def freq(n_adc: int):
            if n_adc < self.channel_count:
                return throughput * math.ceil(self.channel_count / n_adc)
            return throughput / math.floor(n_adc / self.channel_count)

        # Find absolute area range possible
        min_area, max_area = math.inf, -math.inf
        for n in n_adc_to_try:
            try:
                lo, hi = model.design_minmax_area(freq=freq(n))
                min_area = min(min_area, lo * n)
                max_area = max(max_area, hi * n)
            except AssertionError:
                pass

        # Calculate target area
        assert not math.isinf(min_area), \
            'Could not generate ADC for design parameters. Please relax ' \
            'budgets or tech constraints.'
        target_area = math.exp(
            math.log(min_area) * (1 - self.energy_area_tradeoff) +
            math.log(max_area) * self.energy_area_tradeoff
        )

        # Find best design satisfying target area
        for n in list(set(n_adc_to_try)):
            try:
                model.set_design_params(freq=freq(n))
                area, energy = model.pick_design(
                    target_area / n, self.energy_budget)
                if self.energy_per_op is None or energy < self.energy_per_op:
                    self.area_per_channnel = area * n / self.channel_count
                    self.energy_per_op = energy
                    self.adc_count = n
            except AssertionError:
                pass