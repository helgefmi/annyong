test cpx imm n
    LDX #$50
    CPX #$60
    .byte 2
assert flags.c 0
assert flags.z 0
assert flags.n 1

test cpx imm z
    LDX #$50
    CPX #$50
    .byte 2
assert flags.c 1
assert flags.z 1
assert flags.n 0

test cpx imm c
    LDX #$60
    CPX #$50
    .byte 2
assert flags.c 1
assert flags.z 0
assert flags.n 0

test cpx zero
    LDA #$F
    STA $50
    LDX #$F
    CPX $50
    .byte 2
assert flags.z 1

test cpx abs
    LDA #$7F
    STA $5000
    LDX #$7F
    CPX $5000
    .byte 2
assert flags.z 1
