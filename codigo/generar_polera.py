# Polera.dae: silueta de polera extruida 3 cm, con normales por cara y caras hacia afuera (metros, Y arriba).
P=[(-0.25,-0.35),(0.25,-0.35),(0.25,0.12),(0.40,0.05),(0.46,0.20),(0.20,0.35),(0.08,0.35),(0.0,0.28),(-0.08,0.35),(-0.20,0.35),(-0.46,0.20),(-0.40,0.05),(-0.25,0.12)]
def area(p): return sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2
if area(P)<0: P=P[::-1]
def inside(a,b,c,p):
    def s(p1,p2,p3): return (p1[0]-p3[0])*(p2[1]-p3[1])-(p2[0]-p3[0])*(p1[1]-p3[1])
    d1,d2,d3=s(p,a,b),s(p,b,c),s(p,c,a)
    return not ((d1<0 or d2<0 or d3<0) and (d1>0 or d2>0 or d3>0))
idx=list(range(len(P))); tris=[]
while len(idx)>3:
    for k in range(len(idx)):
        i,j,l=idx[k-1],idx[k],idx[(k+1)%len(idx)]; a,b,c=P[i],P[j],P[l]
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<=0: continue
        if any(inside(a,b,c,P[m]) for m in idx if m not in (i,j,l)): continue
        tris.append((i,j,l)); idx.pop(k); break
tris.append(tuple(idx))
H=0.03; n=len(P)
V=[(v,0.0,u) for u,v in P]+[(v,H,u) for u,v in P]
cx=sum(x for x,_,_ in V)/len(V); cz=sum(z for _,_,z in V)/len(V)
def sub(p,q): return (p[0]-q[0],p[1]-q[1],p[2]-q[2])
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(v):
    m=(v[0]**2+v[1]**2+v[2]**2)**0.5; return (v[0]/m,v[1]/m,v[2]/m)
F=[]
def add(a,b,c,want):
    nr=cross(sub(V[b],V[a]),sub(V[c],V[a]))
    if sum(nr[k]*want[k] for k in range(3))<0: b,c=c,b; nr=cross(sub(V[b],V[a]),sub(V[c],V[a]))
    F.append((a,b,c,norm(nr)))
for i,j,l in tris: add(n+i,n+j,n+l,(0,1,0)); add(i,j,l,(0,-1,0))
for i in range(n):
    j=(i+1)%n; mx=(V[i][0]+V[j][0])/2-cx; mz=(V[i][2]+V[j][2])/2-cz
    add(i,j,n+j,(mx,0,mz)); add(i,n+j,n+i,(mx,0,mz))
pos=" ".join(f"{x:.4f} {y:.4f} {z:.4f}" for x,y,z in V)
nrm=" ".join(f"{a:.4f} {b:.4f} {c:.4f}" for *_,(a,b,c) in F)
ind=" ".join(f"{a} {k} {b} {k} {c} {k}" for k,(a,b,c,_) in enumerate(F))
col="0.16 0.44 0.86 1"
dae=f'''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<asset><unit name="meter" meter="1"/><up_axis>Y_UP</up_axis></asset>
<library_effects><effect id="tela-fx"><profile_COMMON><technique sid="c"><phong><emission><color>0.05 0.12 0.25 1</color></emission><ambient><color>{col}</color></ambient><diffuse><color>{col}</color></diffuse><specular><color>0.1 0.1 0.1 1</color></specular><shininess><float>10</float></shininess></phong></technique></profile_COMMON></effect></library_effects>
<library_materials><material id="tela" name="tela"><instance_effect url="#tela-fx"/></material></library_materials>
<library_geometries><geometry id="polera-geo" name="Polera"><mesh>
<source id="pos"><float_array id="pos-arr" count="{len(V)*3}">{pos}</float_array><technique_common><accessor source="#pos-arr" count="{len(V)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
<source id="nrm"><float_array id="nrm-arr" count="{len(F)*3}">{nrm}</float_array><technique_common><accessor source="#nrm-arr" count="{len(F)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
<vertices id="vtx"><input semantic="POSITION" source="#pos"/></vertices>
<triangles material="tela" count="{len(F)}"><input semantic="VERTEX" source="#vtx" offset="0"/><input semantic="NORMAL" source="#nrm" offset="1"/><p>{ind}</p></triangles>
</mesh></geometry></library_geometries>
<library_visual_scenes><visual_scene id="s"><node id="Polera" name="Polera"><instance_geometry url="#polera-geo"><bind_material><technique_common><instance_material symbol="tela" target="#tela"/></technique_common></bind_material></instance_geometry></node></visual_scene></library_visual_scenes>
<scene><instance_visual_scene url="#s"/></scene>
</COLLADA>'''
open('Polera.dae','w').write(dae); print(len(F),"caras con normales")
