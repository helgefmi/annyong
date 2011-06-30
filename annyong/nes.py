from __future__ import absolute_import

from annyong.mappers.mapper0 import Mapper0
from annyong.mpu.mpu6502 import Mpu6502
from annyong.ppu.ppu import PPU
from annyong.rom import Rom

class NES(object):
    # Indexed by iNES' mapper ids.
    mappers = (
        Mapper0,
    )
    def __init__(self):
        self.mpu = Mpu6502()
        self.ppu = PPU(self)
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
        self.mapper = NES.mappers[self.rom.mapper_id](self)

        # Initializes read/write subscribers, and loads the rom into
        # the mpu and ppu.
        self.mapper.connect()
        
    def start(self):
        tracefile = open('trace.log', 'w')
        self.mpu.set_trace_output(tracefile)
        self.mpu.interrupt('reset')
        while True:
            self.frame()

    def frame(self):
        self.ppu.start_frame()
        looping = True
        while looping:
            cycles = self.mpu.step()
            for _ in range(cycles * 3):
                self.ppu.step()
                if self.ppu.scanline == 261:
                    looping = False
                    break
