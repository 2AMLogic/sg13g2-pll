* worker PDK/tool provenance probe
.control
shell sh -c 'echo PDK_ROOT=$PDK_ROOT; for t in ihp-sg13cmos5l ihp-sg13g2; do echo "== $t"; ls -ld $PDK_ROOT/$t; git -C $PDK_ROOT/$t rev-parse HEAD 2>&1; git -C $PDK_ROOT/$t status --porcelain 2>&1 | head -3; cat $PDK_ROOT/$t/.fetched-version 2>&1; head -5 $PDK_ROOT/$t/SOURCES 2>&1; done; sha256sum $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/*.osdi $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib 2>&1; readlink -f $PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103.osdi; ngspice --version | head -3; cat /etc/klt-image-manifest.json /opt/klt/image-manifest.json 2>&1 | head -40; uname -a; grep -m1 "model name" /proc/cpuinfo'
.endc
.end
