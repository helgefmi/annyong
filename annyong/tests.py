from __future__ import absolute_import

from StringIO import StringIO

from annyong.nes import NES
from annyong.mpu.mpu6502 import Mpu6502

def run_nestest(rom_path):
    nes = NES()
    nes.load_rom(rom_path)

    # This is just so the logs can be diffed
    nes.mpu.reg.ps.set(0x24)
    nes.mpu.reg.sp = 0xFD

    # This test compares the trace output of our mpu and nestest.log, so we need
    # to capture this.
    nes.mpu.set_trace_output(StringIO())
    try:
        nes.mpu.run(0xC000)
    except nes.mpu.InvalidOpcodeException:
        pass

    trace_output = nes.mpu.trace_output.getvalue()
    trace_lines = trace_output.strip().split('\n')
    with open('trace.log', 'w') as file:
        file.write(trace_output)

    nestest_logpath = rom_path.replace('.nes', '.log')
    with open(nestest_logpath, 'r') as file:
        correct_lines = file.read().strip().split('\n')

    # Check every line.
    # Note that the mpu will probably stop execution after it should, so
    # trace_lines will contain more lines than correct_lines.
    for i in xrange(len(correct_lines)):
        if i >= len(trace_lines):
            print "ERROR: Not enough lines in trace."
            print "Correct: %d, Trace: %d" % (
                len(correct_lines), len(trace_lines)
            )
            break
        if trace_lines[i].strip() != correct_lines[i].strip():
            print "Error on line %d" % i
            print 'trace  ', trace_lines[i]
            print 'nestest', correct_lines[i]
            break
    else:
        print "%d lines correct!" % len(correct_lines)
