from os.path import dirname, basename, isfile
from pydss.ProfileManager import hooks
import importlib
import glob


modules = glob.glob(hooks.__path__[0]+"/*.py")
pythonFiles = [(basename(f)[:-3], f) for f in modules if isfile(f) and not f.endswith('__init__.py')]

ProfileInterfaces = {}
modules_instances = {}
for module, file in pythonFiles:
    spec = importlib.util.spec_from_file_location(module, file)
    modules_instances[module] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modules_instances[module])
    ProfileInterfaces[module] = modules_instances[module].ProfileManager

def Create(sim_instance, solver, settings, logger, **kwargs):
    source_type = settings.profiles.source_type.value
    if source_type in ProfileInterfaces:
        PostProcessor = ProfileInterfaces[source_type](
            sim_instance, solver, settings, logger, **kwargs
        )
    else:
        raise ModuleNotFoundError(f"{source_type} is not a valid source type. Valid values are {','.join(list(ProfileInterfaces.keys()))}")
    return PostProcessor
