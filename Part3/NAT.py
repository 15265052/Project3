# NAT to translate Athernet data packet and send it through socket
import os
import socket
import threading

import numpy as np

from Part3.all_globals import *
from Part3.config.Type import *
from Part3.config.ACKConfig import *


def set_stream():
    asio_id = 14
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
    global is_noisy
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


def gen_data(pre_data, src_address, dest_address):
    """translate payload into Athernet packet"""
    athernet_frames = []
    for i in range(frame_num):
        data = pre_data[0][i * bytes_per_frame:(i + 1) * bytes_per_frame]
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
            if j < len(data):
                bi = bin(data[j])[2:]
                byte_bit_str_buffer += (8 - len(bi)) * "0" + bi
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


def send_ACK(n_frame):
    global global_status
    global ACK_buffer
    global ACK_predefined
    ACK_buffer.append(ACK_predefined[n_frame])
    global_status = "sending ACK"


def athernet_to_internet():
    """ translate athernet packet to internet packet """
    global global_buffer
    global global_pointer
    global detected_frames
    global is_noisy
    src_ip = None
    src_port = None
    dest_ip = None
    dest_port = None
    stream = set_stream()
    stream.start()
    pointer = global_pointer
    UDP_payload = [None] * frame_num
    # First to receive data from athernet
    print("start to receive athernet packet")
    while detected_frames < frame_num or is_noisy:
        if pointer + block_size > len(global_buffer):
            continue
        block_buffer = global_buffer[pointer: pointer + block_size]
        pointer_frame = detect_preamble(block_buffer)
        if not pointer_frame == "error":
            pointer += pointer_frame
            # detect a frame, first to check its correctness
            if pointer + frame_length - preamble_length > len(global_buffer):
                time.sleep(0.1)
            frame_detected = global_buffer[pointer: pointer + frame_length - preamble_length]
            frame_in_bits = decode_to_bits(frame_detected)
            if check_CRC8(frame_in_bits):
                phy_frame = PhyFrame()
                phy_frame.from_array(frame_in_bits)
                n_frame = phy_frame.get_decimal_num()
                print("sending ACK: ", n_frame)
                send_ACK(n_frame)
                if not frame_confirmed[n_frame]:
                    frame_confirmed[n_frame] = True
                    detected_frames += 1
                # CRC correct, starting decode ip and port
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
    print("start receiving internet data")
    sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    address = (NAT_internet_ip, NAT_port)
    sck.bind(address)
    data, node1_address = sck.recvfrom(1083)
    all_data.append(data)
    print("data: ", data)
    sck.close()
    print("receiving from node1 finished")

    stream = set_stream()
    stream.start()
    global TxFrame
    # then send data to node3
    frames = gen_data(all_data, (NAT_athernet_ip, NAT_port), (node3_ip, node3_port))
    i = 0
    for frame in frames:
        TxFrame = frame.get_modulated_frame()[:]
        send_athernet_data()
        TxFrame = []
        send_time[i] = time.time()
        print("send ", frame.get_decimal_num(), "frame")
        i += 1
        if i % 49 and i >= 49:
            check_ACK(0, i, frames)
    while not check_ACK(0, frame_num, frames):
        pass
    print("sending data to node3 finished")


### for Part3
def pack_icmp_echo_request(ident, seq, payload):
    pseudo = struct.pack(
        '!BBHHH',
        8,
        0,
        0,
        ident,
        seq,
    ) + payload
    checksum = calculate_checksum(pseudo)
    return pseudo[:2] + checksum + pseudo[4:]


def unpack_icmp_echo_reply(icmp):
    _type, code, _, ident, seq, = struct.unpack(
        '!BBHHH',
        icmp[:8]
    )
    if _type != 0:
        return
    if code != 0:
        return

    payload = icmp[8:]

    return ident, seq, payload


def send_icmp_request(sock, addr, ident, magic, seq):
    # currrent time
    sending_ts = time.time()

    # packet current time to payload
    # in order to calculate round trip time from reply
    payload = struct.pack('!d', sending_ts) + magic

    # pack icmp packet
    icmp = pack_icmp_echo_request(ident, seq, payload)

    # send it
    sock.sendto(icmp, 0, (addr, 0))

    time.sleep(1)


def recv_icmp_echo(sock, ident, magic):
    for i in range(4):
        # wait for another icmp packet
        ip, (src_addr, _) = sock.recvfrom(1500)

        # unpack it
        result = unpack_icmp_echo_reply(ip[20:])
        if not result:
            continue

        # print info
        _ident, seq, payload = result
        if _ident != ident:
            continue

        sending_ts, = struct.unpack('!d', payload[:8])
        print('%s seq=%d %5.2fms' % (
            src_addr,
            seq,
            (time.time() - sending_ts) * 1000,
        ))


def Ping(address):
    raw_sck = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    address = socket.gethostbyname(address)
    NAT_address = ("10.20.84.76", 0)
    raw_sck.bind(NAT_address)
    ident = os.getpid()
    magic = b'20010626'

    stop = []

    sender_args = (raw_sck, address, ident, magic, stop,)
    sender_thread = threading.Thread(target=send_thread, args=sender_args)

    sender_thread.start()

    recv_thread(raw_sck, ident, magic)
    stop.append(True)
    sender_thread.join()


def athernet_ping():
    global global_buffer
    global global_pointer
    global detected_frames
    global is_noisy
    global TxFrame

    src_ip = None
    src_port = None
    dest_ip = None
    dest_port = None
    raw_sck = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    NAT_address = ("10.20.84.76", 0)
    raw_sck.bind(NAT_address)
    ident = os.getpid()
    magic = b'20010626'
    stream = set_stream()
    stream.start()
    pointer = global_pointer
    # First to receive data from athernet
    print("start to receive athernet packet")
    while True:
        if pointer + block_size > len(global_buffer):
            continue
        block_buffer = global_buffer[pointer: pointer + block_size]
        pointer_frame = detect_preamble(block_buffer)
        if not pointer_frame == "error":
            pointer += pointer_frame
            # detect a frame, first to check its correctness
            if pointer + frame_length - preamble_length > len(global_buffer):
                time.sleep(0.1)
            frame_detected = global_buffer[pointer: pointer + frame_length - preamble_length]
            frame_in_bits = decode_to_bits(frame_detected)
            if check_CRC8(frame_in_bits):
                phy_frame = PhyFrame()
                phy_frame.from_array(frame_in_bits)
                seq = phy_frame.get_decimal_num()
                # CRC correct, starting decode ip and port
                if src_ip is None:
                    src_ip = decode_ip(phy_frame.get_src_ip())
                if src_port is None:
                    src_port = decode_port(phy_frame.get_src_port())
                if dest_ip is None:
                    dest_ip = decode_ip(phy_frame.get_dest_ip())
                if dest_port is None:
                    dest_port = decode_port((phy_frame.get_dest_port()))
                send_icmp_request(raw_sck, dest_ip, ident, magic, seq)
                ip, (src_addr, _) = raw_sck.recvfrom(1500)
                result = unpack_icmp_echo_reply(ip[20:])
                if not result:
                    continue
                # print info
                _ident, seq, payload = result
                if _ident != ident:
                    continue
                sending_ts, = struct.unpack('!d', payload[:8])
                print('%s seq=%d %5.2fms' % (
                    src_addr,
                    seq,
                    (time.time() - sending_ts) * 1000,
                ))
                frame = PhyFrame()
                frame.set_phy_load(MACFrame())
                frame.set_MAC_load(UDPFrame())
                frame.set_type(icmp)
                frame.set_num(seq)
                frame.set_src_ip(src_addr)
                frame.set_CRC()
                TxFrame = frame.get_modulated_frame()[:]
                send_athernet_data()
            else:
                print("CRC broken!")
            pointer += frame_length - preamble_length
            continue
        pointer += block_size

    print("Athernet receiving finished!")


Ping("www.baidu.com")
