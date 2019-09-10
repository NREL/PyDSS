import pandas as pd
import os

class dssResult:

    def __init__(self, resultPath):
        self.__result_files = [x for x in list(os.walk(os.path.join(resultPath)))[0][2] if x.endswith('.csv')]
        self.__result_dict = {}
        for result in self.__result_files:
            if result != 'event_log.csv':
                self.__result_dict[result.replace('.csv', '')] = pd.read_csv(os.path.join(resultPath, result), index_col=0)
                print(self.__result_dict[result.replace('.csv', '')])

        return

    def get_results_dict(self):
        return self.__result_dict