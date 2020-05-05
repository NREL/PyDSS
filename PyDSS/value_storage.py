
import abc
import re

import h5py
import numpy as np
import pandas as pd

from PyDSS.exceptions import InvalidParameter


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
        self._data = {}
        self._value_type = complex
        self._value = []

        assert (isinstance(values, list) and len(values) == len(label_suffixes)), \
            '"values" and "label_suffixes" should be lists of equal lengths'
        for val, lab_suf in zip(values , label_suffixes):
            label = prop + '__' + lab_suf
            self._data[label] = [val]
            self._labels.append(label)
            self._value.append(val)

    def make_columns(self):
        return [
            self.DELIMITER.join((self._name, f"{x}")) for x in self._labels
        ]


    @property
    def num_columns(self):
        return len(self._data)

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
        self._value = value

    @property
    def num_columns(self):
        return 1

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
            for v , x in zip(node, val):
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

    @property
    def value(self):
        return self._value

    @staticmethod
    def chunk_list(values, nLists):
        return  [values[i * nLists:(i + 1) * nLists] for i in range((len(values) + nLists - 1) // nLists)]

    @property
    def num_columns(self):
        return len(self._labels)

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
        complex: np.complex
    }

    def __init__(self, value, hdf_store, path, max_size):
        dtype = self._TYPE_MAPPING.get(value.value_type)
        assert dtype is not None
        scaleoffset = None
        if isinstance(dtype, np.float) or isinstance(dtype, np.complex):
            scaleoffset = 4
        elif isinstance(dtype, np.int):
            scaleoffset = 0
        self._dataset = DatasetWrapper(
            hdf_store,
            path,
            max_size,
            dtype,
            value.make_columns(),
            scaleoffset=scaleoffset
        )

    def append(self, value):
        """Append a value to the container.

        Parameters
        ----------
        value : ValueStorageBase

        """
        self._dataset.add_value(value.value)

    def max_num_bytes(self):
        """Return the maximum number of bytes the container could hold.

        Returns
        -------
        int

        """
        return self._dataset.max_num_bytes()


class DatasetWrapper:
    """Wrapper class around an HDF dataset."""
    def __init__(
            self, hdf_store, path, max_size, dtype, columns, chunk_size=32764,
            scaleoffset=None
        ):
        self._hdf_store = hdf_store
        self._chunk_size = min(chunk_size, max_size)
        self._num_columns = len(columns)
        self._max_size = max_size
        if self._num_columns == 1:
            shape = (self._chunk_size,)
            chunks = (self._chunk_size,)
        else:
            shape = (self._max_size, self._num_columns)
            chunks = (self._chunk_size, self._num_columns)

        self._dataset = self._hdf_store.create_dataset(
            name=path,
            shape=shape,
            chunks=chunks,
            dtype=dtype,
            compression="gzip",
            compression_opts=4,
            shuffle=True,
            scaleoffset=scaleoffset,
        )
        self._dataset.attrs["columns"] = columns
        self._dataset_index = 0

        self._buf = np.empty(chunks, dtype=dtype)
        self._buf_index = 0

    def add_value(self, value):
        """Add the value to the internal buffer, flushing when full."""
        self._buf[self._buf_index] = value
        self._buf_index += 1
        if self._buf_index == self._chunk_size:
            self.flush()

    def flush(self):
        """Flush the data in the temporary buffer to storage."""
        length = self._buf_index
        new_index = self._dataset_index + length
        self._dataset[self._dataset_index:new_index] = self._buf[0:length]
        self._buf_index = 0
        self._dataset_index = new_index

    def max_num_bytes(self):
        """Return the maximum number of bytes the container could hold.

        Returns
        -------
        int

        """
        return self._buf.itemsize * self._num_columns * self._max_size
