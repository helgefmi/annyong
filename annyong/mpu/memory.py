from array import array

class Memory(object):
    def __init__(self, size=0x10000):
        self._size = size
        self._array = None
        self._read_subscribers = None
        self._write_subscribers = None
        self.reset()

    def get_byte(self, offset):
        for start, end, fn in self._read_subscribers:
            if start <= offset < end:
                return fn(offset)
        return self._array[offset]

    def get_word(self, offset):
        return self.get_byte(offset) + (self.get_byte(offset + 1) << 8)

    def set_byte(self, offset, value):
        for start, end, fn in self._read_subscribers:
            if start <= offset < end:
                fn(offset, value)
        self._array[offset] = value

    def set_word(self, offset, value):
        assert value < 0x10000
        self.set_byte(offset, value & 0xFF)
        self.set_byte(offset + 1, value >> 8)

    def reset(self):
        self._array = array('B', [0] * self._size)
        self._read_subscribers = []
        self._write_subscribers = []

    def subscribe_to_read(start, end, fn):
        for start2, end2, _ in self._read_subscribers:
            if (start2 <= start < end2) or (start2 <= end < end2):
                raise Exception('Tried to subscribe twice to the same region')
        self._read_subscribers.append((start, end, fn))

    def subscribe_to_write(start, end, fn):
        for start2, end2, _ in self._write_subscribers:
            if (start2 <= start < end2) or (start2 <= end < end2):
                raise Exception('Tried to subscribe twice to the same region')
        self._write_subscribers.append((start, end, fn))

    def copy_from_raw(self, raw, start, size=None):
        if size is None:
            size = len(raw)
        assert len(raw) >= size
        for rpos, mpos in enumerate(xrange(start, start + size)):
            self._array[mpos] = ord(raw[rpos])
