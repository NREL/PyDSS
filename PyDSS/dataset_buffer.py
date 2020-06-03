"""Contains DatasetBuffer"""

import logging

import numpy as np
import pandas as pd


KiB = 1024
MiB = KiB * KiB
GiB = MiB * MiB

# The optimal number of chunks to store in memory will vary widely.
# The h5py docs recommend keeping chunk byte sizes between 10 KiB - 1 MiB.
# This attempts to support a higher-end PyDSS case. Might need to provide
# customization capabilities.
# Each element property will have one "chunk" of data in memory.
# Storing 50,000 element properties with a 32 KiB buffer in each of 36
# parallel processes would require 54 GiB of RAM.
DEFAULT_MAX_CHUNK_BYTES = 32 * KiB

logger = logging.getLogger(__name__)


class DatasetBuffer:
    """Provides a write buffer to an HDF dataset to increase performance.
    Users must call flush_data before the object goes out of scope to ensure
    that all data is flushed.

    """
    # TODO add support for context manager, though PyDSS wouldn't be able to
    # take advantage in its current implementation.


    def __init__(
            self, hdf_store, path, max_size, dtype, columns, scaleoffset=None,
            max_chunk_bytes=None, attributes=None
        ):
        if max_chunk_bytes is None:
            max_chunk_bytes = DEFAULT_MAX_CHUNK_BYTES
        self._buf_index = 0
        self._hdf_store = hdf_store
        self._max_size = max_size
        num_columns = len(columns)
        self._chunk_size = self.compute_chunk_count(
            num_columns,
            max_size,
            dtype,
            max_chunk_bytes,
        )
        if num_columns == 1:
            shape = (self._max_size,)
            chunks = (self._chunk_size,)
        else:
            shape = (self._max_size, num_columns)
            chunks = (self._chunk_size, num_columns)

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
        self._path = path
        self._buf = np.empty(chunks, dtype=dtype)

        if attributes is not None:
            for attr, val in attributes.items():
                self._dataset.attrs[attr] = val

    def __del__(self):
        assert self._buf_index == 0, \
            f"DatasetBuffer destructed with data in memory: {self._path}"

    def flush_data(self):
        """Flush the data in the temporary buffer to storage."""
        length = self._buf_index
        if length == 0:
            return

        new_index = self._dataset_index + length
        self._dataset[self._dataset_index:new_index] = self._buf[0:length]
        self._buf_index = 0
        self._dataset_index = new_index
        self._dataset.attrs["length"] = new_index

    def max_num_bytes(self):
        """Return the maximum number of bytes the container could hold.

        Returns
        -------
        int

        """
        size_row = self._buf.size * self._buf.itemsize / len(self._buf)
        return size_row * self._max_size

    def write_value(self, value):
        """Write the value to the internal buffer, flushing when full."""
        self._buf[self._buf_index] = value
        self._buf_index += 1
        if self._buf_index == self._chunk_size:
            self.flush_data()

    @staticmethod
    def compute_chunk_count(
            num_columns,
            max_size,
            dtype,
            max_chunk_bytes=DEFAULT_MAX_CHUNK_BYTES
        ):
        tmp = np.empty((1, num_columns), dtype=dtype)
        size_one_row = tmp.size * tmp.itemsize
        chunk_count = min(int(max_chunk_bytes / size_one_row), max_size)
        logger.debug("chunk_count=%s", chunk_count)
        return chunk_count

    @staticmethod
    def to_dataframe(dataset):
        """Create a pandas DataFrame from a dataset created with this class.

        Parameters
        ----------
        dataset : h5py.Dataset

        Returns
        -------
        pd.DataFrame

        """
        if "length" in dataset.attrs.keys():
            length = dataset.attrs["length"]
        else:
            # This can be removed once projects with the older format aren't
            # supported.
            length = len(dataset)
        return pd.DataFrame(dataset[:length], columns=dataset.attrs["columns"])

    @staticmethod
    def to_datetime(dataset):
        """Create a pandas DatetimeIndex from a dataset.

        Parameters
        ----------
        dataset : h5py.Dataset

        Returns
        -------
        pd.DatetimeIndex

        """
        length = dataset.attrs["length"]
        return pd.to_datetime(dataset[:length], unit="s")
