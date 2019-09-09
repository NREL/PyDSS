from PyDSS.pyAnalyzer.dssResult import dssResult
import os

class VisualizerInstance:
    def __init__(self, **kwargs):
        rootPath = kwargs['Project Path']
        self.__projects = list(os.walk(os.path.join(rootPath)))[0][1]
        self.__active_project = self.__list_projects()
        exportsPath = os.path.join(rootPath, self.__active_project, 'Exports')
        self.__scenarios = list(os.walk(os.path.join(exportsPath)))[0][1]
        self.__scenarios_dict = {}
        for scenario in self.__scenarios:
            self.__scenarios_dict[scenario] = dssResult(os.path.join(exportsPath, scenario))
        return

    def __list_projects(self):
        print('Project list')
        self.__project_dict = {}
        for i, project in enumerate(self.__projects):
            self.__project_dict[i] = project
            print('{}. {}'.format(i, project))
        print('')
        projectKey = input('SEnter a project number: ')
        active_project = self.__project_dict[int(projectKey)]
        return active_project
