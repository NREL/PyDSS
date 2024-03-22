from pydss.pyControllers.pyControllerAbstract import ControllerAbstract
from math import *
import random

class ThermostaticLoad(ControllerAbstract):

    def __init__(self, LoadObj, Settings, dssInstance, ElmObjectList, dssSolver):
        super(ThermostaticLoad, self).__init__(LoadObj, Settings, dssInstance, ElmObjectList, dssSolver)

        self.TimeChange = False
        self.Time = (-1, 0)

        self.__ControlledElm = LoadObj
        self.dssSolver = dssSolver

        self.eClass, self.eName = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + self.eClass + '_' + self.eName
        self.Tmax = Settings["Tmax"]
        self.Tmin = Settings["Tmin"]
        self.T = random.random() * (self.Tmax - self.Tmin) + self.Tmin
        self.On = True if random.random() > 0.5 else False
        self.__ControlledElm.SetParameter("kw", Settings["kw"])
        self.Prated = LoadObj.GetParameter("kw")


        self.a = 1 / (Settings["R"] * Settings["C"])
        self.b = Settings["mu"] / Settings["C"]
        self.w = 0
        return

    @property
    def Name(self):
        return self.__Name

    def debugInfo(self):
        return

    @property
    def ControlledElement(self):
        return "{}.{}".format(self.eClass, self.eName)

    def Update(self, Priority, Time, UpdateResults):
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = (Priority, Time)
        if self.TimeChange:
            timePeriods = 24 * 60 * 60
            Tsec = self.dssSolver.GetOpenDSSTime() * 60 * 50
            Ta = sin(Tsec * 2 * pi * (1 / timePeriods)) * 10 + 30

            if self.On:
                self.dT = -self.a * (self.T - Ta) - self.b * self.Prated + self.w
            else:
                self.dT = -self.a * (self.T - Ta) + self.w

            self.T += self.dT

            if self.T > self.Tmax:
                self.On = True
                self.__ControlledElm.SetParameter("kw", self.Prated)
            elif self.T < self.Tmin:
                self.On = False
                self.__ControlledElm.SetParameter("kw", 0)
        return 0

    def __del__(self):
        self.f.close()
