import csv,io,subprocess,sys
base="sim/sg13cmos5l-postlayout-pex-pvt/corners/"
new="/tmp/r325/hist/"+base
def num(x):
    try: return float(x)
    except: return None
for f in "ld_rc_extract ld_rc_control ld_window_control ld_window_control_delta ld_window ld_ladder ld_ladder_raw ld_tstep_convergence ld_deviation pfd_results pfd_control".split():
    o=list(csv.reader(io.StringIO(subprocess.check_output(["git","show","07751ca:"+base+f+".csv"],text=True))))
    n=list(csv.reader(open(new+f+".csv")))
    if len(o)!=len(n) or o[0]!=n[0]: print(f,"SHAPE DIFF",len(o),len(n)); continue
    rows=0;cat=0;mx=0;worst=None
    for a,b in zip(o[1:],n[1:]):
        d=False
        for h,x,y in zip(o[0],a,b):
            if x==y: continue
            d=True
            fx,fy=num(x),num(y)
            if fx is None or fy is None: cat+=1; worst=worst or (h,x,y); continue
            r=abs(fx-fy)/max(abs(fx),abs(fy),1e-30)
            if r>mx: mx=r; worst=(h,x,y)
        rows+=d
    print(f"{f}: {len(o)-1} rows, {rows} differ, {cat} categorical-cell diffs, max rel num diff {mx:.3g}, worst {worst}")
