class Mapper0(object):
    def __init__(self, nes):
        self.nes = nes

    def _mirror_memory(self, mirror_start, mirror_end, start, end):
        assert start < end
        assert mirror_start < mirror_end
        assert start < mirror_start or start >= mirror_end
        assert end < mirror_start or end >= mirror_end

        mirror_size = mirror_end - mirror_start

        def writer(offset, value):
            new_offset = mirror_start + (offset % mirror_size)
            return self.nes.mpu.memory.set_byte(new_offset, value)

        def reader(offset):
            new_offset = mirror_start + (offset % mirror_size)
            return self.nes.mpu.memory.get_byte(new_offset)

        for i in xrange(start, end, mirror_size):
            self.nes.mpu.memory.subscribe_to_read(i, i + mirror_size, reader)
            self.nes.mpu.memory.subscribe_to_write(i, i + mirror_size, writer)

    def _disallow_write(self, start, end):
        def writer(offset, value):
            assert False
        self.nes.mpu.memory.subscribe_to_write(start, end, writer)

    def connect(self):
        assert self.nes.mapper is self

        mpu = self.nes.mpu
        ppu = self.nes.ppu
        rom = self.nes.rom

        #### SETUP MPU MEMORY ####
        # "Memory locations $0000-$07FF are mirrored three times at $0800-$1FFF"
        self._mirror_memory(0x0, 0x800, 0x800, 0x2000)

        # "Locations $2000-$2007 are mirrored every 8 bytes in the region
        # $2008-$3FFF"
        self._mirror_memory(0x2000, 0x2008, 0x2008, 0x4000)

        # This is just for testing right now.
        # Expansion ROM
        self._disallow_write(0x4020, 0x6000)
        # PRG ROM
        self._disallow_write(0x8000, 0x10000)

        # Load PRG ROM into mpu memory
        mpu.memory.copy_from_raw(rom.prg_banks[0], 0x8000, 0x4000)
        bank2 = rom.prg_banks[1] if len(rom.prg_banks) > 1 else rom.prg_banks[0]
        mpu.memory.copy_from_raw(bank2, 0xC000, 0x4000)

        #### SETUP PPU MEMORY ####
        # Load CHR ROM into ppu memory
        ppu.memory.copy_from_raw(rom.chr_banks[0], 0x0000, 0x2000)
