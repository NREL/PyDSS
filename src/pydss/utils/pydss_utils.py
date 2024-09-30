import numpy as np
import math

def form_Yprim(values):
    dimension = int(math.sqrt(len(values) / 2))
    Yprim = np.array([[complex(0, 0)] * dimension] * dimension)
    for ii in range(dimension):
        for jj in range(dimension):
            Yprim[ii][jj] = complex(values[dimension * ii * 2 + 2 * jj], values[dimension * ii * 2 + 2 * jj + 1])
    return Yprim

def form_Yprim_2(values):
    Ydim = int(math.sqrt(len(values) / 2))
    Yreal = np.array(values[0::2]).reshape((Ydim, Ydim))
    Yimag = np.array(values[1::2]).reshape((Ydim, Ydim))
    Yprim = Yreal + 1j * Yimag
    return Yprim


def get_Yprime_Matrix(dssObjects):
    Elements = dssObjects["Lines"] + dssObjects["Transformers"]
    nElements = len(Elements)
    Ybranch_prim = np.array([[complex(0, 0)] * 2 * nElements] * 2 * nElements)

