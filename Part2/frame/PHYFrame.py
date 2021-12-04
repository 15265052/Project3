"""
This file defines a PHY Frame and supplies functions for decoding the Frame

PHY Frame structure:
    | Preamble | Frame Num | PHY load | CRC |

PHY load here is MAC Frame, which is defined in MACFrame.py

Author: du xiao yuan
Modified At: 2021/10/30
"""
from Part2.frame.MACFrame import *
from Part2.config.globalConfig import *
from Part2.frame.UDPFrame import *


class PhyFrame:
    """
     A physical frame has three parts:
     1. preamble
     2. physical load (MAC frame)
     The actual frame is the combination of 2 and 3
     So the class member doesn't contain preamble
     But every time we get the PHY frame in the form of array
     The preamble will be included automatically
     """

    def __init__(self):
        self.num = None
        self.phy_load = None
        self.CRC = None

    def from_array(self, frame_array):
        """setting from the detected array, preamble is excluded"""
        self.phy_load = MACFrame()
        self.set_type(frame_array[:4])
        self.phy_load.load = UDPFrame()
        self.phy_load.load.set_src_ip(frame_array[4:4+ip_bit_length])
        self.phy_load.load.set_dest_ip(frame_array[4+ip_bit_length:4+2*ip_bit_length])
        self.phy_load.load.set_src_port(frame_array[4+2*ip_bit_length:4+2*ip_bit_length+16])
        self.phy_load.load.set_dest_port(frame_array[4+2*ip_bit_length+16:4+2*ip_bit_length+32])
        self.phy_load.load.set_load(frame_array[4+2*ip_bit_length+32:4+2*ip_bit_length+32+80])
        self.num = frame_array[-16:-8]
        self.CRC = frame_array[-8:]

    def get_modulated_frame(self):
        """ Add preamble to the head, get whole modulated frame"""
        phy_frame = np.concatenate([preamble, modulate_string(self.num), self.phy_load.modulate(), modulate_string(self.CRC)], dtype=object)
        return phy_frame

    def get_phy_load(self):
        """get MAC frame, w/o preamble and CRC"""
        return self.phy_load

    def get_type(self):
        """get the type of frame"""
        return self.phy_load.get_type()

    def set_type(self, data_type):
        """set the type of frame"""
        self.phy_load.set_type(data_type)

    def set_src_ip(self, src_ip):
        self.phy_load.load.set_src_ip(src_ip)

    def set_dest_ip(self, dest_ip):
        self.phy_load.load.set_dest_ip(dest_ip)

    def set_src_port(self, src_port):
        self.phy_load.load.set_src_port(src_port)

    def set_dest_port(self, dest_port):
        self.phy_load.load.set_dest_port(dest_port)

    def set_phy_load(self, phy_load):
        self.phy_load = phy_load

    def set_MAC_load(self, MAC_load):
        self.phy_load.set_load(MAC_load)

    def set_load(self, load):
        self.phy_load.load.set_load(load)

    def get_src_ip(self):
        return self.phy_load.load.get_src_ip()

    def get_dest_ip(self):
        return self.phy_load.load.get_dest_ip()

    def get_src_port(self):
        return self.phy_load.load.get_src_port()

    def get_dest_port(self):
        return self.phy_load.load.get_dest_port()

    def get_load(self):
        return self.phy_load.load.get_load()

    def set_CRC(self):
        self.CRC = gen_CRC8(self.num+self.phy_load.get())[-8:]

    def set_num(self, num):
        temp_str = bin(num)[2:]
        temp_str = (8 - len(temp_str)) * '0' + temp_str
        self.num = temp_str
