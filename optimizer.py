import logging
from typing import Dict
from headers import *
from model import get_energy, get_area
import math
import logging

logger = logging.getLogger(__name__)


class ADCRequest:
    def __init__(
        self,
        bits: float,  # Resolution (bits)
        tech: float,  # Tech node (nm)
        throughput: float = 0,  # ops/channel/second
        n_adc: int = 1,  # Number of ADCs. Fractions allowed
        logger: logging.Logger = None,
    ):
        self.bits = bits
        self.tech = tech
        self.throughput = throughput
        self.n_adc = n_adc
        self.logger = logger
        assert self.bits >= 4, "Resolution must be >= 4 bits"

    def energy_per_op(self, model: Dict) -> float:
        """Returns energy per operation in Joules."""
        design_params = {
            ENOB: self.bits,
            TECH: math.log(self.tech),
            FREQ: math.log(self.throughput / self.n_adc),
        }
        e_per_op = get_energy(design_params, model, True)

        self.logger.info("\tAlternative designs:")
        for n_adc in range(max(self.n_adc - 5, 1), self.n_adc + 5):
            f = self.throughput / n_adc
            design_params[FREQ] = math.log(f)
            try:
                e = get_energy(design_params, model, True)
                a = self.area(model, n_adc)
                l = "\tCHOSEN > " if n_adc == self.n_adc else "\t         "
                self.logger.info(
                    f"{l}{n_adc:2f} ADCs running at {f:2E}Hz: "
                    f"{e:2E}pJ/op, {a/1e6:2E}mm^2"
                )
            except AssertionError:
                pass
        self.logger.info("")
        return e_per_op

    def area(self, model: Dict, n_adc_override=-1) -> float:
        """Returns area in um^2."""
        n_adc = self.n_adc if n_adc_override == -1 else n_adc_override
        design_params = {
            ENOB: self.bits,
            TECH: math.log(self.tech),
            FREQ: math.log(self.throughput / n_adc),
        }
        design_params[ENRG] = math.log(get_energy(design_params, model, True))
        return get_area(design_params, model) * n_adc


CACHED_MODEL = None


def quick_get_area(
    bits: float, tech: float, throughput: float, n_adc: int, energy=None
):
    """Returns area in um^2. For testing purposes."""
    global CACHED_MODEL
    if CACHED_MODEL is None:
        import accelergywrapper
        import yaml

        CACHED_MODEL = yaml.load(
            open(accelergywrapper.MODEL_FILE).read(), Loader=yaml.SafeLoader
        )
    design_params = {
        ENOB: bits,
        TECH: math.log(tech),
        FREQ: math.log(throughput / n_adc),
    }
    design_params[ENRG] = math.log(
        energy or get_energy(design_params, CACHED_MODEL, True)
    )
    return get_area(design_params, CACHED_MODEL) * n_adc


def quick_get_energy(
    bits: float, tech: float, throughput: float, n_adc: int, energy=None
):
    """Returns area in um^2. For testing purposes."""
    global CACHED_MODEL
    if CACHED_MODEL is None:
        import accelergywrapper
        import yaml

        CACHED_MODEL = yaml.load(
            open(accelergywrapper.MODEL_FILE).read(), Loader=yaml.SafeLoader
        )
    design_params = {
        ENOB: bits,
        TECH: math.log(tech),
        FREQ: math.log(throughput / n_adc),
    }
    return get_energy(design_params, CACHED_MODEL)
