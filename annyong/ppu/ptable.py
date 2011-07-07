from array import array

class Tile(object):
    def __init__(self, idx):
        self.idx = idx
        self.memory = array('B', [0] * 16)

    def get_pixel(self, x, y):
        byte1 = self.memory[y]
        byte2 = self.memory[y + 8]
        bit_idx = 7 - x
        pixel = (byte1 >> bit_idx) & 1
        pixel |= ((byte2 >> bit_idx) & 1) << 1
        return pixel

class PTable(object):
    def __init__(self):
        self.tiles = [Tile(i) for i in xrange(16 * 16)]

    def get_tile(self, idx):
        return self.tiles[idx]

    def copy_from_raw(self, raw):
        for i in xrange(0, 0x1000, 16):
            tile_idx = i / 16
            for p in xrange(16):
                self.tiles[tile_idx].memory[p] = ord(raw[i + p])
