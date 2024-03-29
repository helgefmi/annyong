test asl acc n
    LDA #100
    ASL
    .byte 2
assert reg.ac 200
assert flags.z 0
assert flags.c 0
assert flags.n 1

test asl acc c
    LDA #$AB
    ASL
    .byte 2
assert reg.ac 0x56
assert flags.z 0
assert flags.c 1
assert flags.n 0

test asl acc z
    LDA #$80
    ASL
    .byte 2
assert reg.ac 0
assert flags.z 1
assert flags.c 1
assert flags.n 0


test asl zero n
    LDA #100
    STA $50
    ASL $50
    .byte 2
assert mem.0x50 200
assert flags.z 0
assert flags.c 0
assert flags.n 1

test asl zero c
    LDA #$AB
    STA $50
    ASL $50
    .byte 2
assert mem.0x50 0x56
assert flags.z 0
assert flags.c 1
assert flags.n 0

test asl zero z
    LDA #$80
    STA $50
    ASL $50
    .byte 2
assert mem.0x50 0
assert flags.z 1
assert flags.c 1
assert flags.n 0


test asl zero x
    LDX #$A
    LDA #$AB
    STA $5A
    ASL $50,X
    .byte 2
assert flags.n 0
assert flags.z 0
assert mem.0x5A 0x56

test asl abs
    LDA #$AB
    STA $5000
    ASL $5000
    .byte 2
assert flags.n 0
assert flags.z 0
assert mem.0x5000 0x56

test asl abs x
    LDX #$CC
    LDA #$AB
    STA $50CC
    ASL $5000,X
    .byte 2
assert flags.n 0
assert flags.z 0
assert mem.0x50CC 0x56
