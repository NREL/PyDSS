"""Provides access to PyDSS result data."""

import abc
from collections import namedtuple
import os
import re

import pandas as pd

from PyDSS.element_options import ElementOptions
from PyDSS.exceptions import InvalidParameter
from PyDSS.pydss_project import PyDssProject
from PyDSS.ResultData import ElementValuesPerProperty, \
    ValuesByPropertyAcrossElements


class PyDssResults:
    """Interface to perform analysis on PyDSS output data."""
    def __init__(self, project_path):
        options = ElementOptions()
        self._project = PyDssProject.load_project(project_path)
        fs_intf = self._project.fs_interface
        self._scenarios = []
        filename = self._project.get_hdf_store_filename()
        self._hdf_store = pd.HDFStore(filename, "r")

        for name in self._project.list_scenario_names():
            metadata = self._project.read_scenario_export_metadata(name)
            if metadata["type"] == "ElementValuesPerProperty":
                scenario_result = ElementValuesPerPropertyResults(
                    name,
                    self._hdf_store,
                    fs_intf,
                    metadata,
                    options
                )
            elif metadata["type"] == "ValuesByPropertyAcrossElements":
                scenario_result = ValuesByPropertyAcrossElementsResults(
                    name,
                    self._hdf_store,
                    fs_intf,
                    metadata,
                    options
                )
            else:
                assert False, f"type={metadata['type']} is invalid"
            self._scenarios.append(scenario_result)

    def __del__(self):
        if self._hdf_store.is_open:
            self._hdf_store.close()

    @property
    def scenarios(self):
        """Return the PyDssScenarioResults instances for the project.

        Returns
        -------
        list
            list of PyDssScenarioResults

        """
        return self._scenarios


class PyDssScenarioResults(abc.ABC):
    """Contains results for one scenario."""
    def __init__(self, name, store, fs_intf, metadata, options):
        self._name = name
        self._hdf_store = store
        self._metadata = metadata
        self._options = options
        self._fs_intf = fs_intf

    @property
    def name(self):
        """Return the name of the scenario.

        Returns
        -------
        str

        """
        return self._name

    @abc.abstractmethod
    def export_data(self, path, fmt="csv", compress=False):
        """Export data to path.

        Parameters
        ----------
        path : str
            Output directory
        fmt : str
            Filer format type (csv, h5)
        compress : bool
            Compress data

        """

    @abc.abstractmethod
    def get_dataframe(self, element_class, prop, element_name, **kwargs):
        """Return the dataframe for an element.

        Parameters
        ----------
        element_class : str
        prop : str
        element_name : str
        kwargs : **kwargs
            Filter on options. Option values can be strings or regular expressions.

        Returns
        -------
        pd.DataFrame

        Raises
        ------
        InvalidParameter
            Raised if the element is not stored.

        """

    @abc.abstractmethod
    def get_full_dataframe(self, element_class, name_or_prop):
        """Return a dataframe containing all data.  The dataframe is copied.

        Parameters
        ----------
        element_class : str
        name_or_prop : str
            The element name or property, depending on
            ElementValuesPerPropertyResults vs
            ValuesByPropertyAcrossElementsResults

        Returns
        -------
        pd.DataFrame

        """

    @abc.abstractmethod
    def get_option_values(self, element_class, prop, element_name):
        """Return the option values for the element property.

        element_class : str
        prop : str
        element_name : str

        Returns
        -------
        list

        """

    @abc.abstractmethod
    def iterate_dataframes(self, element_class, name_or_prop, **kwargs):
        """Returns a generator over the dataframes by element name.

        Parameters
        ----------
        element_class : str
        name_or_prop : str
            The element name or property, depending on
            ElementValuesPerPropertyResults vs
            ValuesByPropertyAcrossElementsResults
        kwargs : **kwargs
            Filter on options. Option values can be strings or regular expressions.

        Returns
        -------
        tuple
            Tuple containing the name or property and a pd.DataFrame

        """

    @abc.abstractmethod
    def list_element_classes(self):
        """Return the element classes combinations stored in the results.

        Returns
        -------
        list

        """

    @abc.abstractmethod
    def list_element_names(self, element_class, prop):
        """Return the element names for a property stored in the results.

        Parameters
        ----------
        element_class : str
        prop : str

        Returns
        -------
        list

        Raises
        ------
        InvalidParameter
            Raised if the property is not stored.

        """

    @abc.abstractmethod
    def list_element_properties(self, element_class):
        """Return the properties stored in the results for a class.

        Parameters
        ----------
        element_class : str

        Returns
        -------
        list

        Raises
        ------
        InvalidParameter
            Raised if the element_class is not stored.

        """

    def list_element_property_options(self, element_class, prop):
        """List the possible options for the element class and property.

        Parameters
        ----------
        element_class : str
        prop : str

        Returns
        -------
        list

        """
        return self._options.list_options(element_class, prop)

    def list_element_info_files(self):
        """Return the files describing the OpenDSS element objects.

        Returns
        -------
        list
            list of filenames (str)

        """
        return self._metadata["element_info_files"]

    def read_element_info_file(self, filename):
        """Return the contents of file describing an OpenDSS element object.

        Parameters
        ----------
        filename : str
            full path to a file (returned by list_element_info_files) or
            an element class, like "Transformers"

        Returns
        -------
        pd.DataFrame

        """
        if "." not in filename:
            actual = None
            for _file in self.list_element_info_files():
                basename = os.path.splitext(os.path.basename(_file))[0]
                if basename.replace("Info", "") == filename:
                    actual = _file
            if actual is None:
                raise InvalidParameter(
                    f"element info file for {filename} is not stored"
                )
            filename = actual

        return self._fs_intf.read_csv(filename)

    def read_capacitor_changes(self):
        """Read the capacitor state changes from the OpenDSS event log.

        Returns
        -------
        dict
            Maps capacitor names to count of state changes.

        """
        text = self._fs_intf.read_file(self._metadata["event_log"])
        return _read_capacitor_changes(text)

    def read_event_log(self):
        """Returns the event log for the scenario.

        Returns
        -------
        list
            list of dictionaries (one dict for each row in the file)

        """
        text = self._fs_intf.read_file(self._metadata["event_log"])
        return _read_event_log(text)

    def _check_options(self, element_class, prop, **kwargs):
        """Checks that kwargs are valid and returns available option names."""
        for option in kwargs:
            if not self._options.is_option_valid(element_class, prop, option):
                raise InvalidParameter(
                    f"class={element_class} property={prop} option={option} is invalid"
                )

        return self._options.list_options(element_class, prop)

    def _read_file(self, path):
        self._fs_intf.read_file(path)


class ElementValuesPerPropertyResults(PyDssScenarioResults):
    """Result wrapper for ElementValuesPerProperty"""
    def __init__(self, name, hdf_store, fs_intf, metadata, options):
        super(ElementValuesPerPropertyResults, self).__init__(
            name, hdf_store, fs_intf, metadata, options
        )
        # FIXME
        # This workflow has not been updated to support the latest data format
        # changes. It can be fixed relatively easily if it is needed.
        assert False, "not supported"
        self._elements = {}

        for elem_class, elements in metadata["data"].items():
            self._elements[elem_class] = []
            for element in elements:
                obj = ElementValuesPerProperty.deserialize(element)
                self._elements[elem_class].append(obj)

    def export_data(self, path, fmt="csv", compress=False):
        assert False

    def get_dataframe(self, element_class, prop, element_name, **kwargs):
        options = self._check_options(element_class, prop, **kwargs)
        element = self._get_element(element_class, element_name)
        return element.get_dataframe(prop, options, **kwargs)

    def get_full_dataframe(self, element_class, name_or_prop):
        element = self._get_element(element_class, name_or_prop)
        return element.get_full_dataframe()

    def iterate_dataframes(self, element_class, name_or_prop, **kwargs):
        element = self._get_element(element_class, name_or_prop)
        for prop in element.properties:
            options = self._check_options(element_class, prop, **kwargs)
            yield element.iterate_dataframes(prop, options, **kwargs)

    def list_element_classes(self):
        return sorted(list(self._elements.keys()))

    def list_element_names(self, element_class, prop=None):
        return [x.name for x in self._elements.get(element_class)]

    def list_element_properties(self, element_class):
        elements = self._get_elements(element_class)
        assert elements
        properties = sorted(elements[0].properties)
        return properties

    def _get_element(self, element_class, element_name):
        for element in self._get_elements(element_class):
            if element.name == element_name:
                return element

        raise InvalidParameter(
            f"{element_class} / {element_name} is not stored"
        )

    def _get_elements(self, element_class):
        elements = self._elements.get(element_class)
        if elements is None:
            raise InvalidParameter(f"{element_class} is not stored")

        return elements


_ClassProperty = namedtuple("ClassProperty", "element_class, property")


class ValuesByPropertyAcrossElementsResults(PyDssScenarioResults):
    """Result wrapper for ValuesByPropertyAcrossElements"""
    def __init__(self, name, hdf_store, fs_intf, metadata, options):
        super(ValuesByPropertyAcrossElementsResults, self).__init__(
            name, hdf_store, fs_intf, metadata, options
        )
        self._property_aggregators = {}

        for element in metadata["data"]:
            obj = ValuesByPropertyAcrossElements.deserialize(hdf_store, element)
            key = _ClassProperty(obj.element_class, obj.prop)
            self._property_aggregators[key] = obj

    def export_data(self, path, fmt="csv", compress=False):
        for element_class in self.list_element_classes():
            for prop in self.list_element_properties(element_class):
                prop_agg = self._get_property_aggregator(element_class, prop)
                prop_agg.export_data(path, fmt, compress)

    def get_dataframe(self, element_class, prop, element_name, **kwargs):
        options = self._check_options(element_class, prop, **kwargs)
        prop_agg = self._get_property_aggregator(element_class, prop)
        return prop_agg.get_dataframe(element_name, options, **kwargs)

    def get_full_dataframe(self, element_class, name_or_prop):
        prop_agg = self._get_property_aggregator(element_class, name_or_prop)
        return prop_agg.get_full_dataframe()

    def get_option_values(self, element_class, prop, element_name):
        prop_agg = self._get_property_aggregator(element_class, prop)
        return prop_agg.get_option_values(element_name)

    def iterate_dataframes(self, element_class, name_or_prop, **kwargs):
        options = self._check_options(element_class, name_or_prop, **kwargs)
        prop_agg = self._get_property_aggregator(element_class, name_or_prop)
        return prop_agg.iterate_dataframes(options, **kwargs)

    def list_element_classes(self):
        classes = set()
        for key in self._property_aggregators:
            classes.add(key.element_class)
        elem_classes = list(classes)
        elem_classes.sort()
        return elem_classes

    def list_element_properties(self, element_class):
        properties = []
        for key in self._property_aggregators:
            if key.element_class == element_class:
                properties.append(key.property)

        if not properties:
            raise InvalidParameter(f"class={element_class} is not stored")

        properties.sort()
        return properties

    def list_element_names(self, element_class, prop):
        prop_agg = self._get_property_aggregator(element_class, prop)
        return prop_agg.element_names

    def _get_property_aggregator(self, element_class, prop):
        key = _ClassProperty(element_class, prop)
        prop_agg = self._property_aggregators.get(key)
        if prop_agg is None:
            raise InvalidParameter(
                f"class={element_class} / property={prop} is not stored"
            )

        return prop_agg


def _read_capacitor_changes(event_log_text):
    """Read the capacitor state changes from an OpenDSS event log.

    Parameters
    ----------
    event_log_text : str
        Text of event log

    Returns
    -------
    dict
        Maps capacitor names to count of state changes.

    """
    capacitor_changes = {}
    regex = re.compile(r"(Capacitor\.\w+)")

    data = _read_event_log(event_log_text)
    for row in data:
        match = regex.search(row["Element"])
        if match:
            name = match.group(1)
            if name not in capacitor_changes:
                capacitor_changes[name] = 0
            action = row["Action"].replace("*", "")
            if action in ("OPENED", "CLOSED", "STEP UP"):
                capacitor_changes[name] += 1

    return capacitor_changes


def _read_event_log(event_log_text):
    """Return OpenDSS event log information.

    Parameters
    ----------
    event_log_text : str
        Text of event log


    Returns
    -------
    list
        list of dictionaries (one dict for each row in the file)

    """
    data = []

    for line in event_log_text.split("\n"):
        if line == "":
            continue
        tokens = [x.strip() for x in line.split(",")]
        row = {}
        for token in tokens:
            name_and_value = [x.strip() for x in token.split("=")]
            name = name_and_value[0]
            value = name_and_value[1]
            row[name] = value
        data.append(row)

    return data
