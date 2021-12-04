# This file defines a UDP frame
import numpy as np

sample_rate = 48000
signal0 = [0.5, 0.5, 0.5, -0.5, -0.5, -0.5]
signal1 = [-0.5, -0.5, -0.5, 0.5, 0.5, 0.5]


def modulate_string(string):
    modulated_array = []
    for i in string:
        if i == '0':
            modulated_array.append(signal0)
        else:
            modulated_array.append(signal1)
    if len(modulated_array) != 0:
        modulated_array = np.concatenate(modulated_array)
    return modulated_array


class UDPFrame:
    """
    A UDP frame consists of three main parts:
        | IP | PORT | load |
    where IP contains src ip and dest ip
        PORT contains src port and dest port
    """

    def __init__(self):
        self.src_ip = None
        self.dest_ip = None
        self.src_port = None
        self.dest_port = None
        self.load = None

    def get(self):
        return self.src_ip + self.dest_ip + self.src_port + self.dest_port + self.load

    def set_src_ip(self, src_ip):
        self.src_ip = src_ip

    def set_dest_ip(self, dest_ip):
        self.dest_ip = dest_ip

    def set_src_port(self, src_port):
        self.src_port = src_port

    def set_dest_port(self, dest_port):
        self.dest_port = dest_port

    def set_load(self, load):
        self.load = load

    def get_src_ip(self):
        return self.src_ip

    def get_dest_ip(self):
        return self.dest_ip

    def get_src_port(self):
        return self.src_port

    def get_dest_port(self):
        return self.dest_port

    def get_load(self):
        return self.load

    def modulate(self):
        return np.concatenate(
            [modulate_string(self.src_ip), modulate_string(self.dest_ip), modulate_string(self.src_port),
             modulate_string(self.dest_port), modulate_string(self.load), modulate_string(self.load)])
