test tya_1
    LDY #$AB
    TYA
    .byte $2
assert reg.a 0xAB
