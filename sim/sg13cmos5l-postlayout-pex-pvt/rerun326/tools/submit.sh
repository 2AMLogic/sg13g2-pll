#!/bin/bash
# usage: submit.sh N   (request dir /tmp/r326/reqN -> out dir /tmp/r326/outN, report /tmp/r326/reportN.json)
N=$1; rm -f /tmp/r326/done$N
cd /tmp/r326/req$N && timeout 1500 klt sim request.json --backend batch --wait-for-capacity 600 -o /tmp/r326/out$N --report-out /tmp/r326/report$N.json --format json > /tmp/r326/stdout$N 2>/tmp/r326/stderr$N
echo $? > /tmp/r326/done$N
