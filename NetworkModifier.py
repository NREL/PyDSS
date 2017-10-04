import dssElement as dE

class Modifier():

    PV_defaultDict = {'phases':'1', 'kV':'2.2',  'irradiance':'1', 'PF':'1',
                      'daily':'m3pvmult', '%cutin':'0.0', '%cutout':'0.0'}

    Storge_defaultDict = {'bus' : '671', 'kV':'4.12', 'kWRated' : '2000', '%IdlingkW' : '0' ,
                          'phases':'3', '%EffCharge': '80', 'kWhRated'  : '8000', '%reserve': '0',
                          '%EffDischarge': '80', 'state': 'IDLE', '%stored' : '0'}

    DefaultDictSelector ={
        'PVSystem' : PV_defaultDict,
        'Storage'  : Storge_defaultDict,
     }

    def __init__(self, dss, run_command):
        self.__dssInstance = dss
        self.__dssCircuit = dss.Circuit
        self.__dssElement = dss.Element
        self.__dssBus = dss.Bus
        self.__dssClass = dss.ActiveClass
        self.__dssCommand = run_command

    def Add_Elements(self, Class, Properties, Add2dssObjects = False, dssObjects = None):
        DefaultDict  =  self.DefaultDictSelector[Class]
        ElmNames = []
        Values = []

        for key, ValueList in Properties.items():
            ElmNames.append(key)
            Values.append(ValueList)

        for i in range(len(Values[0])):
            for j in range(len(Values)):
                DefaultDict[ElmNames[j]] = Values[j][i]
            Obj = self.Add_Element(Class, Properties['bus'][i], DefaultDict)
            if Add2dssObjects is True:
                dssObjects[Class + '.' + Properties['bus'][i]] = Obj

    def Add_Element(self, Class, Name, Properties):
        Cmd = 'New ' + Class + '.' + Name
        for PptyName, PptyVal in Properties.items():
            if PptyVal is not None:
                tCMD = ' ' + PptyName + '=' + PptyVal
                Cmd += tCMD
        print('Added -> ' + Cmd)
        self.__dssCommand(Cmd)
        return dE.dssElement(self.__dssInstance)

    def Edit_Element(self, Class, Name, Properties):
        Cmd = 'Edit ' + Class + '.' + Name
        for PptyName, PptyVal in Properties.items():
            if PptyVal is not None:
                tCMD = ' ' + PptyName + '=' + PptyVal
                Cmd += tCMD
        self.__dssCommand(Cmd)


