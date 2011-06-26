from __future__ import absolute_import

from annyong.mappers.mapper0 import Mapper0
from annyong.mpu.mpu6502 import Mpu6502
from annyong.rom import Rom

class Annyong(object):
    # Indexed by iNES' mapper ids.
    mappers = (
        Mapper0,
    )
    def __init__(self):
        self.mpu = Mpu6502()
        self.rom = Rom()
        self.mapper = None

    def load_rom(self, path):
        # Resets registers, memory and read/write subscribers (i.e. disconnects
        # the any mappers)
        self.mpu.reset()

        with open(path, 'rb') as file:
            raw = file.read()
        self.rom.load_raw(raw)

        # Create the mapper this ROM uses.
        self.mapper = Annyong.mappers[self.rom.mapper_id](self)

        # Initializes read/write subscribers, and loads the rom into the mpu and
        # ppu.
        self.mapper.connect()
        
    def start(self):
        self.mpu.run()
