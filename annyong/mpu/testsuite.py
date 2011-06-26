import os
import sys

from annyong.mpu.mpu6502 import Mpu6502
from annyong.mpu.flags import *

class TestSuite(object):
    def __init__(self):
        self.mpu = Mpu6502()
        self.mpu.set_trace_output(sys.stdout)
        self.successive_tests = None
        self.failed_tests = None

    def run(self, path):
        if not os.path.exists(path):
            print "Path not found: %s" % path
            print "Couldn't start testsuite :-/"
            return

        self.successive_tests = 0
        self.failed_tests = 0

        if os.path.isdir(path):
            for filename in os.listdir(path):
                if not filename.endswith('.t'):
                    continue
                self.test_file(os.path.join(path, filename))
        else:
            self.test_file(path)

        print "Failed %d/%d tests" % (self.failed_tests,
                                      self.failed_tests + self.successive_tests)

    def test_file(self, path):
        file = open(path, 'r')
        contents = file.read()
        file.close()

        # Remove empty lines
        contents = filter(len, contents)

        contents = contents.split('\n')
        while contents:
            test_name = contents.pop(0)[5:]
            if test_name == '':
                continue

            code = []
            while (contents and
                   not contents[0].startswith('assert') and
                   not contents[0].startswith('test')):
                code.append(contents.pop(0))

            asserts = []
            while contents and contents[0].startswith('assert'):
                asserts.append(contents.pop(0).split())

            print "Running %s" % test_name
            was_success = self.run_test(code, asserts)
            if was_success:
                self.successive_tests += 1
            else:
                self.failed_tests += 1
                print '%s, %s: FAIL' % (path, test_name)

    def run_test(self, code, asserts):
        file = open('asm.tmp', 'w')
        file.write('\n'.join(code))
        file.close()

        compile_success = 0 == os.system('xa -C -W -bt0 asm.tmp')
        if not compile_success:
            print "Couldn't compile test"
            os.unlink("asm.tmp")
            os.unlink("a.o65")
            return False

        file = open('a.o65', 'rb')
        raw = file.read()
        file.close()

        self.mpu.reset()
        self.mpu.memory.copy_from_raw(raw, 0)

        os.unlink("asm.tmp")
        os.unlink("a.o65")

        try:
            self.mpu.run(0)
        except Mpu6502.InvalidOpcodeException, e:
            if e.get_opcode() != 2:
                print str(e)
                exit(1) # TODO
                return False

        # Run through every assertion
        asserts_success = True
        for assertType, source, value in asserts:
            if not self.check_assertion(assertType, source, value):
                asserts_success = False

        return asserts_success

    def check_assertion(self, assertType, str_source, str_value):
        if str_source.startswith('mem.'):
            # We're comparing with a place in memory
            # Might be prefixed by 0x to indicate hex. strtol() takes care of
            # this!
            loc = str_source.split('.')[1]
            loc = int(loc, 16 if 'x' in loc else 10)
            source = self.mpu.memory.get_byte(loc)

        elif str_source.startswith("reg."):
            # We're comparing with a register
            char_val = str_source[4]

            if char_val == 'p':
                if len(str_source) > 5 and str_source[5] == 's':
                    source = int(self.mpu.reg.ps)
                else:
                    source = self.mpu.reg.pc
            elif char_val == 's':
                    source = self.mpu.reg.sp
            elif char_val == 'a':
                    source = self.mpu.reg.ac
            elif char_val == 'x':
                    source = self.mpu.reg.x
            elif char_val == 'y':
                    source = self.mpu.reg.y
            else:
                print 'Invalid source for assertion: %s' % str_source
                sys.exit(1)

        elif str_source.startswith('flags.'):
            char_val = str_source[6]
            if char_val == 'b':
                source = self.mpu.reg.ps[FLAG_BREAK]
            elif char_val == 'z':
                source = self.mpu.reg.ps[FLAG_ZERO]
            elif char_val == 'n':
                source = self.mpu.reg.ps[FLAG_NEGATIVE]
            elif char_val == 'c':
                source = self.mpu.reg.ps[FLAG_CARRY]
            elif char_val == 'd':
                source = self.mpu.reg.ps[FLAG_DECIMAL]
            elif char_val == 'i':
                source = self.mpu.reg.ps[FLAG_INTERRUPT]
            elif char_val == 'v':
                source = self.mpu.reg.ps[FLAG_OVERFLOW]
            else:
                print 'Invalid source for assertion: %s' % str_source
                sys.exit(1)
        else:
            print 'Invalid source for assertion: %s' % str_source
            sys.exit(1)

        value = int(str_value, 16 if 'x' in str_value else 10)

        if source != value:
            print "Failed assertion: '%s %s %s' %s != %s" % (
                assertType,
                str_source,
                str_value,
                source,
                value
            )
            print self.mpu
            sys.exit(1)
            return False
        
        return True
