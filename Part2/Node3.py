# Node3
import struct

from Part2.config.globalConfig import *
from Part2.frame.PHYFrame import *
from Part2.config.Type import *
from all_globals import *


def set_stream():
    asio_id = 10
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
    if np.average(np.abs(indata[:, 0]) > 0.005):
        is_noisy = True
    else:
        is_noisy = False
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

    if global_status == "sending ACK":
        global ACK_buffer
        global ACK_pointer
        global_status = ""
        outdata[:] = np.append(ACK_buffer[ACK_pointer], np.zeros(frames - len(ACK_buffer[ACK_pointer]))).reshape(frames,
                                                                                                                 1)
        ACK_pointer += 1

def gen_data(file_name, src_address, dest_address):
    with open(file_name, "rb") as f:
        data = f.read()
    data = struct.unpack("c" * len(data), data)
    athernet_frames = []
    input_index = 0
    frame_num = int(len(data) / bytes_per_frame)
    if frame_num * bytes_per_frame < len(data):
        frame_num += 1
    for i in range(frame_num):
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
        for j in range(bytes_per_frame):
            if input_index < len(data):
                byte_bit_str_buffer += byte_to_str(data[input_index])
                input_index += 1
            else:
                byte_bit_str_buffer += "00000000"

        frame.set_load(byte_bit_str_buffer)
        frame.set_CRC()
        if i == 0:
            print(check_CRC8(frame.get_phy_load().get() + frame.num + frame.CRC))
        athernet_frames.append(frame)
    return athernet_frames


def send_athernet_data():
    global global_input_index
    global global_status
    global TxFrame
    global_input_index = 0
    while global_input_index < len(TxFrame):
        global_status = "send data"
    global_status = ""


def decode_ACK_bits(ACK_buffer):
    # first to convert all samples to bits
    str_decoded = ""
    pointer = 0
    ACK_length_in_bit = 20
    for i in range(ACK_length_in_bit):
        decode_buffer = ACK_buffer[pointer: pointer + samples_per_bin]
        if np.sum(decode_buffer * signal0) > 0:
            str_decoded += '0'
        else:
            str_decoded += '1'
        pointer += samples_per_bin
    return str_decoded


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
            ACK_frame_array = global_buffer[global_pointer: global_pointer + 20 * samples_per_bin]
            ACK_frame = PhyFrame()
            ACK_frame.from_array(decode_ACK_bits(ACK_frame_array))
            if ACK_frame.check():
                if not ACK_confirmed[ACK_frame.get_decimal_num()]:
                    print("ACK ", ACK_frame.get_decimal_num(), " received!")
                    ACK_confirmed[ACK_frame.get_decimal_num()] = True
                ACK_confirmed[ACK_frame.get_decimal_num()] = True
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


def send_data():
    global TxFrame
    stream = set_stream()
    stream.start()
    frames = gen_data("INPUT.txt", (node3_ip, node3_port), (NAT_athernet_ip, NAT_port))
    i = 0
    for frame in frames:
        TxFrame = frame.get_modulated_frame()[:]
        send_athernet_data()
        TxFrame = []
        send_time[i] = time.time()
        print("send ", i, "frame")
        i += 1
        if i % 49 and i >= 49:
            check_ACK(0, i, frames)
    while not check_ACK(0, frame_num, frames):
        pass

    stream.stop()
    print("Node3 sending data finished")


def send_ACK(n_frame):
    global global_status
    global ACK_buffer
    global ACK_predefined
    ACK_buffer.append(ACK_predefined[n_frame])
    global_status = "sending ACK"


def receive_data():
    stream = set_stream()
    stream.start()
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
    UDP_payload = [None] * frame_num
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
                # CRC correct, starting decode ip and port
                phy_frame = PhyFrame()
                phy_frame.from_array(frame_in_bits)
                n_frame = phy_frame.get_decimal_num()
                print("sending ACK: ", n_frame)
                send_ACK(n_frame)
                if not frame_confirmed[n_frame]:
                    frame_confirmed[n_frame] = True
                    detected_frames += 1
                if src_ip is None:
                    src_ip = decode_ip(phy_frame.get_src_ip())
                if src_port is None:
                    src_port = decode_port(phy_frame.get_src_port())
                if dest_ip is None:
                    dest_ip = decode_ip(phy_frame.get_dest_ip())
                if dest_port is None:
                    dest_port = decode_port((phy_frame.get_dest_port()))
                UDP_payload[n_frame] = str_to_byte(phy_frame.get_load())
        else:
            print("CRC broken!")
        pointer += block_size

    print("receiving data finished... showing contents...")
    for content in UDP_payload:
        print("IP: ", src_ip, " Port: ", src_port)
        print("content: ", content)


send_data()
