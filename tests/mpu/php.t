test php null
    PHP
    .byte $2
assert mem.0x1FF 0x10

test php c flag
    SEC
    PHP
    .byte $2
assert mem.0x1FF 0x11

test php d flag
    SED
    PHP
    .byte $2
assert mem.0x1FF 0x18

test php i flag
    SEI
    PHP
    .byte $2
assert mem.0x1FF 0x14

test php cdi flag
    SEC
    SED
    SEI
    PHP
    .byte $2
assert mem.0x1FF 0x1D
