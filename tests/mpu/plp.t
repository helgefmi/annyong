test plp null
    PHP
    PLP
    .byte $2
assert reg.ps 0x20

test plp c flag
    SEC
    PHP
    CLC
    PLP
    .byte $2
assert reg.ps 0x21

test plp d flag
    SED
    PHP
    SEI
    PLP
    .byte $2
assert reg.ps 0x28

test plp i flag
    SEI
    PHP
    CLI
    PLP
    .byte $2
assert reg.ps 0x24

test plp cdi flag
    SEC
    SED
    SEI
    PHP
    CLC
    CLD
    CLI
    PLP
    .byte $2
assert reg.ps 0x2D
