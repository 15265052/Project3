
from Part2.config.globalConfig import *
RxFrame = []  # frame for Rx to deal with
TxFrame = []  # frame for Tx to send

global_pointer = 0  # for telling the position that is being processed in global buffer
global_buffer = []  # for receiving all the data from speaker
global_status = ""  # determines what to send
global_input_index = 0  # the global input index of data


# for recording how many frames has been detected
detected_frames = 0
send_time = [0]*frame_num
ACK_confirmed = [False]*frame_num
frame_confirmed = [False] * frame_num
frame_rece = [None] * frame_num
frame_retransmit = [0] * frame_num
max_retransmit = 7
