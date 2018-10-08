##!/usr/bin/env bash
# *** PyDSS Runs ***

cd \\Users\\memmanue\\Desktop\\PyDSS

# check log files for convergence issues and whether the run completed
#grep "no conv" *\\*.log
#grep seconds *\\*.log
#findstr "no conv" */*.log
#findstr seconds */*.log

# Mikilua Scenarios (with upgrades)
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-None --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-None-D --dss_file MasterCircuit_Mikilua_baseline2.dss

python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VV --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VV-D --dss_file MasterCircuit_Mikilua_baseline2.dss

python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VW --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VW-D --dss_file MasterCircuit_Mikilua_baseline2.dss

# Mikilua Scenarios (no upgrades)
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-None --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-None-D --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VV --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VV-D --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VW --dss_file MasterCircuit_Mikilua_baseline2.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario None-VW-D --dss_file MasterCircuit_Mikilua_baseline2.dss

python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-None --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-None-D --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-VV --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-VV-D --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-VVall --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-VVall-D --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-VW --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30-VW-D --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss

python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30VV-VV --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30VV-VV-D --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30VV-VW --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario CSS30VV-VW-D --dss_file MasterCircuit_Mikilua_baseline2_CSS30.dss

python dssSingleRunCmd.py --active_project Mikilua --active_scenario ESS-VW --dss_file MasterCircuit_Mikilua_baseline2_ESS.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario ESS-VW-D --dss_file MasterCircuit_Mikilua_baseline2_ESS.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario ESSRural-VW --dss_file MasterCircuit_Mikilua_baseline2_ESS_Rural.dss
python dssSingleRunCmd.py --active_project Mikilua --active_scenario ESSRural-VW-D --dss_file MasterCircuit_Mikilua_baseline2_ESS_Rural.dss

# Spohn-Curtailment scenarios
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Baseline-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Baseline-15min --dss_file MasterCircuit_15min.dss

python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg3Top-VW0-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg3Top-VW0-15min --dss_file MasterCircuit_15min.dss

python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg3Top-VW1End-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg3Top-VW1End-15min --dss_file MasterCircuit_15min.dss

python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg3Top-VW3End-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg3Top-VW3End-15min --dss_file MasterCircuit_15min.dss

python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg5Top-VW0-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg5Top-VW0-15min --dss_file MasterCircuit_15min.dss

python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg5Top-VW1End-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg5Top-VW1End-15min --dss_file MasterCircuit_15min.dss

python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg5Top-VW2End-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario Leg5Top-VW2End-15min --dss_file MasterCircuit_15min.dss

python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario NoLeg-1min --dss_file MasterCircuit_1min.dss --step_resolution_min 1
python dssSingleRunCmd.py --active_project Spohn-Curtailment --active_scenario NoLeg-15min --dss_file MasterCircuit_15min.dss
