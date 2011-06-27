from inspect import getargspec

from annyong.util.bitset import Bitset
from annyong.mpu.debug import trace_step
from annyong.memory import Memory
from annyong.util import signed_byte

# decorators {{{

def defopcode(*args):
    def outer(fn):
        fn.opcodes = args
        return fn
    return outer

def defopcode_implied(opcode_no, cycles):
    return defopcode((opcode_no, 'impl', cycles))

def opcode_invalid(fn):
    fn.invalid_opcode = True
    return fn

def opcode_use_extra_cycles(fn):
    fn.use_extra_cycles = True
    return fn

def defaddrmode(mnemonic, num_operands):
    def outer(fn):
        fn.mnemonic = mnemonic
        fn.num_operands = num_operands
        return fn
    return outer

# }}}

class Mpu6502(object):
    class InvalidOpcodeException(BaseException):
        def __init__(self, opcode):
            self._opcode = opcode

        def __str__(self):
            return 'Invalid OpCode: 0x%02x' % self._opcode

        def get_opcode(self):
            return self._opcode

    class Registers(object):
        def __init__(self):
            self.pc = None          # Program Counter, 16 bit
            self.sp = None          # Stack Pointer, 8 bit
            self.ac = None          # Accumulator, 8 bit
            self.x = None           # General register, 8 bit
            self.y = None           # General register, 8 bit
            self.ps = Bitset(       # Processor Status, 8 * 1 bit
                ('carry', 1),
                ('zero', 1),
                ('interrupt', 1),
                ('decimal', 1),
                ('break_', 1),
                ('sixth', 1),
                ('overflow', 1),
                ('negative', 1),
            )

    def __init__(self):
        self._addrmodes = {}
        self._opcodes = [None] * 256
        self.reg = Mpu6502.Registers()
        self.memory = Memory(0x10000)
        self.cycles = 0
        self.trace_output = None

        self._init_addrmodes()
        self._init_opcodes()
        self.reset()

    def __str__(self):
        return '<mpu6502 PC:%s PS:%s SP:%s AC:%s X:%s Y:%s>' % (
            self.reg.pc,
            self.reg.ps,
            self.reg.sp,
            self.reg.ac,
            self.reg.x,
            self.reg.y,
        )
    repr = __str__

    def _init_addrmodes(self):
        for key in dir(self):
            fn = getattr(self, key)
            if not hasattr(fn, 'mnemonic'):
                continue
            self._addrmodes[fn.mnemonic] = fn

    def _init_opcodes(self):
        for key in dir(self):
            fn = getattr(self, key)
            if not hasattr(fn, 'opcodes'):
                continue
            for opcode, mnemonic, cycles in fn.opcodes:
                self._opcodes[opcode] = (fn, self._addrmodes[mnemonic], cycles)

    def _set_nz_flags(self, value):
        self.reg.ps.zero = 0 == value
        self.reg.ps.negative = value >> 7

    def set_trace_output(self, output):
        self.trace_output = output

    def reset(self):
        self.reg.x = 0
        self.reg.y = 0
        self.reg.ac = 0
        self.reg.pc = 0
        self.reg.ps.set(0)
        self.reg.sp = 0xFF
        self.memory.reset()
        self.cycles = 0

    def run(self, org=None):
        if org is None:
            org = self.memory.get_word(0xFFFC)
        self.reg.pc = org

        while True:
            self.step()

    def step(self):
        opcode = self.memory.get_byte(self.reg.pc)
        if not self._opcodes[opcode]:
            raise Mpu6502.InvalidOpcodeException(opcode)

        if self.trace_output:
            trace_step(self, opcode)

        self.reg.pc = (self.reg.pc + 1) & 0xFFFF
        self.execute_opcode(opcode)

    def execute_opcode(self, opcode):
        fn, addrmode, cycles = self._opcodes[opcode]

        fn_args = getargspec(fn).args
        kwargs = {
            'offset': None,
            'value': None,
            'opcode': opcode,
        }

        if addrmode.mnemonic in ('impl', 'imm', 'acc'):
            kwargs['value'], extra_cycles = addrmode()
        else:
            kwargs['offset'], extra_cycles = addrmode()

        self.reg.pc += addrmode.num_operands

        if kwargs['offset'] is not None:
            kwargs['value'] = self.memory.get_byte(kwargs['offset'])

        for key in kwargs.keys():
            if key not in fn_args:
                del kwargs[key]

        ret = fn(**kwargs)
        self.cycles += cycles
        if ret is not None:
            self.cycles += ret
        if getattr(fn, 'use_extra_cycles', False):
            self.cycles += extra_cycles

        return ret

    # addressing modes {{{

    @defaddrmode('acc', 0)
    def get_accumulator(self):
        return self.reg.ac, 0

    @defaddrmode('impl', 0)
    def get_implied(self):
        return None, 0

    @defaddrmode('imm', 1)
    def get_immediate(self):
        return self.memory.get_byte(self.reg.pc), 0

    @defaddrmode('zp', 1)
    def get_zero_page(self):
        return self.memory.get_byte(self.reg.pc), 0

    @defaddrmode('zp x', 1)
    def get_zero_page_x(self):
        return (self.reg.x + self.memory.get_byte(self.reg.pc)) & 0xFF, 0

    @defaddrmode('zp y', 1)
    def get_zero_page_y(self):
        return (self.reg.y + self.memory.get_byte(self.reg.pc)) & 0xFF, 0

    @defaddrmode('abs', 2)
    def get_absolute(self):
        return self.memory.get_word(self.reg.pc), 0

    @defaddrmode('abs ind', 2)
    def get_absolute_indirect(self):
        op, _ = self.get_absolute()
        # Low and high byte must be taken from the same page; it wraps around in
        # these cases.
        low = self.memory.get_byte(op)
        high = self.memory.get_byte((op & 0xFF00) + ((op + 1) & 0xFF))
        return (high << 8) | low, 0

    @defaddrmode('abs x', 2)
    def get_absolute_x(self):
        arg = self.memory.get_word(self.reg.pc)
        arg_and_x = arg + self.reg.x

        extra_cycles = 0
        if arg_and_x & 0xFF00 != arg & 0xFF00:
            extra_cycles = 1

        return arg_and_x & 0xFFFF, extra_cycles

    @defaddrmode('abs y', 2)
    def get_absolute_y(self):
        arg = self.memory.get_word(self.reg.pc)
        arg_and_y = arg + self.reg.y

        extra_cycles = 0
        if arg_and_y & 0xFF00 != arg & 0xFF00:
            extra_cycles = 1

        return arg_and_y & 0xFFFF, extra_cycles

    @defaddrmode('zp ind x', 1)
    def get_indirect_x(self):
        pos, _ = self.get_zero_page_x()
        # If pos 0xFF, MSB is taken from 0x00
        low = self.memory.get_byte(pos)
        high = self.memory.get_byte((pos + 1) & 0xFF)
        return (high << 8) | low, 0

    @defaddrmode('zp ind y', 1)
    def get_indirect_y(self):
        operand = self.memory.get_byte(self.reg.pc)

        if operand == 0xFF:
            arg = (self.memory.get_word(0) << 8) + self.memory.get_byte(0xFF)
        else:
            arg = self.memory.get_word(operand)

        arg_and_y = arg + self.reg.y & 0xFFFF
        if arg_and_y == 0xFFFF:
            assert False

        extra_cycles = 0
        if arg_and_y & 0xFF00 != arg & 0xFF00:
            extra_cycles += 1

        return arg_and_y, extra_cycles

    # }}}
    # stack methods {{{

    def push_byte(self, value):
        self.memory.set_byte(0x100 + self.reg.sp, value)
        self.reg.sp -= 1

    def push_word(self, value):
        self.push_byte((value >> 8) & 0xFF)
        self.push_byte(value & 0xFF)

    def pop_byte(self):
        self.reg.sp += 1
        return self.memory.get_byte(0x100 + self.reg.sp)

    def pop_word(self):
        a = self.pop_byte()
        b = self.pop_byte()
        return a | (b << 8)

    # }}}

    # valid opcodes {{{

    @opcode_use_extra_cycles
    @defopcode((0xA9, 'imm', 2), (0xA5, 'zp', 3), (0xB5, 'zp x', 4),
               (0xAD, 'abs', 4), (0xBD, 'abs x', 4), (0xB9, 'abs y', 4),
               (0xA1, 'zp ind x', 6), (0xB1, 'zp ind y', 5))
    def op_lda(self, value):
        self.reg.ac = value
        self._set_nz_flags(self.reg.ac)

    @opcode_use_extra_cycles
    @defopcode((0xA2, 'imm', 2), (0xA6, 'zp', 3), (0xB6, 'zp y', 4),
               (0xAE, 'abs', 4), (0xBE, 'abs y', 4))
    def op_ldx(self, value):
        self.reg.x = value
        self._set_nz_flags(self.reg.x)

    @opcode_use_extra_cycles
    @defopcode((0xA0, 'imm', 2), (0xA4, 'zp', 3), (0xB4, 'zp x', 4),
               (0xAC, 'abs', 4), (0xBC, 'abs x', 4))
    def op_ldy(self, value):
        self.reg.y = value
        self._set_nz_flags(self.reg.y)

    @defopcode((0x85, 'zp', 3), (0x95, 'zp x', 4), (0x8D, 'abs', 4),
               (0x9D, 'abs x', 5), (0x99, 'abs y', 5), (0x81, 'zp ind x', 6),
               (0x91, 'zp ind y', 6))
    def op_sta(self, offset):
        self.memory.set_byte(offset, self.reg.ac)

    @defopcode((0x86, 'zp', 3), (0x96, 'zp y', 4), (0x8E, 'abs', 4))
    def op_stx(self, offset):
        self.memory.set_byte(offset, self.reg.x)

    @defopcode((0x84, 'zp', 3), (0x94, 'zp x', 4), (0x8C, 'abs', 4))
    def op_sty(self, offset):
        self.memory.set_byte(offset, self.reg.y)

    @opcode_use_extra_cycles
    @defopcode((0x29, 'imm', 2), (0x25, 'zp', 3), (0x35, 'zp x',4 ),
               (0x2D, 'abs', 4), (0x3D, 'abs x', 4), (0x39, 'abs y', 4),
               (0x21, 'zp ind x', 6), (0x31, 'zp ind y', 5))
    def op_and(self, value):
        self.reg.ac &= value
        self._set_nz_flags(self.reg.ac)

    @opcode_use_extra_cycles
    @defopcode((0x09, 'imm', 2), (0x05, 'zp', 3), (0x15, 'zp x', 4),
               (0x0D, 'abs', 4), (0x1D, 'abs x', 4), (0x19, 'abs y', 4),
               (0x01, 'zp ind x', 6), (0x11, 'zp ind y', 5))
    def op_ora(self, value):
        self.reg.ac |= value
        self._set_nz_flags(self.reg.ac)

    @opcode_use_extra_cycles
    @defopcode((0x49, 'imm', 2), (0x45, 'zp', 3), (0x55, 'zp x', 4),
               (0x4D, 'abs', 4), (0x5D, 'abs x', 4), (0x59, 'abs y', 4),
               (0x41, 'zp ind x', 6), (0x51, 'zp ind y', 5))
    def op_eor(self, value):
        self.reg.ac ^= value
        self._set_nz_flags(self.reg.ac)

    @defopcode((0x24, 'zp', 3), (0x2C, 'abs', 4))
    def op_bit(self, value):
        self.reg.ps.zero = 0 == value & self.reg.ac
        self.reg.ps.negative = value >> 7
        self.reg.ps.overflow = (value >> 6) & 1

    @opcode_use_extra_cycles
    @defopcode((0x69, 'imm', 2), (0x65, 'zp', 3), (0x75, 'zp x', 4),
               (0x6D, 'abs', 4), (0x7D, 'abs x', 4), (0x79, 'abs y', 4),
               (0x61, 'zp ind x', 6), (0x71, 'zp ind y', 5))
    def op_adc(self, value):
        carry = self.reg.ps.carry

        # TODO: Decimal mode removed temporarily.

        result = signed_byte(value) + signed_byte(self.reg.ac) + carry
        self.reg.ps.overflow = result > 127 or result < -128
        self.reg.ps.carry = value + self.reg.ac + carry > 255
        result &= 0xFF

        self.reg.ac = result
        self._set_nz_flags(self.reg.ac)

    @opcode_use_extra_cycles
    @defopcode((0xE9, 'imm', 2), (0xE5, 'zp', 3), (0xF5, 'zp x', 4),
               (0xED, 'abs', 4), (0xFD, 'abs x', 4), (0xF9, 'abs y', 4),
               (0xE1, 'zp ind x', 6), (0xF1, 'zp ind y', 5))
    def op_sbc(self, value):
        return self.op_adc(value ^ 0xFF)

    @defopcode((0x0A, 'acc', 2), (0x06, 'zp', 5), (0x16, 'zp x', 6),
               (0x0E, 'abs', 6), (0x1E, 'abs x', 7))
    def op_asl(self, offset, value):
        self.reg.ps.carry = value >> 7
        value = (value << 1) & 0xFF

        if offset is None: # 0x0A
            self.reg.ac = value
        else:
            self.memory.set_byte(offset, value)
        self._set_nz_flags(value)

    @defopcode((0x4A, 'acc', 2), (0x46, 'zp', 5), (0x56, 'zp x', 6),
               (0x4E, 'abs', 6), (0x5E, 'abs x', 7))
    def op_lsr(self, offset, value):
        self.reg.ps.carry = value & 1
        value >>= 1

        if offset is None: # 0x4A
            self.reg.ac = value
        else:
            self.memory.set_byte(offset, value)
        self._set_nz_flags(value)

    @defopcode((0x2A, 'acc', 2), (0x26, 'zp', 5), (0x36, 'zp x', 6),
               (0x2E, 'abs', 6), (0x3E, 'abs x', 7))
    def op_rol(self, offset, value):
        carry = self.reg.ps.carry
        self.reg.ps.carry = value >> 7

        value = ((value << 1) + carry) & 0xFF

        if offset is None: # 0x2A
            self.reg.ac = value
        else:
            self.memory.set_byte(offset, value)
        self._set_nz_flags(value)

    @defopcode((0x6A, 'acc', 2), (0x66, 'zp', 5), (0x76, 'zp x', 6),
               (0x6E, 'abs', 6), (0x7E, 'abs x', 7))
    def op_ror(self, offset, value):
        new_carry = value & 1

        value = (value >> 1) | (self.reg.ps.carry << 7)
        self.reg.ps.carry = new_carry

        if offset is None: # 0x6A
            self.reg.ac = value
        else:
            self.memory.set_byte(offset, value)
        self._set_nz_flags(value)
    
    @opcode_use_extra_cycles
    @defopcode((0xC9, 'imm', 2), (0xC5, 'zp', 3), (0xD5, 'zp x', 4),
               (0xCD, 'abs', 4), (0xDD, 'abs x', 4), (0xD9, 'abs y', 4),
               (0xC1, 'zp ind x', 6), (0xD1, 'zp ind y', 5))
    def op_cmp(self, value):
        self.reg.ps.carry = self.reg.ac >= value
        self._set_nz_flags((self.reg.ac - value) & 0xFF)

    @defopcode((0xE0, 'imm', 2), (0xE4, 'zp', 3), (0xEC, 'abs', 4))
    def op_cpx(self, value):
        self.reg.ps.carry = self.reg.x >= value
        self._set_nz_flags((self.reg.x - value) & 0xFF)

    @defopcode((0xC0, 'imm', 2), (0xC4, 'zp', 3), (0xCC, 'abs', 4))
    def op_cpy(self, value):
        self.reg.ps.carry = self.reg.y >= value
        self._set_nz_flags((self.reg.y - value) & 0xFF)

    @defopcode((0xE6, 'zp', 5), (0xF6, 'zp x', 6), (0xEE, 'abs', 6),
               (0xFE, 'abs x', 7))
    def op_inc(self, offset, value):
        value = (value + 1) & 0xFF
        self.memory.set_byte(offset, value)
        self._set_nz_flags(value)

    @defopcode((0xC6, 'zp', 5), (0xd6, 'zp x', 6), (0xCE, 'abs', 6),
               (0xDE, 'abs x', 7))
    def op_dec(self, offset, value):
        value = (value - 1) & 0xFF
        self.memory.set_byte(offset, value)
        self._set_nz_flags(value)

    @defopcode_implied(0xE8, 2)
    def op_inx(self):
        self.reg.x = (self.reg.x + 1) & 0xFF
        self._set_nz_flags(self.reg.x)

    @defopcode_implied(0xCA, 2)
    def op_dex(self):
        self.reg.x = (self.reg.x - 1) & 0xFF
        self._set_nz_flags(self.reg.x)

    @defopcode_implied(0xC8, 2)
    def op_iny(self):
        self.reg.y = (self.reg.y + 1) & 0xFF
        self._set_nz_flags(self.reg.y)

    @defopcode_implied(0x88, 2)
    def op_dey(self):
        self.reg.y = (self.reg.y - 1) & 0xFF
        self._set_nz_flags(self.reg.y)

    @defopcode_implied(0xAA, 2)
    def op_tax(self):
        self.reg.x = self.reg.ac
        self._set_nz_flags(self.reg.x)

    @defopcode_implied(0xA8, 2)
    def op_tay(self):
        self.reg.y = self.reg.ac
        self._set_nz_flags(self.reg.y)

    @defopcode_implied(0xBA, 2)
    def op_tsx(self):
        self.reg.x = self.reg.sp
        self._set_nz_flags(self.reg.x)

    @defopcode_implied(0x8A, 2)
    def op_txa(self):
        self.reg.ac = self.reg.x
        self._set_nz_flags(self.reg.ac)

    @defopcode_implied(0x9A, 2)
    def op_txs(self):
        self.reg.sp = self.reg.x

    @defopcode_implied(0x98, 2)
    def op_tya(self):
        self.reg.ac = self.reg.y
        self._set_nz_flags(self.reg.ac)

    @defopcode_implied(0x48, 3)
    def op_pha(self):
        self.push_byte(self.reg.ac)

    @defopcode_implied(0x08, 3)
    def op_php(self):
        self.push_byte(int(self.reg.ps) | (1 << 4))

    @defopcode_implied(0x68, 4)
    def op_pla(self):
        self.reg.ac = self.pop_byte()
        self._set_nz_flags(self.reg.ac)

    @defopcode_implied(0x28, 4)
    def op_plp(self):
        ps = self.pop_byte() & ~(1 << 4) | (1 << 5)
        self.reg.ps.set(ps)

    @defopcode_implied(0x18, 2)
    def op_clc(self):
        self.reg.ps.carry = 0

    @defopcode_implied(0xD8, 2)
    def op_cld(self):
        self.reg.ps.decimal = 0

    @defopcode_implied(0x58, 2)
    def op_cli(self):
        self.reg.ps.interrupt = 0

    @defopcode_implied(0xB8, 2)
    def op_clv(self):
        self.reg.ps.overflow = 0

    @defopcode_implied(0x38, 2)
    def op_sec(self):
        self.reg.ps.carry = 1

    @defopcode_implied(0xF8, 2)
    def op_sed(self):
        self.reg.ps.decimal = 1

    @defopcode_implied(0x78, 2)
    def op_sei(self):
        self.reg.ps.interrupt = 1

    @defopcode_implied(0xEA, 2)
    def op_nop(self):
        pass

    @defopcode_implied(0x00, 7)
    def op_brk(self):
        self.push_word((self.reg.pc + 1) & 0xFFFF)
        self.push_byte(int(self.reg.ps) | (1 << 4))
        self.reg.pc = self.memory.get_word(0xFFFE)

    @defopcode_implied(0x40, 6)
    def op_rti(self):
        self.reg.ps.set(self.pop_byte() | (1 << 5))
        self.reg.pc = self.pop_word()

    @defopcode((0x4C, 'abs', 3), (0x6C, 'abs ind', 5))
    def op_jmp(self, offset):
        self.reg.pc = offset

    @defopcode((0x20, 'abs', 6))
    def op_jsr(self, offset):
        self.push_word((self.reg.pc - 1) & 0xFFFF)
        self.reg.pc = offset

    @defopcode_implied(0x60, 6)
    def op_rts(self, value):
        self.reg.pc = (self.pop_word() + 1) & 0xFFFF

    @defopcode((0x90, 'imm', 2), (0xB0, 'imm', 2),
               (0xD0, 'imm', 2), (0xF0, 'imm', 2),
               (0x10, 'imm', 2), (0x30, 'imm', 2),
               (0x50, 'imm', 2), (0x70, 'imm', 2))
    def op_branch(self, value, opcode):
        flags = {
            0x90: 'carry',    0xB0: 'carry',
            0xD0: 'zero',     0xF0: 'zero',
            0x10: 'negative', 0x30: 'negative',
            0x50: 'overflow', 0x70: 'overflow',
        }
        cond = bool(getattr(self.reg.ps, flags[opcode]))
        branch_if_true = opcode in (0xB0, 0xF0, 0x30, 0x70)

        if cond == branch_if_true:
            old_pc = self.reg.pc
            new_pc = (self.reg.pc + signed_byte(value)) & 0xFFFF
            self.reg.pc = new_pc
            return 2 if (old_pc & 0xFF00) != (new_pc & 0xFF00) else 1

    # }}}
    # invalid opcodes {{{

    @opcode_use_extra_cycles
    @opcode_invalid
    @defopcode((0x04, 'zp', 3), (0x14, 'zp x', 4), (0x34, 'zp x', 4),
               (0x44, 'zp', 3), (0x54, 'zp x', 4), (0x64, 'zp', 3),
               (0x74, 'zp x', 4), (0x80, 'imm', 2), (0x82, 'imm', 2),
               (0x89, 'imm', 2), (0xC2, 'imm', 2),  (0xD4, 'zp x', 4),
               (0xE2, 'imm', 2), (0xF4, 'zp x', 4), (0x0C, 'abs', 4),
               (0x1C, 'abs x', 4), (0x3C, 'abs x', 4), (0x5C, 'abs x', 4),
               (0x7C, 'abs x', 4), (0xDC, 'abs x', 4), (0xFC, 'abs x', 4),
               (0x1A, 'impl', 2), (0x3A, 'impl', 2), (0x5A, 'impl', 2),
               (0x7A, 'impl', 2), (0xDA, 'impl', 2), (0xFA, 'impl', 2))
    def op_nop2(self):
        pass

    @opcode_use_extra_cycles
    @opcode_invalid
    @defopcode((0xA7, 'zp', 3), (0xB7, 'zp y', 4), (0xAF, 'abs', 4),
               (0xBF, 'abs y', 4), (0xA3, 'zp ind x', 6), (0xB3, 'zp ind y', 5))
    def op_lax(self, value):
        self.reg.x = value
        self.reg.ac = value
        self._set_nz_flags(self.reg.ac)

    @opcode_invalid
    @defopcode((0x87, 'zp', 3), (0x97, 'zp y', 4), (0x83, 'zp ind x', 6),
               (0x8F, 'abs', 4))
    def op_sax(self, offset):
        self.memory.set_byte(offset, self.reg.ac & self.reg.x)

    @opcode_invalid
    @defopcode((0xEB, 'imm', 2))
    def op_sbc2(self, value):
        return self.op_sbc(value)

    @opcode_invalid
    @defopcode((0xC7, 'zp', 5), (0xD7, 'zp x', 6), (0xCF, 'abs', 6),
               (0xDF, 'abs x', 7), (0xDB, 'abs y', 7), (0xC3, 'zp ind x', 8),
               (0xD3, 'zp ind y', 8))
    def op_dcp(self, offset, value):
        value = (value - 1) & 0xFF
        self.op_cmp(value)
        self.memory.set_byte(offset, value)

    @opcode_invalid
    @defopcode((0xE7, 'zp', 5), (0xF7, 'zp x', 6), (0xEF, 'abs', 6),
               (0xFF, 'abs x', 7), (0xFB, 'abs y', 7), (0xE3, 'zp ind x', 8),
               (0xF3, 'zp ind y', 8))
    def op_isb(self, offset, value):
        value = (value + 1) & 0xFF
        self.op_sbc(value)
        self.memory.set_byte(offset, value)

    @opcode_invalid
    @defopcode((0x07, 'zp', 5), (0x17, 'zp x', 6), (0x0F, 'abs', 6),
               (0x1F, 'abs x', 7), (0x1B, 'abs y', 7), (0x03, 'zp ind x', 8),
               (0x13, 'zp ind y', 8))
    def op_slo(self, offset, value):
        self.reg.ps.carry = value >> 7
        value = (value << 1) & 0xFF
        self.op_ora(value)
        self.memory.set_byte(offset, value)

    @opcode_invalid
    @defopcode((0x27, 'zp', 5), (0x37, 'zp x', 6), (0x2F, 'abs', 6),
               (0x3F, 'abs x', 7), (0x3B, 'abs y', 7), (0x23, 'zp ind x', 8),
               (0x33, 'zp ind y', 8))
    def op_rla(self, offset, value):
        carry = self.reg.ps.carry
        self.reg.ps.carry = value >> 7
        value = ((value << 1) & 0xFF) | carry
        self.op_and(value)
        self.memory.set_byte(offset, value)

    @opcode_invalid
    @defopcode((0x47, 'zp', 5), (0x57, 'zp x', 6), (0x4F, 'abs', 6),
               (0x5F, 'abs x', 7), (0x5B, 'abs y', 7), (0x43, 'zp ind x', 8),
               (0x53, 'zp ind y', 8))
    def op_sre(self, offset, value):
        carry = value & 1
        value >>= 1
        self.op_eor(value)
        self.reg.ps.carry = carry
        self.memory.set_byte(offset, value)

    @opcode_invalid
    @defopcode((0x67, 'zp', 5), (0x77, 'zp x', 6), (0x6F, 'abs', 6),
               (0x7F, 'abs x', 7), (0x7B, 'abs y', 7), (0x63, 'zp ind x', 8),
               (0x73, 'zp ind y', 8))
    def op_rra(self, offset, value):
        carry = self.reg.ps.carry
        self.reg.ps.carry = value & 1
        value = (value >> 1) | (carry << 7)
        self.op_adc(value)
        self.memory.set_byte(offset, value)

    # }}}
