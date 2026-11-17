import re,sys,glob,os
work,outdir=sys.argv[1:3]
for d in sorted(glob.glob(outdir+"/tb_*")):
    tag=os.path.basename(d)[3:]            # arm_case_offset
    arm,case,off=tag.split("_",2)
    s=open(d+"/stdout.bin",errors="replace").read()
    up=re.search(r"^up_avg *= *([0-9.eE+-]+)",s,re.M); dn=re.search(r"^dn_avg *= *([0-9.eE+-]+)",s,re.M)
    assert up and dn, tag
    open(f"{work}/res.{tag}","w").write(f"{arm},{case},{off},mos_tt,27,3.3,{up.group(1)},{dn.group(1)}\n")
