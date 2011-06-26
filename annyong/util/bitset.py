from array import array

class Bitset(object):
    """
    >>> b = Bitset(8)
    >>> b[0] = 1
    >>> b[1] = True
    >>> b[2] = False
    >>> b[3] = 2
    >>> b[4] = 0.0
    >>> b[5] = None
    >>> b[6] = b
    >>> b[7] = b[6]
    >>> b
    203
    >>> len(b)
    8
    >>> [1 if b[i] else 0 for i in range(8)]
    [1, 1, 0, 1, 0, 0, 1, 1]
    """
    def __init__(self, size):
        self._size = size
        self._mem = None
        self.reset()

    def __getitem__(self, key):
        return self._mem[key]

    def __setitem__(self, key, value):
        self._mem[key] = 1 if value else 0

    def __len__(self):
        return self._size

    def __str__(self):
        return '%d' % int(self)
    __repr__ = __str__

    def set(self, value):
        for i in xrange(self._size):
            self[i] = value & (1 << i)

    def reset(self):
        self._mem = array('b', [0] * self._size)

    def __trunc__(self):
        value = 0
        for i in xrange(self._size):
            value |= self._mem[i] << i
        return value
