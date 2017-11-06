from __future__ import print_function, division
import struct
import sys
import io

import MTS

from MTS.Header import Header
from MTS.word.HeaderWord import HeaderWord

__author__ = 'rob'


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
        # if DEBUG: print('0x{byte:02X} {byte:08b}'.format(byte=nextint))
        headerword = ((headerword & 0x00FF) << 8) | nextint

        if 0 < maximum_bytes <= bytecount:
            raise BufferError("Failed to detect header word in serial stream")

    try:
        h = MTS.Header.Header(word=headerword)
        # if DEBUG: print("Found header word. 0x{:04X}".format(h.word))
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


def captured_stream(filename='Serial-log.isp2'):
    return io.open(
        filename,
        mode='rb',
        buffering=io.DEFAULT_BUFFER_SIZE
    )

# StampedMarker = namedtuple('StampedMarker', 'counter clock')


def live_stream(tty='cu.usbserial'):
    import serial
    try:
        return serial.Serial('/dev/{}'.format(tty), 19200)
    except OSError as e:
        print("Failed to open port", file=sys.stderr)
    return None


def print_packet(i, packet):
    print("{: 5d} 0x{} {}".format(
        i,
        '-'.join(['{:04X}'.format(word) for word in packet.words()]),
        packet.data_line()
    ))


def dump(instream, outstream=None):
    for i, packet in enumerate(read_packets(instream)):
        # Raw dump to screen
        allwords = packet.words()
        print_packet(i, packet)
        outstream.write(struct.pack('{:d}H'.format(len(allwords)), *allwords))
        if i % 100 == 0:
            outstream.flush()
            # print('Flush.', file=sys.stderr)


if __name__ == '__main__':
    import tempfile
    outwrapper = tempfile.NamedTemporaryFile(suffix='.ISP2', delete=False)
    outwrapper.close()
    outfile = io.open(outwrapper.name, mode='w+b')
    print('Logging raw data to temp file: {}'.format(outwrapper.name), file=sys.stderr)
    try:
        # scan_swappedwords(captured_stream())
        dump(
            # live_stream('cu.usbserial'),
            captured_stream('dumped-fromstorage.swapped.ISP2'),
            # live_stream('cu.UC-232AC'),
            outfile
        )
    except BufferError as e:
        print("All done; {}".format(e))
    finally:
        if outfile is not None:
            outfile.close()

