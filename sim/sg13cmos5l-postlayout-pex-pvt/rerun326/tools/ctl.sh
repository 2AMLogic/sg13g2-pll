#!/bin/bash
set -e
cd /tmp/r326
ln -sfn $HOME/share/pdk/ihp-sg13cmos5l.bak-20261015T153923Z pdkpin/ihp-sg13cmos5l
ln -sfn $HOME/share/pdk/ihp-sg13g2.bak-20261015T153923Z pdkpin/ihp-sg13g2
sha256sum pdkpin/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib pdkpin/ihp-sg13cmos5l/libs.tech/ngspice/osdi/r3_cmc.osdi
for t in cur pin; do
  d=/tmp/r326/ctl/$t; mkdir -p $d
  cp lfwork/lf_pex.spice lfwork/lf_pex_inst.clean.spice $d/
  R=$HOME/share/pdk; [ $t = pin ] && R=/tmp/r326/pdkpin
  sed "s|$HOME/share/pdk|$R|g; s|/tmp/r326/lfwork|$d|g" lfwork/lf_ac_postlayout_res_typ_27.sp > $d/deck.sp
  sed "s|$HOME/share/pdk|$R|g" lfwork/.spiceinit > $d/.spiceinit
  (cd $d && timeout 120 ~/.local/bin/ngspice -b deck.sp > out.txt 2>err.txt; echo "$t rc=$?"; grep -cE '^[0-9]+[[:space:]]' out.txt) || true
done
