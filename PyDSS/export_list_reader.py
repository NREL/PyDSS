from collections import defaultdict, namedtuple
import enum
import os
import re

from PyDSS.pyContrReader import pyExportReader
from PyDSS.utils.simulation_utils import calculate_line_loading_percent, \
    calculate_transformer_loading_percent
from PyDSS.utils.utils import load_data
from PyDSS.exceptions import InvalidConfiguration, InvalidParameter
from PyDSS.value_storage import DatasetPropertyType


MinMax = namedtuple("MinMax", "min, max")


CUSTOM_FUNCTIONS = {
    "Lines.LoadingPercent": calculate_line_loading_percent,
    "Transformers.LoadingPercent": calculate_transformer_loading_percent,
}


class LimitsFilter(enum.Enum):
    INSIDE = "inside"
    OUTSIDE = "outside"


class StoreValuesType(enum.Enum):
    ALL = "all"
    SUM = "sum"


class ExportListProperty:
    def __init__(self, elem_class, prop, data):
        self.elem_class = elem_class
        self.name = prop
        self.publish = data.get("publish", False)
        self._limits = self._parse_limits(data)
        self._limits_filter = LimitsFilter(data.get("limits_filter", "outside"))
        self._store_values_type = StoreValuesType(data.get("store_values_type", "all"))
        self._names, self._are_names_regex = self._parse_names(data)
        custom_prop = f"{elem_class}.{prop}"
        self._custom_function = CUSTOM_FUNCTIONS.get(custom_prop)

    @staticmethod
    def _parse_limits(data):
        limits = data.get("limits")
        if limits is None:
            return None

        if not isinstance(limits, list) or len(limits) != 2:
            raise InvalidConfiguration(f"invalid limits format: {limits}")

        return MinMax(limits[0], limits[1])

    @staticmethod
    def _parse_names(data):
        names = data.get("names")
        name_regexes = data.get("name_regexes")

        if names and name_regexes:
            raise InvalidConfiguration(f"names and name_regexes cannot both be set")
        for obj in (names, name_regexes):
            if obj is None:
                continue
            if not isinstance(obj, list) or not isinstance(obj[0], str):
                raise InvalidConfiguration(f"invalid name format: {obj}")

        if names:
            return set(names), False
        if name_regexes:
            return [re.compile(r"{}".format(x)) for x in name_regexes], True

        return None, False

    def _is_inside_limits(self, value):
        """Return True if the value is between min and max, inclusive."""
        return value >= self._limits.min and value <= self._limits.max

    def _is_outside_limits(self, value):
        """Return True if the value is lower than min or greater than max."""
        return value < self._limits.min or value > self._limits.max

    def get_dataset_property_type(self):
        """Return the encoding to use for the dataset backing these values.

        Returns
        -------
        DatasetPropertyType

        """
        if self._limits is not None:
            return DatasetPropertyType.FILTERED
        if self._store_values_type == StoreValuesType.SUM:
            return DatasetPropertyType.SUM
        return DatasetPropertyType.ELEMENT_PROPERTY

    @property
    def custom_function(self):
        return self._custom_function

    @property
    def limits(self):
        """Return the limits for the export property.

        Returns
        -------
        MinMax

        """
        return self._limits

    def should_store_name(self, name):
        """Return True if name matches the input criteria."""
        if self._names is None:
            return True

        if self._are_names_regex:
            for regex in self._names:
                if regex.search(name):
                    return True
            return False

        return name in self._names

    def should_store_value(self, value):
        """Return True if the value meets the input criteria."""
        if self._limits is None:
            return True

        if self._limits_filter == LimitsFilter.OUTSIDE:
            return self._is_outside_limits(value)
        return self._is_inside_limits(value)

    def should_store_timestamp(self):
        """Return True if the timestamp should be stored with the value."""
        return self.limits is not None

    @property
    def store_values_type(self):
        return self._store_values_type

    def serialize(self):
        """Serialize object to a dictionary."""
        if self._are_names_regex:
            raise InvalidConfiguration("cannot serialize when names are regex")
        data = {
            "names": None if not self._names else names,
            "publish": self.publish,
            "store_values_type": self.store_values_type.value,
        }
        if self._limits is not None:
            data["limits"] = [self._limits.min, self._limits.max]
            data["limits_filter"] = self._limits_filter.value

        return data


class ExportListReader:
    def __init__(self, filename):
        self._elem_classes = defaultdict(dict)
        legacy_files = ("ExportMode-byClass.toml", "ExportMode-byElement.toml")
        if os.path.basename(filename) in legacy_files:
            parser = self._parse_legacy_file
        else:
            parser = self._parse_file

        for elem_class, prop, data in parser(filename):
            self._elem_classes[elem_class][prop] = ExportListProperty(
                elem_class, prop, data
            )

    @staticmethod
    def _parse_file(filename):
        data = load_data(filename)
        for elem_class, props in data.items():
            for prop, values in props.items():
                yield elem_class, prop, values

    @staticmethod
    def _parse_legacy_file(filename):
        reader = pyExportReader(filename)
        publications = {tuple(x.split()) for x in reader.publicationList}
        for elem_class, props in reader.pyControllers.items():
            for prop in props:
                publish = (elem_class, prop) in publications
                yield elem_class, prop, {"publish": publish}

    def get_element_property(self, elem_class, prop):
        if elem_class not in self._elem_classes:
            raise InvalidParameter(f"{elem_class} is not stored")
        if prop not in self._elem_classes[elem_class]:
            raise InvalidParameter(f"{prop} is not stored")
        return self._elem_classes[elem_class][prop]

    def iter_export_properties(self, elem_class=None):
        """Returns a generator over the ExportListProperty objects.

        Yields
        ------
        ExportListProperty

        """
        if elem_class is None:
            for props in self._elem_classes.values():
                for prop in props.values():
                    yield prop
        elif elem_class not in self._elem_classes:
            raise InvalidParameter(f"{elem_class} is not stored")
        else:
            for prop in self._elem_classes[elem_class].values():
                yield prop

    def list_element_classes(self):
        return sorted(list(self._elem_classes.keys()))

    def list_element_properties(self, elem_class):
        return sorted(list(self._elem_classes[elem_class].keys()))

    # This name needs to match the interface defined in pyExportReader.
    @property
    def publicationList(self):
        """Return the properties to be published to HELICS.

        Returns
        -------
        list
            Format: ["ElementClass Property"]

        """
        return [
            f"{x.elem_class} {x.name}" for x in self.iter_export_properties()
            if x.publish
        ]

    def serialize(self):
        """Serialize object to a dictionary."""
        data = defaultdict(dict)
        for elem_class, props in self._elem_classes.items():
            for prop in props:
                data[elem_class][prop] = self._elem_classes[elem_class][prop].serialize()

        return data
