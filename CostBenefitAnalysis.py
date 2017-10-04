import matplotlib.pyplot as plt
import pandas as pd
import os

class CBA:
    Time = 0
    CostActual = []
    CostForcast = []
    LMPforcast = []
    LMPactual = []
    CumalativeCostActual = []
    CumalativeCostForcast = []
    def __init__(self,Path, Filename):
        self.LMPsignals = pd.read_excel(os.path.join(Path, Filename), index_col=0)
        self.LMPsignals.columns = ['Forcast', 'Actual']

    def CalculateCost(self, pyObject = None):
        Hour = int(self.Time/ 60)

        self.LMPforcast.append(float(self.LMPsignals['Forcast'].loc[[Hour]]))
        self.LMPactual.append(float(self.LMPsignals['Actual'].loc[[Hour]]))
        BattMW = float(pyObject.GetParameter2('kw'))/1000
        self.CostActual.append(self.LMPactual[-1] * BattMW * 5/60)
        self.CumalativeCostActual.append(sum(self.CostActual))
        self.CostForcast.append(self.LMPforcast[-1] * BattMW * 5 / 60)
        self.CumalativeCostForcast.append(sum(self.CostForcast))
        self.Time += 1
        return

    def PlotLMPsignals(self):
        self.Fig, self.Axs = plt.subplots(2, 2, sharex=True)
        from itertools import chain
        self.Axs = list(chain.from_iterable(self.Axs))
        time = range(len(self.LMPforcast))
        self.Axs[0].plot(self.LMPactual)
        self.Axs[0].plot(self.LMPforcast)
        self.Axs[1].plot(self.CostActual)
        self.Axs[1].plot(self.CostForcast)
        self.Axs[2].plot(self.CumalativeCostActual)
        self.Axs[2].plot(self.CumalativeCostForcast)

        return