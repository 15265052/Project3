"""This file defines the MAC frame structure and supplies some functions to implement the frame"""
import numpy as np

MAC_load_limit = 200  # in bits length
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


class MACFrame:
    """
    A MAC Frame structure is shown below:
        | TYPE | MAC load |
        4 bits for type field
    MAC load's length is limited, its limitation is defined in config/globalConfig.py
    User should not use this class directly, it mostly used in the PHYFrame class

    ps: A Frame is stored in the form of string composed all of bits, like: "100000011101"
    """

    def __init__(self):
        """initialize destination, source and host to None"""
        self.type = None
        self.load = None

    def get(self):
        """get the whole MAC frame in the form of string"""
        if self.load is None:
            return self.type
        return self.type + self.load.get()

    def get_data(self):
        return self.load

    def set_type(self, type):
        """:param type: indicate what type the frame is"""
        self.type = type

    def set_load(self, load):
        self.load = load

    def get_type(self):
        return self.type

    def modulate(self):
        """modulate the whole frame into signals"""
        if self.load is None:
            return modulate_string(self.type)
        return np.concatenate([modulate_string(self.type), self.load.modulate()])
