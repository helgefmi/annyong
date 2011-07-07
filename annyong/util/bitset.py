from array import array

class Bitset(object):
    def __init__(self, *args):
        self._num = 0
        self._format = {}

        pos = 0
        for key, value in args:
            self._format[key] = {
                'bits': value,
                'pos': pos,
                'mask': ((2 ** value) - 1) << pos,
            }
            pos += value
        self._size = pos
        self._initialized = True

    def __trunc__(self):
        return self._num

    def __len__(self):
        return self._size

    def __str__(self):
        return str(self._num)
    __repr__ = __str__

    def __setattr__(self, key, value):
        if hasattr(self, '_format') and key in self._format:
            value = int(value)
            item = self._format[key]
            self._num &= ~item['mask']
            self._num |= (value << item['pos']) & item['mask']
        elif hasattr(self, key) or not hasattr(self, '_initialized'):
            super(Bitset, self).__setattr__(key, value)
        else:
            raise AttributeError, key

    def __getattr__(self, key):
        if hasattr(self, '_format') and key in self._format:
            item = self._format[key]
            return (self._num & item['mask']) >> item['pos']
        raise AttributeError, key

    def set(self, num):
        self._num = num

    def reset(self):
        self._num = 0
