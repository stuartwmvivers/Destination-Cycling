const tc=require("topojson-client"),fs=require("fs");
const w=require("./node_modules/world-atlas/countries-10m.json");
const W=-9.8,E=4.8,S=35.6,N=44.0,k=Math.cos(40*Math.PI/180);
const WIDTH=800,sc=WIDTH/((E-W)*k),HEIGHT=Math.round((N-S)*sc);
const P=([lon0,lat0])=>{const lon=Math.max(W-1.5,Math.min(E+1.5,lon0)),lat=Math.max(S-1.5,Math.min(N+1.5,lat0));return [Math.round((lon-W)*k*sc*2)/2,Math.round((N-lat)*sc*2)/2];};
const inBox=r=>r.some(([x,y])=>x>W-3&&x<E+3&&y>S-3&&y<N+3);
function path(geo){let d="";const polys=geo.type==="Polygon"?[geo.coordinates]:geo.coordinates;
 for(const poly of polys)for(const ring of poly){if(!inBox(ring))continue;let s="",last;for(const c of ring){const p=P(c);if(last&&p[0]==last[0]&&p[1]==last[1])continue;s+=(s?"L":"M")+p.join(",");last=p;}d+=s+"Z";}return d;}
const feats=tc.feature(w,w.objects.countries).features;
const pick=n=>feats.find(f=>f.properties.name===n);
const spain=path(pick("Spain").geometry);
const others=["Portugal","France","Andorra","Morocco","Algeria","Gibraltar","Italy"].map(n=>pick(n)).filter(Boolean).map(f=>path(f.geometry)).join("");
const mline=g=>g.coordinates.map(r=>{let s="",last;for(const c of r){const p=P(c);if(last&&p[0]==last[0]&&p[1]==last[1])continue;s+=(s?"L":"M")+p.join(",");last=p;}return s;}).join("");
const borders=mline(tc.mesh(w,w.objects.countries,(a,b)=>a!==b&&[a.properties.name,b.properties.name].includes("Spain")));
// Girona close-up frame rectangle on the Spain map
const [x0,y0]=P([2.15,42.52]),[x1,y1]=P([3.42,41.62]);
const out={W,E,S,N,k,sc,WIDTH,HEIGHT,spain,others,borders,frame:`M${x0},${y0}L${x1},${y0}L${x1},${y1}L${x0},${y1}Z`};
fs.writeFileSync("spainmap.json",JSON.stringify(out));
console.log(WIDTH,HEIGHT,spain.length,others.length,borders.length);
