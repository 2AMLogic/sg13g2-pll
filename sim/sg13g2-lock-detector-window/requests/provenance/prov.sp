* provenance probe: prints the executing image's PDK marker, hashes and tool version (no circuit)
V1 n1 0 1
R1 n1 0 1k
.control
shell echo PROV-BEGIN
shell cat /opt/pdk/ihp-sg13g2/.fetched-version
shell cat /opt/pdk/ihp-sg13g2/.pdk-store.json
shell sha256sum /opt/pdk/ihp-sg13g2/libs.tech/ngspice/osdi/psp103.osdi /opt/pdk/ihp-sg13g2/libs.tech/ngspice/osdi/psp103_nqs.osdi /opt/pdk/ihp-sg13g2/libs.tech/ngspice/osdi/mosvar.osdi /opt/pdk/ihp-sg13g2/libs.tech/ngspice/osdi/r3_cmc.osdi /opt/pdk/ihp-sg13g2/libs.tech/ngspice/models/cornerMOShv.lib /opt/pdk/ihp-sg13g2/libs.tech/ngspice/models/cornerRES.lib /opt/pdk/ihp-sg13g2/libs.tech/ngspice/models/cornerCAP.lib
shell ngspice --version
shell uname -srm
shell echo PROV-END
op
print v(n1)
.endc
.end
