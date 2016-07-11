
# ISP2 Frame
# 16 bit words in big endian order
# 2 bytes, arriving in [Most-Significant], [Least-Significant]
import ctypes

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

    def desc(self):
        return '0x{:04X} {} Len={:d} words '.format(
                self.word,
                'Data' if self.b.is_data() else 'Response',
                self.b.length()
        )