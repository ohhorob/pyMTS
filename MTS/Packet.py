# coding=utf-8
from __future__ import division
import ctypes

import MTS

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
        fbits = SubPacket()
        fbits.word = packet[1]
        lbits = SubPacket()
        lbits.word = packet[2]
        auxstart += 2

        if len(packet) > 3 and packet[3] & 0x3800 != 0:
            bbits = SubPacket()
            bbits.word = packet[3]
            auxstart += 1

    # Channels
    if len(packet) >= auxstart:
        for channel, auxword in enumerate(packet[auxstart:]):
            abits = SubPacket()
            abits.word = auxword
            chunks.append("ch{:02d}={:4.4f}V".format(channel + 1, abits.aux.volts()))

    return '; '.join(chunks)


class Packet(object):
    def __init__(self, header, body):
        """

        :type body: list of words
        :type header: MTS.Header.Header
        :rtype: Packet
        """
        super(Packet, self).__init__()
        self._header = header
        self._subpackets = []
        self._has_lambda = False
        self._auxstart = 0

        # Optional Function&Lambda&Battery
        if body[0] & MTS.FUNCTION_LAMBDA_MASK == MTS.FUNCTION_LAMBDA_MASK:
            self._has_lambda = True
            fbits = SubPacket()
            fbits.word = body[0]
            self._subpackets.append(fbits)
            lbits = SubPacket()
            lbits.word = body[1]
            self._subpackets.append(lbits)
            self._auxstart += 2
            if len(body) > 2 and body[2] & 0x3800 != 0:
                bbits = SubPacket()
                bbits.word = body[2]
                self._auxstart += 1

        elif body[0] & MTS.FUNCTION_LM_MASK == MTS.FUNCTION_LM_MASK:
            raise ValueError('LM-1 Not implemented.')

        # Channels
        if len(body) >= self._auxstart:
            for channel, auxword in enumerate(body[self._auxstart:]):
                abits = SubPacket()
                abits.word = auxword
                self._subpackets.append(abits)
        else:
            self._auxstart = 0

    def __str__(self):
        result = "Rec={}".format(self._header.b.Recording)
        if self._has_lambda:
            f = getattr(self._subpackets[0], 'function')
            result += " {}={} {}".format(f.function(), f.air_fuel_value(), f.air_fuel_units())
            try:
                result += " AFR={:f}".format(self.air_fuel_ratio())
            except ValueError as afr_error:
                result += " {}".format(afr_error.message)

        if self._auxstart > 0:
            for channel, a in enumerate([p.aux for p in self._subpackets[self._auxstart:]]):
                result += " ch{:02d}={:4.4f}V".format(channel, a.volts())
        return result

    def add_word(self, word):
        """
        Append a word to subpacket list
        :type word: short
        :param word:
        :rtype: None
        """
        p = SubPacket()
        p.word = word
        self._subpackets.append(p)

    def words(self):
        """

        :rtype: list
        """
        return [self._header.word] + [p.word for p in self._subpackets]

    def air_fuel_ratio(self):
        # Air/Fuel Ratio = ((L12..L0) + 500)* (AF7..0) / 10000
        if self._has_lambda:
            # Resolve the Function packet from first sub-packet union
            f = self._subpackets[0].function
            # Must be in 'Normal' function
            if 'Normal' is not f.function():
                raise ValueError('AFR not available. {}'.format(f.function()))
            l = getattr(self._subpackets[1], 'lambda')
            return (l.lambda_value() + 500) * f.air_fuel_value() / 10000


Functions = {
    0b000: 'Normal',
    0b001: 'O2 Tenths',
    0b010: 'Calibrating Air',
    0b011: 'Cal Required',
    0b100: 'Warmup',
    0b101: 'Calibrating Heat',
    0b110: 'Error',
    0b111: 'Reserved'
}


class FunctionBits(ctypes.BigEndianStructure):
    _fields_ = [
        # Low Byte
        ('CLEAR07', ctypes.c_uint8, 1),  # 07
        ('AirFuelLow', ctypes.c_uint8, 7),      # 06..00

        # High Byte
        ('CLEAR15', ctypes.c_uint8, 1),      # 15
        ('SET14', ctypes.c_uint8, 1),        # 14
        ('CLEAR13', ctypes.c_uint8, 1),      # 13
        ('Function', ctypes.c_uint8, 3),     # 12 .. 10
        ('SET09', ctypes.c_uint8, 1),        # 09
        ('AirFuelHigh', ctypes.c_uint8, 1),  # 08
    ]

    def _value(self):
        return (self.AirFuelHigh << 7) | self.AirFuelLow

    def function(self):
        return Functions[self.Function]

    def air_fuel_units(self):
        f = self.function()
        if f is 'Normal':
            return 'ratio'
        if f in ('02 Tenths', 'Warmup'):
            return '%'
        if f is 'Calibrating Heat':
            return 'count'
        # TODO: other function units
        return ''

    def air_fuel_value(self):
        v = self._value()
        f = self.function()
        if f in ('02 Tenths', 'Warmup'):
            v *= 0.10
        elif f in ('Calibrating Air', 'Cal Required',  'Reserved'):
            v = None
        # TODO: other value adjustments
        return v


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

    def _value(self):
        return (self.LambdaHigh << 7) | self.LambdaLow

    def lambda_value(self):
        return self._value()


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


class SubPacket(ctypes.Union):
    _fields_ = [
        ('word', ctypes.c_uint16),
        ('function', FunctionBits),
        ('lambda', LambdaBits),  # use getattr(sub_packet, 'lambda') to avoid reserved word
        ('battery', BatteryBits),
        ('aux', AuxBits)
    ]
