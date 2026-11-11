#!/bin/bash
# usage: submit.sh N   (request dir /tmp/r325/reqN -> out dir /tmp/r325/outN, report /tmp/r325/reportN.json)
N=$1; rm -f /tmp/r325/done$N
cd /tmp/r325/req$N && timeout 3000 klt sim request.json --backend batch --wait-for-capacity 600 -o /tmp/r325/out$N --report-out /tmp/r325/report$N.json --format json > /tmp/r325/stdout$N 2>/tmp/r325/stderr$N
echo $? > /tmp/r325/done$N
