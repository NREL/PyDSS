from PyDSS import PyDSS

a = PyDSS.instance()
#a.create_new_project('as', 'fd')
print(a.run('Automated_comparison_example', 'fd'))