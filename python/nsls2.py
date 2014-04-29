#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Derivation of magic numbers for NSLS2 EVG
"""

from fractions import Fraction as F

from mrfioc2 import EVG as evg

# Simply print what would be sent
from mrfioc2 import canull as ca
# Check with current settings
#from mrfioc2 import cacheck as ca
# Actually write
#from cothread import catools as ca

names = {'SYS':'ACC-TS', 'D':'EVG'}

GEN = evg.EVG(499.68e6, 4)

divSR = 1320/4 # divider TS to get storage ring rev. freq
divBR = 264/4 # divider TS to get booster ring rev. freq
# ~10 KHz orbit feedback clock.
#  period must be an integer multiple of SR period
div10k = GEN.findCommonDiv(10e3, others=[F(1,divSR)])
assert div10k==12540
# ~10 Hz is max Linac rep. rate
#  period must be an integer multiple of:
#    orbit feedback and PSC clock period
#    500 MHz LN LLRF I/Q quadrature clock (ADC/4)
#    3 GHz LN LLRF I/Q quadrature clock
#    500 MHz BR LLRF I/Q quadrature clock
div10 = GEN.findCommonDiv(10,
    others=[F(1,6), # LN 500 MHz LLRF
            F(3,14), # LN 3 GHz LLRF
            F(2,25), # BR LLRF
            F(1,div10k), # Orbit FB
    ]
)
assert div10==12728100
div1 = div10*10
div1000 = div10/100 # 1/1000 of a cycle

print "# SR divider"
ca.caput(GEN.mxcPV(N=0, **names), divSR)
print "# BR divider"
ca.caput(GEN.mxcPV(N=1, **names), divBR)
print "# 10 KHz divider"
ca.caput(GEN.mxcPV(N=2, **names), div10k)
#print "# 10 Hz divider"
#ca.caput(GEN.mxcPV(N=3, **names), div10)

print "# 1 Hz divider"
ca.caput(GEN.mxcPV(N=6, **names), div1)

assert GEN.ticks(10e-3)==1249200
lndly = 1249200 # Linac pre-trigger delay is ~10ms

# Booster cycle start
BRstartbeam = GEN.event(65)
BRstart = GEN.event(25, ref=BRstartbeam, delay=4)

# Linac cycle start
LNprebeam = GEN.event(55, ref=BRstartbeam, delay=1)
LNpre = GEN.event(15, ref=LNprebeam, delay=4)

LNbeam = GEN.event(56, ref=55, delay=lndly)
GEN.event(16, ref=15, delay=lndly)

BRinj1 = GEN.event(21, ref=BRstart, delay=3030*divSR)
BRinjst = GEN.event(22, ref=BRinj1, delay=1*div10)

BRSLM = GEN.event(20, ref=LNbeam, delay=-GEN.ticks(1e-3))
for i in range(9):
    BRSLM = GEN.event(20, ref=BRSLM, delay=GEN.ticks(40e-3))
del BRSLM

# extraction time for 1Hz and 2Hz modes
BRextbeam = GEN.event(66, ref=BRstartbeam, delay=113600*divSR)
BRext = GEN.event(26, ref=BRstart, delay=113600*divSR)

# for Stacking
BRextbeamst = GEN.event(66, ref=BRstartbeam, delay=151418*divSR)
BRextst = GEN.event(26, ref=BRstart, delay=151418*divSR)

# kicker charging for 1Hz
BRIScharge1 = GEN.event(23, ref=BRinj1, delay=6*div10)
BRXScharge1 = GEN.event(28, ref=BRext, delay=6*div10)

# kicker charging for 2Hz
BRIScharge2 = GEN.event(23, ref=BRinj1, delay=1*div10)
BRXScharge2 = GEN.event(28, ref=BRext, delay=1*div10)

# kicker charging for Stacking
BRISchargest = BRIScharge1
BRXSchargest = GEN.event(28, ref=LNpre, delay=1)

# Sequences

# Arbitrary delay from sequencer trigger to avoid perturbing
# the phase of any single events generated by the same trigger (eg SR CW 1Hz, 10Hz, and 10kHz)
BRdelay = 10

SeqLNbeam = GEN.seq(0, div10, name='LN-TS{Seq:B}', events=[(BRstartbeam,BRdelay)], include=[55,56])
SeqLN = GEN.seq(0, div10, name='LN-TS{Seq:N}', events=[(BRstartbeam,BRdelay)], include=[15,16])

SeqBR1beam = GEN.seq(0, div1, name='BR-TS{Seq:B1Hz}', events=[(BRstartbeam,BRdelay)],
                     include=[65,BRextbeam,20]
                     )
SeqBR1 = GEN.seq(0, div1, name='BR-TS{Seq:N1Hz}', events=[(BRstartbeam,BRdelay)],
                 include=[25,BRext,21,BRIScharge1,BRXScharge1]
                 )

SeqBR2beam = GEN.seq(0, div1, name='BR-TS{Seq:B2Hz}', events=[(BRstartbeam,BRdelay)],
                     include=[65,BRextbeam,20]
                     )
SeqBR2 = GEN.seq(0, div1, name='BR-TS{Seq:N2Hz}', events=[(BRstartbeam,BRdelay)],
                 include=[25,BRext,21,BRIScharge2,BRXScharge2]
                 )

SeqBRstbeam = GEN.seq(0, div1, name='BR-TS{Seq:BStk}', events=[(BRstartbeam,BRdelay)],
                     include=[65,BRextbeamst,20]
                     )
SeqBRst = GEN.seq(0, div1, name='BR-TS{Seq:NStk}', events=[(BRstartbeam,BRdelay)],
                 include=[25,BRextst,21,BRinjst,BRISchargest,BRXSchargest]
                 )

for S in GEN.seqs:
    expanded = S.expand()
    print '#Sequence',S.name
    #for E,T in expanded:
    #    print "# ",E,GEN.sec(T),T
    ca.caput(GEN.seqCodesPV(P=S.name), [E[0].num for E in expanded])
    ca.caput(GEN.seqTimesPV(P=S.name), [E[1] for E in expanded])


# Static sequences
print '# Fine delay sequences'
ca.caput(GEN.seqCodesPV(P='ACC-TS{Seq:F0}'), 10)
ca.caput(GEN.seqCodesPV(P='ACC-TS{Seq:F2}'), 11)
ca.caput(GEN.seqCodesPV(P='ACC-TS{Seq:F4}'), 12)
ca.caput(GEN.seqCodesPV(P='ACC-TS{Seq:F6}'), 13)

ca.caput(GEN.seqTimesPV(P='ACC-TS{Seq:F0}'), 17)
ca.caput(GEN.seqTimesPV(P='ACC-TS{Seq:F2}'), 17)
ca.caput(GEN.seqTimesPV(P='ACC-TS{Seq:F4}'), 17)
ca.caput(GEN.seqTimesPV(P='ACC-TS{Seq:F6}'), 17)

print 'First turn sequence'
ca.caput(GEN.seqCodesPV(P='ACC-TS{Seq:FT}'), 47)
ca.caput(GEN.seqTimesPV(P='ACC-TS{Seq:FT}'), 8)


# For documentation

Seq1Hz = GEN.seq(0, div1, name='1Hz', events=[(BRstartbeam,BRdelay)],
include=[15,16,25,BRext,21,BRIScharge1,BRXScharge1,55,56,65,BRextbeam,20])

Seq2Hz = GEN.seq(0, div1, name='1Hz', events=[(BRstartbeam,BRdelay)],
include=[15,16,25,BRext,21,BRIScharge2,BRXScharge2,55,56,65,BRextbeam,20])

SeqStk = GEN.seq(0, div1, name='1Hz', events=[(BRstartbeam,BRdelay)],
include=[15,16,25,BRextst,21,BRinjst,BRISchargest,BRXSchargest,55,56,65,BRextbeamst,20])

for S in [Seq1Hz,Seq2Hz,SeqStk]:
    print '#Sequence',S.name
    expanded = S.expand()
    for E,T in expanded:
        print "# ",E,GEN.sec(T),T