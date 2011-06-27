from annyong.memory import Memory

class PPU(object):
    def __init__(self):
        self.memory = Memory(0x10000)

    # 0x2000 (w)
    def reg_controller(self, offset, value):
        assert False

    # 0x2001 (w)
    def reg_mask(self, offset, value):
        assert False

    # 0x2002 (r)
    def reg_status(self, offset):
        assert False

    # 0x2003 (w)
    def reg_oam_address(self, offset, value):
        assert False

    # 0x2004 (rw)
    def reg_oam_data(self, offset, value):
        assert False

    # 0x2005 (w)
    def reg_scroll(self, offset, value):
        assert False

    # 0x2006 (w)
    def reg_vram_address(self, offset, value):
        assert False

    # 0x2007 (rw)
    def reg_vram_data(self, offset, value):
        assert False
