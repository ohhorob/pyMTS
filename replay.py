from __future__ import print_function, division
from collections import namedtuple
import struct
import sys
import time
import io

import MTS
from MTS.word.HeaderWord import HeaderWord
from MTS.Packet import packet_tostring

DEBUG = False


def scan_to_headerword(serial_input, maximum_bytes=9999, header_magic=HeaderWord.MAGIC_MASK):
    """
    Consume bytes until header magic is found in a word
    :param header_magic:
    :param maximum_bytes:
    :param serial_input:
    :rtype : int
    """
    headerword = 0x0000
    bytecount = 0

    while headerword & header_magic != header_magic:
        # BlockingIOError
        # Read a single byte
        nextbyte = serial_input.read(1)
        if len(nextbyte) == 0:
            raise BufferError("Reached end of stream")
        bytecount += 1
        # Take the low word and shift it high; Use OR to add this byte
        nextint = ord(nextbyte)
        if DEBUG: print('0x{byte:02X} {byte:08b}'.format(byte=nextint))
        headerword = ((headerword & 0x00FF) << 8) | nextint

        if 0 < maximum_bytes <= bytecount:
            raise BufferError("Failed to detect header word in serial stream")

    try:
        h = MTS.Header.Header(word=headerword)
        if DEBUG: print("Found header word. 0x{:04X}".format(h.word))
    except ValueError as e:
        print("Invalid header word 0x{:04X}".format(headerword))
        raise e

    return headerword


def read_packets(serial_input):
    """
    Consume bytes from input, creating packet frames of words
    :type serial_input:
    """
    while 1:
        headerword = scan_to_headerword(serial_input)
        # Read the bytes that are required to complete the packet
        packet_wordlength = (headerword & 0x1000 << 7) | headerword & 0x007F
        packet_bytelength = packet_wordlength * 2
        if DEBUG: print('words={:d}; bytes={:d}'.format(packet_wordlength, packet_bytelength))
        bodybytes = bytearray(b'0' * packet_bytelength)
        if DEBUG: print(' '.join(['{:02X}'.format(b) for b in bodybytes]))

        serial_input.readinto(bodybytes)

        # Take pairs of body bytes for to return words of data
        words = [headerword]
        words.extend([(bodybytes[idx] << 8) | bodybytes[idx + 1] for idx in range(0, packet_bytelength-1, 2)])
        words_hexstring = ' '.join(['{:04X}'.format(w) for w in words])
        print(words_hexstring)
        yield words


def live_stream(tty='cu.SLAB_USBtoUART'):
    import serial
    return serial.Serial('/dev/{}'.format(tty), 19200)


def setInterval(interval):
    import threading

    def decorator(function):
        def wrapper(*args, **kwargs):
            stopped = threading.Event()

            def loop(): # executed in another thread
                while not stopped.wait(interval): # until stopped
                    function(*args, **kwargs)

            t = threading.Thread(target=loop)
            t.daemon = True # stop if the program exits
            t.start()
            return stopped
        return wrapper
    return decorator

elapsed_millis = 0


@setInterval(MTS.Packet.PACKET_INTERVAL/1000)
def send_packet():
    global elapsed_millis, input_stream, output_stream
    packet = read_packets(input_stream).next()
    print("{:12d} {}\n".format(int(elapsed_millis), packet_tostring(packet)))
    elapsed_millis += MTS.Packet.PACKET_INTERVAL
    b = ''.join([struct.pack('>H', h) for h in packet])
    output_stream.write(b)
    output_stream.flush()


if __name__ == '__main__':
    # Open input stream
    input_file = 'openlog-20160710-001.TXT'
    input_stream = io.open(
            input_file,
            mode='rb',
            buffering=io.DEFAULT_BUFFER_SIZE
    )
    print('Reading from: {}'.format(input_file))
    output_stream = live_stream()

    # Debug a chunk; Compare to HexFiend to confirm serial read
    #
    # firstchunk = bytearray(b'0' * 64)
    # input_stream.readinto(firstchunk)
    # print(' '.join('{:02X}'.format(c) for c in firstchunk))
    # print('  '.join(['{:04X}'.format(((firstchunk[idx] & 0x00FF) << 8) | firstchunk[idx + 1]) for idx in range(0, 63, 2)]))

    # Debug first packet
    #
    # p = read_packets(input_stream).next()
    # b = ''.join([struct.pack('>H', h) for h in p])
    # output_stream.write(b)


    #
    # from MTS.Packet import packet_tostring
    # for p in read_packets(input_stream):
    #     print("{:12d} {}\n".format(int(elapsed_millis), packet_tostring(p)))
    #     elapsed_millis += MTS.Packet.PACKET_INTERVAL
    #     b = ''.join([struct.pack('>H', h) for h in p])
    #     output_stream.write(b)
    #     output_stream.flush()
    #     if elapsed_millis > 10000:
    #         break

    from threading import _sleep
    stop = send_packet()  # start timer, the first call is in .5 seconds
    while elapsed_millis < 10000:
        _sleep(1)

    stop.set()

    print('Total Time: {} seconds'.format(int(elapsed_millis / 1000)))
