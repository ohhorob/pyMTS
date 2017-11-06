from __future__ import print_function, division

import io
import sys
import struct
import tempfile

if __name__ == '__main__':
    filename = 'dumped-fromstorage.ISP2'
    serial_input = io.open(
        filename,
        mode='rb',
        buffering=io.DEFAULT_BUFFER_SIZE
    )
    outwrapper = tempfile.NamedTemporaryFile(prefix=filename, suffix='.ISP2', delete=False)
    outwrapper.close()
    swapped_output = io.open(outwrapper.name, mode='w+b')
    bytecount = 0
    try:
        while 1:
            inword = serial_input.read(2)
            if len(inword) != 2:
                raise BufferError("Reached end of stream" if len(inword) == 0 else "Lonely byte")
            bytecount = bytecount + 2
            outword = struct.unpack(u'<H', inword)
            swapped_output.write(struct.pack(u'>H', outword[0]))
    except BufferError as oops:
        print(u'Wrote {} bytes to {}'.format(bytecount, outwrapper.name), file=sys.stdout)
