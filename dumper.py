from __future__ import print_function, division
from collections import namedtuple
import struct
import sys
import time
import io

from MTS.Header import Header

__author__ = 'rob'


# pre-captured data
bytefilepath = 'mts-ssi-4-192.asc'




def scan_to_headerword(serial_input, maximum_bytes=9999, header_magic=HeaderWord.MAGIC_MASK):
    """
    Consume bytes until header magic is found in a word
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
        headerword = ((headerword & 0x00FF) << 8) | nextint
        try:
            h = Header(word=headerword)
        except ValueError as e:
            print("Skipping invalid header word 0x{:04X}".format(headerword))
            continue

        print("Found header word. 0x{:04X}".format(headerword))
        # print("Scanning word for header: 0x{:04X} & 0x{:04X} = 0x{:04X}".format(
        #     headerword,
        #     header_magic,
        #     headerword & header_magic)
        #       , file=sys.stderr
        # )
        if 0 < maximum_bytes <= bytecount:
            raise BufferError("Failed to detect header word in serial stream")

    return headerword


def scan_swappedwords(serial_input):
    swappedword = 0x0000

    while 1:
        nextbyte = serial_input.read(1)
        if len(nextbyte) == 0:
            raise BufferError("Reached end of stream")

        msb = ord(nextbyte)
        swappedword = (msb << 8) | ((swappedword & 0xFF00) >> 8)

        try:
            h = MTSHeader(word=swappedword)
        except ValueError as e:
            print("Skipping invalid header word 0x{:04X}".format(swappedword))
            continue

        print("Found swapped header word. 0x{:04X}".format(swappedword))
        print(" packet word length = {}".format(h.b.length()))


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
        # 'LOG00129.TXT',
        'coldcap-LC2.ISP2',
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


def dump(instream, outstream=None):
    # started = StampedMarker(0, time.time())
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
        scan_swappedwords(captured_stream())
        dump(
            # live_stream('cu.usbserial'),
            captured_stream(),
            outfile
        )
    except BufferError as e:
        print("All done; {}".format(e))
    finally:
        if outfile is not None:
            outfile.close()

