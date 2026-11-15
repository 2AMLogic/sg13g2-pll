* sg13g2-pll :: sim/sg13cmos5l-divider-max-frequency (issue #402)
* `divider_chain` maximum-input-frequency deck: the committed (repaired)
* divider_chain alone, ideal pulse clock at one frequency, one corner,
* one programming word. Counts -- via ngspice `.meas ... when rise=k` --
* the FIRST `1.65` crossing time of every rising edge of the clock (CKIN)
* and of the feedback clock (FB) within `3.678400e-07`; the collector
* (../testbench/collect_maxfreq.py) buckets the CKIN edges per FB period and
* scores each period against the programmed ratio N. Wave units
* ( non-empty) additionally dump the internal stage nodes
* ck1..ck5 (plus CKIN/FB/DIVOUT) as text for the failing-stage isolation
* (AC 3); the collector gzips that dump into ../corners/.
*
* The deck is rendered per unit by ../testbench/gen_maxfreq_requests.py,
* which substitutes the corner (mos_ff), temperature (27), supply
* (3.3, with the 50 % crossing threshold 1.65 -- the supply corners
* make a hard-coded 1.65 V wrong), the clock period (6.793478e-10) and high time
* (2.596739e-10 = 6.793478e-10/2 - 80 p: 80 ps edges and ~50 % duty, the SAME drive shape
* tb_div_speed.sp.tmpl used for the 640 MHz / 1.28 GHz bracket this
* campaign anchors against), timestep, stop time, reltol, the programming
* word, the saved-node list, an optional waveform-dump control block and
* the emitted per-edge .meas lines.
*
* PDK provenance: the deck names the PINNED model files relative to itself
* (`models/`, `osdi/`). `klt sim`'s deck-list preservation contract stages
* those files from the submitting host -- the pinned
* `ihp-sg13cmos5l 607e18d4...` checkout's bytes (staged by the generator,
* which refuses to run without `--pinned-pdk`) -- so neither this deck nor
* the record may cite `$PDK_ROOT` (that resolves on the worker to the
* newer, unpinned fleet image). See ../records/RECORD-001.
*
* Both clock inputs of `divider_chain` are driven from the same source
* (`CKIN` = `CKIN_VCO` = `ck`): in the closed loop they are the same net,
* exactly as in tb_div_func.sp.tmpl. Driving them separately would invent
* a skew the design does not have.
*
* `divider_chain` has NO reset pin: its 13 `dff_tg_hv` state elements have
* no defined power-up state, so the DC operating point is indeterminate and
* ngspice's gmin/source stepping cannot resolve it. These `.ic` statements
* are the minimum symmetry break that makes an OP exist -- a TESTBENCH
* workaround for a DESIGN gap (Finding 1 of
* sim/sg13cmos5l-divider-nrange-retiming/records/RECORD-001), not a
* property of the block.
*
* The `.control` block deliberately contains NO `run`: with a `.control`
* present, the deck-level `.tran` runs exactly once and `run` would execute
* it a second time (measured: the anchor's first cut ran the whole transient
* twice). `pre_osdi` needs to precede only the model resolution, which the
* control block satisfies.

.lib models/cornerMOShv.lib mos_ff
.option scale=1 temp=27
.options reltol=0.001 vntol=1e-4 abstol=1e-9 trtol=7
.global sub!

.include divider_chain.spice

Vdd vdd 0 dc 3.3
Vsub sub! 0 dc 0
Vck ck 0 pulse(0 3.3 0 80p 80p 2.596739e-10 6.793478e-10)
Vp0 p0 0 dc 0
Vp1 p1 0 dc 0
Vp2 p2 0 dc 0
Vp3 p3 0 dc 0
Vp4 p4 0 dc 0
Vp5 p5 0 dc 0

Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain

.ic v(xdiv.xd0.xdffq.m)=0 v(xdiv.xd0.xdffq.s)=0 v(xdiv.xd0.xdffm.m)=0 v(xdiv.xd0.xdffm.s)=0
.ic v(xdiv.xd1.xdffq.m)=0 v(xdiv.xd1.xdffq.s)=0 v(xdiv.xd1.xdffm.m)=0 v(xdiv.xd1.xdffm.s)=0
.ic v(xdiv.xd2.xdffq.m)=0 v(xdiv.xd2.xdffq.s)=0 v(xdiv.xd2.xdffm.m)=0 v(xdiv.xd2.xdffm.s)=0
.ic v(xdiv.xd3.xdffq.m)=0 v(xdiv.xd3.xdffq.s)=0 v(xdiv.xd3.xdffm.m)=0 v(xdiv.xd3.xdffm.s)=0
.ic v(xdiv.xd4.xdffq.m)=0 v(xdiv.xd4.xdffq.s)=0 v(xdiv.xd4.xdffm.m)=0 v(xdiv.xd4.xdffm.s)=0
.ic v(xdiv.xd5.xdffq.m)=0 v(xdiv.xd5.xdffq.s)=0 v(xdiv.xd5.xdffm.m)=0 v(xdiv.xd5.xdffm.s)=0
.ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0

.save v(ck) v(fb)
.tran 2.000000e-11 3.678400e-07 0 2.000000e-11

.control
pre_osdi osdi/psp103.osdi
pre_osdi osdi/psp103_nqs.osdi
pre_osdi osdi/mosvar.osdi
set num_threads=2

.endc
.meas tran tck_1 when v(ck)=1.65 rise=1
.meas tran tck_2 when v(ck)=1.65 rise=2
.meas tran tck_3 when v(ck)=1.65 rise=3
.meas tran tck_4 when v(ck)=1.65 rise=4
.meas tran tck_5 when v(ck)=1.65 rise=5
.meas tran tck_6 when v(ck)=1.65 rise=6
.meas tran tck_7 when v(ck)=1.65 rise=7
.meas tran tck_8 when v(ck)=1.65 rise=8
.meas tran tck_9 when v(ck)=1.65 rise=9
.meas tran tck_10 when v(ck)=1.65 rise=10
.meas tran tck_11 when v(ck)=1.65 rise=11
.meas tran tck_12 when v(ck)=1.65 rise=12
.meas tran tck_13 when v(ck)=1.65 rise=13
.meas tran tck_14 when v(ck)=1.65 rise=14
.meas tran tck_15 when v(ck)=1.65 rise=15
.meas tran tck_16 when v(ck)=1.65 rise=16
.meas tran tck_17 when v(ck)=1.65 rise=17
.meas tran tck_18 when v(ck)=1.65 rise=18
.meas tran tck_19 when v(ck)=1.65 rise=19
.meas tran tck_20 when v(ck)=1.65 rise=20
.meas tran tck_21 when v(ck)=1.65 rise=21
.meas tran tck_22 when v(ck)=1.65 rise=22
.meas tran tck_23 when v(ck)=1.65 rise=23
.meas tran tck_24 when v(ck)=1.65 rise=24
.meas tran tck_25 when v(ck)=1.65 rise=25
.meas tran tck_26 when v(ck)=1.65 rise=26
.meas tran tck_27 when v(ck)=1.65 rise=27
.meas tran tck_28 when v(ck)=1.65 rise=28
.meas tran tck_29 when v(ck)=1.65 rise=29
.meas tran tck_30 when v(ck)=1.65 rise=30
.meas tran tck_31 when v(ck)=1.65 rise=31
.meas tran tck_32 when v(ck)=1.65 rise=32
.meas tran tck_33 when v(ck)=1.65 rise=33
.meas tran tck_34 when v(ck)=1.65 rise=34
.meas tran tck_35 when v(ck)=1.65 rise=35
.meas tran tck_36 when v(ck)=1.65 rise=36
.meas tran tck_37 when v(ck)=1.65 rise=37
.meas tran tck_38 when v(ck)=1.65 rise=38
.meas tran tck_39 when v(ck)=1.65 rise=39
.meas tran tck_40 when v(ck)=1.65 rise=40
.meas tran tck_41 when v(ck)=1.65 rise=41
.meas tran tck_42 when v(ck)=1.65 rise=42
.meas tran tck_43 when v(ck)=1.65 rise=43
.meas tran tck_44 when v(ck)=1.65 rise=44
.meas tran tck_45 when v(ck)=1.65 rise=45
.meas tran tck_46 when v(ck)=1.65 rise=46
.meas tran tck_47 when v(ck)=1.65 rise=47
.meas tran tck_48 when v(ck)=1.65 rise=48
.meas tran tck_49 when v(ck)=1.65 rise=49
.meas tran tck_50 when v(ck)=1.65 rise=50
.meas tran tck_51 when v(ck)=1.65 rise=51
.meas tran tck_52 when v(ck)=1.65 rise=52
.meas tran tck_53 when v(ck)=1.65 rise=53
.meas tran tck_54 when v(ck)=1.65 rise=54
.meas tran tck_55 when v(ck)=1.65 rise=55
.meas tran tck_56 when v(ck)=1.65 rise=56
.meas tran tck_57 when v(ck)=1.65 rise=57
.meas tran tck_58 when v(ck)=1.65 rise=58
.meas tran tck_59 when v(ck)=1.65 rise=59
.meas tran tck_60 when v(ck)=1.65 rise=60
.meas tran tck_61 when v(ck)=1.65 rise=61
.meas tran tck_62 when v(ck)=1.65 rise=62
.meas tran tck_63 when v(ck)=1.65 rise=63
.meas tran tck_64 when v(ck)=1.65 rise=64
.meas tran tck_65 when v(ck)=1.65 rise=65
.meas tran tck_66 when v(ck)=1.65 rise=66
.meas tran tck_67 when v(ck)=1.65 rise=67
.meas tran tck_68 when v(ck)=1.65 rise=68
.meas tran tck_69 when v(ck)=1.65 rise=69
.meas tran tck_70 when v(ck)=1.65 rise=70
.meas tran tck_71 when v(ck)=1.65 rise=71
.meas tran tck_72 when v(ck)=1.65 rise=72
.meas tran tck_73 when v(ck)=1.65 rise=73
.meas tran tck_74 when v(ck)=1.65 rise=74
.meas tran tck_75 when v(ck)=1.65 rise=75
.meas tran tck_76 when v(ck)=1.65 rise=76
.meas tran tck_77 when v(ck)=1.65 rise=77
.meas tran tck_78 when v(ck)=1.65 rise=78
.meas tran tck_79 when v(ck)=1.65 rise=79
.meas tran tck_80 when v(ck)=1.65 rise=80
.meas tran tck_81 when v(ck)=1.65 rise=81
.meas tran tck_82 when v(ck)=1.65 rise=82
.meas tran tck_83 when v(ck)=1.65 rise=83
.meas tran tck_84 when v(ck)=1.65 rise=84
.meas tran tck_85 when v(ck)=1.65 rise=85
.meas tran tck_86 when v(ck)=1.65 rise=86
.meas tran tck_87 when v(ck)=1.65 rise=87
.meas tran tck_88 when v(ck)=1.65 rise=88
.meas tran tck_89 when v(ck)=1.65 rise=89
.meas tran tck_90 when v(ck)=1.65 rise=90
.meas tran tck_91 when v(ck)=1.65 rise=91
.meas tran tck_92 when v(ck)=1.65 rise=92
.meas tran tck_93 when v(ck)=1.65 rise=93
.meas tran tck_94 when v(ck)=1.65 rise=94
.meas tran tck_95 when v(ck)=1.65 rise=95
.meas tran tck_96 when v(ck)=1.65 rise=96
.meas tran tck_97 when v(ck)=1.65 rise=97
.meas tran tck_98 when v(ck)=1.65 rise=98
.meas tran tck_99 when v(ck)=1.65 rise=99
.meas tran tck_100 when v(ck)=1.65 rise=100
.meas tran tck_101 when v(ck)=1.65 rise=101
.meas tran tck_102 when v(ck)=1.65 rise=102
.meas tran tck_103 when v(ck)=1.65 rise=103
.meas tran tck_104 when v(ck)=1.65 rise=104
.meas tran tck_105 when v(ck)=1.65 rise=105
.meas tran tck_106 when v(ck)=1.65 rise=106
.meas tran tck_107 when v(ck)=1.65 rise=107
.meas tran tck_108 when v(ck)=1.65 rise=108
.meas tran tck_109 when v(ck)=1.65 rise=109
.meas tran tck_110 when v(ck)=1.65 rise=110
.meas tran tck_111 when v(ck)=1.65 rise=111
.meas tran tck_112 when v(ck)=1.65 rise=112
.meas tran tck_113 when v(ck)=1.65 rise=113
.meas tran tck_114 when v(ck)=1.65 rise=114
.meas tran tck_115 when v(ck)=1.65 rise=115
.meas tran tck_116 when v(ck)=1.65 rise=116
.meas tran tck_117 when v(ck)=1.65 rise=117
.meas tran tck_118 when v(ck)=1.65 rise=118
.meas tran tck_119 when v(ck)=1.65 rise=119
.meas tran tck_120 when v(ck)=1.65 rise=120
.meas tran tck_121 when v(ck)=1.65 rise=121
.meas tran tck_122 when v(ck)=1.65 rise=122
.meas tran tck_123 when v(ck)=1.65 rise=123
.meas tran tck_124 when v(ck)=1.65 rise=124
.meas tran tck_125 when v(ck)=1.65 rise=125
.meas tran tck_126 when v(ck)=1.65 rise=126
.meas tran tck_127 when v(ck)=1.65 rise=127
.meas tran tck_128 when v(ck)=1.65 rise=128
.meas tran tck_129 when v(ck)=1.65 rise=129
.meas tran tck_130 when v(ck)=1.65 rise=130
.meas tran tck_131 when v(ck)=1.65 rise=131
.meas tran tck_132 when v(ck)=1.65 rise=132
.meas tran tck_133 when v(ck)=1.65 rise=133
.meas tran tck_134 when v(ck)=1.65 rise=134
.meas tran tck_135 when v(ck)=1.65 rise=135
.meas tran tck_136 when v(ck)=1.65 rise=136
.meas tran tck_137 when v(ck)=1.65 rise=137
.meas tran tck_138 when v(ck)=1.65 rise=138
.meas tran tck_139 when v(ck)=1.65 rise=139
.meas tran tck_140 when v(ck)=1.65 rise=140
.meas tran tck_141 when v(ck)=1.65 rise=141
.meas tran tck_142 when v(ck)=1.65 rise=142
.meas tran tck_143 when v(ck)=1.65 rise=143
.meas tran tck_144 when v(ck)=1.65 rise=144
.meas tran tck_145 when v(ck)=1.65 rise=145
.meas tran tck_146 when v(ck)=1.65 rise=146
.meas tran tck_147 when v(ck)=1.65 rise=147
.meas tran tck_148 when v(ck)=1.65 rise=148
.meas tran tck_149 when v(ck)=1.65 rise=149
.meas tran tck_150 when v(ck)=1.65 rise=150
.meas tran tck_151 when v(ck)=1.65 rise=151
.meas tran tck_152 when v(ck)=1.65 rise=152
.meas tran tck_153 when v(ck)=1.65 rise=153
.meas tran tck_154 when v(ck)=1.65 rise=154
.meas tran tck_155 when v(ck)=1.65 rise=155
.meas tran tck_156 when v(ck)=1.65 rise=156
.meas tran tck_157 when v(ck)=1.65 rise=157
.meas tran tck_158 when v(ck)=1.65 rise=158
.meas tran tck_159 when v(ck)=1.65 rise=159
.meas tran tck_160 when v(ck)=1.65 rise=160
.meas tran tck_161 when v(ck)=1.65 rise=161
.meas tran tck_162 when v(ck)=1.65 rise=162
.meas tran tck_163 when v(ck)=1.65 rise=163
.meas tran tck_164 when v(ck)=1.65 rise=164
.meas tran tck_165 when v(ck)=1.65 rise=165
.meas tran tck_166 when v(ck)=1.65 rise=166
.meas tran tck_167 when v(ck)=1.65 rise=167
.meas tran tck_168 when v(ck)=1.65 rise=168
.meas tran tck_169 when v(ck)=1.65 rise=169
.meas tran tck_170 when v(ck)=1.65 rise=170
.meas tran tck_171 when v(ck)=1.65 rise=171
.meas tran tck_172 when v(ck)=1.65 rise=172
.meas tran tck_173 when v(ck)=1.65 rise=173
.meas tran tck_174 when v(ck)=1.65 rise=174
.meas tran tck_175 when v(ck)=1.65 rise=175
.meas tran tck_176 when v(ck)=1.65 rise=176
.meas tran tck_177 when v(ck)=1.65 rise=177
.meas tran tck_178 when v(ck)=1.65 rise=178
.meas tran tck_179 when v(ck)=1.65 rise=179
.meas tran tck_180 when v(ck)=1.65 rise=180
.meas tran tck_181 when v(ck)=1.65 rise=181
.meas tran tck_182 when v(ck)=1.65 rise=182
.meas tran tck_183 when v(ck)=1.65 rise=183
.meas tran tck_184 when v(ck)=1.65 rise=184
.meas tran tck_185 when v(ck)=1.65 rise=185
.meas tran tck_186 when v(ck)=1.65 rise=186
.meas tran tck_187 when v(ck)=1.65 rise=187
.meas tran tck_188 when v(ck)=1.65 rise=188
.meas tran tck_189 when v(ck)=1.65 rise=189
.meas tran tck_190 when v(ck)=1.65 rise=190
.meas tran tck_191 when v(ck)=1.65 rise=191
.meas tran tck_192 when v(ck)=1.65 rise=192
.meas tran tck_193 when v(ck)=1.65 rise=193
.meas tran tck_194 when v(ck)=1.65 rise=194
.meas tran tck_195 when v(ck)=1.65 rise=195
.meas tran tck_196 when v(ck)=1.65 rise=196
.meas tran tck_197 when v(ck)=1.65 rise=197
.meas tran tck_198 when v(ck)=1.65 rise=198
.meas tran tck_199 when v(ck)=1.65 rise=199
.meas tran tck_200 when v(ck)=1.65 rise=200
.meas tran tck_201 when v(ck)=1.65 rise=201
.meas tran tck_202 when v(ck)=1.65 rise=202
.meas tran tck_203 when v(ck)=1.65 rise=203
.meas tran tck_204 when v(ck)=1.65 rise=204
.meas tran tck_205 when v(ck)=1.65 rise=205
.meas tran tck_206 when v(ck)=1.65 rise=206
.meas tran tck_207 when v(ck)=1.65 rise=207
.meas tran tck_208 when v(ck)=1.65 rise=208
.meas tran tck_209 when v(ck)=1.65 rise=209
.meas tran tck_210 when v(ck)=1.65 rise=210
.meas tran tck_211 when v(ck)=1.65 rise=211
.meas tran tck_212 when v(ck)=1.65 rise=212
.meas tran tck_213 when v(ck)=1.65 rise=213
.meas tran tck_214 when v(ck)=1.65 rise=214
.meas tran tck_215 when v(ck)=1.65 rise=215
.meas tran tck_216 when v(ck)=1.65 rise=216
.meas tran tck_217 when v(ck)=1.65 rise=217
.meas tran tck_218 when v(ck)=1.65 rise=218
.meas tran tck_219 when v(ck)=1.65 rise=219
.meas tran tck_220 when v(ck)=1.65 rise=220
.meas tran tck_221 when v(ck)=1.65 rise=221
.meas tran tck_222 when v(ck)=1.65 rise=222
.meas tran tck_223 when v(ck)=1.65 rise=223
.meas tran tck_224 when v(ck)=1.65 rise=224
.meas tran tck_225 when v(ck)=1.65 rise=225
.meas tran tck_226 when v(ck)=1.65 rise=226
.meas tran tck_227 when v(ck)=1.65 rise=227
.meas tran tck_228 when v(ck)=1.65 rise=228
.meas tran tck_229 when v(ck)=1.65 rise=229
.meas tran tck_230 when v(ck)=1.65 rise=230
.meas tran tck_231 when v(ck)=1.65 rise=231
.meas tran tck_232 when v(ck)=1.65 rise=232
.meas tran tck_233 when v(ck)=1.65 rise=233
.meas tran tck_234 when v(ck)=1.65 rise=234
.meas tran tck_235 when v(ck)=1.65 rise=235
.meas tran tck_236 when v(ck)=1.65 rise=236
.meas tran tck_237 when v(ck)=1.65 rise=237
.meas tran tck_238 when v(ck)=1.65 rise=238
.meas tran tck_239 when v(ck)=1.65 rise=239
.meas tran tck_240 when v(ck)=1.65 rise=240
.meas tran tck_241 when v(ck)=1.65 rise=241
.meas tran tck_242 when v(ck)=1.65 rise=242
.meas tran tck_243 when v(ck)=1.65 rise=243
.meas tran tck_244 when v(ck)=1.65 rise=244
.meas tran tck_245 when v(ck)=1.65 rise=245
.meas tran tck_246 when v(ck)=1.65 rise=246
.meas tran tck_247 when v(ck)=1.65 rise=247
.meas tran tck_248 when v(ck)=1.65 rise=248
.meas tran tck_249 when v(ck)=1.65 rise=249
.meas tran tck_250 when v(ck)=1.65 rise=250
.meas tran tck_251 when v(ck)=1.65 rise=251
.meas tran tck_252 when v(ck)=1.65 rise=252
.meas tran tck_253 when v(ck)=1.65 rise=253
.meas tran tck_254 when v(ck)=1.65 rise=254
.meas tran tck_255 when v(ck)=1.65 rise=255
.meas tran tck_256 when v(ck)=1.65 rise=256
.meas tran tck_257 when v(ck)=1.65 rise=257
.meas tran tck_258 when v(ck)=1.65 rise=258
.meas tran tck_259 when v(ck)=1.65 rise=259
.meas tran tck_260 when v(ck)=1.65 rise=260
.meas tran tck_261 when v(ck)=1.65 rise=261
.meas tran tck_262 when v(ck)=1.65 rise=262
.meas tran tck_263 when v(ck)=1.65 rise=263
.meas tran tck_264 when v(ck)=1.65 rise=264
.meas tran tck_265 when v(ck)=1.65 rise=265
.meas tran tck_266 when v(ck)=1.65 rise=266
.meas tran tck_267 when v(ck)=1.65 rise=267
.meas tran tck_268 when v(ck)=1.65 rise=268
.meas tran tck_269 when v(ck)=1.65 rise=269
.meas tran tck_270 when v(ck)=1.65 rise=270
.meas tran tck_271 when v(ck)=1.65 rise=271
.meas tran tck_272 when v(ck)=1.65 rise=272
.meas tran tck_273 when v(ck)=1.65 rise=273
.meas tran tck_274 when v(ck)=1.65 rise=274
.meas tran tck_275 when v(ck)=1.65 rise=275
.meas tran tck_276 when v(ck)=1.65 rise=276
.meas tran tck_277 when v(ck)=1.65 rise=277
.meas tran tck_278 when v(ck)=1.65 rise=278
.meas tran tck_279 when v(ck)=1.65 rise=279
.meas tran tck_280 when v(ck)=1.65 rise=280
.meas tran tck_281 when v(ck)=1.65 rise=281
.meas tran tck_282 when v(ck)=1.65 rise=282
.meas tran tck_283 when v(ck)=1.65 rise=283
.meas tran tck_284 when v(ck)=1.65 rise=284
.meas tran tck_285 when v(ck)=1.65 rise=285
.meas tran tck_286 when v(ck)=1.65 rise=286
.meas tran tck_287 when v(ck)=1.65 rise=287
.meas tran tck_288 when v(ck)=1.65 rise=288
.meas tran tck_289 when v(ck)=1.65 rise=289
.meas tran tck_290 when v(ck)=1.65 rise=290
.meas tran tck_291 when v(ck)=1.65 rise=291
.meas tran tck_292 when v(ck)=1.65 rise=292
.meas tran tck_293 when v(ck)=1.65 rise=293
.meas tran tck_294 when v(ck)=1.65 rise=294
.meas tran tck_295 when v(ck)=1.65 rise=295
.meas tran tck_296 when v(ck)=1.65 rise=296
.meas tran tck_297 when v(ck)=1.65 rise=297
.meas tran tck_298 when v(ck)=1.65 rise=298
.meas tran tck_299 when v(ck)=1.65 rise=299
.meas tran tck_300 when v(ck)=1.65 rise=300
.meas tran tck_301 when v(ck)=1.65 rise=301
.meas tran tck_302 when v(ck)=1.65 rise=302
.meas tran tck_303 when v(ck)=1.65 rise=303
.meas tran tck_304 when v(ck)=1.65 rise=304
.meas tran tck_305 when v(ck)=1.65 rise=305
.meas tran tck_306 when v(ck)=1.65 rise=306
.meas tran tck_307 when v(ck)=1.65 rise=307
.meas tran tck_308 when v(ck)=1.65 rise=308
.meas tran tck_309 when v(ck)=1.65 rise=309
.meas tran tck_310 when v(ck)=1.65 rise=310
.meas tran tck_311 when v(ck)=1.65 rise=311
.meas tran tck_312 when v(ck)=1.65 rise=312
.meas tran tck_313 when v(ck)=1.65 rise=313
.meas tran tck_314 when v(ck)=1.65 rise=314
.meas tran tck_315 when v(ck)=1.65 rise=315
.meas tran tck_316 when v(ck)=1.65 rise=316
.meas tran tck_317 when v(ck)=1.65 rise=317
.meas tran tck_318 when v(ck)=1.65 rise=318
.meas tran tck_319 when v(ck)=1.65 rise=319
.meas tran tck_320 when v(ck)=1.65 rise=320
.meas tran tck_321 when v(ck)=1.65 rise=321
.meas tran tck_322 when v(ck)=1.65 rise=322
.meas tran tck_323 when v(ck)=1.65 rise=323
.meas tran tck_324 when v(ck)=1.65 rise=324
.meas tran tck_325 when v(ck)=1.65 rise=325
.meas tran tck_326 when v(ck)=1.65 rise=326
.meas tran tck_327 when v(ck)=1.65 rise=327
.meas tran tck_328 when v(ck)=1.65 rise=328
.meas tran tck_329 when v(ck)=1.65 rise=329
.meas tran tck_330 when v(ck)=1.65 rise=330
.meas tran tck_331 when v(ck)=1.65 rise=331
.meas tran tck_332 when v(ck)=1.65 rise=332
.meas tran tck_333 when v(ck)=1.65 rise=333
.meas tran tck_334 when v(ck)=1.65 rise=334
.meas tran tck_335 when v(ck)=1.65 rise=335
.meas tran tck_336 when v(ck)=1.65 rise=336
.meas tran tck_337 when v(ck)=1.65 rise=337
.meas tran tck_338 when v(ck)=1.65 rise=338
.meas tran tck_339 when v(ck)=1.65 rise=339
.meas tran tck_340 when v(ck)=1.65 rise=340
.meas tran tck_341 when v(ck)=1.65 rise=341
.meas tran tck_342 when v(ck)=1.65 rise=342
.meas tran tck_343 when v(ck)=1.65 rise=343
.meas tran tck_344 when v(ck)=1.65 rise=344
.meas tran tck_345 when v(ck)=1.65 rise=345
.meas tran tck_346 when v(ck)=1.65 rise=346
.meas tran tck_347 when v(ck)=1.65 rise=347
.meas tran tck_348 when v(ck)=1.65 rise=348
.meas tran tck_349 when v(ck)=1.65 rise=349
.meas tran tck_350 when v(ck)=1.65 rise=350
.meas tran tck_351 when v(ck)=1.65 rise=351
.meas tran tck_352 when v(ck)=1.65 rise=352
.meas tran tck_353 when v(ck)=1.65 rise=353
.meas tran tck_354 when v(ck)=1.65 rise=354
.meas tran tck_355 when v(ck)=1.65 rise=355
.meas tran tck_356 when v(ck)=1.65 rise=356
.meas tran tck_357 when v(ck)=1.65 rise=357
.meas tran tck_358 when v(ck)=1.65 rise=358
.meas tran tck_359 when v(ck)=1.65 rise=359
.meas tran tck_360 when v(ck)=1.65 rise=360
.meas tran tck_361 when v(ck)=1.65 rise=361
.meas tran tck_362 when v(ck)=1.65 rise=362
.meas tran tck_363 when v(ck)=1.65 rise=363
.meas tran tck_364 when v(ck)=1.65 rise=364
.meas tran tck_365 when v(ck)=1.65 rise=365
.meas tran tck_366 when v(ck)=1.65 rise=366
.meas tran tck_367 when v(ck)=1.65 rise=367
.meas tran tck_368 when v(ck)=1.65 rise=368
.meas tran tck_369 when v(ck)=1.65 rise=369
.meas tran tck_370 when v(ck)=1.65 rise=370
.meas tran tck_371 when v(ck)=1.65 rise=371
.meas tran tck_372 when v(ck)=1.65 rise=372
.meas tran tck_373 when v(ck)=1.65 rise=373
.meas tran tck_374 when v(ck)=1.65 rise=374
.meas tran tck_375 when v(ck)=1.65 rise=375
.meas tran tck_376 when v(ck)=1.65 rise=376
.meas tran tck_377 when v(ck)=1.65 rise=377
.meas tran tck_378 when v(ck)=1.65 rise=378
.meas tran tck_379 when v(ck)=1.65 rise=379
.meas tran tck_380 when v(ck)=1.65 rise=380
.meas tran tck_381 when v(ck)=1.65 rise=381
.meas tran tck_382 when v(ck)=1.65 rise=382
.meas tran tck_383 when v(ck)=1.65 rise=383
.meas tran tck_384 when v(ck)=1.65 rise=384
.meas tran tck_385 when v(ck)=1.65 rise=385
.meas tran tck_386 when v(ck)=1.65 rise=386
.meas tran tck_387 when v(ck)=1.65 rise=387
.meas tran tck_388 when v(ck)=1.65 rise=388
.meas tran tck_389 when v(ck)=1.65 rise=389
.meas tran tck_390 when v(ck)=1.65 rise=390
.meas tran tck_391 when v(ck)=1.65 rise=391
.meas tran tck_392 when v(ck)=1.65 rise=392
.meas tran tck_393 when v(ck)=1.65 rise=393
.meas tran tck_394 when v(ck)=1.65 rise=394
.meas tran tck_395 when v(ck)=1.65 rise=395
.meas tran tck_396 when v(ck)=1.65 rise=396
.meas tran tck_397 when v(ck)=1.65 rise=397
.meas tran tck_398 when v(ck)=1.65 rise=398
.meas tran tck_399 when v(ck)=1.65 rise=399
.meas tran tck_400 when v(ck)=1.65 rise=400
.meas tran tck_401 when v(ck)=1.65 rise=401
.meas tran tck_402 when v(ck)=1.65 rise=402
.meas tran tck_403 when v(ck)=1.65 rise=403
.meas tran tck_404 when v(ck)=1.65 rise=404
.meas tran tck_405 when v(ck)=1.65 rise=405
.meas tran tck_406 when v(ck)=1.65 rise=406
.meas tran tck_407 when v(ck)=1.65 rise=407
.meas tran tck_408 when v(ck)=1.65 rise=408
.meas tran tck_409 when v(ck)=1.65 rise=409
.meas tran tck_410 when v(ck)=1.65 rise=410
.meas tran tck_411 when v(ck)=1.65 rise=411
.meas tran tck_412 when v(ck)=1.65 rise=412
.meas tran tck_413 when v(ck)=1.65 rise=413
.meas tran tck_414 when v(ck)=1.65 rise=414
.meas tran tck_415 when v(ck)=1.65 rise=415
.meas tran tck_416 when v(ck)=1.65 rise=416
.meas tran tck_417 when v(ck)=1.65 rise=417
.meas tran tck_418 when v(ck)=1.65 rise=418
.meas tran tck_419 when v(ck)=1.65 rise=419
.meas tran tck_420 when v(ck)=1.65 rise=420
.meas tran tck_421 when v(ck)=1.65 rise=421
.meas tran tck_422 when v(ck)=1.65 rise=422
.meas tran tck_423 when v(ck)=1.65 rise=423
.meas tran tck_424 when v(ck)=1.65 rise=424
.meas tran tck_425 when v(ck)=1.65 rise=425
.meas tran tck_426 when v(ck)=1.65 rise=426
.meas tran tck_427 when v(ck)=1.65 rise=427
.meas tran tck_428 when v(ck)=1.65 rise=428
.meas tran tck_429 when v(ck)=1.65 rise=429
.meas tran tck_430 when v(ck)=1.65 rise=430
.meas tran tck_431 when v(ck)=1.65 rise=431
.meas tran tck_432 when v(ck)=1.65 rise=432
.meas tran tck_433 when v(ck)=1.65 rise=433
.meas tran tck_434 when v(ck)=1.65 rise=434
.meas tran tck_435 when v(ck)=1.65 rise=435
.meas tran tck_436 when v(ck)=1.65 rise=436
.meas tran tck_437 when v(ck)=1.65 rise=437
.meas tran tck_438 when v(ck)=1.65 rise=438
.meas tran tck_439 when v(ck)=1.65 rise=439
.meas tran tck_440 when v(ck)=1.65 rise=440
.meas tran tck_441 when v(ck)=1.65 rise=441
.meas tran tck_442 when v(ck)=1.65 rise=442
.meas tran tck_443 when v(ck)=1.65 rise=443
.meas tran tck_444 when v(ck)=1.65 rise=444
.meas tran tck_445 when v(ck)=1.65 rise=445
.meas tran tck_446 when v(ck)=1.65 rise=446
.meas tran tck_447 when v(ck)=1.65 rise=447
.meas tran tck_448 when v(ck)=1.65 rise=448
.meas tran tck_449 when v(ck)=1.65 rise=449
.meas tran tck_450 when v(ck)=1.65 rise=450
.meas tran tck_451 when v(ck)=1.65 rise=451
.meas tran tck_452 when v(ck)=1.65 rise=452
.meas tran tck_453 when v(ck)=1.65 rise=453
.meas tran tck_454 when v(ck)=1.65 rise=454
.meas tran tck_455 when v(ck)=1.65 rise=455
.meas tran tck_456 when v(ck)=1.65 rise=456
.meas tran tck_457 when v(ck)=1.65 rise=457
.meas tran tck_458 when v(ck)=1.65 rise=458
.meas tran tck_459 when v(ck)=1.65 rise=459
.meas tran tck_460 when v(ck)=1.65 rise=460
.meas tran tck_461 when v(ck)=1.65 rise=461
.meas tran tck_462 when v(ck)=1.65 rise=462
.meas tran tck_463 when v(ck)=1.65 rise=463
.meas tran tck_464 when v(ck)=1.65 rise=464
.meas tran tck_465 when v(ck)=1.65 rise=465
.meas tran tck_466 when v(ck)=1.65 rise=466
.meas tran tck_467 when v(ck)=1.65 rise=467
.meas tran tck_468 when v(ck)=1.65 rise=468
.meas tran tck_469 when v(ck)=1.65 rise=469
.meas tran tck_470 when v(ck)=1.65 rise=470
.meas tran tck_471 when v(ck)=1.65 rise=471
.meas tran tck_472 when v(ck)=1.65 rise=472
.meas tran tck_473 when v(ck)=1.65 rise=473
.meas tran tck_474 when v(ck)=1.65 rise=474
.meas tran tck_475 when v(ck)=1.65 rise=475
.meas tran tck_476 when v(ck)=1.65 rise=476
.meas tran tck_477 when v(ck)=1.65 rise=477
.meas tran tck_478 when v(ck)=1.65 rise=478
.meas tran tck_479 when v(ck)=1.65 rise=479
.meas tran tck_480 when v(ck)=1.65 rise=480
.meas tran tck_481 when v(ck)=1.65 rise=481
.meas tran tck_482 when v(ck)=1.65 rise=482
.meas tran tck_483 when v(ck)=1.65 rise=483
.meas tran tck_484 when v(ck)=1.65 rise=484
.meas tran tck_485 when v(ck)=1.65 rise=485
.meas tran tck_486 when v(ck)=1.65 rise=486
.meas tran tck_487 when v(ck)=1.65 rise=487
.meas tran tck_488 when v(ck)=1.65 rise=488
.meas tran tck_489 when v(ck)=1.65 rise=489
.meas tran tck_490 when v(ck)=1.65 rise=490
.meas tran tck_491 when v(ck)=1.65 rise=491
.meas tran tck_492 when v(ck)=1.65 rise=492
.meas tran tck_493 when v(ck)=1.65 rise=493
.meas tran tck_494 when v(ck)=1.65 rise=494
.meas tran tck_495 when v(ck)=1.65 rise=495
.meas tran tck_496 when v(ck)=1.65 rise=496
.meas tran tck_497 when v(ck)=1.65 rise=497
.meas tran tck_498 when v(ck)=1.65 rise=498
.meas tran tck_499 when v(ck)=1.65 rise=499
.meas tran tck_500 when v(ck)=1.65 rise=500
.meas tran tck_501 when v(ck)=1.65 rise=501
.meas tran tck_502 when v(ck)=1.65 rise=502
.meas tran tck_503 when v(ck)=1.65 rise=503
.meas tran tck_504 when v(ck)=1.65 rise=504
.meas tran tck_505 when v(ck)=1.65 rise=505
.meas tran tck_506 when v(ck)=1.65 rise=506
.meas tran tck_507 when v(ck)=1.65 rise=507
.meas tran tck_508 when v(ck)=1.65 rise=508
.meas tran tck_509 when v(ck)=1.65 rise=509
.meas tran tck_510 when v(ck)=1.65 rise=510
.meas tran tck_511 when v(ck)=1.65 rise=511
.meas tran tck_512 when v(ck)=1.65 rise=512
.meas tran tck_513 when v(ck)=1.65 rise=513
.meas tran tck_514 when v(ck)=1.65 rise=514
.meas tran tck_515 when v(ck)=1.65 rise=515
.meas tran tck_516 when v(ck)=1.65 rise=516
.meas tran tck_517 when v(ck)=1.65 rise=517
.meas tran tck_518 when v(ck)=1.65 rise=518
.meas tran tck_519 when v(ck)=1.65 rise=519
.meas tran tck_520 when v(ck)=1.65 rise=520
.meas tran tck_521 when v(ck)=1.65 rise=521
.meas tran tck_522 when v(ck)=1.65 rise=522
.meas tran tck_523 when v(ck)=1.65 rise=523
.meas tran tck_524 when v(ck)=1.65 rise=524
.meas tran tck_525 when v(ck)=1.65 rise=525
.meas tran tck_526 when v(ck)=1.65 rise=526
.meas tran tck_527 when v(ck)=1.65 rise=527
.meas tran tck_528 when v(ck)=1.65 rise=528
.meas tran tck_529 when v(ck)=1.65 rise=529
.meas tran tck_530 when v(ck)=1.65 rise=530
.meas tran tck_531 when v(ck)=1.65 rise=531
.meas tran tck_532 when v(ck)=1.65 rise=532
.meas tran tck_533 when v(ck)=1.65 rise=533
.meas tran tck_534 when v(ck)=1.65 rise=534
.meas tran tck_535 when v(ck)=1.65 rise=535
.meas tran tck_536 when v(ck)=1.65 rise=536
.meas tran tck_537 when v(ck)=1.65 rise=537
.meas tran tck_538 when v(ck)=1.65 rise=538
.meas tran tck_539 when v(ck)=1.65 rise=539
.meas tran tck_540 when v(ck)=1.65 rise=540
.meas tran tck_541 when v(ck)=1.65 rise=541
.meas tran tck_542 when v(ck)=1.65 rise=542
.meas tran tfb_1 when v(fb)=1.65 rise=1
.meas tran tfb_2 when v(fb)=1.65 rise=2
.meas tran tfb_3 when v(fb)=1.65 rise=3
.meas tran tfb_4 when v(fb)=1.65 rise=4
.meas tran tfb_5 when v(fb)=1.65 rise=5
.meas tran tfb_6 when v(fb)=1.65 rise=6
.meas tran tfb_7 when v(fb)=1.65 rise=7
.meas tran tfb_8 when v(fb)=1.65 rise=8
.meas tran tfb_9 when v(fb)=1.65 rise=9
.meas tran tfb_10 when v(fb)=1.65 rise=10
.meas tran tfb_11 when v(fb)=1.65 rise=11
.end
