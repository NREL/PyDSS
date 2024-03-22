from  pydss.pyControllers.pyControllerAbstract import ControllerAbstract
import math
import abc

class GenController(ControllerAbstract):
    """Implementation of smart control modes of modern inverter systems. Subclass of the :class:`pydss.pyControllers.pyControllerAbstract.ControllerAbstract` abstract class.

        :param PvObj: A :class:`pydss.dssElement.dssElement` object that wraps around an OpenDSS 'PVSystem' element
        :type FaultObj: class:`pydss.dssElement.dssElement`
        :param Settings: A dictionary that defines the settings for the PvController.
        :type Settings: dict
        :param dssInstance: An :class:`opendssdirect` instance
        :type dssInstance: :class:`opendssdirect`
        :param ElmObjectList: Dictionary of all dssElement, dssBus and dssCircuit objects
        :type ElmObjectList: dict
        :param dssSolver: An instance of one of the classed defined in :mod:`pydss.SolveMode`.
        :type dssSolver: :mod:`pydss.SolveMode`
        :raises: AssertionError if 'PvObj' is not a wrapped OpenDSS PVSystem element

    """

    def __init__(self, GenObj, Settings, dssInstance, ElmObjectList, dssSolver):
        """Constructor method
        """
        super(GenController, self).__init__(GenObj, Settings, dssInstance, ElmObjectList, dssSolver)
        self.TimeChange = False
        self.Time = (-1, 0)

        self.oldPcalc = 0
        self.oldQcalc = 0

        self.__vDisconnected = False
        self.__pDisconnected = False

        self.__ElmObjectList = ElmObjectList
        self.ControlDict = {
            'None'           : lambda: 0,
            'VVar'           : self.VVARcontrol,
        }

        self.__ControlledElm = GenObj
        self.ceClass, self.ceName = self.__ControlledElm.GetInfo()

        assert (self.ceClass.lower()=='generator'), 'GenController works only with an OpenDSS generator element'
        self.__Name = 'pyCont_' + self.ceClass + '_' +  self.ceName
        if '_' in  self.ceName:
            self.Phase =  self.ceName.split('_')[1]
        else:
            self.Phase = None
        self.__ElmObjectList = ElmObjectList
        self.__ControlledElm = GenObj
        self.__dssInstance = dssInstance
        self.__dssSolver = dssSolver
        self.__Settings = Settings

        self.__BaseKV = float(GenObj.GetParameter('kv'))
        self.__Srated = float(GenObj.GetParameter('kVA'))
        self.__Prated = float(GenObj.GetParameter('kW'))
        self.__Qrated = float(GenObj.GetParameter('maxkvar'))
        GenObj.SetParameter('minkvar', -self.__Qrated)

        if Settings['Model as PVsystem']:
            GenObj.SetParameter('model', 3)


        self.__dampCoef = Settings['DampCoef']

        self.__PFrated = Settings['PFlim']
        self.Pmppt = 100
        self.pf = 1

        self.update = [self.ControlDict[Settings['Control' + str(i)]] for i in [1, 2, 3]]
        self.QlimPU = min(self.__Qrated / self.__Srated, 1.0)
        return


    def Name(self):
        return self.__Name

    def ControlledElement(self):
        return "{}.{}".format(self.ceClass, self.ceName)

    def debugInfo(self):
        return [self.__Settings['Control{}'.format(i+1)] for i in range(3)]

    def Update(self, Priority, Time, Update):
        self.TimeChange = self.Time != (Priority, Time)
        self.Time = (Priority, Time)
        if not self.TimeChange:
            self.Itr += 1
        else:
            self.Itr = 0
        return self.update[Priority]()

    def VVARcontrol(self):
        """Volt / var control implementation
        """
        uMin = self.__Settings['uMin']
        uMax = self.__Settings['uMax']
        pfLim = self.__Settings['PFlim']
        uDbMin = self.__Settings['uDbMin']
        uDbMax = self.__Settings['uDbMax']
        Priority = self.__Settings['Priority']

        uIn = max(self.__ControlledElm.sBus[0].GetVariable('puVmagAngle')[::2])

        m1 = self.QlimPU / (uMin - uDbMin)
        m2 = self.QlimPU / (uDbMax - uMax)
        c1 = self.QlimPU * uDbMin / (uDbMin - uMin)
        c2 = self.QlimPU * uDbMax / (uMax - uDbMax)

        phases = int(self.__ControlledElm.GetParameter('phases'))
        S = self.__ControlledElm.GetVariable('Powers')[: 2*phases]
        Ppv = abs(sum(S[::2]))
        Pcalc = Ppv / self.__Srated
        Qpv = -sum(S[1::2])
        Qpv = Qpv / self.__Srated

        Qcalc = 0
        if uIn <= uMin:
            Qcalc = self.QlimPU
        elif uIn <= uDbMin and uIn > uMin:
            Qcalc = uIn * m1 + c1
        elif uIn <= uDbMax and uIn > uDbMin:
            Qcalc = 0
        elif uIn <= uMax and uIn > uDbMax:
            Qcalc = uIn * m2 + c2
        elif uIn >= uMax:
            Qcalc = -self.QlimPU

        # adding heavy ball term to improve convergence
        a = 0.7 + 0.5 * self.__dampCoef * (1 - self.Itr / self.__dssSolver.MaxIterations)
        b = 0.1 / self.__dampCoef
        Qcalc = Qpv + (Qcalc - Qpv) * a + (Qpv - self.oldQcalc) * b
        dQ = Qcalc - Qpv

        #Qcalc = Qpv + (Qcalc - Qpv)# + (Qpv - self.oldQcalc) * 0.1 / self.__dampCoef
        #dQ = Qcalc - Qpv

        Plim = 1
        if Priority == 'Var':
            Plim = (1 - Qcalc ** 2) ** 0.5
        elif Priority == 'Watt':
            Qlim = (1 - Ppv/self.__Prated ** 2) ** 0.5

        self.__ControlledElm.SetParameter('kW', self.__Prated * Plim)
        self.__ControlledElm.SetParameter('kvar', self.__Srated * Qcalc)
        return abs(dQ)
