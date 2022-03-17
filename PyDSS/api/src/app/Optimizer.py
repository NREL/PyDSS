from scipy.optimize import differential_evolution
import opendssdirect as dss
from shutil import copyfile
from glob import glob
from math import pi
import pandas as pd
import helics as h
import numpy as np
import random
import time
import toml
import h5py
import os

cmd = dss.run_command

class Optimizer:
    def __init__(self, projectfolder, masterfile, newmasterfile):  
        self.fix_opendss_load_models(os.path.join(projectfolder, "DSSfiles"))
        self.dssfile = os.path.join(projectfolder, "DSSfiles", masterfile)
        self.newdssfile = os.path.join(projectfolder, "DSSfiles", newmasterfile)
    
    def Optimize(self, source_voltage, Pt, Qt):
            self.source_voltage = source_voltage
            self.Pt = Pt
            self.Qt = Qt
            self.target_pf  = Pt / (Pt**2 + Qt**2)**0.5
            
            cmd("clear")
            reply = cmd(f"compile {self.dssfile}")
            assert not reply, f"Error compiling the opendss model: {self.dssfile}"
            
            dss.Vsources.PU(source_voltage)
            reply = cmd(f"solve")
            P, Q = dss.Circuit.TotalPower()
            
            print(P, Q)
            self.P = abs(P)
            self.limits = 3 * self.P
            bounds = [(-self.limits, self.limits)]
            
            print("Target power factor: ", self.target_pf)
            print("Source voltage: ", source_voltage)
            print("Active power: ", self.P)
            print("Rective power limits: ", self.limits)
            
            
            result = differential_evolution(self.cost_function, bounds, maxiter=10, popsize=20)
            Qcalc = result.x[0]
            err = result.fun

            Scalc = (self.P ** 2 + Qcalc ** 2) ** 0.5
            PFcalc = abs(P / Scalc)

            self.update_master_file(self.dssfile, PFcalc)
            
            
            cmd("clear")
            reply = cmd(f"compile {self.dssfile}")
            assert not reply, f"Error compiling the opendss model: {self.dssfile}"
            reply = cmd(f"solve")
            P, Q  = dss.Circuit.TotalPower()
            pmult = Pt / P
            qmult = Qt / Q
            return pmult, qmult
    
    def fix_opendss_load_models(self, basepath):
        EXT = "*.dss"
        all_dss_files = [file
                 for path, subdir, files in os.walk(basepath)
                 for file in glob(os.path.join(path, EXT))]


        for file in all_dss_files:
            if "Loads_new.dss" in file:
                print(file)
                lines = open(file, "r").readlines()
                lines_seen = []
                for line in lines:
                    if line.startswith("New Load."):
                        slices = line.split(" ")
                        for j, s in enumerate(slices):
                            if "kw=" in slices[j].lower():
                                slices[j] = slices[j].lower().replace("kw=", "kva=")
                            elif "kvar=" in slices[j].lower():
                                slices[j] = "pf=1.0"

                        L = " ".join(slices)
                        lines_seen.append(L)
                if lines_seen:
                    f = open(file, "w")
                    f.writelines(lines_seen)
                    f.close()
    
    def update_master_file(self, path, pf):
        edit_line = f"BatchEdit Load.load_* pf={pf}\n"
        lines = open(path, "r").readlines()
        for i, line in enumerate(lines):
            if "batchedit load.load_*" in line.lower():
                lines[i] = edit_line
                break
            elif "solve" in line.lower():
                lines.insert(i, edit_line)
                break

        edit_line = f"vsource.source.pu={self.source_voltage}\n"
        for i, line in enumerate(lines):
            if line.lower().startswith("vsource.source.pu="):
                lines[i] = edit_line
                break
            elif "solve" in line.lower():
                lines.insert(i, edit_line)
                break
        
        open(path, "w").writelines(lines)
        return
    
    
    def update_load_pf(self, pf):
        load = dss.Loads.First()
        while load: 
            if dss.Loads.Name().startswith("load_"):
                kw = dss.Loads.kW()
                S = kw / pf
                kvar = (S**2 - kw**2)**0.5
                dss.Loads.kvar(kvar)
            load = dss.Loads.Next()
    
    def cost_function(self, Q):
        S1 = ((self.P) ** 2 + (Q[0]) ** 2) ** 0.5
        pf = self.P / S1

        #self.update_load_pf(pf)
        reply = cmd(f"BatchEdit Load.load_* pf={pf}")
        assert not reply, f"Error batch editing load power factor"
        dss.Solution.SolveNoControl()
        Pc, Qc = dss.Circuit.TotalPower()
        Pc = -Pc / 1000.0
        Qc = -Qc / 1000.0
        Sc = (Pc**2 + Qc**2) ** 0.5

        if Sc==0:
            PFc = 1
        else:
            PFc = -abs(Pc/Sc) if Qc < 0 else abs(Pc/Sc)

        err = (PFc - self.target_pf)**2
        print("Optimization error: ", err)
        return err

if __name__ == ':_main__':  
    O = Optimizer(
        r"C:\Users\alatif\Documents\GitHub\PyDSS\PyDSS\api\src\tmp_pydss_project\project1",
        "new_master.dss",
        "final_master.dss"
    )
    pmult, qmult = O.Optimize(1.00, 30 , 10)
    print("P multiplier: ", pmult)
    print("Q multiplier: ", qmult)