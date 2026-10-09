.model dffb d_dff(clk_delay=20p set_delay=20p reset_delay=20p ic=0
+ rise_delay=20p fall_delay=20p)
.model adcb adc_bridge(in_low=1.40 in_high=1.90)
.model dacb dac_bridge(out_low=0 out_high=@VDD@ out_undef=1.65
+ t_rise=80p t_fall=80p)
Aad [clk] [dclk] adcb
Ab1 q1b dclk NULL NULL q1 q1b dffb
Ab2 q2b q1   NULL NULL q2 q2b dffb
Ab3 q3b q2   NULL NULL q3 q3b dffb
Ab4 q4b q3   NULL NULL q4 q4b dffb
Ab5 q5b q4   NULL NULL q5 q5b dffb
Ab6 q6b q5   NULL NULL q6 q6b dffb
Ada [q6] [fb] dacb
