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
    def __init__(self, logfile=None):
        self.mpu = Mpu6502(self)
        self.ppu = PPU(self)
        self.rom = Rom()
        self.mapper = None
        self.frame_num = None
        self.logfile = logfile or open('trace.log', 'w')
        self.ppucycles = None

    def log(self, msg):
        if self.logfile:
            self.logfile.write(msg + '\n')

    def load_rom(self, path):
        # Resets registers, memory and read/write subscribers (i.e. disconnects
        # the any mappers)
        self.mpu.reset()
        self.frame_num = 0
        self.ppucycles = 0

        with open(path, 'rb') as file:
            raw = file.read()
        self.rom.load_raw(raw)

        # Create the mapper this ROM uses.
        self.mapper = NES.mappers[self.rom.mapper_id](self)

        # Initializes read/write subscribers, and loads the rom into
        # the mpu and ppu.
        self.mapper.connect()
        
    def start(self):
        self.mpu.interrupt('reset')
        while True:
            self.frame()

    def frame(self):
        self.frame_num += 1

        print "Frame %04d" % self.frame_num
        self.log('Frame %04d' % self.frame_num)

        while True:
            self.ppu.start_scanline()

            if self.ppu.scanline == 241 and self.ppu.ctrlreg1.nmi_on_vblank:
                self.ppucycles += self.mpu.interrupt('nmi') * 3

            while self.ppucycles < 341:
                self.ppucycles += self.mpu.step() * 3
            self.ppucycles -= 341

            self.ppu.end_scanline()

            if self.ppu.scanline == -1:
                break

        print "Screen"
        print self.format_buffer(self.ppu.screen, 256, 240)

        buffers = self.ppu.render_nametable()
        for base, buffer in buffers.iteritems():
            print "Name table %04X" % base
            print self.format_buffer(buffer, 256, 240)

        buffers = self.ppu.render_pattern_tables()
        for base, buffer in buffers.iteritems():
            print "Pattern table %04X" % base
            print self.format_buffer(buffer, 128, 128)
    
    def format_buffer(self, buffer, w, h):
        ret = ''
        for y in xrange(h):
            for x in xrange(w):
                ret += str(buffer[y * w + x])
            ret += '\n'
        return ret.replace('0', '.').strip()
