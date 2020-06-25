
from collections import defaultdict
import abc
import copy
import logging
import os

import h5py
import numpy as np
import pandas as pd
import opendssdirect as dss

from PyDSS.common import DataConversion, StoreValuesType
from PyDSS.exceptions import InvalidConfiguration, InvalidParameter
from PyDSS.storage_filters import STORAGE_TYPE_MAP, StorageFilterBase
from PyDSS.value_storage import ValueByNumber


logger = logging.getLogger(__name__)


class MetricBase(abc.ABC):
    """Base class for all metrics"""
    def __init__(self, prop, dss_objs, options):
        self._name = prop.name
        self._base_path = None
        self._hdf_store = None
        self._max_chunk_bytes = options["Exports"]["HDF Max Chunk Bytes"]
        self._num_steps = None
        self._properties = {}  # StoreValuesType to ExportListProperty
        self._dss_objs = dss_objs

        self.add_property(prop)

    def add_property(self, prop):
        """Add an instance of ExportListProperty for tracking."""
        existing = self._properties.get(prop.store_values_type)
        if existing is None:
            self._properties[prop.store_values_type] = prop
        elif prop != existing:
            raise InvalidParameter(f"{prop.store_values_type} is already stored")

    @abc.abstractmethod
    def append_values(self, time_step, store_nan=False):
        """Get the values for all elements at the current time step."""

    def close(self):
        """Perform any final writes to the container."""
        for container in self.iter_containers():
            if container is not None:
                container.close()

    def flush_data(self):
        """Flush any data in memory to storage."""
        for container in self.iter_containers():
            container.flush_data()

    def initialize_data_store(self, hdf_store, base_path, num_steps):
        """Initialize data store values."""
        self._hdf_store = hdf_store
        self._base_path = base_path
        self._num_steps = num_steps

    @staticmethod
    def is_circuit_wide():
        """Return True if this metric should be used once for a circuit."""
        return False

    @abc.abstractmethod
    def iter_containers(self):
        """Return an iterator over the StorageFilterBase containers."""

    def label(self):
        """Return a label for the metric.

        Returns
        -------
        str

        """
        prop = next(iter(self._properties.values()))
        return f"{prop.elem_class}.{prop.name}"

    def _make_elem_names(self):
        return [x.FullName for x in self._dss_objs]

    def make_storage_container(self, hdf_store, path, prop, num_steps, max_chunk_bytes, values, **kwargs):
        """Make a storage container.

        Returns
        -------
        StorageFilterBase

        """
        if prop.store_values_type not in STORAGE_TYPE_MAP:
            raise InvalidConfiguration(f"unsupported {prop.store_values_type}")
        elem_names = self._make_elem_names()
        cls = STORAGE_TYPE_MAP[prop.store_values_type]
        container = cls(hdf_store, path, prop, num_steps, max_chunk_bytes, values, elem_names, **kwargs)
        return container

    def max_num_bytes(self):
        """Return the maximum number of bytes the containers could hold.

        Returns
        -------
        int

        """
        total = 0
        for container in self.iter_containers():
            if container is not None:
                total += container.max_num_bytes()
        return total


class ChangeCountMetricBase(MetricBase, abc.ABC):
    """Base class for any metric that only tracks number of changes."""
    def __init__(self, prop, dss_objs, options):
        super().__init__(prop, dss_objs, options)
        self._container = None
        self._last_values = {x.FullName: None for x in dss_objs}
        self._change_counts = {x.FullName: 0 for x in dss_objs}

    def append_values(self, time_step, store_nan=False):
        pass

    def close(self):
        assert len(self._properties) == 1
        prop = next(iter(self._properties.values()))
        path = f"{self._base_path}/{prop.elem_class}/ElementProperties/{prop.storage_name}"
        values = [
            ValueByNumber(x, prop.name, y)
            for x, y in self._change_counts.items()
        ]
        # This class creates an instance of ValueContainer directly because
        # these metrics can only store one type, and so don't need an instance
        # of StorageFilterBase.
        self._container = StorageFilterBase.make_container(
            self._hdf_store,
            path,
            prop,
            self._num_steps,
            self._max_chunk_bytes,
            values,
            [x.FullName for x in self._dss_objs],
        )
        self._container.append(values)
        self._container.flush_data()

    def iter_containers(self):
        yield self._container


class MultiValueTypeMetricBase(MetricBase, abc.ABC):
    """Stores a property with multiple values of StoreValueType.

    For example, a user might want to store a moving average as well as the
    max of all instantaneous values.

    """
    def __init__(self, prop, dss_objs, options):
        super().__init__(prop, dss_objs, options)
        self._containers = {}  # StoreValuesType to StorageFilterBase

    @abc.abstractmethod
    def _get_value(self, dss_obj, time_step):
        """Get a value at the current time step."""

    def _initialize_containers(self, values):
        prop_name = None
        for prop in self._properties.values():
            if prop_name is None:
                prop_name = prop.name
            else:
                assert prop.name == prop_name, f"{prop.name} {prop_name}"
            if prop.data_conversion != DataConversion.NONE:
                vals = [
                    convert_data(x.FullName, prop_name, y, prop.data_conversion)
                    for x, y in zip(self._dss_objs, values)
                ]
            else:
                vals = values
            path = f"{self._base_path}/{prop.elem_class}/ElementProperties/{prop.storage_name}"
            self._containers[prop.store_values_type] = self.make_storage_container(
                self._hdf_store,
                path,
                prop,
                self._num_steps,
                self._max_chunk_bytes,
                vals,
            )

    def append_values(self, time_step, store_nan=False):
        values = [self._get_value(x, time_step) for x in self._dss_objs]

        if not self._containers:
            self._initialize_containers(values)

        if store_nan:
            for val in values:
                val.set_nan()

        for value_type, container in self._containers.items():
            prop = self._properties[value_type]
            if prop.data_conversion != DataConversion.NONE and not store_nan:
                vals = [
                    convert_data(x.FullName, prop.name, y, prop.data_conversion)
                    for x, y in zip(self._dss_objs, values)
                ]
            else:
                vals = values
            container.append_values(vals, time_step)

        return vals

    def iter_containers(self):
        return self._containers.values()


class OpenDssPropertyMetric(MultiValueTypeMetricBase):
    """Stores metrics for any OpenDSS element property."""

    def _get_value(self, dss_obj, _time_step):
        return dss_obj.UpdateValue(self._name)

    def append_values(self, time_step, store_nan=False):
        curr_data = {}
        values = super().append_values(time_step, store_nan=store_nan)
        for dss_obj, value in zip(self._dss_objs, values):
            if len(value.make_columns()) > 1:
                for column, val in zip(value.make_columns(), value.value):
                    curr_data[column] = val
            else:
                curr_data[value.make_columns()[0]] = value.value

        return curr_data


class LineLoadingPercent(MultiValueTypeMetricBase):
    """Calculates line loading percent at every time point."""
    def __init__(self, prop, dss_objs, options):
        super().__init__(prop, dss_objs, options)
        self._normal_amps = {}  # Name to normal_amps value

    def _get_value(self, dss_obj, _time_step):
        line = dss_obj
        normal_amps = self._normal_amps.get(line.Name)
        if normal_amps is None:
            normal_amps = line.GetValue("NormalAmps", convert=True).value
            self._normal_amps[line.Name] = normal_amps

        currents = line.UpdateValue("Currents").value
        current = max([abs(x) for x in currents])
        loading = current / normal_amps * 100
        return ValueByNumber(line.Name, "LineLoading", loading)


class TransformerLoadingPercent(MultiValueTypeMetricBase):
    """Calculates transformer loading percent at every time point."""
    def __init__(self, prop, dss_objs, options):
        super().__init__(prop, dss_objs, options)
        self._normal_amps = {}  # Name to normal_amps value

    def _get_value(self, dss_obj, _time_step):
        transformer = dss_obj
        normal_amps = self._normal_amps.get(transformer.Name)
        if normal_amps is None:
            normal_amps = transformer.GetValue("NormalAmps", convert=True).value
            self._normal_amps[transformer.Name] = normal_amps

        currents = transformer.UpdateValue("Currents").value
        current = max([abs(x) for x in currents])
        loading = current / normal_amps * 100
        return ValueByNumber(transformer.Name, "TransformerLoading", loading)


class SummedElementsOpenDssPropertyMetric(MetricBase):
    """Sums all elements' values for a given property at each time point."""
    def __init__(self, prop, dss_objs, options):
        super().__init__(prop, dss_objs, options)
        self._container = None
        self._data_conversion = prop.data_conversion

    def append_values(self, time_step, store_nan=False):
        if store_nan:
            return

        total = None
        for obj in self._dss_objs:
            value = obj.UpdateValue(self._name)
            if self._data_conversion != DataConversion.NONE:
                value = convert_data(
                    "Total",
                    next(iter(self._properties.values())).name,
                    value,
                    self._data_conversion,
                )
            if total is None:
                total = value
            else:
                total += value

        if self._container is None:
            assert len(self._properties) == 1
            prop = next(iter(self._properties.values()))
            assert prop.store_values_type in (StoreValuesType.ALL, StoreValuesType.SUM)
            total.set_name("Total")
            path = f"{self._base_path}/{prop.elem_class}/SummedElementProperties/{prop.storage_name}"
            self._container = self.make_storage_container(
                self._hdf_store,
                path,
                prop,
                self._num_steps,
                self._max_chunk_bytes,
                [total],
            )
        self._container.append_values([value], time_step)


    @staticmethod
    def is_circuit_wide():
        return True

    def iter_containers(self):
        yield self._container


class NodeVoltageMetric(MetricBase):
    """Stores metrics for node voltages."""
    def __init__(self, prop, dss_obj, options):
        super().__init__(prop, dss_obj, options)
        # Indices for node names are tied to indices for node voltages.
        self._node_names = None
        self._containers = {}
        self._voltages = None

    def _make_elem_names(self):
        return self._node_names

    def append_values(self, time_step, store_nan=False):
        voltages = dss.Circuit.AllBusMagPu()
        if not self._containers:
            # TODO: limit to objects that have been added
            self._node_names = dss.Circuit.AllNodeNames()
            self._voltages = [ValueByNumber(x, "Voltage", y) for x, y in zip(self._node_names, voltages)]
            for prop in self._properties.values():
                path = f"{self._base_path}/Nodes/ElementProperties/{prop.storage_name}"
                self._containers[prop.store_values_type] = self.make_storage_container(
                    self._hdf_store,
                    path,
                    prop,
                    self._num_steps,
                    self._max_chunk_bytes,
                    self._voltages,
                )
        else:
            for i in range(len(voltages)):
                self._voltages[i].set_value_from_raw(voltages[i])
        if store_nan:
            for i in range(len(voltages)):
                self._voltages[i].set_nan()
        for sv_type, prop in self._properties.items():
            self._containers[sv_type].append_values(self._voltages, time_step)

    @staticmethod
    def is_circuit_wide():
        return True

    def iter_containers(self):
        for sv_type in self._properties:
            if sv_type in self._containers:
                yield self._containers[sv_type]


class TrackCapacitorChangeCounts(ChangeCountMetricBase):
    """Store the number of changes for a capacitor."""

    def append_values(self, _time_step, store_nan=False):
        if store_nan:
            return

        for capacitor in self._dss_objs:
            self._update_counts(capacitor)

    def _update_counts(self, capacitor):
        dss.Capacitors.Name(capacitor.Name)
        if dss.CktElement.Name() != dss.Element.Name():
            raise InvalidParameter(
                f"Object is not a circuit element {capacitor.Name}"
            )
        states = dss.Capacitors.States()
        if states == -1:
            raise Exception(
                f"failed to get Capacitors.States() for {capacitor.Name}"
            )

        cur_value = sum(states)
        last_value = self._last_values[capacitor.FullName]
        if last_value is None and cur_value != last_value:
            logger.debug("%s changed state old=%s new=%s", capacitor.Name,
                         last_value, cur_value)
            self._change_counts[capacitor.FullName] += 1

        self._last_values[capacitor.FullName] = cur_value


class TrackRegControlTapNumberChanges(ChangeCountMetricBase):
    """Store the number of tap number changes for a RegControl."""

    def append_values(self, _time_step, store_nan=False):
        if store_nan:
            return

        for reg_control in self._dss_objs:
            self._update_counts(reg_control)

    def _update_counts(self, reg_control):
        dss.RegControls.Name(reg_control.Name)
        if reg_control.dss.CktElement.Name() != dss.Element.Name():
            raise InvalidParameter(
                f"Object is not a circuit element {reg_control.Name()}"
            )
        tap_number = dss.RegControls.TapNumber()
        last_value = self._last_values[reg_control.FullName]
        if last_value is not None:
            self._change_counts[reg_control.FullName] += abs(tap_number - last_value)
            logger.debug("%s changed count from %s to %s count=%s",
                         reg_control.Name, last_value, tap_number,
                         self._change_counts[reg_control.FullName])

        self._last_values[reg_control.FullName] = tap_number


class OpenDssExportMetric(MetricBase):
    def __init__(self, prop, dss_objs, options):
        super().__init__(prop, dss_objs, options)
        self._containers = {}
        self._sum_elements = prop.sum_elements
        if self._sum_elements:
            self._append_func = self._append_summed_values
        else:
            self._append_func = self._append_values
        self._check_output()

        # The OpenDSS file output upper-cases the name.
        # Make a mapping for fast matching and lookup.
        self._names = {}
        self._values =  []
        for i, dss_obj in enumerate(dss_objs):
            elem_type, name = dss_obj.FullName.split(".")
            self._names[f"{elem_type}.{name.upper()}"] = i
            if self._sum_elements and not self._values:
                self._values.append(ValueByNumber("Total", self.label(), 0.0))
                break
            self._values.append(ValueByNumber(dss_obj.FullName, self.label(), 0.0))

    def _run_command(self):
        cmd = f"{self.export_command()}"
        result = dss.utils.run_command(cmd)
        if not result:
            raise Exception(f"{cmd} failed")
        return result

    def append_values(self, time_step, store_nan=False):
        filename = self._run_command()
        if not self.parse_file(filename):
            return

        self._append_func(time_step, store_nan=store_nan)

    def _append_values(self, time_step, store_nan=False):
        if not self._containers:
            for prop in self._properties.values():
                if prop.window_sizes and prop.is_moving_average():
                    # This is somewhat ugly code to allow different
                    # sizes for different element types collected in the same
                    # OpenDSS report.
                    window_sizes = self._get_window_size_by_name_index(prop)
                else:
                    window_sizes = None
                path = f"{self._base_path}/{self.element_class()}/ElementProperties/{prop.storage_name}"
                self._containers[prop.store_values_type] = self.make_storage_container(
                    self._hdf_store,
                    path,
                    prop,
                    self._num_steps,
                    self._max_chunk_bytes,
                    self._values,
                    window_sizes=window_sizes
                )

        if store_nan:
            for i in range(len(self._values)):
                self._values[i].set_nan()

        for sv_type, prop in self._properties.items():
            self._containers[sv_type].append_values(self._values, time_step)

    def _append_summed_values(self, time_step, store_nan=False):
        if store_nan:
            return

        self._values[0].set_value(sum([x.value for x in self._values]))

        prop = next(iter(self._properties.values()))
        if not self._containers:
            if len(self._properties) > 1:
                raise InvalidConfiguration("summing elements only supports one Property")
            assert len(self._properties) == 1
            assert prop.store_values_type in (StoreValuesType.ALL, StoreValuesType.SUM)
            path = f"{self._base_path}/{prop.elem_class}/SummedElementProperties/{prop.storage_name}"
            self._containers[prop.store_values_type] = self.make_storage_container(
                self._hdf_store,
                path,
                prop,
                self._num_steps,
                self._max_chunk_bytes,
                self._values,
            )

        self._containers[prop.store_values_type].append_values(self._values, time_step)

    def _check_output(self):
        filename = self._run_command()
        df = pd.read_csv(filename)
        for index, val in self.expected_column_headers().items():
            if df.columns[index].strip() != val:
                raise Exception(
                    f"Unexpected format in export file file: {index} {val} {df.columns}"
                )

    @staticmethod
    def _get_name_from_line(fields):
        return fields[0].strip()[1:-1]

    def _get_window_size_by_name_index(self, prop):
        """Returns a list of window sizes per element name corresponding to self._names."""
        if not prop.opendss_classes:
            raise InvalidConfiguration(f"window_sizes requires opendss_classes: {prop.name}")

        window_sizes = [None] * len(self._names)
        for opendss_class, window_size in prop.window_sizes.items():
            if opendss_class not in prop.opendss_classes:
                raise InvalidConfiguration(
                    f"{opendss_class} is not defined in opendss_classes: {prop.name}"
                )

        # Note: names have singluar class names, such as Line.line1.
        # opendss_classes are plural, such as Lines
        mapping = {}
        for i, name in enumerate(self._names):
            opendss_class_singular = name.split(".")[0]
            size = mapping.get(opendss_class_singular)
            if size is None:
                for opendss_class in prop.opendss_classes:
                    if opendss_class.startswith(opendss_class_singular):
                        size = prop.window_sizes[opendss_class]
                        mapping[opendss_class_singular] = size
            if size is None:
                raise InvalidConfiguration(f"Failed to find window_size for {name}")
            window_sizes[i] = size

        return window_sizes

    @staticmethod
    @abc.abstractmethod
    def element_class():
        """Return the element class."""

    @staticmethod
    @abc.abstractmethod
    def expected_column_headers():
        """Return the expected column headers in the CSV file."""

    @staticmethod
    @abc.abstractmethod
    def export_command():
        """Return the command to run in OpenDSS."""

    @staticmethod
    @abc.abstractmethod
    def label():
        """Return the label to use in dataframe columns."""

    def iter_containers(self):
        yield self._containers.values()

    @staticmethod
    def is_circuit_wide():
        return True

    def iter_containers(self):
        for sv_type in self._properties:
            if sv_type in self._containers:
                yield self._containers[sv_type]

    @abc.abstractmethod
    def parse_file(self, filename):
        """Parse data in filename.

        Returns
        -------
        bool
            Returns False is there is no data to store.

        """


class ExportOverloadsMetric(OpenDssExportMetric):

    @staticmethod
    def element_class():
        return "CktElement"

    @staticmethod
    def expected_column_headers():
        return {0: "Element", 5: "%Normal"}

    @staticmethod
    def export_command():
        return "export overloads"

    @staticmethod
    def label():
        return "Overloads"

    def parse_file(self, filename):
        found_data = False
        with open(filename) as f_in:
            # Skip the header.
            next(f_in)
            for line in f_in:
                fields = line.split(",")
                name = self._get_name_from_line(fields)
                if name in self._names:
                    index = self._names[name]
                    val = float(fields[5].strip())
                    self._values[index].set_value_from_raw(val)
                    found_data = True

        return found_data


class ExportPowersMetric(OpenDssExportMetric):

    @staticmethod
    def element_class():
        return "CktElement"

    @staticmethod
    def export_command():
        return "export powers"

    @staticmethod
    def expected_column_headers():
        return {0: "Element", 1: "Terminal", 2: "P(kW)"}

    @staticmethod
    def label():
        return "Powers"

    def parse_file(self, filename):
        data = defaultdict(list)
        with open(filename) as f_in:
            # Skip the header.
            next(f_in)
            for line in f_in:
                fields = line.split(",")
                name = self._get_name_from_line(fields)
                if name in self._names:
                    #terminal = fields[1]
                    val = abs(float(fields[2].strip()))
                    data[name].append(val)

        if not data:
            return False

        for name, vals in data.items():
            index = self._names[name]
            # TODO DT: is sum correct?
            self._values[index].set_value_from_raw(sum(vals))

        return True


def convert_data(name, prop_name, value, conversion):
    if conversion == DataConversion.ABS:
        converted = copy.deepcopy(value)
        if isinstance(value.value, list):
            converted.set_value([abs(x) for x in value.value])
        else:
            converted.set_value(abs(value.value))
    elif conversion == DataConversion.SUM:
        converted = ValueByNumber(name, prop_name, sum(value.value))
    elif conversion == DataConversion.ABS_SUM:
        converted = ValueByNumber(name, prop_name, abs(sum(value.value)))
    else:
        converted = value

    return converted
