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
        self.phy_load = None
        self.CRC = None

    def from_array(self, frame_array):
        """setting from the detected array, preamble is excluded"""
        self.phy_load = MACFrame()
        self.set_type(frame_array[:8])
        self.phy_load.load = UDPFrame()
        self.phy_load.load.set_src_ip(frame_array[8:40])
        self.phy_load.load.set_dest_ip(frame_array[40:72])
        self.phy_load.load.set_src_port(frame_array[72:88])
        self.phy_load.load.set_dest_port(frame_array[88:104])
        self.phy_load.load.set_load(frame_array[104:264])
        self.CRC = frame_array[264:]

    def get_modulated_frame(self):
        """ Add preamble to the head, get whole modulated frame"""
        phy_frame = np.concatenate([preamble, self.phy_load.modulate()], dtype=object)
        return phy_frame

    def get_phy_load(self):
        """get MAC frame, w/o preamble and CRC"""
        return self.phy_load

    def get_type(self):
        """get the type of frame"""
        return self.phy_load.get_type()

    def set_type(self, type):
        """set the type of frame"""
        self.phy_load.set_type(type)

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
