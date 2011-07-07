from array import array

class Memory(object):
    def __init__(self, size):
        self._size = size
        self._array = None
        self._read_subscribers = None
        self._write_subscribers = None
        self.reset()

    def reset(self):
        self._array = array('B', [0] * self._size)
        self._read_subscribers = [None] * self._size
        self._write_subscribers = [None] * self._size

    def get_byte(self, offset):
        if self._read_subscribers[offset] is not None:
            return self._read_subscribers[offset](offset)
        return self._array[offset]

    def get_word(self, offset):
        return self.get_byte(offset) + (self.get_byte(offset + 1) << 8)

    def set_byte(self, offset, value):
        if self._write_subscribers[offset]:
            return self._write_subscribers[offset](offset, value=value)
        self._array[offset] = value

    def set_word(self, offset, value):
        self.set_byte(offset, value & 0xFF)
        self.set_byte(offset + 1, value >> 8)

    def subscribe_to_read(self, start, end, fn):
        for i in xrange(start, end):
            assert self._read_subscribers[i] is None
            self._read_subscribers[i] = fn

    def subscribe_to_write(self, start, end, fn):
        for i in xrange(start, end):
            assert self._write_subscribers[i] is None
            self._write_subscribers[i] = fn

    def copy_from_raw(self, raw, start, size=None):
        size = size or len(raw)
        assert len(raw) >= size
        for rpos, mpos in enumerate(xrange(start, start + size)):
            self._array[mpos] = ord(raw[rpos])
