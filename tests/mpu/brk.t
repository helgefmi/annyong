test brk simple
    LDA #label1
    STA $FFFE

    BRK
    .byte 3
    .byte 3

label1:
    LDY #$AB
    .byte 2

label2:
    LDX #$AB
    .byte 2
assert reg.y 0xAB
assert reg.x 0
assert flags.b 0
assert flags.c 0


test brk simple2
    LDA #label2
    STA $FFFE

    BRK
    .byte 3
    .byte 3

label1:
    LDY #$AB
    .byte 2

label2:
    LDX #$AB
    .byte 2
assert reg.y 0
assert reg.x 0xAB
assert flags.b 0
assert flags.c 0
assert flags.v 0


test brk flags
    SEC
    LDA #label2
    STA $FFFE

    BRK
    .byte 3
    .byte 3

label1:
    LDY #$AB
    .byte 2

label2:
    LDX #$AB
    .byte 2
assert reg.y 0
assert reg.x 0xAB
assert flags.b 0
assert flags.c 1
assert flags.v 0


test brk absval
    LDA #2
    STA $ABCD

    LDA #$CD
    STA $FFFE
    LDA #$AB
    STA $FFFF

    BRK
assert reg.p 0xABCD
