# Python program to calculate geographic
# coordinates of places using google
# geocoding API

# importing required modules
import random
import copy
import os


class ModelGenerator:
    def __init__(self, pydssProjectPath, ExportPath, isSubstation):
        self.basePath = pydssProjectPath
        if not os.path.exists(pydssProjectPath):
            raise Exception("Path to PyDSS project does not exist")
        if not os.path.exists(ExportPath):
            raise Exception("Export path does not exist. Provide a valid export path")
        path = os.path.join(pydssProjectPath, "DSSfiles")
        if isSubstation:
            self.paths = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
            self.subpath = path
        else:
            self.paths = [os.path.join(path, f) for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
            self.subpath = None

        self.Motors = {}
        self.PVsystems = {}

    def findPpty(self, ppty, LineData, castType=None):
        ppty = ppty + "="
        value = [x for x in LineData if ppty in x][0].replace(ppty, "")
        if castType:
            value = castType(value)
        return value

    def createMotor(self, line, MotorSize, scenarioName):
        line = line.replace("\n", "")
        lineData = line.split(" ")
        loadkW = 0
        motorkW = 0
        if len(lineData) > 1:
            phases = self.findPpty("Phases", lineData, int)
            if phases == 2:
                ld = lineData[1].replace("Load.", "")
                MotorName = f"Load.motor_{ld}"
                kv = self.findPpty("kV", lineData, float)
                motorkv = kv / 1.732 * 2
                conn = self.findPpty("conn", lineData)
                kW = self.findPpty("kW", lineData, float)
                loadkW = (1 - MotorSize / 100.0) * kW
                motorkW = MotorSize / 100.0 * kW
                kvar = self.findPpty("kvar", lineData, float)
                loadkvar = kvar - 0.2 * motorkW
                motorkvar = 0.2 * motorkW
                bus = self.findPpty("bus1", lineData)
                mdl = f"New {MotorName} conn={conn} bus1={bus} kV={kv} kW={motorkW} kvar={motorkvar} Phases=2 Vminpu=0.0 Vmaxpu=1.2 model=1\n"
                self.handleMotorFile.write(mdl)
                mdl = f"New {lineData[1]} conn={conn} bus1={bus} kV={kv} kW={loadkW} kvar={loadkvar} Phases=2 Vminpu=0.8 Vmaxpu=1.2 model=1\n"
                self.handleMotorFile.write(mdl)
                self.Motors[scenarioName][MotorName] = (motorkW, motorkvar)
            else:
                self.handleMotorFile.write(line + "\n")
                loadkW = self.findPpty("kW", lineData, float)
        return loadkW + motorkW

    def createPVsystem(self, line, PVsize, scenarioName):
        line = line.replace("\n", "")
        lineData = line.split(" ")
        pv_kva = 0
        if len(lineData) > 1:
            gen = lineData[1].replace("Load.", "")
            phases = self.findPpty("Phases", lineData, int)
            kv = self.findPpty("kV", lineData, float)
            conn = self.findPpty("conn", lineData)
            kW = self.findPpty("kW", lineData, float)
            kvar = self.findPpty("kvar", lineData, float)
            pv_kva = kW * PVsize[0]
            pv_kvar = kvar * PVsize[1]
            bus = self.findPpty("bus1", lineData)
            if phases == 2:
                kv = kv / 1.732 * 2
                phases = 1
            PVname = f"Generator.pv_{gen}"
            mdl = f"New {PVname} conn={conn} bus1={bus} kV={kv} model=7 kW={pv_kva} kvar={pv_kvar} Phases={phases}\n"
            self.handlePVsystemFile.write(mdl)
            self.PVsystems[scenarioName].append(PVname)
        return pv_kva

    def GenerateScenario(self, PV_penetration, PVsize, motor_load_penetration, MotorSize, FileTypes):
        for feeder in self.paths:
            scenarioName = feeder.split("\\")[-1]
            self.Motors[scenarioName] = {}
            self.PVsystems[scenarioName] = []
            load_file = os.path.join(feeder, FileTypes["load"])
            motor_file = os.path.join(feeder, FileTypes["motor"])
            PV_file = os.path.join(feeder, FileTypes["PVsystem"])
            self.handleMotorFile = open(motor_file, "w")
            self.handlePVsystemFile = open(PV_file, "w")
            totalLoad = 0
            totalGeneration = 0
            with open(load_file, 'r') as f:
                for line in f:
                    if random.random() < motor_load_penetration:
                        Motors = self.createMotor(line, MotorSize, scenarioName)
                        totalLoad += Motors
                    if random.random() < PV_penetration:
                        PVsystems = self.createPVsystem(line, PVsize, scenarioName)
                        totalGeneration += PVsystems
            self.handleMotorFile.flush()
            self.handleMotorFile.close()
            self.handlePVsystemFile.flush()
            self.handlePVsystemFile.close()
            self.createMasterFile(feeder, FileTypes)
            if self.subpath:
                self.createMasterFile(self.subpath, FileTypes)

    def createMasterFile(self, feeder, FileTypes):
        masterFile = os.path.join(feeder, FileTypes["master"])
        newMasterFile = os.path.join(feeder, FileTypes["new_master"])

        f = open(masterFile, "r")
        contents = f.readlines()
        new_contents = copy.copy(contents)
        f.close()
        for i, line in enumerate(contents):
            if line.endswith('Loads.dss\n'):
                new_line = line.replace('Loads.dss', FileTypes["motor"])
                new_contents.insert(i, new_line)
                new_line = line.replace('Loads.dss', FileTypes["PVsystem"])
                new_contents.insert(i+1, new_line)
            if line.startswith('Set Voltagebases'):
                new_contents.insert(i+2, 'BatchEdit Fuse.. enabled = false\n')

        xContents = []
        for i, line in enumerate(new_contents):
            if not ("Loads.dss" in line or "PVSystems.dss" in line):
                xContents.append(line)

        f = open(newMasterFile, "w")
        new_contents = "".join(xContents)
        f.write(new_contents)
        f.close()



