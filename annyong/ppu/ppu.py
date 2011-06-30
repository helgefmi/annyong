from annyong.memory import Memory
from annyong.util.bitset import Bitset

class PPU(object):
    def __init__(self, nes):
        self.nes = nes
        self.memory = Memory(0x10000)
        self.ctrlreg1 = Bitset(
            ('name_tbl_addr', 2), # 1-2
            ('ppu_addr_inc',  1), # 3
            ('spr_tbl_addr',  1), # 4
            ('bg_tbl_addr',   1), # 5
            ('spr_size',      1), # 6
            ('unused',        1), # 7
            ('nmi_on_vblank', 1), # 8
        )
        self.ctrlreg2 = Bitset(
            ('display_type',   1), # 1
            ('bg_clipping',    1), # 2
            ('spr_clipping',   1), # 3
            ('bg_visibility',  1), # 4
            ('spr_visibility', 1), # 5
            ('color',          3), # 6-8
        )
        self.statusreg = Bitset(
            ('unused',             4), # 1-4
            ('ignore_vram_writes', 1), # 5
            ('scanline_spr_count', 1), # 6
            ('spr0_hit',           1), # 7
            ('vblank',             1), # 8
        )
        self.spr_ram = None
        self.spr_ram_addr = None
        self.xpos = 0

        self.reset()

    def reset(self):
        self.ctrlreg1.set(0)
        self.ctrlreg2.set(0)
        self.statusreg.set(0)
        self.spr_ram = [0] * 256
        self.spr_ram_addr = 0
        self.xpos = 0

    # 0x2000 (w)
    def reg_controller(self, offset, value):
        self.ctrlreg1.set(value)

    # 0x2001 (w)
    def reg_mask(self, offset, value):
        self.ctrlreg2.set(value)

    # 0x2002 (r)
    def reg_status(self, offset):
        ret = int(self.statusreg)
        self.statusreg.vblank = 0
        return ret

    # 0x2003 (w)
    def reg_oam_address(self, offset, value):
        self.spr_ram_addr = value

    # 0x2004 (rw)
    def reg_oam_data(self, offset, **kwargs):
        # read
        if 'value' not in kwargs:
            return self.spr_ram[self.spr_ram_addr]

        # write
        self.spr_ram[self.spr_ram_addr] = kwargs['value']
        self.spr_ram_addr = (self.spr_ram_addr + 1) & 0xFF

    # 0x2005 (w)
    def reg_scroll(self, offset, value):
        assert False

    # 0x2006 (w)
    def reg_vram_address(self, offset, value):
        assert False

    # 0x2007 (rw)
    def reg_vram_data(self, offset, value):
        assert False

    # 0x4014 (w)
    def reg_oam_transfer(self, offset, value):
        data_offset = value * 0x100

        for i in xrange(256):
            byte = self.nes.mpu.memory.get_byte(data_offset)
            self.reg_oam_data(0x2004, value=byte)

        # 513 for odd cycles
        self.nes.mpu.add_halt_cycles(514 - (self.nes.mpu.cycles & 1))

    def start_frame(self):
        self.cycles = 0
        self.scanline = -1

    def step(self):
        if self.cycles == 0:
            self.start_scanline()

        self.cycles += 1

        if self.cycles == 341:
            self.end_scanline()

    def start_scanline(self):
        if self.scanline == 241:
            self.statusreg.vblank = 1

    def end_scanline(self):
        self.cycles = 0
        self.scanline += 1
