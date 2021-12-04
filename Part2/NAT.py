# NAT to translate Athernet data packet and send it through socket
import socket

from Part2.all_globals import *
from Part2.frame.PHYFrame import *
from Part2.config.Type import *


def set_stream():
    asio_id = 12
    asio_in = sd.AsioSettings(channel_selectors=[0])
    asio_out = sd.AsioSettings(channel_selectors=[1])

    sd.default.extra_settings = asio_in, asio_out
    sd.default.device[0] = asio_id
    sd.default.device[1] = asio_id
    stream = sd.Stream(sample_rate, blocksize=2048, dtype=np.float32, callback=callback, channels=1)
    return stream


def callback(indata, outdata, frames, time, status):
    global global_buffer
    global global_pointer
    global global_status
    global TxFrame
    global_buffer = np.append(global_buffer, indata[:, 0])
    if global_status == "":
        # when not sending, then receiving
        outdata.fill(0)

    if global_status == "send data":
        global global_input_index
        global TxFrame
        if len(TxFrame) - global_input_index > frames:
            outdata[:] = np.array(TxFrame[global_input_index:global_input_index + frames]).reshape(frames, 1)
        else:
            if len(TxFrame) - global_input_index >= 0:
                outdata[:] = np.append(TxFrame[global_input_index:],
                                       np.zeros(frames - len(TxFrame) + global_input_index)).reshape(frames, 1)
        global_input_index += frames


def gen_data(pre_data, src_address, dest_address):
    """translate payload into Athernet packet"""
    athernet_frames = []
    i = 0
    for data in pre_data:
        frame = PhyFrame()
        frame.set_phy_load(MACFrame())
        frame.set_MAC_load(UDPFrame())
        frame.set_type(data_frame)
        frame.set_src_ip(translate_ip_to_bits(src_address[0]))
        frame.set_src_port(translate_port_to_bits(src_address[1]))
        frame.set_dest_ip(translate_ip_to_bits(dest_address[0]))
        frame.set_dest_port(translate_port_to_bits(dest_address[1]))
        frame.set_num(i)
        byte_bit_str_buffer = ""
        for by in data:
            byte_bit_str_buffer += byte_to_str(by)
        frame.set_load(byte_bit_str_buffer)
        frame.set_CRC()
        athernet_frames.append(frame)
        i += 1
    return athernet_frames


def send_athernet_data():
    global global_input_index
    global global_status
    global TxFrame
    global_input_index = 0
    while global_input_index < len(TxFrame):
        global_status = "send data"
    global_status = ""


def check_ACK(range1, range2, data):
    """
    check if ACK received from range1 to range2
    retransmit frame if time out
    """
    global global_buffer
    global TxFrame
    global global_pointer
    while global_pointer < len(global_buffer):
        pointer_ACK = detect_preamble(global_buffer[global_pointer:global_pointer + 1024])
        if not pointer_ACK == 'error':
            global_pointer += pointer_ACK
            ACK_frame = int(self.decode_ACK(global_buffer[global_pointer:global_pointer + samples_per_bin * 8]), 2)
            if not ACK_confirmed[ACK_frame]:
                print("ACK ", ACK_frame, " received!")
                ACK_confirmed[ACK_frame] = True
            global_pointer += 48
        global_pointer += 1024
    global_pointer = len(global_buffer) >> 2
    res = True
    for i in range(range1, range2):
        if not ACK_confirmed[i]:
            res = False
            if time.time() - send_time[i] > retransmit_time and send_time[i] != 0:
                frame_retransmit[i] += 1
                if frame_retransmit[i] >= max_retransmit:
                    print("link error! exit")
                    exit(-1)
                else:
                    print("ACK ", i, " time out, time used: ", time.time() - send_time[i], ", retransmit")
                    # retransmit
                    TxFrame = data[i].get_modulated_frame()[:]
                    send_athernet_data()
                    send_time[i] = time.time()
                    TxFrame = []
                    res = False
    return res


def athernet_to_internet():
    """ translate athernet packet to internet packet """
    global global_buffer
    global global_pointer
    global detected_frames
    src_ip = None
    src_port = None
    dest_ip = None
    dest_port = None
    stream = set_stream()
    stream.start()
    pointer = global_pointer
    UDP_payload = []
    # First to receive data from athernet
    print("start to receive athernet packet")
    while detected_frames < frame_num:
        if pointer + block_size > len(global_buffer):
            continue
        block_buffer = global_buffer[pointer: pointer + block_size]
        pointer_frame = detect_preamble(block_buffer)
        if not pointer_frame == "error":
            detected_frames += 1
            pointer += pointer_frame
            # detect a frame, first to check its correctness
            if pointer + frame_length - preamble_length > len(global_buffer):
                time.sleep(0.1)
            frame_detected = global_buffer[pointer: pointer + frame_length - preamble_length]
            frame_in_bits = decode_to_bits(frame_detected)
            if check_CRC8(frame_in_bits):
                print("frame received all frames: ", detected_frames)
                # CRC correct, starting decode ip and port
                phy_frame = PhyFrame()
                phy_frame.from_array(frame_in_bits)
                if src_ip is None:
                    src_ip = decode_ip(phy_frame.get_src_ip())
                if src_port is None:
                    src_port = decode_port(phy_frame.get_src_port())
                if dest_ip is None:
                    dest_ip = decode_ip(phy_frame.get_dest_ip())
                if dest_port is None:
                    dest_port = decode_port((phy_frame.get_dest_port()))
                UDP_payload.append(str_to_byte(phy_frame.get_load()))
            else:
                print("CRC broken!")
            pointer += frame_length - preamble_length
            continue
        pointer += block_size

    print("Athernet receiving finished!")

    # sending internet data
    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for data in UDP_payload:
        byte_str = b''
        for byte in data:
            byte_str += byte
        sck.sendto(byte_str, (node1_ip, node1_port))
    sck.close()
    print("Finish sending")


def internet_to_athernet():
    # first to receive data from node1
    all_data = []
    node1_address = None
    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    address = (NAT_internet_ip, NAT_port)
    sck.bind(address)
    while True:
        data, node1_address = sck.recvfrom(20)
        all_data.append(data)
        if len(data) == 0:
            break
    sck.close()
    print("receiving from node1 finished")

    global TxFrame
    # then send data to node3
    frames = gen_data(all_data, (NAT_athernet_ip, NAT_port), (node3_ip, node3_port))
    i = 0
    for frame in frames:
        TxFrame = frame.get_modulated_frame()[:]
        send_athernet_data()
        TxFrame = []
        send_time[i] = time.time()
        i += 1
        if i % 9 == 0 and i >= 10:
            check_ACK(0, i, frames)
    while not check_ACK(0, frame_num, frames):
        pass
    print("sending data to node3 finished")


athernet_to_internet()
