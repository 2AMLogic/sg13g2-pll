* pdk identity probe (worker)
V1 a 0 dc 1
R1 a b 1k
R2 b 0 1k
.control
op
shell echo PDKROOT=$PDK_ROOT; ls -la /opt/pdk /opt/pdk/ihp-sg13cmos5l | head -40
shell for t in ihp-sg13cmos5l ihp-sg13g2; do echo == $t; ls -a /opt/pdk/$t | head -30; cat /opt/pdk/$t/.fetched-version /opt/pdk/$t/SOURCES /opt/pdk/$t/.git/HEAD /opt/pdk/$t/VERSION 2>&1 | head -20; done
shell cd /opt/pdk; for t in ihp-sg13cmos5l ihp-sg13g2; do (cd $t 2>/dev/null && git rev-parse HEAD 2>&1 | head -2); done; find /opt/pdk -maxdepth 2 -iname '*version*' -o -maxdepth 2 -iname 'SOURCES*' -o -maxdepth 2 -iname '*.json' | head
shell sha256sum /opt/pdk/ihp-sg13cmos5l/libs.tech/ngspice/osdi/*.osdi /opt/pdk/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib /opt/pdk/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib 2>&1
.endc
.end
