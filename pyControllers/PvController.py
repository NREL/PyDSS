import matplotlib.pyplot as plt
import math

class PvController:
    doCurtail = 0
    uOld = 1
    pOld = 0
    PmaxOld = 0
    PloadOld = 0
    Qvar = 0
    Pvar = 0
    Load = None
    def __init__(self, PvObj, Settings, dssInstance, ElmObjectList, dssSolver):
        self.__ElmObjectList = ElmObjectList
        self.P_ControlDict = {
            'None'           : lambda: 0,
            'VW'             : self.VWcontrol,}

        self.Q_ControlDict = {
            'None'           : lambda: 0,
            'CPF'            : self.CPFcontrol,
            'VPF'            : self.VPFcontrol,
            'VVar'           : self.VVARcontrol, }

        self.__ControlledElm = PvObj
        Class, Name = self.__ControlledElm.GetInfo()
        self.__Name = 'pyCont_' + Class + '_' + Name
        if '_' in Name:
            self.Phase = Name.split('_')[1]
        else:
            self.Phase = None
        print(self.Phase)
        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = PvObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.__Srated = float(PvObj.GetParameter2('kVA'))
        self.__Prated = PvObj.SetParameter('Pmpp', self.__Srated)
        self.__Qrated = PvObj.SetParameter('kVARlimit', Settings['QlimPU'] * self.__Srated)
        self.__PFrated = Settings['PFlim']

        self.P_update = self.P_ControlDict[Settings['Pcontrol']]
        self.Q_update = self.Q_ControlDict[Settings['Qcontrol']]

        self.Fig, self.Axs = plt.subplots(2, 2, sharex=True)
        from itertools import chain
        self.Axs = list(chain.from_iterable(self.Axs))

        self.ConnectedLoads = self.FindConnectedLoads()
        print(self.ConnectedLoads)
        self.Sout = []
        self.Pout = []
        self.Qout = []
        self.uPCC = []
        self.PFout = []
        self.State = []
        return

    def FindConnectedLoads(self):
        Loads = []
        BusName = self.__ControlledElm.sBus[0].GetInfo()
        self.__dssInstance.Circuit.SetActiveClass('Load')
        Load = self.__dssInstance.ActiveClass.First()
        while Load:
            for Bus in self.__dssInstance.CktElement.BusNames():
                if BusName in Bus:
                    Loadname = self.__dssInstance.CktElement.Name()
                    if self.Phase in Bus.split('.')[1:]:
                        Loads.append([Loadname,Bus.split('.')[1:]])
            Load = self.__dssInstance.ActiveClass.Next()
        return Loads

    def GetLoadPowers(self):
        for LoadInfo in self.ConnectedLoads:
            LoadName = LoadInfo[0]
            self.__dssInstance.Circuit.SetActiveElement(LoadName)
            #print(LoadName , self.__dssInstance.CktElement.Powers())
        return float(self.__dssInstance.CktElement.Powers()[0])

    def Update(self, Time, Update):
        if Time >= 1:
            self.Time = Time
            self.doUpdate = Update

            if Update:
                self.UpdateResults()
            dP = self.P_update()
            dQ = self.Q_update()
            Error = dP + dQ
            if Time == 1439:
                for ax in self.Axs:
                    ax.clear()

                self.Axs[0].plot(self.Sout, label='S - [kVA]')
                self.Axs[0].plot(self.Pout, label='P - [kW]')
                self.Axs[0].plot(self.Qout, label='Q - [kVAR]')
                self.Axs[1].plot(self.uPCC, label='U - [p.u.]')
                self.Axs[2].plot(self.PFout, label='Power Factor')
                self.Axs[3].plot(self.State)
                self.Fig.subplots_adjust(hspace=0)

                for ax in self.Axs:
                    ax.grid()
                    ax.legend()
        else:
            Error = 0
        return Error

    def UpdateResults(self):
        nPhases = int(self.__ControlledElm.GetParameter2('phases'))
        P = sum(-float(x) for x in  self.__ControlledElm.GetVariable('Powers')[0:nPhases:2])
        Q = sum(-float(x) for x in self.__ControlledElm.GetVariable('Powers')[1:nPhases+1:2])
        uPCC = self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[0]
        self.Pout.append(P)
        self.Qout.append(Q)
        self.Sout.append((P**2 + Q**2)**(0.5))
        self.uPCC.append(uPCC)
        self.PFout.append(P/self.Sout[-1] if self.Sout[-1]>0 else 1)
        return

    def VWcontrol(self):
        uMinC = self.__Settings['uMinC']
        uMaxC = self.__Settings['uMaxC']
        busName = self.__ControlledElm.GetParameter2('bus1')
        self.__dssInstance.Circuit.SetActiveBus(busName)
        uIn = self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[0]
        nPhases = int(self.__ControlledElm.GetParameter2('phases'))
        Ppv = -float(self.__ControlledElm.GetVariable('Powers')[0])
        Pload = self.GetLoadPowers() / self.__Srated
        #dPload = (Pload - self.PloadOld)/ self.__Srated
        print(Pload)
        m = 1 / (uMinC - uMaxC)
        c = uMaxC / (uMaxC - uMinC)

        if uIn < uMinC:
            Pmax = 1
        elif uIn < uMaxC and uIn >= uMinC:
            self.doCurtail += 1
            Pmax = m * uIn + c
        else:
            Pmax = 0

        Pmax = Pmax + Pload if 0 < (Pmax + Pload) < 1 else 1 if (Pmax + Pload) > 1 else 0

        self.__ControlledElm.SetParameter('pctPmpp',  Pmax * 100)
        Error = abs(Pmax - self.PmaxOld)
        self.PmaxOld = Pmax
        if self.doUpdate:
            self.PloadOld = Pload
        return Error

    def CPFcontrol(self):
        PF = self.__Settings['pf']

        nPhases = int(self.__ControlledElm.GetParameter2('phases'))
        Pcalc = sum(-(float(x)) for x in self.__ControlledElm.GetVariable('Powers')[0:nPhases:2]) / self.__Srated
        Qcalc = Pcalc* math.tan(math.acos(PF))
        Scalc = (Pcalc ** 2 + Qcalc ** 2) ** (0.5)
        #print(Pcalc, Qcalc, Scalc)

        if Scalc > 1:
            Scaler = (1 - (Scalc - 1) / Scalc)
            Pcalc = Scaler
        else:
            Pcalc = 1

        self.__ControlledElm.SetParameter('irradiance', Pcalc)
        self.__ControlledElm.SetParameter('pf', -PF)
        print(PF, self.__ControlledElm.GetParameter2('PF'))


        Error = abs(Pcalc - self.Pvar)
        self.Pvar = Pcalc
        return Error

    def VPFcontrol(self):
        Pmin = self.__Settings['Pmin']
        Pmax = self.__Settings['Pmax']
        PFmin = self.__Settings['pfMin']
        PFmax = self.__Settings['pfMax']
        nPhases = int(self.__ControlledElm.GetParameter2('phases'))
        Pcalc = sum(-(float(x)) for x in self.__ControlledElm.GetVariable('Powers')[0:nPhases:2]) / self.__Srated

        Ppu = Pcalc / self.__Srated
        m1 = (PFmin + 1) / (Pmin - 0.5)
        c1 = (2 * Pmin + PFmin) / (1 - 2 * Pmin)
        c2 = (-2 * Pmax + PFmax) / (1 - 2 * Pmax)
        if Ppu < Pmin:
            PF = PFmin
        elif Ppu < 0.5 and Ppu >= Pmin:
            PF = m1 * Ppu + c1
        elif Ppu < Pmax and Ppu >= 0.5:
            PF = (m1 * Ppu + c2)
        else:
            PF = PFmax

        Qcalc = Pcalc * math.tan(math.acos(PF))
        Scalc = (Pcalc ** 2 + Qcalc ** 2) ** (0.5)
        #print(Pcalc, Qcalc, Scalc)
        if Scalc > 1:
            Scaler = (1 - (Scalc - 1) / Scalc)
            Pcalc = Scaler
        else:
            Pcalc = 1

        self.__ControlledElm.SetParameter('irradiance', Pcalc)
        self.__ControlledElm.SetParameter('pf', PF)
        Error = abs(Pcalc - self.Pvar)
        self.Pvar = Pcalc
        return 0

    def VVARcontrol(self):
        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        uDbMin = self.__Settings['uDbMin']
        uDbMax = self.__Settings['uDbMax']
        QlimPU = self.__Settings['QlimPU']
        PFlim = self.__Settings['PFlim']

        uIn = self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[0]

        m1 = QlimPU / (uMin - uDbMin)
        m2 = QlimPU / (uDbMax - uMax)
        c1 = QlimPU * uDbMin / (uDbMin - uMin)
        c2 = QlimPU * uDbMax / (uMax - uDbMax)

        Qcalc = 0
        if uIn <= uMin:
            Qcalc = QlimPU
        elif uIn <= uDbMin and uIn > uMin:
            Qcalc = uIn * m1 + c1
        elif uIn <= uDbMax and uIn > uDbMin:
            Qcalc = 0
        elif uIn <= uMax and uIn > uDbMax:
            Qcalc = uIn * m2 + c2
        elif uIn >= uMax:
            Qcalc = -QlimPU

        nPhases = int(self.__ControlledElm.GetParameter2('phases'))
        Pcalc = sum(-(float(x)) for x in self.__ControlledElm.GetVariable('Powers')[0:nPhases:2])
        Pcalc = Pcalc / self.__Srated

        Qlim = abs((Pcalc / PFlim) * math.sin(math.acos(PFlim)))
        if Qcalc < -Qlim:
            Qcalc = -Qlim
        elif Qcalc > Qlim:
            Qcalc = Qlim

        Scalc = (Pcalc ** 2 + Qcalc ** 2) ** (0.5)
        if Scalc > 1:
            Scaler = (1 - (Scalc - 1) / Scalc)
        else:
            Scaler = 1
        print(uIn)
        #print (Pcalc, Pnew, Pinv)
        #PFout  = math.cos(math.atan2(Qcalc,Pcalc))

        #self.__ControlledElm.SetParameter('irradiance', Pinv)
        self.__ControlledElm.SetParameter('kvar', self.__Settings['DampCoef']*Qcalc*self.__Srated)

        #self.__ControlledElm.SetParameter('pf', PFout)

        Error = abs(Qcalc-self.Qvar)
        self.Qvar = Qcalc
        return Error

