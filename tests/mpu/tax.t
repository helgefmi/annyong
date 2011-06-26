test tax_1
    LDA #$AB
    TAX
    .byte $2
assert reg.x 0xAB
