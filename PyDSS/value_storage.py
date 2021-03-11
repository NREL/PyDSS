
import abc
import enum
import os
import re

import numpy as np

from PyDSS.dataset_buffer import DatasetBuffer
from PyDSS.exceptions import InvalidParameter, InvalidConfiguration


class DatasetPropertyType(enum.Enum):
    ELEMENT_PROPERTY = "elem_prop"  # data is stored at every time point
    FILTERED = "filtered"  # data is stored after being filtered
    NUMBER = "number"  # Only a single value is written
    TIMESTAMP = "timestamp"  # data are timestamps, tied to FILTERED


class ValueStorageBase(abc.ABC):

    DELIMITER = "__"

    def __init__(self):
        self._dataset = None

    @staticmethod
    def get_columns(df, name, options, **kwargs):
        """Return the column names in the dataframe that match name and kwargs.

        Parameters
        ----------
        df : pd.DataFrame
        name : str
        kwargs : **kwargs
            Filter on options. Option values can be strings or regular expressions.

        Returns
        -------
        list

        """
        field_indices = {option: i + 1 for i, option in enumerate(options)}
        columns = []
        for column in df.columns:
            col = column
            index = column.find(" [")
            if index != -1:
                col = column[:index]
            # [name, option1, option2, ...]
            fields = col.split(ValueStorageBase.DELIMITER)
            if options and kwargs:
                assert len(fields) == 1 + len(options), f"fields={fields} options={options}"
            _name = fields[0]
            if _name != name:
                continue
            match = True
            for key, val in kwargs.items():
                if isinstance(val, str):
                    if fields[field_indices[key]] != val:
                        match = False
                elif isinstance(val, re.Pattern):
                    if val.search(fields[field_indices[key]]) is None:
                        match = False
                elif val is None:
                    continue
                else:
                    raise InvalidParameter(f"unhandled option value '{val}'")
                if not match:
                    break
            if match:
                columns.append(column)

        if not columns:
            raise InvalidParameter(f"{name} does not exist in DataFrame")

        return columns

    @staticmethod
    def get_option_values(df, name):
        """Return the option values parsed from the column names.

        Parameters
        ----------
        df : pd.DataFrame
        name : str

        Returns
        -------
        list

        """
        values = []
        for column in df.columns:
            col = column
            index = column.find(" [")
            if index != -1:
                col = column[:index]
            # [name, option1, option2, ...]
            fields = col.split(ValueStorageBase.DELIMITER)
            _name = fields[0]
            if _name != name:
                continue
            values += fields[1:]

        if not values:
            raise InvalidParameter(f"{name} does not exist in DataFrame")

        return values

    @abc.abstractmethod
    def make_columns(self):
        """Return a list of column names

        Returns
        -------
        list

        """

    @property
    @abc.abstractmethod
    def num_columns(self):
        """Return the number of columns in the data.

        Returns
        -------
        int

        """

    @abc.abstractmethod
    def set_element_property(self, prop):
        """Set the element property name.

        Parameters
        ----------
        prop : str

        """

    @abc.abstractmethod
    def set_value(self, value):
        """Set the value.

        Parameters
        ----------
        value : list | float | complex

        """

    @property
    @abc.abstractmethod
    def value(self):
        """Return the value.

        Returns
        -------
        list | float | complex

        """

    @property
    @abc.abstractmethod
    def value_type(self):
        """Return the type of value being stored.

        Returns
        -------
        Type

        """


class ValueByList(ValueStorageBase):
    """"Stores a list of lists of numbers by an arbitrary suffix. This is a generic method to handle lists returned from
    a function call. An example would be returned values "taps" function for transformer elements. The class can be
    used for any methods that return a list.
    """
    def __init__(self, name, prop, values, label_suffixes):
        """Constructor for ValueByLabel

        Parameters
        ----------
        name : str
        prop : str
        label_prefix : str
            Text to use as a prefix for column labels. Ex: Phase
        labels : list
            list of str
        values : list
            Pairs of values that can be interpreted as complex numbers.

        """
        super().__init__()
        self._name = name
        self._prop = prop
        self._labels = []
        self._value_type = None
        self._value = []
        assert (isinstance(values, list) and len(values) == len(label_suffixes)), \
            '"values" and "label_suffixes" should be lists of equal lengths'
        for val, lab_suf in zip(values, label_suffixes):
            label = prop + self.DELIMITER + lab_suf
            self._labels.append(label)
            self._value.append(val)
            if self._value_type is None:
                self._value_type = type(val)

    def __iadd__(self, other):
        for i in range(len(self._value)):
            self._value[i] += other.value[i]
        return self

    def make_columns(self):
        return [
            self.DELIMITER.join((self._name, f"{x}")) for x in self._labels
        ]

    @property
    def num_columns(self):
        return len(self._labels)

    def set_element_property(self, prop):
        self._prop = prop

        # Update the property inside each label.
        for i, label in self._labels:
            fields = label.split(self.DELIMITER)
            assert len(fields) == 2
            fields[0] = prop
            self._labels[i] = self.DELIMITER.join(fields)

    def set_value(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    @property
    def value_type(self):
        return self._value_type


class ValueByNumber(ValueStorageBase):
    """Stores a list of numbers for an element/property."""
    def __init__(self, name, prop, value):
        super().__init__()
        assert not isinstance(value, list), str(value)
        self._name = name
        self._prop = prop
        self._value_type = type(value)
        if self._value_type == str:
            raise InvalidConfiguration(
                f"Data export feature does not support strings: name={name} prop={prop} value={value}"
            )
        self._value = value

    def __iadd__(self, other):
        self._value += other.value
        return self

    @property
    def num_columns(self):
        return 1

    def set_element_property(self, prop):
        self._prop = prop

    def set_value(self, value):
        self._value = value

    def make_columns(self):
        return [ValueStorageBase.DELIMITER.join((self._name, self._prop))]

    @property
    def value(self):
        return self._value

    @property
    def value_type(self):
        return self._value_type


class ValueByLabel(ValueStorageBase):
    """Stores a list of lists of numbers by an arbitrary label. Use this class when working with cktElement function
    calls like Currents, currentMagAng where every two consecutive values in the returned list are representing one
    quantity. The class differentiates between complex and mag / angle representation and stores the values appropriately
    """
    def __init__(self, name, prop, value, Nodes, is_complex, units):
        """Constructor for ValueByLabel

        Parameters
        ----------
        name : str
        prop : str
        label_prefix : str
            Text to use as a prefix for column labels. Ex: Phase
        labels : list
            list of str
        values : list
            Pairs of values that can be interpreted as complex numbers.

        """
        super().__init__()
        phs = {
            1: 'A',
            2: 'B',
            3: 'C',
            0: 'N',
        }

        self._name = name
        self._prop = prop
        self._labels = []
        self._value = []
        self._value_type = complex if is_complex else float

        n = 2
        m = int(len(value) / (len(Nodes)*n))
        value = self.chunk_list(value, n)
        value = self.chunk_list(value, m)

        # Chunk_list example
        # X = list(range(12)) , nList= 2
        # Y = chunk_list(X, nList) -> [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]]
        # Given element has 2 terminals m = 12 / (2*2) = 3
        # Z =  chunk_list(Y, m) - > [
        #                            [[0, 1], [2, 3], [4, 5]],  Terminal one complex pairs
        #                            [[6, 7], [8, 9], [10, 11]] Terminal two complex pairs
        #                            ]

        for i, node_val in enumerate(zip(Nodes, value)):
            node, val = node_val
            for v, x in zip(node, val):
                label = '{}{}'.format(phs[v], str(i+1))
                if is_complex:
                    label += " " + units[0]
                    self._labels.append(label)
                    self._value += [complex(x[0], x[1])]
                else:
                    # TODO: only generate labels once.
                    # Should be able to do that with an existing instance.
                    label_mag = label + self.DELIMITER + "mag" + ' ' + units[0]
                    label_ang = label + self.DELIMITER + "ang" + ' ' + units[1]
                    self._labels.extend([label_mag, label_ang])
                    self._value += [x[0], x[1]]

    def __iadd__(self, other):
        for i in range(len(self._value)):
            self._value[i] += other.value[i]
        return self

    @property
    def value(self):
        return self._value

    @staticmethod
    def chunk_list(values, nLists):
        return  [values[i * nLists:(i + 1) * nLists] for i in range((len(values) + nLists - 1) // nLists)]

    @property
    def num_columns(self):
        return len(self._labels)

    def set_element_property(self, prop):
        self._prop = prop

    def set_value(self, value):
        self._value = value

    def make_columns(self):
        return [
            self.DELIMITER.join((self._name, f"{x}")) for x in self._labels
        ]

    @property
    def value_type(self):
        return self._value_type


class ValueContainer:
    """Container for a sequence of instances of ValueStorageBase."""

    # These could potentially be reduced in bit lengths. Compression probably
    # makes that unnecessary.
    _TYPE_MAPPING = {
        float: np.float,
        int: np.int,
        complex: np.complex,
    }

    def __init__(self, value, hdf_store, path, max_size, dataset_property_type, max_chunk_bytes=None,
                 store_timestamp=False):
        group_name = os.path.dirname(path)
        basename = os.path.basename(path)
        try:
            if basename in hdf_store[group_name].keys():
                raise InvalidParameter(f"duplicate dataset name {basename}")
        except KeyError:
            # Don't bother checking each sub path.
            pass

        dtype = self._TYPE_MAPPING.get(value.value_type)
        assert dtype is not None
        scaleoffset = None
        if dtype == np.float:
            scaleoffset = 4
        elif dtype == np.int:
            scaleoffset = 0
        attributes = {"type": dataset_property_type.value}
        timestamp_path = None

        if store_timestamp:
            timestamp_path = self.timestamp_path(path)
            self._timestamps = DatasetBuffer(
                hdf_store,
                timestamp_path,
                max_size,
                np.float,
                ["Timestamp"],
                scaleoffset=scaleoffset,
                max_chunk_bytes=max_chunk_bytes,
                attributes={"type": DatasetPropertyType.TIMESTAMP.value},
            )
            attributes["timestamp_path"] = timestamp_path
        else:
            self._timestamps = None

        self._dataset = DatasetBuffer(
            hdf_store,
            path,
            max_size,
            dtype,
            value.make_columns(),
            scaleoffset=scaleoffset,
            max_chunk_bytes=max_chunk_bytes,
            attributes=attributes,
        )

    @staticmethod
    def timestamp_path(path):
        return path + "Timestamp"

    def append(self, value, timestamp=None):
        """Append a value to the container.

        Parameters
        ----------
        value : ValueStorageBase
        timestamp : float | None

        """
        self._dataset.write_value(value.value)
        if self._timestamps is not None:
            assert timestamp is not None
            self._timestamps.write_value(timestamp)

    def flush_data(self):
        """Flush any outstanding data to disk."""
        self._dataset.flush_data()
        if self._timestamps is not None:
            self._timestamps.flush_data()

    def max_num_bytes(self):
        """Return the maximum number of bytes the container could hold.

        Returns
        -------
        int

        """
        return self._dataset.max_num_bytes()


def get_dataset_property_type(dataset):
    """Return the property type of this dataset.

    Returns
    -------
    DatasetPropertyType

    """
    return DatasetPropertyType(dataset.attrs["type"])


def get_timestamp_path(dataset):
    """Return the path to the timestamps for this dataset.

    Returns
    -------
    pd.DatetimeIndex

    """
    return dataset.attrs["timestamp_path"]
