import numpy as np
from scipy.sparse import lil_matrix
import scipy.sparse.linalg as sp
import scipy.sparse as sparse
import math
import csv
import matplotlib.pyplot as plt

def linear_powerflow_model(Y00,Y01,Y10,Y11_inv,I_coeff,V1,slack_no):
    # voltage linearlization
    V1_conj = np.conj(V1[slack_no:])
    V1_conj_inv = 1 / V1_conj
    coeff_V = Y11_inv * V1_conj_inv
    coeff_V_P = coeff_V
    coeff_V_Q = -1j*coeff_V
    coeff_Vm = -np.dot(Y11_inv,np.dot(Y10,V1[:slack_no]))

    # voltage magnitude linearization
    m = coeff_Vm
    m_inv = 1 / coeff_Vm
    coeff_Vmag_k = abs(m)
    A = (np.multiply(coeff_V.transpose(),m_inv)).transpose()
    coeff_Vmag_P = (np.multiply(A.real.transpose(),coeff_Vmag_k)).transpose()
    coeff_Vmag_Q = (np.multiply((-1j*A).real.transpose(),coeff_Vmag_k)).transpose()

    # current linearization
    if len(I_coeff):
        coeff_I_P = np.dot(I_coeff[:,slack_no:],coeff_V_P)
        coeff_I_Q = np.dot(I_coeff[:,slack_no:],coeff_V_Q)
        coeff_I_const = np.dot(I_coeff[:,slack_no:],coeff_Vm) + np.dot(I_coeff[:,:slack_no],V1[:slack_no])
    else:
        coeff_I_P = []
        coeff_I_Q = []
        coeff_I_const = []

    #=========================================Yiyun's Notes===========================================#
    # Output relations: Vmag = coeff_Vmag_P * Pnode + coeff_Vmag_Q * Qnode + coeff_Vm
    #                      I = coeff_I_P * Pnode + coeff_I_Q * Qnode + coeff_I_const (complex value)
    # ================================================================================================#

    return coeff_V_P, coeff_V_Q, coeff_Vm, coeff_Vmag_P, coeff_Vmag_Q, coeff_Vmag_k, coeff_I_P, coeff_I_Q, coeff_I_const

def validate_linear_model(coeff_Vp,coeff_Vq,coeff_Vm,PQ_node,slack_number):
    V_cal = coeff_Vm + np.dot(coeff_Vp,np.array([np.real(ii)*1000 for ii in PQ_node[slack_number:]])) + np.dot(coeff_Vq,np.array([np.imag(ii)*1000 for ii in PQ_node[slack_number:]]))
    v_cal_1 = coeff_Vm + np.dot(coeff_Vp,np.conj(PQ_node[slack_number:]*1000))
    #coeff_Vp*Pnode + coeff_Vq*Qnode + coeff_Vm

    # =========================================Yiyun's Notes===========================================#
    # 1000 should be the S base
    # =================================================================================================#

    return [V_cal,v_cal_1]

def check_VI_correct(V1,PQ_node,slack_number,coeff_V,coeff_Vm,coeff_Vmag_P,coeff_Vmag_Q,coeff_Vmag_k,Y10,Y11,coeff_I_P, coeff_I_Q, coeff_I_const,I_coeff):
    V1_linear = np.dot(coeff_V,np.conj(PQ_node[slack_number:]*1000)) + coeff_Vm
    V1_linear = list(V1_linear)
    Vdiff = list(map(lambda x: abs(x[0]-x[1])/abs(x[0])*100,zip(V1[slack_number:],V1_linear)))
    with open('voltage_diff.csv','w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(Vdiff)
    f.close()

    V1_mag_linear = np.dot(coeff_Vmag_P,(PQ_node[slack_number:]*1000).real) + np.dot(coeff_Vmag_Q,(PQ_node[slack_number:]*1000).imag) + coeff_Vmag_k
    V1_mag_linear = list(V1_mag_linear)
    Vdiff = list(map(lambda x: abs(abs(x[0])-x[1])/abs(x[0])*100,zip(V1[slack_number:],V1_mag_linear)))
    with open('voltageMag_diff.csv','w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(Vdiff)
    f.close()

    # get Ibus   
    Ibus = list(map(lambda x: (x[0]*1000/x[1]).conjugate(),zip(list(PQ_node)[slack_number:],V1[slack_number:])))
    Ibus_cal_0 = np.dot(Y10,V1[0:slack_number])
    Ibus_cal_1 = np.dot(Y11,V1[slack_number:])
    Ibus_cal = list(map(lambda x: x[0]+x[1],zip(Ibus_cal_0,Ibus_cal_1)))
    Idiff = list(map(lambda x: abs(x[0]-x[1]),zip(Ibus,Ibus_cal)))
    with open('currentBus_diff.csv','w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(Idiff)
    f.close()

    # get Ibranch
    Ibranch = np.dot(I_coeff,V1)
    Ibranch_cal = np.dot(I_coeff[:,slack_number:],V1_linear)+np.dot(I_coeff[:,0:slack_number],V1[:slack_number])
    Ibranch_diff = list(map(lambda x: abs(x[0]-x[1]),zip(Ibranch,Ibranch_cal)))
    with open('current_diff.csv','w') as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(Ibranch_diff)
    f.close()

def costFun(x,dual_upper,dual_lower,v1_pu,Ppv_max,coeff_p,coeff_q,NPV,control_bus_index,Vupper,Vlower,dual_current,ThermalLimit,I1_mag):
    # cost_function = coeff_p*(Pmax-P)^2+coeff_q*Q^2+dual_upper*(v1-1.05)+dual_lower*(0.95-v1)
    f1 = 0
    for ii in range(NPV):
        f1 = f1 + coeff_p*(Ppv_max[ii]-x[ii])*(Ppv_max[ii]-x[ii])+coeff_q*x[ii+NPV]*x[ii+NPV]
    #f = f1 + np.dot(dual_upper,(np.array(v1_pu)[control_bus_index]-Vupper)) + np.dot(dual_lower,(Vlower-np.array(v1_pu)[control_bus_index]))
    v_evaluate = [v1_pu[ii] for ii in control_bus_index]
    f2 = f1 + np.dot(dual_upper,np.array([max(ii-Vupper,0) for ii in v_evaluate])) + np.dot(dual_lower,np.array([max(Vlower-ii,0) for ii in v_evaluate]))
    f3 = np.dot(dual_current,np.array([max(ii,0) for ii in list(map(lambda x: x[0]*x[0]-x[1]*x[1],zip(I1_mag,ThermalLimit)))]))
    f = f2+f3

    # =========================================Yiyun's Notes===========================================#
    # f1 is the quadratic PV curtailment plus quadratic reactive power injection
    # f2 is the Lagrangian term for voltage violations and line current violations
    # ===> Note the "control_bus_index" might be the index for measurement sensitivity analysis
    # =================================================================================================#

    return [f1,f]

def PV_costFun_gradient(x, coeff_p, coeff_q, Pmax):
    grad = np.zeros(len(x))
    for ii in range(int(len(x)/2)):
        grad[ii] = -2*coeff_p*(Pmax[ii]*1000-x[ii]*1000)
        grad[ii+int(len(x)/2)] = 2*coeff_q*x[ii+int(len(x)/2)]*1000
        #grad[ii + int(len(x) / 2)] = 0

    # =========================================Yiyun's Notes===========================================#
    # x is the decision vector [P,Q]
    # =================================================================================================#

    return grad

def voltage_constraint_gradient(AllNodeNames,node_withPV, dual_upper, dual_lower, coeff_Vmag_p, coeff_Vmag_q):
    node_noslackbus = AllNodeNames
    node_noslackbus[0:3] = []

    # =========================================Yiyun's Notes===========================================#
    # remove the slack bus
    # =================================================================================================#

    grad_upper = np.matrix([0] * len(node_noslackbus)*2).transpose()
    grad_lower = np.matrix([0] * len(node_noslackbus)*2).transpose()
    count = 0
    for node in node_noslackbus:
        if node in node_withPV:
            grad_upper[count] = dual_upper.transpose()*coeff_Vmag_p[:,count]
            grad_upper[count+len(node_noslackbus)] = dual_upper.transpose() * coeff_Vmag_q[:,count]
            grad_lower[count] = -dual_lower.transpose() * coeff_Vmag_p[:, count]
            grad_lower[count + len(node_noslackbus)] = -dual_lower.transpose() * coeff_Vmag_q[:, count]
        count = count + 1
    return [grad_upper,grad_lower]

def current_constraint_gradient(AllNodeNames,node_withPV, dual_upper,coeff_Imag_p, coeff_Imag_q):
    node_noslackbus = AllNodeNames
    node_noslackbus[0:3] = []
    grad_upper = np.matrix([0] * len(node_noslackbus)*2).transpose()
    count = 0
    for node in node_noslackbus:
        if node in node_withPV:
            grad_upper[count] = dual_upper.transpose()*coeff_Imag_p[:,count]
            grad_upper[count+len(node_noslackbus)] = dual_upper.transpose() * coeff_Imag_q[:,count]
        count = count + 1
    return grad_upper

    # =========================================Yiyun's Notes===========================================#
    # PV_costFun_gradient,  voltage_constraint_gradient, current_constraint_gradient and project_PV..
    # ... are set up for updating the PV decision variables in eq(10)
    # =================================================================================================#

def voltage_constraint(V1_mag):
    g = V1_mag-1.05
    g.append(0.95-V1_mag)
    return g

def current_constraint(I1_mag,Imax):
    g = []
    g.append(I1_mag-Imax)

    # =========================================Yiyun's Notes===========================================#
    # assume single directional power flow
    # voltage_constraint, current_constraint, and project_dualvariable are set up for updating the dual...
    # ... variables in eq (11)
    # =================================================================================================#

    return g

def project_dualvariable(mu):
    for ii in range(len(mu)):
        mu[ii] = max(mu[ii],0)

    # =========================================Yiyun's Notes===========================================#
    # If the corresponding constraints in primal problem is in canonical form, then dual variable is >=0
    # =================================================================================================#

    return mu

def project_PV(x,Pmax,Sinv):
    Qavailable = 0
    Pavailable = 0
    num = len(Sinv)
    for ii in range(num):
        if x[ii] > Pmax[ii]:
            x[ii] = Pmax[ii]
        elif x[ii] < 0:
            x[ii] = 0

        if Sinv[ii] > x[ii]:
            Qmax = math.sqrt(Sinv[ii]*Sinv[ii]-x[ii]*x[ii])
        else:
            Qmax = 0
        if x[ii+num] > Qmax:
            x[ii+num] = Qmax
        # elif x[ii + num] < 0:
        #     x[ii + num] = 0
        elif x[ii+num] < -Qmax:
            x[ii+num] = -Qmax

        Pavailable = Pavailable + Pmax[ii]
        Qavailable = Qavailable + Qmax
    return [x,Pavailable,Qavailable]

def dual_update(mu,coeff_mu,constraint):
    mu_new = mu + coeff_mu*constraint
    mu_new = project_dualvariable(mu_new)

    # =========================================Yiyun's Notes===========================================#
    # normal way for update Lagrangian variable is by the sub-gradient of cost function
    # Here is the equation (11) in the draft paper
    # =================================================================================================#

    return mu_new

def matrix_cal_for_subPower(V0, Y00, Y01, Y11, V1_noload):
    diag_V0 = np.matrix([[complex(0, 0)] * 3] * 3)
    diag_V0[0, 0] = V0[0]
    diag_V0[1, 1] = V0[1]
    diag_V0[2, 2] = V0[2]
    K = diag_V0 * Y01.conj() * np.linalg.inv(Y11.conj())
    g = diag_V0 * Y00.conj() * np.matrix(V0).transpose().conj() + diag_V0 * Y01.conj() * V1_noload.conj()
    return[K,g]

def subPower_PQ(V1, PQ_node, K, g):
    diag_V1 = np.matrix([[complex(0, 0)] * len(V1)] * len(V1))
    for ii in range(len(V1)):
        diag_V1[ii, ii] = V1[ii]
    M = K * np.linalg.inv(diag_V1)
    MR = M.real
    MI = M.imag
    P0 = g.real + (MR.dot(PQ_node.real)*1000 - MI.dot(PQ_node.imag)*1000)
    Q0 = g.imag + (MR.dot(PQ_node.imag)*1000 + MI.dot(PQ_node.real)*1000)

    P0 = P0/1000
    Q0 = Q0/1000 # convert to kW/kVar

    # =========================================Yiyun's Notes===========================================#
    # Power injection at substation/feeder head
    # =================================================================================================#

    return [P0, Q0, M]

def sub_costFun_gradient(x, sub_ref, coeff_sub, sub_measure, M, node_withPV):
    grad_a = np.matrix([0] * len(x)).transpose()
    grad_b = np.matrix([0] * len(x)).transpose()
    grad_c = np.matrix([0] * len(x)).transpose()

    MR = M.real
    MI = M.imag
    count = 0
    for node in node_withPV:
        grad_a[count] = -MR[0, int(node)]
        grad_b[count] = -MR[1, int(node)]
        grad_c[count] = -MR[2, int(node)]

        grad_a[count + len(node_withPV)] = MI[0, int(node)]
        grad_b[count + len(node_withPV)] = MI[1, int(node)]
        grad_c[count + len(node_withPV)] = MI[2, int(node)]

        count = count + 1

    res = coeff_sub * ((sub_measure[0] - sub_ref[0]) *1000* grad_a + (sub_measure[1] - sub_ref[1])*1000 * grad_b
                       + (sub_measure[2] - sub_ref[2])*1000 * grad_c)
    res = res/1000

    return res

def projection(x,xmax,xmin):
    for ii in range(len(x)):
        if x.item(ii) > xmax[ii]:
            x[ii] = xmax[ii]
        if x.item(ii) < xmin[ii]:
            x[ii] = xmin[ii]
    return x

class DERMS:
    def __init__(self, pvData,controlbus,controlelem,controlelem_limit,sub_node_names,sub_elem_names):
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # PV_name: names of all PVs in the zone
        # PV_size: sizes of all PVs in the zone
        # PV_location: busnames of all PVs in the zone
        # controlbus: names of all controlled nodes
        # sub_node_names: names of all nodes in the zone
        # sub_node_names "include" controlbus
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        self.PV_name = pvData["pvName"]
        self.PV_location = pvData["pvLocation"]
        self.PV_size = pvData["pvSize"]
        self.inverter_size = pvData["inverterSize"]
        self.control_bus = controlbus

        sub_node_names = [ii.upper() for ii in sub_node_names]
        self.controlbus_index = [sub_node_names.index(ii.upper()) for ii in controlbus] # control bus index in the sub system (number)
        # here
        PVbus_index = []
        for bus in self.PV_location:
            temp = bus.split('.')
            if len(temp) == 1:
                temp = temp + ['1', '2', '3']
            for ii in range(len(temp) - 1):
                PVbus_index.append(sub_node_names.index((temp[0] + '.' + temp[ii + 1]).upper()))

        # =========================================Yiyun's Notes===========================================#
        # adding .1 .2 .3 following the number to recognize the three phases.
        # =================================================================================================#
        self.PVbus_index = PVbus_index
        self.control_elem = controlelem
        self.controlelem_limit = controlelem_limit
        self.controlelem_index = [sub_elem_names.index(ii) for ii in controlelem] # control branches index in the sub system (number)

    def monitor(self, dss, dssObjects, PVSystem_1phase):
        PVpowers = []
        for pv in PVSystem_1phase["Name"].tolist():
            nPhases = dssObjects["Generators"][pv].GetValue("phases")
            power = dssObjects["Generators"][pv].GetValue("Powers")
            PVpowers.append([sum(power[::2])/nPhases, sum(power[1::2])/nPhases])
        PVpowers = np.asarray(PVpowers)

        Vmes = []
        for bus in self.control_bus:
            busName = bus.split('.')[0].lower()
            Vmag = dssObjects["Buses"][busName].GetValue("puVmagAngle")[::2]
            allbusnode = dss.Bus.Nodes()
            phase = bus.split('.')[1]
            index = allbusnode.index(int(phase))
            Vnode = Vmag[index]
            Vmes.append(Vnode)

        Imes = []
        for elem in self.control_elem:
            className = elem.split('.')[0] + "s"
            I = dssObjects[className][elem].GetValue("CurrentsMagAng")[::2][:3] #TODO: Why is there a hardcoded [:3] ?
            Imes.append(I)

        return [self.PV_location,PVpowers,Vmes,Imes]



    def control(self, linear_PF_coeff, Options,stepsize,mu0,Vlimit,PVpower,Imes,Vmes,PV_Pmax_forecast):
        coeff_p = Options["coeff_p"]
        coeff_q = Options["coeff_q"]

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # linear_PF_coeff is the linear power flow model coefficients for the zone, and linear power flow model
        #                coefficients are the result vector from function "linear_powerflow_model"
        # coeff_p, coeff_q are constant coefficients in PV cost function
        # stepsize is a vector of stepsize constants
        # mu0 is the dual variable from last time step: mu_Vmag_upper0, mu_Vmag_lower0, mu_I0
        # Vlimit is the allowed voltage limit: Vupper and Vlower
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        PVname = self.PV_name
        NPV = len(PVname)
        x0 = np.zeros(2 * NPV)
        for ii in range(NPV):
            x0[ii] = -PVpower[ii][0] # in kW
            x0[ii + NPV] = -PVpower[ii][1] # in kVar

        #coeff_V_P = linear_PF_coeff[0]
        #coeff_V_Q = linear_PF_coeff[1]
        #coeff_Vm = linear_PF_coeff[2]
        coeff_Vmag_P = linear_PF_coeff[3]
        coeff_Vmag_Q = linear_PF_coeff[4]
        #coeff_Vmag_k = linear_PF_coeff[5]
        coeff_I_P = linear_PF_coeff[6]
        coeff_I_Q = linear_PF_coeff[7]
        #coeff_I_const = linear_PF_coeff[8]
        stepsize_xp = stepsize[0]
        stepsize_xq = stepsize[1]
        stepsize_mu = stepsize[2]
        Vupper = Vlimit[0]
        Vlower = Vlimit[1]

        controlbus_index = self.controlbus_index
        PVbus_index = self.PVbus_index
        controlelem_index = self.controlelem_index
        PV_inverter_size = self.inverter_size
        Imes_limit = self.controlelem_limit

        mu_Vmag_upper0 = mu0[0]
        mu_Vmag_lower0 = mu0[1]
        mu_I0 = mu0[2]

        PVcost_fun_gradient = PV_costFun_gradient(x0, coeff_p, coeff_q, PV_Pmax_forecast)

        Vmag_upper_gradient = np.concatenate((np.dot(coeff_Vmag_P[np.ix_([ii for ii in controlbus_index],[ii for ii in PVbus_index])].transpose(), mu_Vmag_upper0),
                                              np.dot(coeff_Vmag_Q[np.ix_([ii for ii in controlbus_index], [ii for ii in PVbus_index])].transpose(), mu_Vmag_upper0)),axis=0)
        Vmag_lower_gradient = np.concatenate((np.dot(coeff_Vmag_P[np.ix_([ii for ii in controlbus_index],[ii for ii in PVbus_index])].transpose(), mu_Vmag_lower0),
                                              np.dot(coeff_Vmag_Q[np.ix_([ii for ii in controlbus_index],[ii for ii in PVbus_index])].transpose(), mu_Vmag_lower0)),axis=0)

        Vmag_gradient = Vmag_upper_gradient - Vmag_lower_gradient
        if len(mu_I0)>0 :
            temp_real = mu_I0 * np.array(Imes.real)
            temp_imag = mu_I0 * np.array(Imes.imag)

            I_gradient_real = np.concatenate((np.dot(
                coeff_I_P[np.ix_([ii for ii in controlelem_index], [ii for ii in PVbus_index])].real.transpose(),
                temp_real), np.dot(
                coeff_I_Q[np.ix_([ii for ii in controlelem_index], [ii for ii in PVbus_index])].real.transpose(),
                temp_real)), axis=0)
            I_gradient_imag = np.concatenate((np.dot(
                coeff_I_P[np.ix_([ii for ii in controlelem_index], [ii for ii in PVbus_index])].imag.transpose(),
                temp_imag), np.dot(
                coeff_I_Q[np.ix_([ii for ii in controlelem_index], [ii for ii in PVbus_index])].imag.transpose(),
                temp_imag)), axis=0)
            I_gradient = 2 * I_gradient_real + 2 * I_gradient_imag
        else:
            I_gradient = 0

        gradient = PVcost_fun_gradient + Vmag_gradient + I_gradient / 1000

        # compute x1, mu1
        x1 = np.concatenate([x0[:NPV] - stepsize_xp * gradient[:NPV], x0[NPV:] - stepsize_xq * gradient[NPV:]])
        [x1, Pmax_allPV, Qmax_allPV] = project_PV(x1, PV_Pmax_forecast, PV_inverter_size)
        x1 = np.array([round(ii, 5) for ii in x1])

        mu_Vmag_lower1 = mu_Vmag_lower0 + stepsize_mu * (Vlower - np.array(Vmes))
        mu_Vmag_upper1 = mu_Vmag_upper0 + stepsize_mu * (np.array(Vmes) - Vupper)
        mu_Vmag_lower1 = project_dualvariable(mu_Vmag_lower1)
        mu_Vmag_upper1 = project_dualvariable(mu_Vmag_upper1)
        if mu_I0:
            mu_I1 = mu_I0 + stepsize_mu / 300 * np.array(list(map(lambda x: x[0] * x[0] - x[1] * x[1], zip(Imes, Imes_limit))))
            mu_I1 = project_dualvariable(mu_I1)
        else:
            mu_I1 = mu_I0
        mu1 = [mu_Vmag_upper1,mu_Vmag_lower1,mu_I1]
        # =========================================Yiyun's Notes===========================================#
        # Each time of calling DERMS.control, it is a one step update of PV real and reactive power outputs
        # =================================================================================================#

        return [x1,mu1]
