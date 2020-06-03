import os
import logging
from multiprocessing import current_process
import inspect
from queue import Empty
from PyDSS.dssInstance import OpenDSS
from PyDSS.valiate_settings import validate_settings
from PyDSS.api.src.web.parser import restructure_dictionary
logger = logging.getLogger(__name__)

class PyDSS:

    commands = {
        "run" : None
    }

    def __init__(self, event=None, queue=None):

        self.initalized = False
        self.uuid = current_process().name

        ''' TODO: work on logging.yaml file'''
        
        logging.info("{} - initiallized ".format({self.uuid}))

        self.shutdownevent = event
        self.queue = queue

        try:
            self.pydss_obj = OpenDSS()
        except:
            result = {"Status": 500, "Message": f"Failed to create a PyDSS instance"}
            self.queue.put(result)
            return

        #self.RunSimulation()
        logger.info("{} - pydss dispatched".format(self.uuid))

        result = {
            "Status": 200,
            "Message": "PyDSS {} successfully initialized.".format(self.uuid),
            "UUID":self.uuid
        }

        if self.queue != None: self.queue.put(result)

        self.run_process()
    
    def run_process(self):
        logger.info("PyDSS simulation starting")
        while not self.shutdownevent.is_set():
            try:
                task = self.queue.get()
                if task == 'END':
                    break
                elif "parameters" not in task:
                    result = {
                        "Status": 500,
                        "Message": "No parameters passed"
                    }
                else:
                    command = task["command"]
                    parameters = task["parameters"]
                    if hasattr(self, command):
                        func = getattr(self, command)
                        status, msg = func(parameters)
                        result = {"Status": status, "Message": msg, "UUID": self.uuid}
                    else:
                        logger.info(f"{command} is not a valid PyDSS command")
                        result = {"Status": 500, "Message": f"{command} is not a valid PyDSS command"}
                self.queue.put(result)
            
            except Empty:
                continue

            except (KeyboardInterrupt, SystemExit):
                break
        logger.info(f"{self.uuid} - finishing PyDSS simulation")


    def close_instance(self):
        del self.pydss_obj
        logger.info(f'PyDSS case {self.uuid} closed.')

    def init(self, params):
        logger.info(f'Reading pydss project')

        args = restructure_dictionary(params)

        try:
            validate_settings(args)
            logger.info(f'Parameter validation a success')
        except Exception as e:
            return 500, f"Invalid simulation settings passed, {e}"

        try:
            self.pydss_obj.init(args)
            self.initalized = True
            return 200, "PyDSS project successfully loaded"
        except Exception as e:
            return 500, f"Failed to load a PyDSS project, {e}"

    def run(self, params):
        if self.initalized:
            try:
                Steps, sTime, eTime = self.pydss_obj._dssSolver.SimulationSteps()
                for i in range(Steps):
                    update_dict = {} #TODO: will be ued to interface with websocket implemntation (helics subscriptions)
                    results = self.pydss_obj.RunStep(i, update_dict)
                    #TODO: results will be ued to interface with websocket implemntation (helics publications)
                self.initalized = False
                return 200, f"Simulation complete..."
            except Exception as e:
                self.initalized = False
                return 500, f"Simulation crashed at at simulation time step: {self.pydss_obj._dssSolver.GetDateTime()}, {e}"
        else:
            return 500, f"No project initialized. Load a project first using the 'init' command"

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logger.basicConfig(level=logger.INFO, format=FORMAT)
    a = PyDSS()
    del a
