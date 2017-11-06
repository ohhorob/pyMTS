
# ISP2 Frame
# 16 bit words in big endian order
# 2 bytes, arriving in [Most-Significant], [Least-Significant]
from __future__ import print_function

import ctypes

from MTS.Packet import Packet
from MTS.word.HeaderWord import HeaderWord

c_uint8 = ctypes.c_uint8

# Convenience Union to access the word or the fields


class Header(ctypes.Union):
    _fields_ = [
        ('word', ctypes.c_uint16),
        ('b', HeaderWord)
    ]
    _anonymous_ = 'b'

    def __init__(self, *args, **kwargs):
        super(Header, self).__init__(*args, **kwargs)
        if 'word' in kwargs:
            self.word = kwargs['word']
            self.b.is_valid()

    def word_count(self):
        return (self.b.LengthHigh << 7) | self.b.LengthLow

    def read_packet(self, in_stream, debug_stream=None):
        # Read the bytes that are required to complete the packet
        wordslen = (self.word & 0x1000 << 7) | self.word & 0x007F
        byteslen = wordslen * 2
        if debug_stream:
            print(
                'words={:d}; bytes={:d}'.format(wordslen, byteslen),
                file=debug_stream
            )
        bodybytes = bytearray(b'0' * byteslen)
        if debug_stream:
            print(' '.join(['{:02X}'.format(b) for b in bodybytes]), file=debug_stream)

        in_stream.readinto(bodybytes)

        # Take pairs of body bytes for to return words of data
        body = [(bodybytes[idx] << 8) | bodybytes[idx + 1] for idx in range(0, byteslen-1, 2)]
        return Packet(self, body)

        # words.extend()
        # words_hexstring = ' '.join(['{:04X}'.format(w) for w in words])
        # print(words_hexstring)

    def desc(self):
        return '0x{:04X} {} Len={:d} words '.format(
                self.word,
                'Data' if self.b.is_data() else 'Response',
                self.b.length()
        )
