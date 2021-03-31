from os.path import dirname, basename, isfile
from PyDSS.ProfileManager import hooks
import glob


modules = glob.glob(hooks.__path__[0]+"/*.py")
pythonFiles = [basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]

ProfileInterfaces = {}
for file in pythonFiles:
    exec('from PyDSS.ProfileManager.hooks import {}'.format(file))
    exec('ProfileInterfaces["{}"] = {}.ProfileManager'.format(file, file))


def Create(sim_instance, solver, options, logger, **kwargs):
    source_type = options["Profiles"]["source_type"]
    if source_type in ProfileInterfaces:
        PostProcessor = ProfileInterfaces[source_type](
            sim_instance, solver, options, logger, **kwargs
        )
    else:
        raise ModuleNotFoundError(f"{source_type} is not a valid source type. Valid values are {','.join(list(ProfileInterfaces.keys()))}")
    return PostProcessor
