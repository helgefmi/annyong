import struct

def bcd2bin(bcd):
    h = '%02x' % bcd
    assert len(h) == 2
    assert h.isdigit(), h
    return int(h, 10)

def bin2bcd(bin):
    d = '%02d' % bin
    assert len(d) == 2
    return int(d, 16)

def signed_byte(byte):
    assert 0 <= byte <= 255
    return struct.unpack('b', chr(byte))[0]
