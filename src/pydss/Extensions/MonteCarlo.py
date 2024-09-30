from ast import literal_eval
import os

from loguru import logger
from scipy import stats
import numpy as np

from pydss.simulation_input_models import SimulationSettingsModel
from pydss.utils import utils

class MonteCarloSim:

    def __init__(self, settings: SimulationSettingsModel, dssPaths, dssObjects, dssObjectsByClass):
        self.__dssPaths = dssPaths
        self.__dssObjects = dssObjects
        self._settings = settings
        self.__dssObjectsByClass = dssObjectsByClass

        try:
            MCfile = os.path.join(self._settings.project.active_scenario, 'Monte_Carlo', 'MonteCarloSettings.toml')
            MCfilePath = os.path.join(self.__dssPaths['Import'], MCfile)

            logger.info('Reading monte carlo scenario settings file from ' + MCfilePath)
            self.__MCsettingsDict = utils.load_data(MCfilePath)
        except:
            logger.error('Failed to read Monte Carlo scenario generation file %s', MCfilePath)
            raise
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
                logger.warning(Properties['Class'] + ' class not present in object dictionary.')
        return


