from annyong.memory import Memory

class PPU(object):
    def __init__(self):
        self.memory = Memory(0x4000)
