from __future__ import absolute_import

from annyong.mpu.mpu6502 import Mpu6502
from annyong.rom import Rom

class Annyong(object):
    def __init__(self):
        self.mpu = Mpu6502()
        self.rom = Rom()

    def load_rom(self, path):
        # Resets registers, memory and read/write subscribers
        self.mpu.reset()

        with open(path, 'rb') as file:
            raw = file.read()
        #self.rom.reset()
        self.rom.load_raw(raw)

        # Initializes read/write subscribers
        #self.mapper.connect()
        self.mpu.memory.copy_from_raw(self.rom._chr_raw, 0x0000, 0x2000)
        self.mpu.memory.copy_from_raw(self.rom._prg_raw, 0x8000, 0x4000)
        self.mpu.memory.copy_from_raw(self.rom._prg_raw, 0xC000, 0x4000)
        
    def start(self):
        self.mpu.run()
