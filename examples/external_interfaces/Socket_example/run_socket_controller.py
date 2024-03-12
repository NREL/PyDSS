# first of all import the socket library
import socket
import struct
import time 
# next create a socket object

def example():
    sockets = []
    for i in range(2):
        print("socket bound")
        s = socket.socket()
        s.bind(('127.0.0.1', 5001 + i))
        s.listen(5)
        sockets.append(s)
        print(sockets)

    while True:
        # Establish connection with client.
        conns = []
        for s in sockets: 
            c, addr = s.accept()
            print(c, addr)
            conns.append(c)

        while True:
            for c in conns:
                Data = c.recv(1024)
                print(Data)
                if Data:
                    numDoubles = int(len(Data) / 8)
                    tag = str(numDoubles) + 'd'
                    Data = list(struct.unpack(tag, Data))
                    print(Data)
                

            for c , v in zip(conns, [5, 3]):
                values = [v]
                print(values)
            c.sendall(struct.pack('%sd' % len(values), *values))
            
if __name__ == "__main__":
    example()

