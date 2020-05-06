
import os
import tempfile

import h5py
import numpy as np
import pandas as pd

from PyDSS.dataset_buffer import DatasetBuffer


def test_dataset_buffer__compute_chunk_count():
    one_year_at_5_minutes = 60 / 5 * 24 * 365
    assert DatasetBuffer.compute_chunk_count(
        num_columns=4,
        max_size=96,
        dtype=np.float
    ) == 96
    assert DatasetBuffer.compute_chunk_count(
        num_columns=4,
        max_size=one_year_at_5_minutes,
        dtype=np.float
    ) == 1024
    assert DatasetBuffer.compute_chunk_count(
        num_columns=6,
        max_size=one_year_at_5_minutes,
        dtype=np.complex
    ) == 341


def test_dataset_buffer__max_num_bytes():
    filename = os.path.join(tempfile.gettempdir(), "store.h5")
    try:
        with h5py.File(filename, "w") as store:
            columns = ("1", "2", "3", "4")
            dataset = DatasetBuffer(store, "data", 100, np.float, columns)
            assert dataset.max_num_bytes() == 3200
    finally:
        if os.path.exists(filename):
            os.remove(filename)


def test_dataset_buffer__write_value():
    filename = os.path.join(tempfile.gettempdir(), "store.h5")
    try:
        with h5py.File(filename, "w") as store:
            columns = ("1", "2", "3", "4")
            max_size = 2000
            dataset = DatasetBuffer(store, "data", max_size, np.float, columns)
            assert dataset._chunk_size == 1024
            for i in range(max_size):
                data = np.ones(4)
                dataset.write_value(data)
            assert dataset._buf_index == 2000 - dataset._chunk_size
            dataset.flush_data()
            assert dataset._buf_index == 0

        with h5py.File(filename, "r") as store:
            data = store["data"][:]
            assert len(data) == max_size
            assert [x for x in store["data"].attrs["columns"]] == list(columns)
            for i in range(max_size):
                for j in range(4):
                    assert data[i][j] == 1.0

            df = DatasetBuffer.to_dataframe(store["data"])
            assert isinstance(df, pd.DataFrame)
            assert len(df) == max_size
            assert df.iloc[0, 0] == 1.0
    finally:
        if os.path.exists(filename):
            os.remove(filename)
