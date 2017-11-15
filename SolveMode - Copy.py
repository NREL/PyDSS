import matplotlib.pyplot as plt

uMinC = 1.02
uMaxC = 1.05


m = 0
c = 0
x = []
PFhist = []

for i in range (60):
    uIn = 1.0+ i/1000
    print('uIn : ', uIn)
    x.append(uIn)
    m = 1 / (uMinC - uMaxC)
    c = uMaxC / (uMaxC - uMinC)

    if uIn < uMinC:
        Pcalc = 1
    elif uIn < uMaxC and uIn >= uMinC:
        Pcalc = m * uIn + c
    elif uIn >= uMaxC:
        Pcalc = 0

    PFhist.append(Pcalc)

print ('Umin : '+ str(uMinC))
print ('Umax : '+ str(uMaxC))
print ('y='+str(m)+'.x+' +str(c))
plt.plot(x,PFhist)
plt.show()