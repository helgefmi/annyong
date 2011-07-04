from array import array

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
        self.fine_x = 0
        self.first_write = None
        self.loopy_t = None
        self.loopy_v = None
        self.vram_buffer = None
        self.scanline = None
        self.screen = None

        self.reset()

    def __str__(self):
        c1 = ','.join([
            'nim=%d' % self.ctrlreg1.nmi_on_vblank,
        ])
        c2 = ','.join([
            'bg=%d' % self.ctrlreg2.bg_visibility,
            'spr=%d' % self.ctrlreg2.spr_visibility,
        ])
        status = ','.join([
            'vb=%d' % self.statusreg.vblank,
        ])

        return '<ppu SL:%d c1:%s(%s) c2:%s(%s) s:%s(%s)>' % (
            self.scanline,
            self.ctrlreg1, c1,
            self.ctrlreg2, c2,
            self.statusreg, status,
        )
    __repr__ = __str__

    def reset(self):
        self.ctrlreg1.set(0)
        self.ctrlreg2.set(0)
        self.statusreg.set(0)
        self.spr_ram = array('B', [0] * 256)
        self.spr_ram_addr = 0
        self.fine_x = 0
        self.first_write = True
        self.loopy_t = 0
        self.loopy_v = 0
        self.vram_buffer = 0
        self.scanline = -1
        self.screen = [0] * (256 * 240)

    def has_visible(self):
        return self.ctrlreg2.bg_visibility or self.ctrlreg2.spr_visibility

    # Registers {{{

    # 0x2000 (w)
    def reg_controller(self, offset, value):
        self.ctrlreg1.set(value)
        assert self.ctrlreg1.spr_size == 0
        # t:0000110000000000=d:00000011
        self.loopy_t &= 0b1111001111111111
        self.loopy_t |= self.ctrlreg1.name_tbl_addr << 10

    # 0x2001 (w)
    def reg_mask(self, offset, value):
        self.ctrlreg2.set(value)

    # 0x2002 (r)
    def reg_status(self, offset):
        ret = int(self.statusreg)
        self.statusreg.vblank = 0
        self.first_write = True
        return ret

    # 0x2003 (w)
    def reg_oam_address(self, offset, value):
        self.spr_ram_addr = value

    # 0x2004 (rw)
    def reg_oam_data(self, offset, **kwargs):
        ret = None
        if 'value' not in kwargs:
            # read
            ret = self.spr_ram[self.spr_ram_addr]
        else:
            # write
            self.spr_ram[self.spr_ram_addr] = kwargs['value']
        self.spr_ram_addr = (self.spr_ram_addr + 1) & 0xFF
        return ret

    # 0x2005 (w)
    def reg_scroll(self, offset, value):
        if self.first_write:
            # t:0000000000011111=d:11111000
            # x=d:00000111
            self.loopy_t &= 0b1111111111100000
            self.loopy_t |= (value >> 3) & 31
            self.fine_x = value & 7
        else:
            # t:0000001111100000=d:11111000
            # t:0111000000000000=d:00000111
            self.loopy_t &= 0b1000110000011111
            self.loopy_t |= (value >> 3) << 5
            self.loopy_t |= (value & 7) << 12
        self.first_write = not self.first_write

    # 0x2006 (w)
    def reg_vram_address(self, offset, value):
        if self.first_write:
            # t:0011111100000000=d:00111111
            # t:1100000000000000=0
            self.loopy_t &= 0b0000000011111111
            self.loopy_t |= (value & 63) << 8
        else:
            # t:0000000011111111=d:11111111
            # v=t
            self.loopy_t &= 0b1111111100000000
            self.loopy_t |= value
            self.loopy_v = self.loopy_t
        self.first_write = not self.first_write

    # 0x2007 (rw)
    def reg_vram_data(self, offset, **kwargs):
        data_offset = self.loopy_v & 0x7FFF
        self.loopy_v += (32 if self.ctrlreg1.ppu_addr_inc else 1)
        self.loopy_v &= 0x7FFF

        ret = None
        if 'value' in kwargs:
            self.memory.set_byte(data_offset, kwargs['value'])
        elif data_offset & 0x3F00 < 0x3F00:
            ret = self.vram_buffer
            self.vram_buffer = self.memory.get_byte(data_offset)
        else:
            ret = self.memory.get_byte(data_offset)
            self.vram_buffer = ret
        return ret

    # 0x4014 (w)
    def reg_oam_transfer(self, offset, value):
        data_offset = value * 0x100
        for i in xrange(256):
            byte = self.nes.mpu.memory.get_byte(data_offset | self.spr_ram_addr)
            self.reg_oam_data(0x2004, value=byte)
        self.nes.mpu.add_halt_cycles(513)

    # }}}
    # Rendering {{{

    def start_scanline(self):
        if self.scanline == -1:
            if self.has_visible():
                # v=t
                self.loopy_v = self.loopy_t
            self.statusreg.vblank = 0
            self.statusreg.scanline_spr_count = 0
            self.statusreg.spr0_hit = 0

        elif self.has_visible() and 0 <= self.scanline <= 240:
            # v:0000010000011111=t:0000010000011111
            self.loopy_v &= 0b1111101111100000
            self.loopy_v |= self.loopy_t & 0b0000010000011111

        elif self.scanline == 241:
            self.statusreg.vblank = 1

    def end_scanline(self):
        if self.has_visible() and (0 <= self.scanline <= 239):
            self.render_current_scanline()

        self.scanline += 1

        if self.scanline == 262:
            self.scanline = -1
        elif self.scanline == 0:
            pass
        elif self.has_visible() and 0 <= self.scanline <= 240:
            # 0000, 1000, 2000 .... 6000, 7000, 0020, 1020 ... 7020, 0040 ..
            self.loopy_v += 0x1000
            if self.loopy_v & 0x8000:
                self.loopy_v -= 0x7FE0
                # 0380, 03A0, 0800, 0820 ... 0B80, 0BA0, 0000, 0020 ... etc 
                if self.loopy_v & 0x3FF == 0x3C0:
                    next = (self.loopy_v + 0x440) & 0xFFF
                    self.loopy_v &= ~0xFFF
                    self.loopy_v |= next
                # 03C0, 03E0, 0000, 0020 ... 0380, 03A0, 0800 ... etc
                elif self.loopy_v & 0xFFF in [0x400, 0xC00]:
                    self.loopy_v -= 0x400
                
    def render_current_scanline(self):
        v = self.loopy_v
        fine_y = (v >> 12) & 7
        for tileno in xrange(32):
            tile_index = self.memory.get_byte(0x2000 | (v & 0xFFF))
            tile_index <<= 4
            tile_index |= 0x1000 * self.ctrlreg1.bg_tbl_addr
            tile_index += fine_y

            tile_byte_1 = self.memory.get_byte(tile_index)
            tile_byte_2 = self.memory.get_byte(tile_index + 8)

            for i in xrange(8):
                pixno = 7 - ((i + self.fine_x) & 7)

                tile_data = (tile_byte_1 >> pixno) & 1
                tile_data |= ((tile_byte_2 >> pixno) & 1) << 1
                self.screen[self.scanline * 256 + tileno * 8 + i] = tile_data

            if tileno == 31:
                break

            # Update loopy_v
            # 0000, 0001, 0002, 0003 .... 001E, 001F, 0400, 0401 .... 041E,
            # 041F, 0000, 0001 ... etc
            v += 1
            if v & 0xFF == 0x20:
                v ^= 0x420
        self.loopy_v = v

    # }}}

    # Debug {{{

    def render_nametable(self):
        buffers = {}
        for base in [0x2000, 0x2400, 0x2800, 0x2C00]:
            buffers[base] = [None] * (256 * 240)
            for nm_y in xrange(30):
                for nm_x in xrange(32):
                    nm_index = nm_y * 32 + nm_x
                    pt_index = self.memory.get_byte(base + nm_index)
                    for y in xrange(8):
                        pt_byte_1 = self.memory.get_byte(pt_index + y)
                        pt_byte_2 = self.memory.get_byte(pt_index + 8 + y)
                        for x in xrange(8):
                            pixno = 7 - x
                            pixel = (pt_byte_1 >> pixno) & 1
                            pixel |= ((pt_byte_2 >> pixno) & 1) << 1
                            buf_idx = (nm_y * 8 + y) * 256 + (nm_x * 8 + x)
                            buffers[base][buf_idx] = pixel
        return buffers

    def render_pattern_tables(self):
        buffers = {}
        for base in [0x0, 0x1000]:
            buffers[base] = [None] * (16 * 8 * 16 * 8)
            for pt_y in xrange(16):
                for pt_x in xrange(16):
                    pt_index = pt_y * 256 + (pt_x * 16)
                    for y in xrange(8):
                        pt_byte_1 = self.memory.get_byte(pt_index + y)
                        pt_byte_2 = self.memory.get_byte(pt_index + 8 + y)
                        for x in xrange(8):
                            pixno = 7 - x
                            pixel = (pt_byte_1 >> pixno) & 1
                            pixel |= ((pt_byte_2 >> pixno) & 1) << 1
                            buf_idx = (pt_y * 8 + y) * 128 + (pt_x * 8 + x)
                            buffers[base][buf_idx] = pixel
        return buffers
    # }}}
