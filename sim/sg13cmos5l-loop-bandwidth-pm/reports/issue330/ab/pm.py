import sys, math
for fn in sys.argv[1:]:
    rows=[list(map(float,l.split())) for l in open(fn) if l.strip()]
    for a,b in zip(rows,rows[1:]):
        if a[1]>=1>=b[1]:
            t=(math.log(1/a[1]))/(math.log(b[1]/a[1]))
            f=math.exp(math.log(a[0])+t*(math.log(b[0])-math.log(a[0])))
            ph=a[3]+t*(b[3]-a[3])
            print(f"{fn}: fc={f:.6e} Hz PM={180+ph:.3f} deg"); break
