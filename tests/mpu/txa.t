test txa_1
    LDX #$AB
    TXA
    .byte $2
assert reg.a 0xAB
