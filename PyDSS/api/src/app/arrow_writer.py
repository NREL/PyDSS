# -*- coding: utf-8 -*-
# Standard libraries
import os

# Third party libraries
import pandas as pd
import pyarrow as pa


class ArrowWriter:
    """ Class that handles writing simulation results to arrow
        files.
    """

    def __init__(self, log_dir):
        """ Constructor """
        self.log_dir = log_dir

        # Create arrow writer for each object type
        self.arrow_writers = {}

    def write_asset_status(self, fed_name, currenttime, powerflow_output):
        """
        Writes the status of BES assets at a particular timestep to an
            arrow file.

        :param fed_name: name of BES federate
        :param log_fields: list of objects to log
        :param currenttime: simulation timestep
        :param powerflow_output: Powerflow solver timestep output as a dict
        """

        print("Writing to arrow file")

        # Iterate through each object type
        for obj_type in powerflow_output:
            # Add object status data to a DataFrame
            df = pd.DataFrame(data=powerflow_output[obj_type], index=[0])
            #print(df)
            # Add additional columns
            df["TimeStep"] = float(currenttime)
            df["Interconnect"] = fed_name

            try:
                # Create a record batch
                record_batch = pa.RecordBatch.from_pandas(df=df)
                arrow_file = os.path.join(self.log_dir,
                                          f"{obj_type.lower()}.arrow")

                # Create new writer object if one does not already exist for
                #   the powerflow object type
                if obj_type not in self.arrow_writers:
                    self.arrow_writers[obj_type] = pa.RecordBatchStreamWriter(
                        arrow_file, record_batch.schema)
                self.arrow_writers[obj_type].write_batch(record_batch)

            except Exception as ex:
                print(f"\n\tError writing to arrow file: {obj_type} > {ex}")