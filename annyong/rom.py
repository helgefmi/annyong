import struct
from StringIO import StringIO

class Rom(object):
    class InvalidRomException(BaseException):
        pass

    def __init__(self):
        # For Rom's attributes, look in reset()
        self.reset()

    def reset(self):
        # From header
        self.mirroring = None
        self.battery_sram = None
        self.has_trainer = None
        self.mapper_id = None
        # Raw data
        self.trainer_raw = None
        self.prg_raw = None
        self.chr_raw = None

    def load_raw(self, raw):
        self.reset()
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

        self.mirroring = 'v' if flags1 & 1 else ('4' if flags1 & 8 else 'h')
        self.battery_sram = flags1 & 2 > 0
        self.has_trainer = flags1 & 4 > 0
        self.mapper_id = ((flags1 >> 4) & 0xF) | (flags2 & 0xF0)
        is_nes2 = (flags2 >> 2) & 3 == 2

        # Bytes 8-16
        if not is_nes2:
            if sum(struct.unpack('8B', raw.read(8))) != 0:
                raise Rom.InvalidRomException('bytes 8-16 isn\'t zeroed')
        else:
            assert False

        # Trainer data (if it's present)
        if self.has_trainer:
            self.trainer_raw = raw.read(512)
        else:
            self.trainer_raw = None

        # PRG ROM data
        prg_len = prg_count * 16384
        self.prg_raw = raw.read(prg_len)
        if len(self.prg_raw) != prg_len:
            raise Rom.InvalidRomException('not enough data for the PRG pages')

        # CHR ROM data
        chr_len = chr_count * 8192
        self.chr_raw = raw.read(chr_len)
        if len(self.chr_raw) != chr_len:
            raise Rom.InvalidRomException('not enough data for the CHR pages')

        # Make sure we've read everything.
        if raw.read(1):
            raise Rom.InvalidRomException('unused data')
