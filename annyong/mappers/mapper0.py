class Mapper0(object):
    def __init__(self, nes):
        self.nes = nes

    def _mirror_memory(self, memory, mirror_start, mirror_size, start, end):
        mirror_end = mirror_start + mirror_size

        assert start < end
        assert mirror_start < mirror_end
        assert start < mirror_start or start >= mirror_end
        assert end < mirror_start or end >= mirror_end

        def writer(offset, value):
            new_offset = mirror_start + (offset % mirror_size)
            return memory.set_byte(new_offset, value)

        def reader(offset):
            new_offset = mirror_start + (offset % mirror_size)
            return memory.get_byte(new_offset)

        for i in xrange(start, end, mirror_size):
            memory.subscribe_to_read(i, i + mirror_size, reader)
            memory.subscribe_to_write(i, i + mirror_size, writer)

    def _disallow_write(self, memory, start, end):
        def writer(offset, value):
            assert False, (hex(offset), hex(value))
        memory.subscribe_to_write(start, end, writer)

    def connect(self):
        assert self.nes.mapper is self

        mpu = self.nes.mpu
        ppu = self.nes.ppu
        rom = self.nes.rom


        #### SETUP MPU MEMORY ####
        # "Memory locations $0000-$07FF are mirrored three times at $0800-$1FFF"
        self._mirror_memory(mpu.memory, 0x0000, 0x0800, 0x0800, 0x2000)

        # "Locations $2000-$2007 are mirrored every 8 bytes in the region
        # $2008-$3FFF"
        self._mirror_memory(mpu.memory, 0x2000, 0x0008, 0x2008, 0x4000)

        # This is just for testing right now.
        # Expansion ROM
        self._disallow_write(mpu.memory, 0x4020, 0x6000)
        # PRG ROM
        self._disallow_write(mpu.memory, 0x8000, 0x10000)

        # Load PRG ROM into mpu memory
        mpu.memory.copy_from_raw(rom.prg_banks[0], 0x8000, 0x4000)
        bank2 = rom.prg_banks[1] if len(rom.prg_banks) > 1 else rom.prg_banks[0]
        mpu.memory.copy_from_raw(bank2, 0xC000, 0x4000)


        #### SETUP PPU MEMORY ####
        # Load CHR ROM into ppu memory
        if len(rom.chr_banks) > 0:
            ppu.memory.copy_from_raw(rom.chr_banks[0], 0x0000, 0x2000)

        # Set up mirroring of name tables
        if rom.mirroring == 'h':
            self._mirror_memory(ppu.memory, 0x2000, 0x0400, 0x2400, 0x2800)
            self._mirror_memory(ppu.memory, 0x2800, 0x0400, 0x2C00, 0x3000)
        elif rom.mirroring == 'v':
            self._mirror_memory(ppu.memory, 0x2000, 0x0400, 0x2800, 0x2C00)
            self._mirror_memory(ppu.memory, 0x2400, 0x0400, 0x2C00, 0x3000)

        # These sections are always mirrored
        self._mirror_memory(ppu.memory, 0x2000, 0x0F00, 0x3000, 0x3F00)
        self._mirror_memory(ppu.memory, 0x0000, 0x1000, 0x4000, 0x8000)

        # "Addresses $3F10/$3F14/$3F18/$3F1C are mirrors of
        # $3F00/$3F04/$3F08/$3F0C."
        for i in xrange(0x3F00, 0x3F10, 0x4):
            self._mirror_memory(ppu.memory, i, 0x0001, i + 0x0010, i + 0x0011)

        mpu.memory.subscribe_to_write(0x2000, 0x2001, ppu.reg_controller)
        mpu.memory.subscribe_to_write(0x2001, 0x2002, ppu.reg_mask)
        mpu.memory.subscribe_to_read( 0x2002, 0x2003, ppu.reg_status)
        mpu.memory.subscribe_to_write(0x2003, 0x2004, ppu.reg_oam_address)
        mpu.memory.subscribe_to_write(0x2004, 0x2005, ppu.reg_oam_data)
        mpu.memory.subscribe_to_write(0x2005, 0x2006, ppu.reg_scroll)
        mpu.memory.subscribe_to_write(0x2006, 0x2007, ppu.reg_vram_address)
        mpu.memory.subscribe_to_read( 0x2007, 0x2008, ppu.reg_vram_data)
        mpu.memory.subscribe_to_write(0x2007, 0x2008, ppu.reg_vram_data)
