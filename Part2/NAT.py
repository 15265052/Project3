# NAT to translate Athernet data packet and send it through socket
import socket

from Part2.all_globals import *
from Part2.frame.PHYFrame import *

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

    if global_status == "":
        # when not sending, then receiving
        global_buffer = np.append(global_buffer, indata[:, 0])
        outdata.fill(0)


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

    print("Athernet receiving finished!")

    # sending internet data
    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for data in UDP_payload:
        sck.sendto(data, (dest_ip, dest_port))
    sck.close()
    print("Finish sending")

def internet_to_athernet():
    # first to receive data from node1
    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    address = (NAT_internet_ip)
