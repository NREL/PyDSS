import matplotlib.pyplot as plt

uMin = 0.95
uMax = 1.05
uDbMin = 0.98
uDbMax = 1.02
QlimPU = 0.40


m = 0
c = 0
x = []
Qhist = []

for i in range (150):
    uIn = 0.925 + i/1000
    print('uIn : ', uIn)
    x.append(uIn)
    m1 = QlimPU / (uMin - uDbMin)
    m2 = QlimPU / (uDbMax - uMax)
    c1 = QlimPU * uDbMin / (uDbMin - uMin)
    c2 = QlimPU * uDbMax / (uMax - uDbMax)

    if uIn <= uMin:
        Qcalc = QlimPU
    elif uIn <= uDbMin and uIn > uMin:
        Qcalc = uIn * m1 + c1
    elif uIn <= uDbMax and uIn > uDbMin:
        Qcalc = 0
    elif uIn <= uMax and uIn > uDbMax:
        Qcalc = uIn * m2 + c2
    else:
        Qcalc = -QlimPU

    Qhist.append(Qcalc)


plt.plot(x,Qhist)
plt.show()