import pandas as pd
import numpy as np
import os

FileList = ['Loads-VoltagesMagAng.csv', 'PVsystems-Powers.csv']
FolderList = ['HP-Legacy', 'HP-VV']
Root = os.getcwd()

VoltageRanges = {
    'Voltages-Legacy' : '',
    'Voltages-VV':'',
}

dP = 0

Data = {}
for i, Folder in enumerate(FolderList):
    for File in FileList:
        FilePath = os.path.join(Root,Folder,File)
        if Folder not in Data:
            Data[Folder] = {}
        FileData = pd.read_csv(FilePath, dtype=float)
        Columns = FileData.columns
        FileData = FileData[Columns[::2]]
        if 'Loads' in File:
            FileData = FileData.loc[:, (FileData != 0).any(axis=0)]
            Vmax = FileData.max()
            Vmin = FileData.min()
            print (np.divide(np.subtract(Vmax, Vmin),Vmin))
            if VoltageRanges['Voltages-Legacy'] is '':
                VoltageRanges['Voltages-Legacy'] = np.divide(np.subtract(Vmax, Vmin),Vmin)
            else:
                VoltageRanges['Voltages-VV'] = np.divide(np.subtract(Vmax, Vmin),Vmin)


        Data[Folder][File.split('.')[0]] = FileData

VoltageDeviation = np.divide(VoltageRanges['Voltages-VV'], VoltageRanges['Voltages-Legacy'])
print('Voltage Deviations')
print((VoltageRanges['Voltages-VV'].max() - VoltageRanges['Voltages-VV'].min())/\
(VoltageRanges['Voltages-Legacy'].max() - VoltageRanges['Voltages-Legacy'].min()))

print('Minimum load voltage deviation - ' + str(VoltageDeviation.min()) + ' p.u.')
print('Average load voltage deviation - ' + str(VoltageDeviation.mean()) + ' p.u.')
print('Maximum load voltage deviation - ' + str(VoltageDeviation.max()) + ' p.u.')

dP = np.subtract(Data['HP-Legacy']['PVsystems-Powers'], Data['HP-VV']['PVsystems-Powers'])

dP = dP.fillna(0)
print('Curtailment ' + str(dP.sum().sum()/4) + ' kWh')
dP = np.divide(dP, Data['HP-Legacy']['PVsystems-Powers'])
dP = np.multiply(dP, 100)
print('Minimum PV power deviation - ' + str(dP.min().min()/10) + '%')
print('Average PV power deviation - ' + str(dP.mean().mean()) + '%')
print('Maximum PV power deviation - ' + str(dP.max().max()) + '%')

newdP = dP.cumsum(axis = 0)


