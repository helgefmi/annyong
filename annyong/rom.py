import struct
from StringIO import StringIO

class Rom(object):
    class InvalidRomException(BaseException):
        pass

    def __init__(self):
        pass

    def load_raw(self, raw):
        raw = StringIO(raw)

        # Bytes 0-4
        if not raw.read(4).startswith('NES\x1a'):
            raise Rom.InvalidRomException('doesn\'t seem to be a .nes file')

        # Bytes 4-8
        prg_count, chr_count, flags1, flags2 = struct.unpack('4B', raw.read(4))

        if not (0 < prg_count < 64):
            raise Rom.InvalidRomException('invalid PRG page count: %d' %
                prg_count
            )
        if not (0 < chr_count < 64):
            raise Rom.InvalidRomException('invalid CHR page count: %d' %
                chr_count
            )

        self._mirroring = 'v' if flags1 & 1 else ('4' if flags1 & 8 else 'h')
        self._battery_sram = flags1 & 2 > 0
        has_trainer = flags1 & 4 > 0
        self._mapper_no = ((flags1 >> 4) & 0xF) | (flags2 & 0xF0)
        is_nes2 = (flags2 >> 2) & 3 == 2

        # Bytes 8-16
        if not is_nes2:
            if sum(struct.unpack('8B', raw.read(8))) != 0:
                raise Rom.InvalidRomException('bytes 8-16 isn\'t zeroed')
        else:
            assert False

        # 16-528 (if trainer is present)
        if has_trainer:
            self._trainer_raw = raw.read(512)
        else:
            self._trainer_raw = None

        # PRG ROM data
        prg_len = prg_count * 16384
        self._prg_raw = raw.read(prg_len)
        if len(self._prg_raw) != prg_len:
            raise Rom.InvalidRomException('not enough data for the PRG pages')

        # CHR ROM data
        chr_len = chr_count * 8192
        self._chr_raw = raw.read(chr_len)
        if len(self._chr_raw) != chr_len:
            raise Rom.InvalidRomException('not enough data for the CHR pages')

        if raw.read(1):
            raise Rom.InvalidRomException('unused data')
