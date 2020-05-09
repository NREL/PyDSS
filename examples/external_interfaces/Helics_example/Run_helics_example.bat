call "C:\ProgramData\Anaconda3\Scripts\activate.bat"
call conda activate disco_pydss
pause
start python run_dummy_federate.py
timeout 3
python run_pyDSS.py
pause