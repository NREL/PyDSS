
import math

from PyDSS.value_storage import ValueContainer, ValueByNumber


def calculate_line_loading_percent(line):
    normal_amps = line.GetValue("NormalAmps", convert=True).value
    currents = line.GetValue("Currents", convert=True).value
    current = max([math.sqrt(x.real**2 + x.imag**2) for x in currents])
    loading = current / normal_amps * 100
    return ValueByNumber(line.Name, "LineLoading", loading)


def calculate_transformer_loading_percent(transformer):
    normal_amps = transformer.GetValue("NormalAmps", convert=True).value
    currents = transformer.GetValue("Currents", convert=True).value
    current = max([math.sqrt(x.real**2 + x.imag**2) for x in currents])
    loading = current / normal_amps * 100
    return ValueByNumber(transformer.Name, "TransformerLoading", loading)
