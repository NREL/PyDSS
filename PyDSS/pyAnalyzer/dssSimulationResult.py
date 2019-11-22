import pandas as pd
import os

class ResultObject:

    def __init__(self, resultPath):
        #print(resultPath)
        self.__result_files = [x for x in list(os.walk(resultPath))[0][2] if x.endswith('.csv')]
        self.__result_dict = {}
        for result in self.__result_files:
            if result != 'event_log.csv':
                self.__result_dict[result.replace('.csv', '')] = pd.read_csv(os.path.join(resultPath, result), index_col=0)

        return

    def get_results(self):
        return self.__result_dict