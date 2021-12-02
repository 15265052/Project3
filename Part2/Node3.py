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
        byte_bit_str_buffer = ""
        for j in range(bytes_per_frame):
            if input_index < len(data):
                byte_bit_str_buffer += byte_to_str(data[input_index])
                input_index += 1
            else:
                byte_bit_str_buffer += "00000000"

        frame.set_load(byte_bit_str_buffer)
        frame.set_CRC()
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


def send_data():
    global Txframe
    stream = set_stream()
    stream.start()
    frames = gen_data("INPUT.txt", (node3_ip, node3_port), (NAT_athernet_ip, NAT_port))
    for frame in frames:
        TxFrame = frame.get_modulated_frame()[:]
        send_athernet_data()
        TxFrame = []
    stream.stop()
    print("Node3 sending data finished")


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
    UDP_payload = []
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
        pointer += block_size

    print("receiving data finished... showing contents...")
    for content in UDP_payload:
        print("IP: ", src_ip, " Port: ", src_port)
        print("content: ", content)

send_data()
