class Mapper0(object):
    def __init__(self, nes):
        self.nes = nes

    def connect(self):
        assert self.nes.mapper is self

        mpu = self.nes.mpu
        rom = self.nes.rom

        mpu.memory.copy_from_raw(rom.chr_raw, 0x0000, 0x2000)
        mpu.memory.copy_from_raw(rom.prg_raw, 0x8000, 0x4000)
        mpu.memory.copy_from_raw(rom.prg_raw, 0xC000, 0x4000)
