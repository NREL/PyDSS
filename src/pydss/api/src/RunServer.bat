call activate naerm-pydss
start chrome http://127.0.0.1:5000/docs
python main.py -e ../endpoints.yaml -l ../logging.yaml
