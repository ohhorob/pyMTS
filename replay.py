from __future__ import print_function, division

import os
import struct
import sys
import time
import io
import logging

import MTS
from MTS.word.HeaderWord import HeaderWord
from MTS.Packet import packet_tostring
from apscheduler.schedulers.blocking import BlockingScheduler

DEBUG = False


def scan_to_headerword(serial_input, maximum_bytes=9999, header_magic=HeaderWord.MAGIC_MASK):
    """
    Consume bytes until header magic is found in a word
    :param header_magic:
    :param maximum_bytes:
    :param serial_input:
    :rtype : MTS.Header.Header
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
        return h
    except ValueError as e:
        print("Invalid header word 0x{:04X}".format(headerword))
        raise e


def read_packets(serial_input):
    """
    Consume bytes from input, creating packet frames of words
    :rtype: MTS.Packet.Packet
    :type serial_input:
    """
    while 1:
        header = scan_to_headerword(serial_input)
        yield header.read_packet(serial_input)


def live_stream(tty='cu.SLAB_USBtoUART'):
    import serial
    from serial import SerialException
    try:
        return serial.Serial('/dev/{}'.format(tty), 19200)
    except SerialException as e:
        print("Failed to open port", file=sys.stderr)
    return None


elapsed_millis = 0
previous_send_time = time.time()
send_count = 0
packet = None
send_byte_buffer = None
start_time = None


def send_packet():
    global packet, \
        send_byte_buffer, \
        send_count, \
        elapsed_millis, \
        input_stream, output_stream, \
        previous_send_time, start_time
    now = time.time()
    delta = (now - previous_send_time) * 1000.0
    previous_send_time = now
    if send_byte_buffer is not None:
        start_time = now
        elapsed = now - start_time
        output_stream.write(send_byte_buffer)
        output_stream.flush()
        send_count += 1
        elapsed_millis += MTS.Packet.PACKET_INTERVAL
        print("{:05d} {:1f} {:12d} {}\n".format(
                send_count,
                delta,
                int(elapsed_millis),
                packet
        ))

    packet = read_packets(input_stream).next()
    words = packet.words()
    send_byte_buffer = ''.join([struct.pack('>H', h) for h in words])


# Debug a chunk; Compare to HexFiend to confirm serial read
def debug_chunk():

    firstchunk = bytearray(b'0' * 64)
    input_stream.readinto(firstchunk)
    print(' '.join('{:02X}'.format(c) for c in firstchunk))
    print('  '.join(['{:04X}'.format(((firstchunk[idx] & 0x00FF) << 8) | firstchunk[idx + 1]) for idx in range(0, 63, 2)]))


if __name__ == '__main__':
    logging.basicConfig()
    # Open input stream
    input_file = 'openlog-20160710-001.TXT'
    input_stream = io.open(
            input_file,
            mode='rb',
            buffering=io.DEFAULT_BUFFER_SIZE
    )
    print('Reading from: {}'.format(input_file))
    output_stream = live_stream()


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

    # Debug with a single packet
    send_packet()
    send_packet()

    scheduler = BlockingScheduler()
    scheduler.add_job(send_packet, 'interval', seconds=MTS.Packet.PACKET_INTERVAL/1000)
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

    # from threading import _sleep
    # stop = send_packet()  # start timer, the first call is in .5 seconds
    # while elapsed_millis < 10000:
    #     _sleep(1)
    #
    # stop.set()

    print('Total Time: {} seconds'.format(int(elapsed_millis / 1000)))