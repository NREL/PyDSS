from ast import literal_eval
from scipy import stats
import pandas as pd
import numpy as np
import logging


class MonteCarloSim:

    def __init__(self, dss, run_command, SimulationSettings, dssPaths, dssObjects, dssObjectsByClass, dssSolver):
        LoggerTag = SimulationSettings['Active Project'] + '_' + SimulationSettings['Active Scenario']
        self.pyLogger = logging.getLogger(LoggerTag)
        self.__dssInstance = dss
        self.__dssPaths = dssPaths
        self.__dssSolver = dssSolver
        self.__dssObjects = dssObjects
        self.__dssCommand = run_command
        self.__Settings = SimulationSettings
        self.__dssObjectsByClass = dssObjectsByClass

        try:
            MCfile = self.__Settings['Active Scenario'] + '\\MonteCarloSettings\\MonteCarloSettings.xlsx'
            MCfilePath = self.__dssPaths['Import'] + '\\' + MCfile
            self.pyLogger.info('Reading monte carlo scenario settings file from ' + MCfilePath)
            MCsettings = pd.read_excel(MCfilePath,sheetname=0).T
            self.__MCsettingsDict = MCsettings.to_dict()
        except:
            self.pyLogger.warning('Monte Carlo scenario generation file not found')
            return
        return

    def Create_Scenario(self):
        for key, Properties in self.__MCsettingsDict.items():
            if Properties['Class'] in self.__dssObjectsByClass:
                Elements = self.__dssObjectsByClass[Properties['Class']]
                ElmNames = list(Elements.keys())
                if Properties['useWildCard']:
                    ElmNames = [x for x in ElmNames if Properties['Wildcard'] in x]
                NumElms = len(ElmNames)
                distParams = literal_eval(Properties['Parameters'])

                dist = getattr(stats, Properties['Distribution'].replace(' ', ''))
                if not Properties['isList']:
                    MCsamples = dist.rvs(*distParams, size=NumElms)
                    if Properties['isInteger']:
                        MCsamples = [int(round(x)) for x in MCsamples]
                    for ElmName, Value in zip(ElmNames,MCsamples):
                        Elements[ElmName].SetParameter(Properties['Property'], Value)
                else:
                    MCsamples = dist.rvs(*distParams, size=NumElms * Properties['ListLength'])
                    if Properties['isInteger']:
                        MCsamples = [int(round(x)) for x in MCsamples]
                    MCsamples = np.reshape(MCsamples, (NumElms, Properties['ListLength']))
                    for ElmName, Value in zip(ElmNames, MCsamples):
                        Value = str(Value).replace('\n', '').replace('\r', '').replace('[ ', '[').replace(' ]', ']')
                        Elements[ElmName].SetParameter(Properties['Property'], Value)
            else:
                self.pyLogger.warning(Properties['Class'] + ' class not present in object dictionary.')
        return


