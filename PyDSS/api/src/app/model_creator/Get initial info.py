
import pandas as pd
import math
import os

models = [14203, 14303, 14352, 15108, 15561, 17604, 17605, 37102, 37124, 37121]
basepath = r"C:\Users\alatif\Desktop\Naerm\PyDSS"

def UpdateLoadkvar(idx, dsspath, path=r"C:\Users\alatif\Desktop\Naerm\PyPSSE\Transdata.csv"):
    data = pd.read_csv(path, index_col=0)
    networkdata = data.T[idx]
   # print(networkdata)
    P1 = networkdata["P load"]
    Q = networkdata["Q Load"]
    S = (P1**2 + Q**2)**(0.5)
    PF1 = P1 / S

    P2 = networkdata["PV gen (MW)"]
    Q = networkdata["PV gen (Mvar)"]
    S = (P2 ** 2 + Q ** 2) ** (0.5)
    PF2 = P2 / S

    mPen = networkdata["% motor D"]


    PVpenreq = P2 / P1 * 100
    print("Target Load PF: ", str(PF1))
    print("Target PV PF: ", str(PF1))
    print("Target MotorD penetration: ", str(mPen))
    print("Target PV penetration: ", str(P2 / P1 * 100))
    totalKwLoad = 0
    totalKwPV = 0
    totalKwMotor = 0
    for root, dirs, files in os.walk(dsspath):
        for file in files:

            if file == "Loads.dss":
                h = open(os.path.join(root, file))
                newLines, KwLoad = fixKvar(h, PF1)
                totalKwLoad += KwLoad
                h.close()

                h = open(os.path.join(root, file), "w")
                h.writelines(newLines)
                h.close()

            if file == "PVSystems.dss":
                h = open(os.path.join(root, file))
                newLines, KwPV = fixKvar(h, PF2, True)
                totalKwPV += KwPV
                #print("PV installation: ", totalKwPV)
                h.close()

                h = open(os.path.join(root, file), "w")
                h.writelines(newLines)
                h.close()

            if file == "Motors.dss":
                h = open(os.path.join(root, file))
                newLines, KwM = fixKvar(h, 0.8, True)
                totalKwMotor += KwM
                #print("PV installation: ", totalKwPV)
                h.close()

                h = open(os.path.join(root, file), "w")
                h.writelines(newLines)
                h.close()


    pvpen = totalKwPV / totalKwLoad * 100
    motorpen = totalKwMotor / (totalKwMotor + totalKwLoad) * 100
    print("PV penetration: ", pvpen)
    print("Motor penetration: ", motorpen)
    changeReq = PVpenreq / pvpen
    changeReqLd = 1 - mPen /100
    MotorlD =  totalKwLoad *  mPen /100
    changeReqMtr = MotorlD / totalKwMotor
    for root, dirs, files in os.walk(dsspath):
        for file in files:
            if file == "PVSystems.dss":
                h = open(os.path.join(root, file))
                newLines, KwPV = fixKw(h, changeReq, True)
                totalKwPV += KwPV
                #print("PV installation: ", totalKwPV)
                h.close()

                h = open(os.path.join(root, file), "w")
                h.writelines(newLines)
                h.close()

            # if file == "Loads.dss":
            #     h = open(os.path.join(root, file))
            #     newLines, KwPV = fixKw(h, changeReqLd, True)
            #     totalKwPV += KwPV
            #     #print("PV installation: ", totalKwPV)
            #     h.close()
            #
            #     h = open(os.path.join(root, file), "w")
            #     h.writelines(newLines)
            #     h.close()
            #
            # if file == "Motors.dss":
            #     h = open(os.path.join(root, file))
            #     newLines, KwPV = fixKw(h, changeReqMtr, True)
            #     totalKwPV += KwPV
            #     #print("PV installation: ", totalKwPV)
            #     h.close()
            #
            #     h = open(os.path.join(root, file), "w")
            #     h.writelines(newLines)
            #     h.close()



def fixKw(h, ratio, lead=False):
    totalKw = 0
    newLines = []
    lines = h.readlines()
    for line in lines:
        if "kW" in line:
            data = line.split(" ")
            kW = None
            for i, d in enumerate(data):
                if "kW" in d:
                    kW = float(d.split("=")[1])
                    data[i] = f"kW={ratio * kW}"
                    totalKw += kW
                    break
            newLine = ' '.join(data)
            newLines.append(newLine)
    return newLines, totalKw

def fixKvar(h, PF, lead=False):
    totalKw = 0
    newLines = []
    lines = h.readlines()
    for line in lines:
        if "kW" in line:
            data = line.split(" ")
            kW = None
            for i, d in enumerate(data):
                if "kW" in d:
                    kW = float(d.split("=")[1])
                    totalKw += kW
                    break
            for i, d in enumerate(data):
                if "kvar" in d:
                    S = kW /PF
                    Q = (S**2 - kW**2)**0.5
                    if lead:
                        data[i] = f"kvar={-Q}"
                    else:
                        data[i] = f"kvar={Q}"
            newLine = ' '.join(data)
            newLines.append(newLine)
    return newLines, totalKw

def getAllLoads(dss):
    ld = dss.Loads.First()
    kw = 0
    kvar = 0
    while ld:
        kw += dss.Loads.kW()
        dss.Loads.kvar()
        kvar += dss.Loads.kvar()
        ld = dss.Loads.Next()

    return kw, kvar


def getAllPVs(dss):
    pv = dss.PVsystems.First()
    kw = 0
    kvar = 0
    while pv:
        kw += dss.PVsystems.kW()
        kvar += dss.PVsystems.kvar()
        pv = dss.PVsystems.Next()
    return kw, kvar



substations = [x[0] for x in os.walk(r'C:\Users\alatif\Desktop\NEARM_sim\PyDSS_projects')]
all_values = []
for sub in models:
    print("Network: ", sub)
    dsspath = os.path.join(basepath, str(sub), "DSSfiles")
    UpdateLoadkvar(sub,  dsspath)


    from opendssdirect.utils import run_command as dss_cmd
    import opendssdirect as dss
    master_file = os.path.join(dsspath, 'Master.dss')
    dss.Basic.ClearAll()
    dss_cmd('Clear')
    reply = dss_cmd('compile ' + master_file)
    print('OpenDSS:  ' + reply)
    assert ('error ' not in reply.lower()), 'Error compiling OpenDSS model.\n{}'.format(reply)
    dss.Solution.Mode(2)
    dss.Solution.Hour(0)
    dss.Solution.Seconds(0)
    dss.Solution.Number(1)
    dss.Solution.StepSize(1)
    dss.Solution.MaxControlIterations(1)
    dss.Solution.Solve()

    Lp, Lq = getAllLoads(dss)
    Pp, Pq = getAllPVs(dss)

    dss.Vsources.First()
    Circuit = dss.Circuit.Name()
    KV = dss.Vsources.BasekV()
    Power = dss.Circuit.TotalPower()
    Vs = dss.Circuit.AllBusMagPu()
    Vs = [x for x in Vs if x > 0.3]
    all_values.append([Circuit, KV,-Power[0]/1000.0, -Power[1]/1000.0, min(Vs), max(Vs), Lp, Lq, Pp, Pq])
init_data = pd.DataFrame(all_values, columns=['Circuit name', 'Base kV', 'P', 'Q', 'Vmin', 'Vmax', 'Lp', 'Lq', 'Pp', 'Pq'])
init_data.to_csv(r'C:\Users\alatif\Desktop\Naerm\PyDSS\init_Conditions.csv')
