from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
import os

FileList = ['PVsystems-VoltagesMagAng.csv', 'PVsystems-Powers.csv']
FolderList = ['HP-VV' , 'HP-VV-VW-R']
Root = os.getcwd()
Data = {}
for i, Folder in enumerate(FolderList):
    for File in FileList:
        FilePath = os.path.join(Root,Folder,File)
        if Folder not in Data:
            Data[Folder] = {}
        FileData = pd.read_csv(FilePath, dtype=float)
        Columns = FileData.columns
        # drop all odd columns
        FileData = FileData[Columns[::2]]
        # drop all zero columns
        FileData = FileData.loc[:, (FileData != 0).any(axis=0)]
        if 'VoltagesMagAng' in File:
            Columns = FileData.columns
            for col in Columns:
                if FileData[col].mean() < 5000:
                    FileData[col] = np.divide(FileData[col], 240)
                else:
                    FileData[col] = np.divide(FileData[col], 7200)
            print(FileData)
        else:
            FileData = np.multiply(FileData, -1)
        FileData.plot(legend=False)
        plt.title(Folder)
        #FileData.plot(legend=False, color='grey' , alpha=0.4)
plt.show()