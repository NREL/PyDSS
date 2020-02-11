from os.path import dirname, basename, isfile
import glob

from PyDSS.pyPostprocessor import PostprocessScripts




modules = glob.glob(PostprocessScripts.__path__[0]+"/*.py")
pythonFiles = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]

POST_PROCESSES = {}
for file in pythonFiles:
    exec('from PyDSS.pyPostprocessor.PostprocessScripts import {}'.format(file))
    exec('POST_PROCESSES["{}"] = {}.{}'.format(file, file, file))

def Create(dssInstance, dssSolver, dssObjects, dssObjectsByClass, simulationSettings, Logger):
    test = None
    PostProcessorClass = None
    ScriptName = simulationSettings['PostProcess']['Post processing script']

    assert (ScriptName in pythonFiles), \
        "Defination for '{}' post process script not found. \n " \
        "Please define the controller in ~PyDSS\pyPostprocessor\PostprocessScripts".format(
            ScriptName
    )
    PostProcessor = POST_PROCESSES[ScriptName](dssInstance, dssSolver, dssObjects, dssObjectsByClass,
                                               simulationSettings, Logger)
    return PostProcessor
