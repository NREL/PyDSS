# Dynamic Voltage Support Controller (DynamicVoltageSupport.py)
The DynamicVoltageSupport (DVS) controller will control the DER to provide "rapid reactive power exchanges during voltage excursions" per 1547-2018 clause 6.4.2.6. The addition of DVS for DER objects may improve system stability during faults and/or improve ride-through capabilities for DERs. 

The DynamicVoltageSupport controller works with OpenDSS **Generator** objects and can be applied to one or more generators. Generator objects must be **3ph** and must have the following parameters defined: **kV**, **kVA**, **kW**, **kVAr**. The opendss generator model defined in the opendss file does not matter when using this controller as it will be overwritten by the controller upon initialization. The controller is designed to **mimic the current-limited behavior of OpenDSS generator model 7**. For comparison purposes, one can run a baseline simulation without this controller using generator model 7. 

DVS can be use alone or can be coupled with the **PvVpltageRideThru** controller (see notes below on required parameters). This controller can be used in both **QSTS** and **dynamic** simulations.

## Controller Assignment
The controller may be assigned to DERs via the pydss registry. 

## Controller Settings .toml File
The following is an example of the required Settings.toml file for implementing DVS control. Each of these fields must be defined and linked in the controller registry. 

**Example Settings.toml file:**\
[DVS]\
"Trv" = 0.001\
"dbd1" = -0.12\
"dbd2" = 0.1\
"Kqv" = 100\
"iqh1" = 1.1\
"iql1" = -1.1\
"kvar_max" = 0.44\
"kvar_min" = -0.44\
"capacitive_support" = true\
"inductive_support" = true\
"post_fault_reset" = 1\
"overvoltage_kva_limited" = true\
"current_limited_error_tolerance" = 0.0001\
"priority" = "var"\
"Use with Voltage Ride Through" = false

**Parameter Definitions:**\
**TRV** = Time-constant for voltage transducer. Use a smaller number for a faster DER response.\
**dbd1** = single-sided lower deadband (∆V p.u). DER will provide DVS when voltage drops below this threshold.\
**dbd2** = single-sided upper deadband (∆V p.u). DER will provide DVS when voltage rises above this threshold.\
**Kqv** = proportional gain constant. Use a larger value for a faster reactive power ramp.\
**iqh1** = current limit for injection (p.u). Typical is 1.1 p.u.\
**iql1** = current limit for absorption (p.u.) --> THIS IS NOT USED\
**kvar_max** = max kvar injection (p.u). This should be a positive number. If set to 0.44, the DER will provide 44% of its nameplate rating as reactive power injection. Depending on the inverter headroom it will curtail active power to reach this.\
**kvar_min** = max kvar absorption (p.u). This should be a negative number. If set to -0.44, the DER will provide 44% of its nameplate rating as reactive power absorption. Depending on the inverter headroom it will curtail active power to reach this.\
**capacitive_support** = bool indicating if gen will provide capacitive support. If true, DER will inject reactive power during undervoltage events. If false, DER will take no action during undervoltage events.\
**inductive_support** = bool indicating if gen will provide inductive support.If true, DER will absorb reactive power during overvoltage events. If false, DER will take no action during overvoltage events.\
**post_fault_reset** = time (s) after fault before gen provides more support. This can be used to avoid cyclic behavior when voltages hover around the deadband values.\
**overvoltage_kva_limited** = bool indicating if gen is kva limited. If true, DER will be limited by it's kva rating. This only makes a difference during overvoltage events (when the kva nameplate is more limiting than the current limit), or if the current limit is set below 1.0\
**current_limited_error_tolerance** = error tolerance (%) when evaluating current limit adherance. Use a larger number to improve convergence. Larger numbers may result in more noticeable discrepancies between the current limit using OpenDSS Generator model 7 and that implemented by this controller.\
**priority** = var vs watt priority --> DVS is always in VAr priority. THIS IS NOT USED \
**Use with Voltage Ride Through** = bool indicating if DVS controller is used in conjunction with the VRT controller. If the user is coupling this controller with the PvVoltageRideThru controller, this must be set to true. There is a an equivalent setting in the PvVoltageRideThru settings .toml file ('Use with Dynamic Voltage Support') to indicate it is being used alongside DVS controller, which also must be set to true. 

## Example Results (created using controller version 1.0)
The following results show a single generator object's reaction to a FIDVR or to simple step changes in voltage simulated with a voltage profile applied at the slack bus. The dotted lines represent a baseline simulation run without DVS, utilizing generator model 7, vminpu=0.91, and vmaxpu=1.1. The values plotted are PCC voltage, DER powers, and DER Currents. Voltage sags are balanced. 

### Varying 1qh1
**iqh1=1.1:** Notice the significant real power curtailment during the initial voltage sag and moderate curtailment as voltage is slow to recover.\
![](images\iqh1_1_1.png)

**iqh1=2.0:** Notice the significant current spike during the initial drop in voltage and less active power curtailment during this period. \
![](images\iqh1_2_0.png)

### Varying kvarmax
**kvarmax=0.44:** With peak generation around 85 kVA, prior to the fault, 0.44 represents about 37 kVA. The middle plot confirms this. \
![](images\iqh1_1_1.png)

**kvarmax=1.0:** One can set the inverter to produce *only* reactive power during a fault, sacrificing all active power production. Here we see reactive power climb to 85 kVA and active power drop to zero. \
![](images\kvarmax_1_0.png)

### Capacitive and Inductive Support
**Capacitive_support=true**, **Inductive_support=false:** Notice the DER only provides capacitive support during the simulated undervoltage event, taking no action during the overvoltage event.\
![](images\capacitive_only.png)

**Capacitive_support=false**, **Inductive_support=true:** Notice the DER only provides inductive support during the simulated overvoltage event, taking no action during the undervoltage event.\
![](images\inductive_only.png)

**Capacitive_support=true**, **Inductive_support=true:** Notice the DER provides support during both events, taking no action during the overvoltage event.\
![](images\both_support.png)

### Overvoltage kVA limiting
**overvoltage_kva_limited = true:** During an overvoltage event the DER will not exceed its kVA nameplate limit, despite not hitting its current limit. This is consistent with OpenDSS model 7.\
![](images\kva_limit_true.png)

**overvoltage_kva_limited = false:** During an overvoltage event the DER will exceed its kVA nameplate limit up to its current limit.\
![](images\kva_limit_false.png)

### Modeling Multiple Generators with DVS Control
28, 3ph generators modeled below.\
![](images\multi_gen.png)

## Combining DVS and VRT Controller
The following scenario descriptions represent the 13 scenarios plotted below, used to illustrate the effects of combining DVS and VRT. This uses a smart-DS feeder with 28, 200 kW generator objects (total 5.6 MW or 86% peak load).\

1. **Baseline_No_Trip** 
    * No controllers used. 
    * All generators set to use model 7. 
2.	**NO_VRT** 
    * Instantaneous tripping below 0.88 p.u. No voltage ride-through capabilities. 
    * No dynamic voltage support
3.	**NO_VRT_DVS** 
    * Instantaneous tripping below 0.88 p.u. No voltage ride-through capabilities. 
    * Dynamic voltage support active, providing current limit enforcement, and providing capacitive support during undervoltages. 
4.	**NO_VRT_DVS_INACTIVE** 
    * Instantaneous tripping below 0.88 p.u. 
    * No voltage ride-through capabilities. 
    * Dynamic voltage support active and enforcing current limit, but not providing any capacitive support. 
5.	**VRT_CAT_I** 
    * 1547 Category I voltage ride through settings. 
    * No dynamic voltage support
6.	**VRT_CAT_I_DVS**
    * 1547 Category I voltage ride through settings. 
    * Dynamic voltage support active, providing current limit enforcement, and providing capacitive support during undervoltages. 
7.	**VRT_CAT_I_DVS_INACTIVE**
    * 1547 Category I voltage ride through settings.
    * Dynamic voltage support active and enforcing current limit, but not providing any capacitive support. 
8.	**VRT_CAT_II** 
    * 1547 Category II voltage ride through settings. 
    * No dynamic voltage support
9.	**VRT_CAT_II_DVS**
    * 1547 Category II voltage ride through settings. 
    * Dynamic voltage support active, providing current limit enforcement, and providing capacitive support during undervoltages. 
10.	**VRT_CAT_II_DVS_INACTIVE**
    * 1547 Category II voltage ride through settings.
    * Dynamic voltage support active and enforcing current limit, but not providing any capacitive support. 
11.	**VRT_CAT_III** 
    * 1547 Category III voltage ride through settings. 
    * No dynamic voltage support
12.	**VRT_CAT_III_DVS**
    * 1547 Category III voltage ride through settings. 
    * Dynamic voltage support active, providing current limit enforcement, and providing capacitive support during undervoltages. 
13.	**VRT_CAT_III_DVS_INACTIVE**
    * 1547 Category III voltage ride through settings.
    * Dynamic voltage support active and enforcing current limit, but not providing any capacitive support.

### Ride-Through Category: No Voltage Ride Through
* All 28 generators trip. Aggregate generation drops to 0 kW immediately. 
* Average PCC voltage drops (compared with baseline) due to all DERs tripping offline.
* Adding dynamic voltage support makes no difference, given the instantaneous trip. Generators start to ramp up kVAR production prior to tripping.

![](images\no_vrt_1.png)
![](images\no_vrt_2.png)
![](images\no_vrt_3.png)

### Ride-Through Category: 1547 Category I
* 26/28 DERs trip offline in VRT_CAT_I without any DVS. 
* 0/28 DERs trip when also adding DVS.
* We see an improvement in average PCC voltage (compared to baseline) due to VAR support from DVS (green vs. blue line in top chart). 
* The reduction in aggregate kW generation in VRT_CAT_I_DVS (compared to baseline) is due to real power curtailment to provide VAR support.

![](images\cat_1_1.png)
![](images\cat_1_2.png)
![](images\cat_1_3.png)

### Ride-Through Category: 1547 Category II
* 0/28 DERs trip regardless of whether DVS is active or not. 
* We still see improvement in average PCC voltages when DVS is active. 

![](images\cat_2_1.png)
![](images\cat_2_2.png)
![](images\cat_2_3.png)

### Ride-Through Category: 1547 Category III
* 26/28 DERs trip offline, 0 with DVS. Momentary cessation capability allows for re-entering service as voltage recovers. 
* Slight discrepancy in when DERs re-enter service between VRT_CAT_III and VRT_CAT_III_DVS_INACTIVE scenarios, which needs to be investigated further. 

![](images\cat_3_1.png)
![](images\cat_3_2.png)
![](images\cat_3_3.png)


