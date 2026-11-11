exec > probe.out 2>&1
echo "PDK_ROOT env: $PDK_ROOT"
for r in $(find / -maxdepth 5 -type d \( -name ihp-sg13cmos5l -o -name ihp-sg13g2 \) 2>/dev/null | head -8); do
  echo "TREE $r"; ls -la $r | head -4; cat $r/.fetched-version 2>&1 | head -1; (cd $r && git rev-parse HEAD 2>&1 | head -1)
  for f in libs.tech/ngspice/models/cornerRES.lib libs.tech/ngspice/models/cornerMOShv.lib libs.tech/ngspice/osdi/psp103.osdi libs.tech/ngspice/osdi/psp103_nqs.osdi libs.tech/ngspice/osdi/mosvar.osdi libs.tech/ngspice/osdi/r3_cmc.osdi libs.tech/ngspice/osdi/cap_cmomi.osdi; do
    sha256sum $r/$f 2>&1; ls -la $r/$f 2>&1 | awk '{print "   ",$1,$5,$9,$10,$11}'; done
done
ngspice --version | head -2; uname -m; ls -la $(command -v ngspice); sha256sum $(command -v ngspice)
