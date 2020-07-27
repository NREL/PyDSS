from collections import namedtuple
import logging
import os
import tempfile

import h5py
import mock
import numpy as np
import pandas as pd

from PyDSS.dataset_buffer import DatasetBuffer
from PyDSS.export_list_reader import ExportListProperty
from PyDSS.metrics import ExportOverloadsMetric, OpenDssExportMetric
import PyDSS.metrics
from PyDSS.utils.utils import load_data


logger = logging.getLogger(__name__)

FakeObj = namedtuple("FakeObj", "FullName, Name")
OBJS = [
    FakeObj("Line.one", "one"),
    FakeObj("Line.two", "two"),
    FakeObj("Transformer.one", "one"),
    FakeObj("Transformer.two", "two"),
]
OPTIONS = load_data("PyDSS/defaults/simulation.toml")
STORE_FILENAME = os.path.join(tempfile.gettempdir(), "store.h5")
EXPORTED_OVERLINES_BASE_FILENAME = "tests/data/exported_overloads/FEEDER_EXP_OVERLOADS"
NUM_OVERLINES_FILES = 3
LINE_1_VALUES = [147.47, 148.53, 147.88]
LINE_2_VALUES = [147.34, 150.05, 149.73]
TRANSFORMER_1_VALUES = [178.2, 179.6, 178.4]
TRANSFORMER_2_VALUES = [175.7, 178.6, 177.1]


overloads_file_id = 1
def mock_run_command():
    filename = f"{EXPORTED_OVERLINES_BASE_FILENAME}{overloads_file_id}.CSV"
    return filename


@mock.patch("PyDSS.metrics.OpenDssExportMetric._run_command", side_effect=mock_run_command)
def test_export_overloads(mocked_func):
    data1 = {
        "property": "ExportOverloadsMetric",
        "store_values_type": "all",
        "opendss_elements": ["Lines", "Transformers"],
    }
    prop1 = ExportListProperty("CktElement", data1)
    data2 = {
        "property": "ExportOverloadsMetric",
        "store_values_type": "max",
        "opendss_elements": ["Lines", "Transformers"],
    }
    prop2 = ExportListProperty("CktElement", data2)
    num_time_steps = NUM_OVERLINES_FILES
    metric = ExportOverloadsMetric(prop1, OBJS, OPTIONS)
    metric.add_property(prop2)
    with h5py.File(STORE_FILENAME, mode="w", driver="core") as hdf_store:
        metric.initialize_data_store(hdf_store, "", num_time_steps)
        global overloads_file_id
        for i in range(num_time_steps):
            metric.append_values(i)
            overloads_file_id += 1
        metric.close()

        dataset1 = hdf_store["CktElement/ElementProperties/ExportOverloadsMetric"]
        assert dataset1.attrs["length"] == num_time_steps
        assert dataset1.attrs["type"] == "per_time_point"
        df = DatasetBuffer.to_dataframe(dataset1)
        assert isinstance(df, pd.DataFrame)
        assert [x for x in df["Line.one__Overloads"].values] == LINE_1_VALUES
        assert [x for x in df["Line.two__Overloads"].values] == LINE_2_VALUES
        assert [x for x in df["Transformer.one__Overloads"].values] == TRANSFORMER_1_VALUES
        assert [x for x in df["Transformer.two__Overloads"].values] == TRANSFORMER_2_VALUES

        dataset2 = hdf_store["CktElement/ElementProperties/ExportOverloadsMetricMax"]
        assert dataset2.attrs["length"] == 1
        assert dataset2.attrs["type"] == "value"
        assert dataset2[0][0] == max(LINE_1_VALUES)
        assert dataset2[0][1] == max(LINE_2_VALUES)
        assert dataset2[0][2] == max(TRANSFORMER_1_VALUES)
        assert dataset2[0][3] == max(TRANSFORMER_2_VALUES)
