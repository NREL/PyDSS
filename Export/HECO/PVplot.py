from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
import os

FileList = ['PVsystems-VoltagesMagAng.csv', 'PVsystems-Powers.csv']
Folder = 'HP-VV-VW-R'
Root = os.getcwd()

Voltages = pd.read_csv(os.path.join(Root,Folder,FileList[0]), dtype=float)
Columns  = Voltages.columns
Voltages = Voltages[Columns[::2]]

Powers   = pd.read_csv(os.path.join(Root,Folder,FileList[1]), dtype=float)
Columns  = Powers.columns
pPowers  = Powers[Columns[0:-1:2]]
qPowers  = Powers[Columns[1:-1:2]]

print(pPowers.columns)
print(qPowers.columns)
qPowers.columns = pPowers.columns

PVlist = Voltages.columns
for PVname in PVlist:
    if PVname != 'Unnamed: 3384':
        U = Voltages[PVname]
        P = pPowers[PVname]
        Q = qPowers[PVname]
        if U.mean() < 3000:
            U = np.divide(U, 240)
        else:
            U = np.divide(U, 7200)

        if  max(U) > 1.07 and max(abs(Q))> 0.1:
            fig, axs = plt.subplots(3,1)
            plt.title(PVname)
            axs[0].plot(U)
            plt.title(PVname)
            axs[1].plot(P)
            plt.title(PVname)
            axs[2].plot(Q)
            plt.draw()
            plt.pause(1)  # <-------
            input("<Hit Enter To Close>")
            plt.close(fig)