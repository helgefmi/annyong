test clv_v_set_by_bit
    LDA #$FF
    STA $CD
    BIT $CD
    CLV
    .byte 2
assert flags.v 0
