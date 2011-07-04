import struct

def disassemble(mpu, opcode, operands, nestest_trace):
    fn, addrmode, _ = mpu._opcodes[opcode]

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

    if nestest_trace:
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

    if operands:
        bytes = ''.join(chr(o) for o in operands)
        operands = struct.unpack('H' if len(bytes) > 1 else 'B', bytes)[0]

    asm += ' %s' % (addrmode_fmts[addrmode.mnemonic] % operands)
    return asm.strip().ljust(11)
