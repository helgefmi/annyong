from array import array

class NTable(object):
    def __init__(self, ppu):
        self.ppu = ppu # Used for get_tile()
        self.indexes = array('B', [0] * 0x3C0)
        self.attribs = array('B', [0] * 0x40)

    def get_tile(self, x, y):
        idx = self.indexes[y * 32 + x]
        return self.ppu.ptables[self.ppu.ctrlreg1.bg_tbl_addr].get_tile(idx)

    def get_attrib(self, x, y):
        """
        00 01 | 02 03 ... 1C 1D | 1E 1F  the 2x2 tiles at each corner get their
        20 21 | 22 23 ... 3C 3D | 3E 3F  2 high bits from the appropriate bit.
        ------+------ ... ------+------         %AABB CCDD        DD | CC
        40 41 | 42 43 ... 5C 5D | 5E 5F                           ---+---
        60 61 | 62 63 ... 7C 7D | 7E 7F                           BB | AA
        """

        attribs = self.attribs[(y / 4) * 8 + (x / 4)]
        bit_index = ((x & 2) >> 1) | (y & 3)
        return (attribs >> bit_index) & 3
