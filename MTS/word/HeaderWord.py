import ctypes
c_uint8 = ctypes.c_uint8


class HeaderWord(ctypes.BigEndianStructure):

    MAGIC_MASK = 0xA280

    _fields_ = [
        # Low Byte
        ('CLEAR07',        c_uint8, 1),         # 07
        ('LengthLow',      c_uint8, 7),       # 06..00

        # High Byte
        ('HEADER15',       c_uint8, 1),  # 15
        ('Recording',      c_uint8, 1),  # 14
        ('CLEAR13',        c_uint8, 1),  # 13
        ('DataOrResponse', c_uint8, 1),  # 12
        ('LogCapable',     c_uint8, 1),  # 11
        ('RESERVED10',     c_uint8, 1),  # 10
        ('CLEAR09',        c_uint8, 1),  # 09
        ('LengthHigh',     c_uint8, 1),  # 08
    ]

    def is_valid(self):
        if self.HEADER15 == 0:
            raise ValueError('Header start marker (15) not set.')
        if self.CLEAR13 == 0:
            raise ValueError('(13) not set')
        if self.CLEAR09 == 0:
            raise ValueError('(09) not set')
        if self.CLEAR07 == 0:
            raise ValueError('(07) not set')
        return True

    def is_data(self):
        return self.DataOrResponse > 0

    def is_response(self):
        return self.DataOrResponse < 1

    def can_log(self):
        return self.LogCapable > 0

    def is_recording(self):
        return self.Recording > 0

    def length(self):
        return (self.LengthHigh << 7) | self.LengthLow
