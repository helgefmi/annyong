import struct
from annyong.util import signed_byte

def disassemble(fn, opcode, addrmode, operands, simple_trace):
    # To have better code, these opcodes were writting as one method in the mpu,
    # so we can't infer their mnemonics by looking at the method name.
    branch_opcodes = {
        0x90: 'BCC', 0xB0: 'BCS', 0xD0: 'BNE', 0xF0: 'BEQ',
        0x10: 'BPL', 0x30: 'BMI', 0x50: 'BVC', 0x70: 'BVS',
    }

    if opcode in branch_opcodes:
        asm = branch_opcodes[opcode]
    else:
        # This will also make NOP2 into NOP.
        asm = fn.__name__[3:6].upper()

    if simple_trace:
        return asm

    addrmode_fmts = {
        'impl': '',
        'imm': '#$%02X',
        'acc': 'A',
        'zp': '$%02X',
        'zp x': '$%02X,X',
        'zp y': '$%02X,Y',
        'zp ind x': '($%02X,X)',
        'zp ind y': '($%02X),Y',
        'abs': '$%04X',
        'abs x': '$%04X,X',
        'abs y': '$%04X,Y',
        'abs ind': '($%04X)',
    }

    asm_extra = ''
    if operands:
        bytes = ''.join(chr(o) for o in operands)
        operands = struct.unpack('H' if len(bytes) > 1 else 'B', bytes)[0]

    asm_extra = ' %s' % (addrmode_fmts[addrmode.mnemonic] % operands)
    asm += asm_extra
    return asm.strip().ljust(11)

def trace_step(mpu, opcode):
    fn, addrmode, _ = mpu._opcodes[opcode]

    num_operands = addrmode.num_operands
    operands = [mpu.memory.get_byte(mpu.reg.pc + i)
                    for i in xrange(1, num_operands + 1)]

    simple_trace = getattr(mpu.trace_output, 'simple_trace', False)
    asm = disassemble(fn, opcode, addrmode, operands, simple_trace)

    cyc = (mpu.cycles * 3) % 341
    sl = (mpu.cycles * 3) / 341

    sl += 241
    while sl >= 261:
        sl -= 262

    mpu.trace_output.write(
        ('%04X  %02X %s %s%s  A:%02X '
         'X:%02X Y:%02X P:%02X SP:%02X CYC:%3d SL:%d\n') % (
            mpu.reg.pc,
            opcode,
            ' '.join('%02X' % o for o in operands).ljust(5),
            '*' if getattr(fn, 'invalid_opcode', False) else ' ',
            asm,
            mpu.reg.ac,
            mpu.reg.x,
            mpu.reg.y,
            int(mpu.reg.ps),
            mpu.reg.sp,
            cyc,
            sl,
        )
    )
    mpu.trace_output.flush()
