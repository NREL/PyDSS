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
        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = PvObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.__BaseKV = float(PvObj.GetParameter2('kv'))
        self.__Srated = float(PvObj.GetParameter2('kVA'))
        self.__Prated = float(PvObj.GetParameter2('Pmpp'))
        self.__Qrated = float(PvObj.GetParameter2('kVARlimit'))
        #self.__Qrated = PvObj.SetParameter('%cutin', Settings['%Cutin'])
        #self.__Qrated = PvObj.SetParameter('%cutout',Settings['%Cutout'])

        self.__PFrated = Settings['PFlim']

        self.P_update = self.P_ControlDict[Settings['Pcontrol']]
        self.Q_update = self.Q_ControlDict[Settings['Qcontrol']]

        #self.ConnectedLoads = self.FindConnectedLoads()
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
            dP = self.P_update()
            dQ = self.Q_update()
            Error = dP + dQ
        else:
            Error = 0
        return Error

    def VWcontrol(self):
        uMinC = 0.99 #self.__Settings['uMinC']
        uMaxC = 1.0 #self.__Settings['uMaxC']
        Pmin  = 0    #self.__Settings['PminVW'] / 100
        self.__ControlledElm.SetParameter('pctPmpp', 100)
        self.__dssSolver.reSolve()

        uIn = self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[0]
        Ppv = abs(sum(self.__ControlledElm.GetVariable('Powers')[::2]))
        PpvPercentage = Ppv / self.__Prated * 100
        m = (1 - Pmin) / (uMinC - uMaxC)
        c = ((Pmin * uMinC) - uMaxC) / (uMinC - uMaxC)

        if uIn < uMinC:
            Pmax = 1
        elif uIn < uMaxC and uIn > uMinC:
            Pmax = m * uIn + c
        else:
            Pmax = Pmin

        PperOfPmmt = Pmax * Ppv / self.__Srated * 100
        print(Ppv, self.__Prated, PpvPercentage, PperOfPmmt)
        # Error = abs(Pmax - self.PmaxOld)
        # # if Error < 1E-4:
        # #     break
        # self.PmaxOld = Pmax
        self.__ControlledElm.SetParameter('pctPmpp',  30)
        self.__dssSolver.reSolve()

        return 0

    def CPFcontrol(self):
        PF = self.__Settings['pf']
        #self.__dssSolver.reSolve()

        self.__ControlledElm.SetParameter('irradiance', 1)
        self.__ControlledElm.SetParameter('pf', -PF)

        Error = PF + float(self.__ControlledElm.GetParameter2('pf'))

        Pirr = float(self.__ControlledElm.GetParameter2('irradiance'))
        self.__ControlledElm.SetParameter('irradiance', Pirr * (1 + Error * 3))
        self.__ControlledElm.SetParameter('pf', str(-PF))

        return Error

    def VPFcontrol(self):
        Pmin = self.__Settings['Pmin']
        Pmax = self.__Settings['Pmax']
        PFmin = self.__Settings['pfMin']
        PFmax = self.__Settings['pfMax']
        self.__dssSolver.reSolve()
        Pcalc = abs(sum(-(float(x)) for x in self.__ControlledElm.GetVariable('Powers')[0::2]) )/ self.__Srated
        if Pcalc > 0:
            if Pcalc < Pmin:
                PF = PFmax
            elif Pcalc > Pmax:
                PF = PFmin
            else:
                m = (PFmax - PFmin) / (Pmin - Pmax)
                c = (PFmin * Pmin - PFmax * Pmax) / (Pmin - Pmax)
                PF = Pcalc * m + c
        else:
            PF = PFmax

        self.__ControlledElm.SetParameter('irradiance', 1)
        self.__ControlledElm.SetParameter('pf', str(-PF))
        self.__dssSolver.reSolve()

        for i in range(10):
            Error =  PF + float(self.__ControlledElm.GetParameter2('pf'))
            if abs(Error) < 1E-4:
                break
            Pirr = float(self.__ControlledElm.GetParameter2('irradiance'))
            self.__ControlledElm.SetParameter('pf', str(-PF))
            self.__ControlledElm.SetParameter('irradiance', Pirr * (1 + Error*1.5))
            self.__dssSolver.reSolve()
        return 0

    def VVARcontrol(self):
        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        uDbMin = self.__Settings['uDbMin']
        uDbMax = self.__Settings['uDbMax']
        QlimPU = self.__Settings['QlimPU']
        PFlim = self.__Settings['PFlim']

        kVBase = self.__ControlledElm.sBus[0].GetVariable('kVBase')
        if 'bb_258064_1_5' in self.__Name.lower():
            k = 10
        else:
            k = 1

        for i in range(k):
            uIn = max([x/(self.__BaseKV*1000) for x in self.__ControlledElm.GetVariable('VoltagesMagAng')[::2]])

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
            # Pcalc = abs(Pcalc / self.__Srated)
            #
            # Qlim = abs((Pcalc / PFlim) * math.sin(math.acos(PFlim)))
            # if Qcalc < -Qlim:
            #     Qcalc = -Qlim
            # elif Qcalc > Qlim:
            #     Qcalc = Qlim

            if Pcalc > 0:
                PFout = math.cos(math.atan(Qcalc / Pcalc))
                self.__ControlledElm.SetParameter('pf', str(-PFout))
            elif Pcalc <= 0:
                PFout = 1
                self.__ControlledElm.SetParameter('pf', str(PFout))

            if uIn > 1.03:
                print('uIn - ', str(uIn) , '  Qcalc - ', str(Qcalc), '  Pcalc - ', str(Pcalc))
            if k == 10:
                self.__dssSolver.reSolve()

            Error = (Qcalc - self.Qvar)**2
            self.Qvar = Qcalc
        return Error

