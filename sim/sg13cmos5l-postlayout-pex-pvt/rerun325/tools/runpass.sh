#!/bin/bash
# one runner pass with the bridge shim; prints pending count
cd /tmp/r325/hist/sim/sg13cmos5l-postlayout-pex-pvt
find /tmp/r325/pending -mindepth 1 -maxdepth 1 -exec rm -rf {} +
PATH=/tmp/r325/shim2:$PATH PDK_ROOT=$HOME/share/pdk PDK=ihp-sg13cmos5l LD_WORK=/tmp/r325/ldwork ./testbench/run_lock_detector.sh > /tmp/r325/ld_pass$1.log 2>&1
echo "runner rc=$?  pending=$(ls /tmp/r325/pending | wc -l)"; tail -2 /tmp/r325/ld_pass$1.log
