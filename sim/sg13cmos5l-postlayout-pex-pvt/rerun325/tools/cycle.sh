#!/bin/bash
# usage: cycle.sh N : convert pending -> reqN, submit, wait (bounded ~100 min via caller polling)
N=$1
python3 /tmp/r325/tools/passdeck.py convert /tmp/r325/req$N $HOME/share/pdk ihp-sg13cmos5l /tmp/r325/ldwork/.spiceinit && \
(nohup /tmp/r325/tools/submit.sh $N >/dev/null 2>&1 &)
