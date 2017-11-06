from __future__ import print_function, division

import io
import logging
import os
import struct
import time

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler
from blessed import Terminal
from blessed.keyboard import Keystroke

import MTS
from MTS.Packet import packet_tostring
from MTS.word.HeaderWord import HeaderWord
from termapp.Display import Display

from termapp.settings import Settings

DEBUG = False
if 'PYDEVD_EGG' in os.environ:
    # Turn on remote-debug
    env_term = os.environ['TERM']
    env_pydevd = os.environ['PYDEVD_EGG']

    import sys
    sys.path.append(env_pydevd)
    import pydevd

    debughost = '127.0.0.1'
    pydevd.settrace(debughost, port=7777, suspend=False)
    # Restore original TERM after pydevd stole it
    if env_term:
        os.environ['TERM'] = env_term


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


def live_stream(tty='cu.UC-232AC'):
    import serial
    from serial import SerialException
    try:
        return serial.Serial('/dev/{}'.format(tty), 19200)
    except SerialException as e:
        _log.warn("Failed to open port: %s", e)
    return None


elapsed_millis = 0
previous_send_time = time.time()
send_count = 0
packet = None
send_byte_buffer = None
start_time = None
input_stream = None


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
        # elapsed = now - start_time
        output_stream.write(send_byte_buffer)
        output_stream.flush()
        send_count += 1
        elapsed_millis += MTS.Packet.PACKET_INTERVAL
        with _t.location(0, _t.height - 5):
            print(_t.clear_eol + "{:05d} {:.1f} {:12d} {}\n".format(
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


_t = Terminal(force_styling=True)
_s = Settings(path='settings.json')
_log = logging.getLogger('replay')


def open_input(path=None):
    global input_stream
    # Open input stream
    input_file = path if path is not None else 'data/openlog-20160710-001.TXT'
    print(_t.bold('Reading from: {}'.format(input_file)))
    input_stream = io.open(
        input_file,
        mode='rb',
        buffering=io.DEFAULT_BUFFER_SIZE
    )
    return input_stream


def add_sender():
    global scheduler, sendjob

    sendjob = scheduler.add_job(send_packet, 'interval', seconds=MTS.Packet.PACKET_INTERVAL / 1000)

    if not scheduler.running:
        scheduler.start()


if __name__ == '__main__':
    logging.basicConfig()

    d = Display(_t)

    def listener(event):
        if event.exception:
            sendjob.remove()

    scheduler = BackgroundScheduler()
    scheduler.add_listener(listener, EVENT_JOB_ERROR)
    sendjob = None
    # Suppress exception logging on default executor
    logging.getLogger('apscheduler.executors.default').setLevel('CRITICAL')

    # open_input(path='data/openlog-20160807-002.TXT')  # return from Wilder Ranch
    # open_input(path='data/openlog-20160807-001.TXT')  # return from Wilder Ranch
    output_stream = live_stream()

    # Install input handlers (callbacks for commands)
    d.add_command('send', add_sender)
    d.add_command('pause', lambda: sendjob.pause())
    d.add_command('resume', lambda: sendjob.resume())

    # Restart sending: <shift> + F8
    def restart():
        global sendjob
        sendjob.remove()
        add_sender()

    d.add_key(Keystroke(ucs='', code=284, name='KEY_F20'), restart)

    # Start the display
    d.start()
