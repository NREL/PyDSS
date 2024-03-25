from multiprocessing import current_process
from queue import Empty
import os

from loguru import logger

from pydss.simulation_input_models import SimulationSettingsModel
from pydss.api.src.app.JSON_writer import JSONwriter
from pydss.dssInstance import OpenDSS


class PyDSS:
    commands = {
        "run": None
    }

    def __init__(self, event=None, queue=None, parameters=None):

        self.initalized = False
        self.uuid = current_process().name

        ''' TODO: work on logging.yaml file'''

        logger.info("{} - initialized ".format({self.uuid}))

        self.shutdownevent = event
        self.queue = queue

        try:
            settings = SimulationSettingsModel(**parameters['parameters'])
            self.pydss_obj = OpenDSS(settings)
            export_path = os.path.join(self.pydss_obj._dssPath['Export'], settings.project.active_scenario)
            Steps, sTime, eTime = self.pydss_obj._dssSolver.SimulationSteps()
            self.a_writer = JSONwriter(export_path, Steps)
            self.initalized = True
        except:
            result = {"Status": 500, "Message": f"Failed to create a pydss instance"}
            self.queue.put(result)
            return

        # self.RunSimulation()
        logger.info("{} - pydss dispatched".format(self.uuid))

        result = {
            "Status": 200,
            "Message": "Pydss {} successfully initialized.".format(self.uuid),
            "UUID": self.uuid
        }

        if self.queue != None: self.queue.put(result)

        self.run_process()

    def run_process(self):
        logger.info("Pydss simulation starting")
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
                        logger.info(f"{command} is not a valid pydss command")
                        result = {"Status": 500, "Message": f"{command} is not a valid pydss command"}
                self.queue.put(result)

            except Empty:
                continue

            except (KeyboardInterrupt, SystemExit):
                break
        logger.info(f"Pydss subprocess {self.uuid} has ended")

    def close_instance(self):
        del self.pydss_obj
        logger.info(f'Pydss case {self.uuid} closed.')

    def run(self, params):
        if self.initalized:
            try:
                Steps, sTime, eTime = self.pydss_obj._dssSolver.SimulationSteps()
                for i in range(Steps):
                    results = self.pydss_obj.RunStep(i)
                    restructured_results = {}
                    for k, val in results.items():
                        if "." not in k:
                            class_name = "Bus"
                            elem_name = k
                        else:
                            class_name, elem_name = k.split(".")
                        if class_name not in restructured_results:
                            restructured_results[class_name] = {}
                        if not isinstance(val, complex):
                            restructured_results[class_name][elem_name] = val
                    self.a_writer.write(
                        self.pydss_obj._Options["Helics"]["Federate name"],
                        self.pydss_obj._dssSolver.GetTotalSeconds(),
                        restructured_results,
                        i
                    )

                self.initalized = False
                return 200, f"Simulation complete..."
            except Exception as e:
                self.initalized = False
                return 500, f"Simulation crashed at at simulation time step: {self.pydss_obj._dssSolver.GetDateTime()}, {e}"
        else:
            return 500, f"No project initialized. Load a project first using the 'init' command"

    def registerPubSubs(self, params):
        subs = params["Subscriptions"]
        pubs = params["Publications"]
        self.pydss_obj._HI.registerPubSubTags(pubs, subs)
        return 200, f"Publications and subscriptions have been registered; Federate has entered execution mode"


if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logger.basicConfig(level=logger.INFO, format=FORMAT)
    a = PyDSS()
    del a
