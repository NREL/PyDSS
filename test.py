from PyDSS import pyDSS

a = pyDSS.instance()
#a.create_new_project('as', 'fd')
print(a.run('project', 'scenario1'))