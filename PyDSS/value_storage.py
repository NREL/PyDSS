
import abc

import pandas as pd

from PyDSS.exceptions import InvalidParameter


class _ValueStorageBase(abc.ABC):

    DELIMITER = "__"

    @staticmethod
    def get_columns(df, name, options, **kwargs):
        """Return the column names in the dataframe that match name and kwargs.

        Parameters
        ----------
        df : pd.DataFrame
        name : str
        kwargs : **kwargs
            Filter with option values

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
            fields = col.split(_ValueStorageBase.DELIMITER)
            assert len(fields) == 1 + len(options), f"fields={fields} options={options}"
            _name = fields[0]
            if _name != name:
                continue
            match = True
            for key, val in kwargs.items():
                if fields[field_indices[key]] != val:
                    match = False
                    break
            if match:
                columns.append(column)

        if not columns:
            raise InvalidParameter(f"{name} does not exist in DataFrame")

        return columns


    @abc.abstractmethod
    def to_dataframe(self):
        """Convert the stored data to a DataFrame.

        Returns
        -------
        pd.DataFrame

        """

class   ValueByList(_ValueStorageBase):
    """"Stores a list of lists of numbers by an arbitrary suffix. This is a generic method to handle lists returned from
    a function call. An example would be returned values  "taps" function for transformer elements. The calss can be
    used for any methods that returns a list.
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
        self._name = name
        self._prop = prop
        self._labels = []
        self._data = {}

        assert (isinstance(values, list) and len(values) == len(label_suffixes)), \
            '"values" and "label_suffixes" should be lists of equal lengths'
        for val, lab_suf in zip(values , label_suffixes):
            label = prop + '__' + lab_suf
            self._data[label] = [val]
            self._labels.append(label)

    def _make_columns(self):
        return [
            self.DELIMITER.join((self._name, f"{x}")) for x in self._labels
        ]

    def __iter__(self):
        return self._data.__iter__()

    def __len__(self):
        return len(self._data)

    def append(self, other):
        """Append values from another instance of ValueByLabel"""
        for key in other:
            assert key in self._data
            for val in other.get(key):
                self._data[key].append(val)

    def get(self, key):
        """Return the list of data for key.

        Parameters
        ----------
        key : str

        Returns
        -------
        list

        """
        return self._data[key]

    @property
    def num_columns(self):
        return len(self._data)

    def to_dataframe(self):
        df = pd.DataFrame(self._data)
        df.columns = self._make_columns()
        return df

class ValueByNumber(_ValueStorageBase):
    """Stores a list of numbers for an element/property."""
    def __init__(self, name, prop, value):
        self._data = [value]
        self._name = name
        self._prop = prop

    def __iter__(self):
        return self._data.__iter__()

    def __len__(self):
        return len(self._data)

    def append(self, other):
        """Append values from another instance of ValueByNumber"""
        self._data += other

    @property
    @staticmethod
    def num_columns():
        return 1

    @staticmethod
    def _make_column(name, prop):
        return _ValueStorageBase.DELIMITER.join((name, prop))

    def to_dataframe(self):
        return pd.DataFrame(self._data, columns=[self._make_column(self._name, self._prop)])




class ValueByLabel(_ValueStorageBase):
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
        phs = {
            1: 'A',
            2: 'B',
            3: 'C',
            0: 'N',
        }

        self._name = name
        self._prop = prop
        self._labels = []
        self._data = {}

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
                    self._data[label] = [complex(x[0], x[1])]
                else:
                    label_mag = label + ' ' + units[0]
                    label_ang = label + ' ' + units[1]
                    self._labels.extend([label_mag, label_ang])
                    self._data[label_mag] = [x[0]]
                    self._data[label_ang] = [x[1]]

    @staticmethod
    def chunk_list(values, nLists):
        return  [values[i * nLists:(i + 1) * nLists] for i in range((len(values) + nLists - 1) // nLists)]

    def __iter__(self):
        return self._data.__iter__()

    def __len__(self):
        return len(self._data)

    def append(self, other):
        """Append values from another instance of ValueByLabel"""
        for key in other:
            assert key in self._data
            for val in other.get(key):
                self._data[key].append(val)

    def get(self, key):
        """Return the list of data for key.

        Parameters
        ----------
        key : str

        Returns
        -------
        list

        """
        return self._data[key]

    @property
    def num_columns(self):
        return len(self._data)

    def _make_columns(self):
        return [
            self.DELIMITER.join((self._name, f"{x}")) for x in self._labels
        ]

    def to_dataframe(self):
        df = pd.DataFrame(self._data)
        df.columns = self._make_columns()
        return df

def get_value_class(class_name):
    """Return the class with the given name."""
    if class_name == "ValueByNumber":
        cls = ValueByNumber
    elif class_name == "ValueByLabel":
        cls = ValueByLabel
    else:
        raise InvalidParameter(f"invalid class name={class_name}")

    return cls
