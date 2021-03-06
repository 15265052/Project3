import os
import socket
import time


# UDP Client to send data, i.e. NODE2
def byte_to_str(byte):
    bi = bin(byte)[2:]
    return (8 - len(bi)) * "0" + bi


address = ("10.20.234.160", 12527)
sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for i in range(10):
    rand_byte = os.urandom(20)
    sck.sendto(rand_byte, address)

    print("Time: ", i, "s Send", str(rand_byte))
    time.sleep(1)
sck.close()
print("Finished sending....")
