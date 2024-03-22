# -*- coding: utf-8 -*-
# Standard libraries
import os

# Third party libraries
import pandas as pd
import h5py

class hdf5Writer:
    """ Class that handles writing simulation results to arrow
        files.
    """

    def __init__(self, log_dir, columnLength):
        """ Constructor """
        self.log_dir = log_dir
        self.store = h5py.File(os.path.join(log_dir, 'groups_dict.hdf5'), 'w')
        self.store_groups = {}
        self.store_datasets = {}
        self.row = {}
        self.columnLength = columnLength
        self.chunkRows = 24
        self.step = 0
        self.dfs = {}
        # Create arrow writer for each object type

    def write(self, fed_name, currenttime, powerflow_output, index):
        """
        Writes the status of BES assets at a particular timestep to an
            arrow file.

        :param fed_name: name of BES federate
        :param log_fields: list of objects to log
        :param currenttime: simulation timestep
        :param powerflow_output: Powerflow solver timestep output as a dict
        """

        # Iterate through each object type

        for obj_type in powerflow_output:
            Data = pd.DataFrame(powerflow_output[obj_type], index=[self.step])
            if obj_type not in self.row:
                self.row[obj_type] = 0
                self.store_groups[obj_type] = self.store.create_group(obj_type)
                self.store_datasets[obj_type] = {}
                for colName in powerflow_output[obj_type].keys():
                    self.store_datasets[obj_type][colName] = self.store_groups[obj_type].create_dataset(
                        colName,
                        shape=(self.columnLength, ),
                        maxshape=(None, ),
                        chunks=True,
                        compression="gzip",
                        compression_opts=4
                    )
            if obj_type not in self.dfs:
                self.dfs[obj_type] = Data
            else:
                if self.dfs[obj_type] is None:
                    self.dfs[obj_type] = Data
                else:
                    self.dfs[obj_type] = self.dfs[obj_type].append(Data, ignore_index=True)

            if self.step % self.chunkRows == self.chunkRows - 1:
                si = int(self.step / self.chunkRows) * self.chunkRows
                ei = si + self.chunkRows
                for colName in powerflow_output[obj_type].keys():
                    self.store_datasets[obj_type][colName][si:ei] = self.dfs[obj_type][colName]
                self.dfs[obj_type] = None
            # Add object status data to a DataFrame
        self.step += 1

    def __del__(self):
        self.store.flush()
        self.store.close()