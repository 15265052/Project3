import time

import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd
from scipy import signal, integrate


def gen_preamble():
    t = np.linspace(0, 1, 48000, endpoint=True, dtype=np.float32)
    t = t[0:60]
    f_p = np.concatenate([np.linspace(1000, 10000, 30), np.linspace(10000, 1000, 30)])
    preamble = (np.sin(2 * np.pi * integrate.cumtrapz(f_p, t))).astype(np.float32)
    return preamble


def detect_preamble(block_buffer):
    corr = signal.correlate(block_buffer, preamble)
    if np.max(corr) > threshold:
        # detect preamble
        return np.argmax(corr) + 1
    else:
        return "error"


def write_to_file(file_name, data):
    with open(file_name, 'ab') as f:
        f.write(data)


def clean_file(file_name):
    with open(file_name, 'w') as f:
        f.truncate()


def str_to_one_byte(str_buffer):
    temp = int(str_buffer, 2)
    return temp.to_bytes(1, 'big')


def str_to_byte(all_str):
    bytes_res = []
    for i in range(bytes_per_frame):
        bytes_res.append(str_to_one_byte(all_str[i * bins_per_byte:(i + 1) * bins_per_byte]))
    return bytes_res


def byte_to_str(byte):
    temp_bin = int.from_bytes(byte, 'big')
    bi = bin(temp_bin)[2:]
    return (8 - len(bi)) * "0" + bi


def write_byte_to_file(file_name, decoded_bits):
    for byte in str_to_byte(decoded_bits):
        write_to_file(file_name, byte)


def gen_CRC8(string):
    loc = [8, 2, 1, 0]
    p = [0 for i in range(9)]
    for i in loc:
        p[i] = 1
    info = list(string)
    info = [int(i) for i in info]
    info1 = list(string)
    info1 = [int(i) for i in info1]
    # print(info)
    times = len(info)
    n = 9
    for i in range(8):
        info.append(0)
    consult = []
    for i in range(times):
        if info[i] == 1:
            consult.append(1)
            for j in range(n):
                info[j + i] = info[j + i] ^ p[j]
        else:
            consult.append(0)
    mod = info[-8::]
    # print(mod)
    code = info1.copy()
    # print(code)
    for i in mod:
        code.append(i)
    code = "".join('%s' % id for id in code)
    # print(code)
    return code


def check_CRC8(string):
    loc = [8, 2, 1, 0]
    p = [0 for i in range(9)]
    for i in loc:
        p[i] = 1
    info = list(string)
    info = [int(i) for i in info]
    times = len(info)
    n = 9
    consult = []
    for i in range(times - 8):
        if info[i] == 1:
            consult.append(1)
            for j in range(n):
                info[j + i] = info[j + i] ^ p[j]
        else:
            consult.append(0)
    mod = info[-8::]
    # print(mod)
    mod = int("".join('%s' % id for id in mod))
    if mod == 0:
        return True
    else:
        return False


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


def translate_ip_to_bits(ip_address):
    ip_bits = ""
    num_str = ip_address.split('.')
    # there is four 8 bits ip num str
    assert len(num_str) == 4
    for one_str in num_str:
        # turn one num str to 8 bits
        temp_int = int(one_str)
        temp_bi = bin(temp_int)[2:]
        ip_bits += (8 - len(temp_bi)) * "0" + temp_bi
    assert len(ip_bits) == 4 * 8
    return ip_bits


def decode_to_bits(frame):
    str_decoded = ""
    for i in range(frame_length_in_bit):
        decode_buffer = frame[i * samples_per_bin: (i + 1) * samples_per_bin]
        str_decoded += decode_one_bit(decode_buffer)
    return str_decoded


def decode_one_bit(s_buffer):
    sum = np.sum(s_buffer * signal0)
    if sum >= 0:
        return '0'
    else:
        return '1'


def decode_ip(ip_bits):
    ip_str = ""
    for i in range(4):
        num_bits = ip_bits[i * 8: (i + 1) * 8]
        ip_str += str(int(num_bits, 2)) + '.'
    return ip_str[:-1]


def decode_port(port_bits):
    return int(port_bits, 2)


sample_rate = 48000
signal0 = [0.5, 0.5, -0.5, -0.5]
signal1 = [-0.5, -0.5, 0.5, 0.5]
latency = 0.0015
block_size = 2048
threshold = 10

preamble = gen_preamble()
preamble_length = len(preamble)

bins_per_byte = 8
samples_per_bin = 4
frame_num = 250
frame_num_2 = 200
bytes_per_frame = 20
ip_bit_length = 4 * 8
payload_length = bytes_per_frame * bins_per_byte * samples_per_bin
CRC_length = 8 * samples_per_bin
type_length = 4 * samples_per_bin
ip_length = samples_per_bin * ip_bit_length
port_length = 16 * samples_per_bin
frame_length = preamble_length + type_length + 2 * ip_length + 2 * port_length + payload_length + CRC_length
frame_length_in_bit = int(frame_length / samples_per_bin)

node1_ip = "10.20.234.160"
NAT_athernet_ip = "192.168.1.1"
NAT_internet_ip = "10.20.84.36"
node3_ip = "192.168.1.2"
node3_port = 9527
NAT_port = 9527

retransmit_time = 0.18
max_retransmit = 10

