import ctypes

PACKET_INTERVAL = 81.92 # 8000000 / 655360

def packet_tostring(packet):
    # chunks = ["Size={:02d}".format(len(packet))]
    # Header word
    from MTS.Header import Header
    header = Header()
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

class FunctionBits(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', ctypes.c_uint8, 1),  # 07
        ('AirFuelLow', ctypes.c_uint8, 7),      # 06..00

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
        ('LambdaLow', ctypes.c_uint8, 7),       # 06..00

        # High Byte
        ('CLEAR15', ctypes.c_uint8, 1),     # 15
        ('CLEAR14', ctypes.c_uint8, 1),     # 14
        ('LambdaHigh', ctypes.c_uint8, 6),  # 13 .. 08
    ]


class BatteryBits(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', ctypes.c_uint8, 1),  # 07
        ('BatteryLow', ctypes.c_uint8, 7),      # 06..00

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
        ('AuxLow', ctypes.c_uint8, 7),          # 06..00

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
