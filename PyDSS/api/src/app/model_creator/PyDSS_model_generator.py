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
            if phases != 2:
                ld = lineData[1].replace("Load.", "")
                MotorName = f"Load.motor_{ld}"
                kv = self.findPpty("kV", lineData, float)
                conn = self.findPpty("conn", lineData)
                kW = self.findPpty("kW", lineData, float)
                loadkW = (1 - MotorSize / 100.0) * kW
                MotorSize = MotorSize + random.random() * 0.2 * MotorSize
                motorkvar = 0.2 * MotorSize
                bus = self.findPpty("bus1", lineData)
                mdl = f"New {MotorName} conn={conn} bus1={bus} kV={kv} kW={MotorSize} kvar={motorkvar} Phases={phases} Vminpu=0.0 Vmaxpu=1.2 model=1\n"
                self.handleMotorFile.write(mdl)
                self.Motors[scenarioName][MotorName] = (motorkW, motorkvar)
            # else:
            #     self.handleMotorFile.write(line + "\n")
            #     loadkW = self.findPpty("kW", lineData, float)
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
            if pv_kva:
                self.handlePVsystemFile.write(mdl)
                self.PVsystems[scenarioName].append(PVname)
        return pv_kva

    def GenerateScenario(self, PV_penetration, PVsize, motor_load_penetration, MotorSize, FileTypes):
     
        for feeder in self.paths:
            scenarioName = feeder.split("\\")[-1]
            self.Motors[scenarioName] = {}
            self.PVsystems[scenarioName] = []
            new_load_file = os.path.join(feeder, FileTypes["new_loads"])
            print(new_load_file)
            load_file = os.path.join(feeder, FileTypes["load"])
            motor_file = os.path.join(feeder, FileTypes["motor"])
            PV_file = os.path.join(feeder, FileTypes["PVsystem"])
            self.handlenewLoadsFile = open(new_load_file, "w")
            print(new_load_file)
            self.handleMotorFile = open(motor_file, "w")
            self.handlePVsystemFile = open(PV_file, "w")
            totalLoad = 0
            totalGeneration = 0
            with open(load_file, 'r') as f:
                for line in f:
                    if random.random() < motor_load_penetration:
                        print("motor_load_penetration: ", motor_load_penetration)
                        Motors = self.createMotor(line, MotorSize, scenarioName)
                        
                        totalLoad += Motors
                    else:
                        self.handlenewLoadsFile.write(line)
                        
                    if random.random() < PV_penetration:
                        PVsystems = self.createPVsystem(line, PVsize, scenarioName)
                        totalGeneration += PVsystems
            self.handleMotorFile.flush()
            self.handleMotorFile.close()
            self.handlePVsystemFile.flush()
            self.handlePVsystemFile.close()
            self.handlenewLoadsFile.flush()
            self.handlenewLoadsFile.close()
            self.createMasterFile(feeder, FileTypes)
            if self.subpath:
                self.createMasterFile(self.subpath, FileTypes)

    def createMasterFile(self, feeder, FileTypes):
        masterFile = os.path.join(feeder, FileTypes["master"])
        newMasterFile = os.path.join(feeder, FileTypes["new_master"])

        f = open(masterFile, "r")
        contents = f.readlines()
        new_contents = []
        f.close()
        for i, line in enumerate(contents):
   
            if line.endswith('Loads.dss\n'):
                new_line = line.replace('Loads.dss', "Loads_new.dss")
                new_contents.append(new_line)
                new_line = line.replace('Loads.dss', FileTypes["motor"])
                new_contents.append(new_line)
                new_line = line.replace('Loads.dss', FileTypes["PVsystem"])
                new_contents.append(new_line)
            elif line.startswith('Set Voltagebases'):
                new_contents.append(line)
                new_contents.append('BatchEdit Fuse.. enabled = false\n')
            else:
                new_contents.append(line)
        # xContents = []
        # for i, line in enumerate(new_contents):
        #     if not ("Loads.dss" in line or "PVSystems.dss" in line):
        #         xContents.append(line)

        f = open(newMasterFile, "w")
        new_contents = "".join(new_contents)
        f.write(new_contents)
        f.close()



