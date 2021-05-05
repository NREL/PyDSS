# first of all import the socket library
import socket
import struct

# next create a socket object
sockets = []
for i in range(2):
    s = socket.socket()
    s.bind(('127.0.0.1', 5001 + i))
    s.listen(5)
    sockets.append(s)

while True:
    # Establish connection with client.
    conns = []
    for s in sockets:
        c, addr = s.accept()
        conns.append(c)

    while True:
        for c in conns:
            Data = c.recv(1024)
            if Data:
                numDoubles = int(len(Data) / 8)
                tag = str(numDoubles) + 'd'
                Data = list(struct.unpack(tag, Data))

        for c , v in zip(conns, [5, 3]):
            values = [v]
            c.sendall(struct.pack('%sd' % len(values), *values))

