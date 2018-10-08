# *** PyDSS Runs ***

cd \\Users\\memmanue\\PyDSS\\bin

# check log files for convergence issues and whether the run completed
#grep "no conv" */*.log
#grep seconds */*.log

python3 dssSingleRunCmd.py --start_day 20 --end_day 26 --active_project Mikilua --active_scenario None-None-D --dss_file MasterCircuit_Mikilua_baseline2.dss
python3 dssSingleRunCmd.py --start_day 20 --end_day 26 --active_project Mikilua --active_scenario None-VV-D --dss_file MasterCircuit_Mikilua_baseline2.dss
python3 dssSingleRunCmd.py --start_day 20 --end_day 26 --active_project Mikilua --active_scenario None-VW-D --dss_file MasterCircuit_Mikilua_baseline2.dss

python3 dssSingleRunCmd.py --start_day 20 --end_day 26 --active_project Mikilua --active_scenario None-None --dss_file MasterCircuit_Mikilua_baseline2.dss
python3 dssSingleRunCmd.py --start_day 20 --end_day 26 --active_project Mikilua --active_scenario None-VV --dss_file MasterCircuit_Mikilua_baseline2.dss
python3 dssSingleRunCmd.py --start_day 20 --end_day 26 --active_project Mikilua --active_scenario None-VW --dss_file MasterCircuit_Mikilua_baseline2.dss
