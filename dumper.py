from __future__ import print_function, division
from collections import namedtuple
import struct
import sys
import time

__author__ = 'rob'

import io
import ctypes
c_uint8 = ctypes.c_uint8

# MTS Log protocol -- http://www.innovatemotorsports.com/support/downloads/Seriallog-2.pdf
# Serial: 8-N-1-19.2 kbit/sec
# Packet periodicity: 81.92 milliseconds (12.2 hertz) (8 MHz / 655360)
# Sample resolution: 10 bits (0..5V at 0.1% resolution)

# pre-captured data
bytefilepath = 'mts-ssi-4-192.asc'


# ISP2 Frame
# 16 bit words in big endian order


class HeaderWord(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', c_uint8, 1),         # 07
        ('LengthLow', c_uint8, 7),       # 06..00

        # High Byte
        ('HEADER15', c_uint8, 1),        # 15
        ('Recording', c_uint8, 1),       # 14
        ('CLEAR13', c_uint8, 1),         # 13
        ('DataOrResponse', c_uint8, 1),  # 12
        ('LogCapable', c_uint8, 1),      # 11
        ('RESERVED10', c_uint8, 1),      # 10
        ('CLEAR09', c_uint8, 1),         # 09
        ('LengthHigh', c_uint8, 1),      # 08
    ]

    def is_data(self):
        return self.DataOrResponse > 0

    def can_log(self):
        return self.LogCapable > 0

    def is_recording(self):
        return self.Recording > 0

    def length(self):
        return (self.LengthHigh << 7) | self.LengthLow


# Convenience Union to access the word or the fields
class MTSHeader(ctypes.Union):
    _fields_ = [
        ('word', ctypes.c_uint16),
        ('b', HeaderWord)
    ]
    _anonymous_ = 'b'

    MAGIC_MASK = 0xA280

    def __init__(self, *args, **kwargs):
        super(MTSHeader, self).__init__(*args, **kwargs)
        if 'word' in kwargs:
            self.word = kwargs['word']

    def word_count(self):
        return (self.b.LengthHigh << 7) | self.b.LengthLow

    def desc(self):
        return '0x{:04X} {} Len={:d} '.format(
            self.word,
            'Data' if self.b.is_data() else 'Response',
            self.b.length()
        )

class FunctionBits(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', ctypes.c_uint8, 1),  # 07
        ('AirFuelLow', c_uint8, 7),      # 06..00

        # High Byte
        ('SET15', ctypes.c_uint8, 1),        # 15
        ('Recording', ctypes.c_uint8, 1),    # 14
        ('CLEAR13', ctypes.c_uint8, 1),      # 13
        ('Function', ctypes.c_uint8, 3),     # 12 .. 10
        ('CLEAR09', ctypes.c_uint8, 1),      # 09
        ('AirFuelHigh', ctypes.c_uint8, 1),  # 08
    ]


class LambdaBits(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', ctypes.c_uint8, 1),  # 07
        ('LambdaLow', c_uint8, 7),       # 06..00

        # High Byte
        ('CLEAR15', ctypes.c_uint8, 1),     # 15
        ('CLEAR14', ctypes.c_uint8, 1),     # 14
        ('LambdaHigh', ctypes.c_uint8, 6),  # 13 .. 08
    ]


class BatteryBits(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', ctypes.c_uint8, 1),  # 07
        ('BatteryLow', c_uint8, 7),      # 06..00

        # High Byte
        ('CLEAR15', ctypes.c_uint8, 1),      # 15
        ('CLEAR14', ctypes.c_uint8, 1),      # 14
        ('Divider', ctypes.c_uint8, 3),      # 13 .. 11
        ('BatteryHigh', ctypes.c_uint8, 3),  # 13 .. 11
    ]


class AuxBits(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', ctypes.c_uint8, 1),  # 07
        ('AuxLow', c_uint8, 7),          # 06..00

        # High Byte
        ('CLEAR15', ctypes.c_uint8, 1),  # 15
        ('CLEAR14', ctypes.c_uint8, 1),  # 14
        ('CLEAR13', ctypes.c_uint8, 1),  # 13
        ('CLEAR12', ctypes.c_uint8, 1),  # 12
        ('CLEAR11', ctypes.c_uint8, 1),  # 11
        ('AuxHigh', ctypes.c_uint8, 3),  # 10 .. 08
    ]

    MAX_VOLTS = 5.0
    MAX_VALUE = (1 << 10) - 1
    RPM_FACTOR = 10

    def aux(self):
        return (self.AuxHigh << 7) | self.AuxLow

    def percent(self):
        value = self.aux()
        if value != 0:
            value /= AuxBits.MAX_VALUE
        return value

    def volts(self):
        """
        Aux Inputs digitized to 10 bits. 0 = 0V, 1023 = 5V.

        :return: measured voltage
        """
        value = self.aux()
        if value != 0:
            value = value * AuxBits.MAX_VOLTS / AuxBits.MAX_VALUE
        return value

    def rpm(self):
        return self.aux() * AuxBits.RPM_FACTOR


class MTSSubPacket(ctypes.Union):
    _fields_ = [
        ('word', ctypes.c_uint16),
        ('function', FunctionBits),
        ('lambda', LambdaBits),
        ('battery', BatteryBits),
        ('aux', AuxBits)
    ]


def scan_to_headerword(serial_input, maximum_bytes=99, header_magic=MTSHeader.MAGIC_MASK):
    """
    Consume bytes until header magic is found in a word
    :param serial_input:
    :rtype : int
    """
    headerword = 0x0000
    bytecount = 0

    while headerword & header_magic != header_magic:
        # BlockingIOError
        nextbyte = serial_input.read(1)
        if len(nextbyte) == 0:
            raise BufferError("Reached end of stream")
        headerword = (headerword << 8) | ord(nextbyte)
        bytecount += 1
        if 0 < maximum_bytes <= bytecount:
            raise BufferError("Failed to detect header word in serial stream")

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
        bodybytes = bytearray(b'0' * packet_bytelength)
        serial_input.readinto(bodybytes)

        # Take pairs of body bytes for to return words of data
        words = [headerword]
        words.extend([(bodybytes[idx] << 8) | bodybytes[idx] for idx in range(0, packet_bytelength-1, 2)])
        yield words


def captured_stream():
    return io.open(
        bytefilepath,
        mode='rb',
        buffering=io.DEFAULT_BUFFER_SIZE
    )

# StampedMarker = namedtuple('StampedMarker', 'counter clock')


def live_stream(tty='cu.usbserial'):
    import serial
    return serial.Serial('/dev/{}'.format(tty), 19200)


def packet_tostring(packet):
    # chunks = ["Size={:02d}".format(len(packet))]
    # Header word
    header = MTSHeader()
    header.word = packet[0]
    chunks = [header.desc()]

    auxstart = 1

    # Optional Function&Lambda&Battery
    if packet[1] & 0x80 == 0x80:
        fbits = MTSSubPacket()
        fbits.word = packet[1]
        lbits = MTSSubPacket()
        lbits.word = packet[2]
        auxstart += 2

        if len(packet) > 3 and packet[3] & 0x3800 != 0:
            bbits = MTSSubPacket()
            bbits.word = packet[3]
            auxstart += 1

    # Channels
    if len(packet) >= auxstart:
        for channel, auxword in enumerate(packet[auxstart:]):
            abits = MTSSubPacket()
            abits.word = auxword
            chunks.append("ch{:02d}={:4.4f}V".format(channel + 1, abits.aux.volts()))

    return '; '.join(chunks)


def dump(instream, outstream=None):
    # started = StampedMarker(0, time.time())
    """

    :type outstream: io.BufferedWriter
    """
    packetmillis = 8000000 / 655360
    for i, packet in enumerate(read_packets(instream)):
        # now = time.time()
        # if now - started.clock >= 10.0:
        #     print("{: 5d} in {:.3f} sec = {:.3f} packets/sec".format(
        #         i - started.counter,
        #         now - started.clock,
        #         (i - started.counter) / (now - started.clock)
        #     ))
        #     started = StampedMarker(i, now)
        # Raw dump to screen
        stamp = i * packetmillis
        print("{: 5d} {: 3d}:{:06.3f} 0x{}\n      {}".format(
            i,
            int(stamp / 60.0),
            stamp % 60.0,
            '-'.join(['{:04X}'.format(word) for word in packet]),
            packet_tostring(packet)
        ))
        outstream.write(struct.pack('{:d}H'.format(len(packet)), *packet))
        if i % 100 == 0:
            outstream.flush()
            print('Flush.', file=sys.stderr)


if __name__ == '__main__':
    import tempfile
    outwrapper = tempfile.NamedTemporaryFile(suffix='.ISP2', delete=False)
    outwrapper.close()
    outfile = io.open(outwrapper.name, mode='w+b' )
    print('Logging raw data to temp file: {}'.format(outwrapper.name), file=sys.stderr)
    try:
        dump(
            live_stream('cu.usbserial'),
            outfile
        )
    except BufferError as e:
        print("All done; {}".format(e))
    finally:
        if outfile is not None:
            outfile.close()

