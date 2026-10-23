const fs=require("fs");
const g=JSON.parse(fs.readFileSync("./node_modules/@geo-maps/earth-lands-100m/map.geo.json"));
const frames={
  sol:{W:-5.35,E:-3.65,S:36.25,N:37.0,lat0:36.6},
  blanca:{W:-0.75,E:0.35,S:38.2,N:38.95,lat0:38.6},
  mallorca:{W:2.25,E:3.55,S:39.2,N:40.0,lat0:39.6},
};
const out={};
function clip(ring,x0,x1,y0,y1){
  const edges=[[p=>p[0]>=x0,(a,b)=>{const t=(x0-a[0])/(b[0]-a[0]);return [x0,a[1]+t*(b[1]-a[1])];}],
    [p=>p[0]<=x1,(a,b)=>{const t=(x1-a[0])/(b[0]-a[0]);return [x1,a[1]+t*(b[1]-a[1])];}],
    [p=>p[1]>=y0,(a,b)=>{const t=(y0-a[1])/(b[1]-a[1]);return [a[0]+t*(b[0]-a[0]),y0];}],
    [p=>p[1]<=y1,(a,b)=>{const t=(y1-a[1])/(b[1]-a[1]);return [a[0]+t*(b[0]-a[0]),y1];}]];
  let pts=ring;
  for(const [inside,cut] of edges){const res=[];if(!pts.length)break;let prev=pts[pts.length-1];
    for(const cur of pts){const ci=inside(cur),pi=inside(prev);if(ci){if(!pi)res.push(cut(prev,cur));res.push(cur);}else if(pi)res.push(cut(prev,cur));prev=cur;}
    pts=res;}
  return pts;
}
for(const [name,f] of Object.entries(frames)){
  const k=Math.cos(f.lat0*Math.PI/180),WIDTH=800,sc=WIDTH/((f.E-f.W)*k),HEIGHT=Math.round((f.N-f.S)*sc);
  const m=0.15;
  const P=([lon,lat])=>{lon=Math.max(f.W-m,Math.min(f.E+m,lon));lat=Math.max(f.S-m,Math.min(f.N+m,lat));return [Math.round((lon-f.W)*k*sc*2)/2,Math.round((f.N-lat)*sc*2)/2];};
  let d="";
  for(const G of g.geometries){const ps=G.type=="Polygon"?[G.coordinates]:G.coordinates;
    for(const poly of ps){const outer=poly[0];let hit=false,minx=1e9,maxx=-1e9,miny=1e9,maxy=-1e9;
      for(const [x,y] of outer){if(x<minx)minx=x;if(x>maxx)maxx=x;if(y<miny)miny=y;if(y>maxy)maxy=y;}
      if(maxx<f.W-m||minx>f.E+m||maxy<f.S-m||miny>f.N+m)continue;
      for(const ring0 of [poly[0]]){const ring=clip(ring0,f.W-m,f.E+m,f.S-m,f.N+m);let s="",last=null,n=0;
        for(const c of ring){const p=P(c);if(last&&Math.hypot(p[0]-last[0],p[1]-last[1])<1.2)continue;s+=(s?"L":"M")+p.join(",");last=p;n++;}
        if(n>2)d+=s+"Z";}}}
  out[name]={W:f.W,E:f.E,S:f.S,N:f.N,k,sc,WIDTH,HEIGHT,land:d};
  console.log(name,WIDTH,HEIGHT,d.length);
}
fs.writeFileSync("closeups.json",JSON.stringify(out));
