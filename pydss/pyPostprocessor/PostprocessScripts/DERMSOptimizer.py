from pydss.pyPostprocessor.pyPostprocessAbstract import AbstractPostprocess
from pydss.pyPostprocessor.PostprocessScripts.DERMSOptimizer_helper_modules.opt_funcs import *
from scipy.sparse import lil_matrix
import scipy.sparse.linalg as sp
import scipy.sparse as sparse
from scipy import stats
import pydss.dssInstance as dI
import pandas as pd
from math import *
import numpy as np
import os

class DERMSOptimizer(AbstractPostprocess):
    REQUIRED_INPUT_FIELDS_AND_DEFAULTS = {
        "control_flag": True,
        "control_all_flag": True,
        "num_DERMS": 1,
        "Vlower": 0.955,
        "Vupper": 1.038,
        "coeff_p": 0.0005,
        "coeff_q": 0.000001,
        "stepsize_xp": 1,
        "stepsize_xq": 5,
        "stepsize_mu": 10,
        "opf_iteration": 60,
        "max_iterations": 50,
        'time_trigger_sec': 900,
        "measurements_noises_flag": True,
        "implementation_mode": "Voltage triggered",
        'Distributions' : {
            "Vmes": ["norm", [0.0, 0.01]],
            "Imes": ["norm", [0.0, 0.01]],
        },
    }

    IMPLEMENTATION_MODES = ["Continuous", "Voltage triggered", "Time triggered", "Off"]

    def __init__(self, project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger):
        """Constructor method
        """
        super(DERMSOptimizer, self).__init__(project, scenario, inputs, dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger)
        self.Options = {**self.REQUIRED_INPUT_FIELDS_AND_DEFAULTS, **inputs}
        self.Settings = simulationSettings
        self.Objects = dssObjectsByClass

        self.dssSolver = dssSolver
        self.dss = dssInstance
        self.Logger = Logger
        self.logger.info('Creating DERMS Optimizer module')

        self.rootPath = simulationSettings['Project']['Project Path']
        self.dssPath = os.path.join(self.rootPath, simulationSettings['Project']['Active Project'], 'DSSfiles')

        self.Buses = []
        self.BusDistance = []
        self.Vbase_allnode = []

        self.initialize_optimizer()
        self.ExportCSVfiles = True
        self.sim_start = False
        self.DERMS_trigger_fail_count = 0
        self.DERMS_trigger_count = 0
        self.DERMS_trigger_success_count = 0

        PVdata = self.getDERdata()

        assert self.Options["implementation_mode"] in self.IMPLEMENTATION_MODES, 'valid implementation modes are ()'.fomrmat(
            self.IMPLEMENTATION_MODES
        )
        self.dermsController = DERMS(
            PVdata, self.controlbus, self.controlelem, self.BEcapacity, self.Nodes[self.nSlack:], self.BEname
        )

    def initialize_optimizer(self):
        self.dss.utils.run_command('calcV')
        self.Nodes = self.dss.Circuit.YNodeOrder()
        self.nNodes = len(self.Nodes)

        self.Slack = self.Objects['Vsources']["Vsource.source"]
        self.nSlack = int(self.Slack.GetValue("phases"))

        for node in self.Nodes:
            node = node.lower()
            bus, phaseInfo = node.split(".", 1)
            self.Vbase_allnode.append(self.Objects['Buses'][bus].GetVariable("kVBase") * 1000)
            self.BusDistance.append(self.Objects['Buses'][bus].GetVariable("Distance"))

        for x in self.Nodes:
            bName = x.split('.')[0]
            if bName not in self.Buses:
                self.Buses.append(bName)
        self.nBus = len(self.Buses)

        Y00, Y01, Y10, Y11, Y11_sparse, Y11_inv, Ybus = self.ExtractImpednceMatrix()
        self.getBranchInfo()

        self.dssSolver.Solve()
        V1, V1_pu = self.get_voltage_Yorder()

        capNames = self.dss.Capacitors.AllNames()
        hCapNames = ",".join(capNames)

        loadData = self.get_elem_data(
            "Loads",
            ["Name", "kV", "kW", "pf", "phase", "bus", "phases", "VoltagesMagAng", "Powers", "conn"]
        )
        total_load = sum([L["kW"] for L in loadData])
        #Do we want profile implementation here or a dedicatied profile manager?

        self.PVSystem = self.get_elem_data(
            "Generators",
            ["Name", "bus", "busFull", "phase", "kVA", "kW", "phases", "conn"]
        )
        self.PVSystem_1phase = self.convert_3phasePV_to_1phasePV(self.PVSystem)
        self.PVSystem_1phaseDF = pd.DataFrame(self.PVSystem_1phase)
        if self.Options["control_flag"]:
            PVlocation = []
            NPV = len(self.PVSystem_1phase)
            nodeIndex_withPV = []
            PV_inverter_size = []
            for pv in self.PVSystem_1phase:
                allpvbus = pv["bus"].split('.')
                PVlocation.append(allpvbus[0])
                if len(allpvbus) == 1:
                    allpvbus = allpvbus + ['1', '2', '3']
                for ii in range(len(allpvbus) - 1):
                    pvbus = allpvbus[0] + '.' + allpvbus[ii + 1]
                    nodeIndex_withPV.append(self.Nodes.index(pvbus.upper()))
                PV_inverter_size.append(float(pv['kVA']) / (len(allpvbus) - 1))

            capacitors = self.get_elem_data("Capacitors", ["Name", "bus", "phase", "phases", "kV", "kvar"])
            PQ_load, PQ_PV, PQ_node, Qcap = self.calc_node_PQ()

            if self.Options["control_all_flag"]:
                self.controlbus = self.Nodes[self.nSlack:]
            else:
                self.controlbus = self.getContolBuses(["Generators", "Capacitors"])

            self.controlelem = []
            self.mu0 = [
                np.zeros(len(self.controlbus)),
                np.zeros(len(self.controlbus)),
                np.zeros(len(self.controlelem))
            ]

            self.power_flow_data = linear_powerflow_model(Y00, Y01, Y10, Y11_inv, [], V1, self.nSlack)

            self.stepsize_control = [self.Options["stepsize_xp"], self.Options["stepsize_xq"],
                                     self.Options["stepsize_mu"]]
            self.Vlimit = [self.Options["Vupper"], self.Options["Vlower"]]
        return

    def calc_node_PQ(self):
        PQ_load = self.get_PQ_by_class("Loads")
        PQ_PV = self.get_PQ_by_class("Generators")
        PQ_CAP = self.get_PQ_by_class("Capacitors")
        Qcap = PQ_CAP.imag
        PQ_node = - PQ_load + PQ_PV - 1j * np.array(Qcap)  # power injection
        return PQ_load, PQ_PV, PQ_node, Qcap

    def get_PQ_by_class(self, className):
        P = [0] * len(self.Nodes)
        Q = [0] * len(self.Nodes)
        for name, obj in self.Objects[className].items():
            power = obj.GetValue("Powers")
            bus = obj.GetValue("BusNames")[0]
            nodes = bus.split(".")[1:] if len(bus.split(".")[1:]) else [1, 2, 3]

            for i, ii in enumerate(nodes):
                nodeName = "{}.{}".format(bus.split(".")[0], ii)
                index = self.Nodes.index(nodeName.upper())
                P[index] = power[2 * i]
                Q[index] = power[2 * i + 1]
        PQ = np.array(P) + 1j * np.array(Q)
        return PQ

    def get_elem_data(self, ElementClass, Properties):
        data = []
        for name, obj in self.Objects[ElementClass].items():
            datum = {}
            for ppty in Properties:
                if ppty == "bus":
                    datum[ppty] = obj.GetValue("BusNames")[0].split(".")[0]
                elif ppty == "phase":
                    phases = obj.GetValue("BusNames")[0].split(".")[1:]
                    datum[ppty] = phases if len(phases) else [1, 2, 3]
                elif ppty == "busFull":
                    datum[ppty] = obj.GetValue("BusNames")[0]
                else:
                    datum[ppty] = obj.GetValue(ppty)
            data.append(datum)
        return data

    def convert_3phasePV_to_1phasePV(self, PVSystems):
        # convert multi-phase PV into multiple 1-phase PVs for control implementation purpose
        PVSystem_1phase = []
        for pv in PVSystems:
            for i, ii in enumerate(pv["phase"]):
                pv_perphase = {}
                pv_perphase["Name"] = pv["Name"]  # +'_node'+bus[ii+1]
                pv_perphase["bus"] = pv["bus"] + '.' + ii
                pv_perphase["kW"] = pv["kW"] / pv["phases"]
                pv_perphase["kVA"] = pv["kVA"] / pv["phases"]
                PVSystem_1phase.append(pv_perphase)
        return PVSystem_1phase

    def get_incidence_matrix(self):
        #self.dss.utils.run_command('solve mode=fault') dont think this is needed. May be wrong
        Ybranch_prim, branch_node_incidence, nNeutral, record_index = self.construct_Yprime()
        current_coeff_matrix = np.dot(Ybranch_prim, branch_node_incidence)
        current_coeff_matrix = current_coeff_matrix[record_index, :-nNeutral]
        branch_node_incidence = branch_node_incidence[record_index, :-nNeutral]
        return current_coeff_matrix, branch_node_incidence, current_coeff_matrix

    def ExtractImpednceMatrix(self):
        Y = self.dss.Circuit.SystemY()
        Ybus = self.to_complex(Y)
        Y00 = Ybus[0:self.nSlack, 0:self.nSlack]
        Y01 = Ybus[0:self.nSlack, self.nSlack:]
        Y10 = Ybus[self.nSlack:, 0:self.nSlack]
        Y11 = Ybus[self.nSlack:, self.nSlack:]
        Y11_sparse = lil_matrix(Y11)
        Y11_sparse = Y11_sparse.tocsr()
        a_sps = sparse.csc_matrix(Y11)
        lu_obj = sp.splu(a_sps)
        Y11_inv = lu_obj.solve(np.eye(self.nNodes - self.nSlack))
        return Y00, Y01, Y10, Y11, Y11_sparse, Y11_inv, Ybus

    def get_voltage_Yorder(self):
        temp_Vbus = self.dss.Circuit.YNodeVArray()
        voltage = [complex(0, 0)] * self.nNodes
        for ii in range(self.nNodes):
            voltage[ii] = complex(temp_Vbus[ii * 2], temp_Vbus[ii * 2 + 1])
        voltage_pu = list(map(lambda x: abs(x[0]) / x[1], zip(voltage, self.Vbase_allnode)))
        return voltage, voltage_pu

    def to_complex(self, values):
        Ydim = int(sqrt(len(values) / 2))
        Yreal = np.array(values[0::2]).reshape((Ydim, Ydim))
        Yimag = np.array(values[1::2]).reshape((Ydim, Ydim))
        Ycmplx = Yreal + 1j * Yimag
        return Ycmplx

    def construct_Yprime(self):
        Ybranch_prim = np.array([[complex(0, 0)] * 2 * self.nBarnchElements] * 2 * self.nBarnchElements)
        branch_node_incidence = np.zeros([2 * self.nBarnchElements, self.nNodes + 422])  #TODO fix hard coded 422 for Green, 104 for Diamond

        record_index = []
        nNeutral = 0
        start_no = 0
        count = 0

        temp_AllNodeNames = self.dss.Circuit.YNodeOrder()
        for elemName, elmObj in self.branchElements.items():
            values = elmObj.GetValue('YPrim')
            Yprim = self.to_complex(values)
            buses = [ii.split('.')[0] for ii in elmObj.GetValue('BusNames')]
            nodes = elmObj.GetValue('NodeOrder')
            nPhases = int(len(nodes) / 2)
            nNeutral += nodes.count(0)
            for ii in range(nPhases):
                from_node = buses[0] + '.' + str(nodes[ii])
                to_node = buses[1] + '.' + str(nodes[ii + nPhases])
                if nodes[ii] == 0:
                    temp_AllNodeNames.append(from_node.upper())
                if nodes[ii + nPhases] == 0:
                    temp_AllNodeNames.append(to_node.upper())
                from_node_index = temp_AllNodeNames.index(from_node.upper())
                to_node_index = temp_AllNodeNames.index(to_node.upper())
                branch_node_incidence[2 * count + ii, from_node_index] = 1
                branch_node_incidence[2 * count + nPhases + ii, to_node_index] = 1
                record_index.append(2 * count + ii)
            count = count + nPhases
            end_no = start_no + 2 * nPhases
            Ybranch_prim[start_no:end_no, start_no:end_no] = Yprim
            start_no = end_no

        return Ybranch_prim, branch_node_incidence, nNeutral, record_index

    def getContolBuses(self, classNames):
        controlbus = []
        for className in classNames:
            for elm in self.get_elem_data(className, ["bus", "phases"]):
                for phase in elm["phases"]:
                    controlbus.append("{}.{}".format(elm["bus"], phase))
        return controlbus

    @staticmethod
    def _get_required_input_fields():
        return {}

    def getBranchInfo(self):
        self.branchElements = {**self.Objects["Lines"], **self.Objects["Transformers"]}
        self.nBarnchElements = len(self.branchElements)
        self.BEindex = []
        self.BEcapacity = []
        self.BEname = []

        for elmName, elmObj in self.branchElements.items():
            nTerms = elmObj.GetValue("NumTerminals")
            Nodes = elmObj.GetValue("NodeOrder")
            nPhases = int(len(Nodes) / nTerms)
            self.BEindex.append(list(range(nPhases)))
            for ii in range(nPhases):
                self.BEcapacity.append(elmObj.GetValue("NormalAmps"))
                self.BEname.append("{}.{}".format(elmName, Nodes[ii]))

    def getDERdata(self):
        data = self.get_elem_data("Generators", ["Name", "busFull", "phase", "kVA", "kW", "phases", "conn"])
        data = pd.DataFrame(data)
        data.index = data["Name"]
        PVdata = {
            "pvName": [],
            "pvLocation": [],
            "bus": [],
            "pvSize": [],
            "inverterSize": [],
        }
        for pv1P in self.PVSystem_1phaseDF["Name"].tolist():
            pv = data.loc[pv1P]
            PVdata["pvName"].append(pv['Name'])
            PVdata["bus"].append(pv['busFull'])
            PVdata["pvSize"].append(pv['kW'])
            PVdata["inverterSize"].append(pv['kVA'])
            for b in self.buses(pv):
                if b.upper() not in PVdata["pvLocation"]:
                    PVdata["pvLocation"].append(b.upper())
                    break
        return PVdata

    def buses(self, pv):
        bus = pv['busFull'].split(".")
        if len(bus) == 1:
            bus += ["1", "2", "3"]
        return [f"{bus[0]}.{i}" for i in bus[1:]]

    def run(self, step, stepMax, simulation=None):
        """Induces and removes a fault as the simulation runs as per user defined settings.
        """
        self.logger.info('Running DERMS optimization module')
        opt_iter = 0

        #Really bad codeing form
        mu0 = [
            [0 for x in range(len(self.controlbus))],
            [0 for x in range(len(self.controlbus))],
            [0 for x in range(len(self.controlelem))]
        ]

        PVmax = [pv["kW"] if pv["kW"] < pv["kVA"] else pv["kVA"] for pv in self.PVSystem_1phase]

        while opt_iter < self.Options["max_iterations"]:
            self.dssSolver.reSolve()
            PVlocation, PVpower, Vmes, Imes = self.dermsController.monitor(self._dssInstance, self.Objects,
                                                                           self.PVSystem_1phaseDF)
            self.Logger.info('Voltage measurements: {}'.format(len(Vmes)))
            self.Logger.info('Maximum voltage: {}'.format(max(Vmes)))

            if self.Options["measurements_noises_flag"]:
                distName, distParams = self.Options['Distributions']["Vmes"]
                dist = getattr(stats, distName)
                Vmes = Vmes + dist.rvs(*distParams, size=len(Vmes))
                distName, distParams = self.Options['Distributions']["Imes"]
                dist = getattr(stats, distName)
                Imes = Imes + dist.rvs(*distParams, size=len(Imes))

            if self.Options["implementation_mode"] == "Continuous":
                DERMS_trigger = 1
            elif self.Options["implementation_mode"] == "Voltage triggered":
                if max(Vmes) > self.Options["Vupper"] or min(Vmes) < self.Options["Vlower"]:
                    DERMS_trigger = 1
                    #TODO: Should DERMS trigger count be in this if statement?
                elif max(Vmes) <= self.Options["Vupper"] and min(Vmes) >= self.Options["Vlower"] and opt_iter >= 1:
                    DERMS_trigger = 0
                    self.DERMS_trigger_count += 1
                    self.DERMS_trigger_success_count += 1
                    self.Logger.info('DERMS OPF successfully triggered, maxV: {}'.fotmat(max(Vmes)))
                    break
                else:
                    DERMS_trigger = 0
            elif self.Options["implementation_mode"] == "Time triggered":
                #TODO: Is step * stepsize_sim >= time_mode_resolution required? Is the idea to ensure that the controller does not run on the first iteration?
                if step > 0 and self.dssSolver.GetTotalSeconds() % self.Options["time_trigger_sec"] == 0:
                    DERMS_trigger = 1
                else:
                    DERMS_trigger = 0
            elif self.Options["implementation_mode"] == "Off":
                DERMS_trigger = 0

            if DERMS_trigger == 1:

                [x1, mu1] = self.dermsController.control(
                    self.power_flow_data,
                    self.Options,
                    self.stepsize_control,
                    mu0,
                    self.Vlimit,
                    PVpower,
                    Imes,
                    Vmes,
                    PVmax
                )
                # ------ apply the setpoint ------
                nPV_1_phs = len(self.PVSystem_1phase)
                for pv in self.PVSystem:
                    idx = [i for i, x in enumerate(self.PVSystem_1phase) if x["Name"] == pv["Name"]]
                    self.Objects["Generators"][pv["Name"]].SetParameter("kW", sum([x1[ii] for ii in idx]))
                    self.Objects["Generators"][pv["Name"]].SetParameter("kvar",  sum([x1[ii + nPV_1_phs] for ii in idx]))

                mu0 = mu1
                # resV_record.append(max(Vmes))
                opt_iter = opt_iter + 1
                if max(Vmes) <= self.Options["Vupper"] and min(Vmes) >= self.Options["Vlower"]:
                    self.DERMS_trigger_count += 1
                    self.DERMS_trigger_success_count += 1
                    self.Logger.info('DERMS OPF successfully triggered')
                    break
            elif DERMS_trigger == 0:
                # TODO: Is this piece of code required?
                # for pv in self.PVSystem:
                #     PVgen = float(pv['kW']) * PVshape[
                #         int((present_step - 1) * stepsize_sim / data_resolution + 3600 / data_resolution * startH)]
                #     if PVgen > float(pv["kVA"]):
                #         PVgen = float(pv["kVA"])
                #     dss.run_command('edit ' + str(pv["name"]) + ' kW=' + str(PVgen) + ' pf=' + str(pf_auto))
                break
            if opt_iter == self.Options["max_iterations"]:
                self.DERMS_trigger_count += 1
                if max(Vmes) > self.Options["Vupper"] or min(Vmes) < self.Options["Vlower"]:
                    self.DERMS_trigger_fail_count += 1
                    self.Logger.warning('DERMS OPF triggered and failed')


            opt_iter += 1
        #step-=1 # uncomment the line if the post process needs to rerun for the same point in time
        return step

    def getPreoptimizationResults(self):
        return