const tc=require("topojson-client"),fs=require("fs");
const es=require("./node_modules/es-atlas/es/provinces.json");
const w=require("./node_modules/world-atlas/countries-10m.json");
const W=2.15,E=3.42,S=41.62,N=42.52,k=Math.cos(42*Math.PI/180);
const WIDTH=800,sc=WIDTH/((E-W)*k),HEIGHT=Math.round((N-S)*sc);
const P=([lon,lat])=>[Math.round((lon-W)*k*sc*2)/2,Math.round((N-lat)*sc*2)/2];
function ring(r,close){let s="",last;for(const c of r){const p=P(c);if(last&&p[0]==last[0]&&p[1]==last[1])continue;s+=(s?"L":"M")+p.join(",");last=p;}return s+(close?"Z":"");}
const chain=JSON.parse(fs.readFileSync("land_clip.json"))[0][0];
const land=ring([...chain,[1.0,43.6],[4.48,43.6]],true);
const coast=ring(chain,false);
const mline=g=>g.coordinates.map(r=>ring(r,false)).join("");
const frEs=tc.mesh(w,w.objects.countries,(a,b)=>{const n=[a.properties.name,b.properties.name].sort().join();return n==="France,Spain";});
const gb=tc.mesh(es,es.objects.provinces,(a,b)=>[a.id,b.id].sort().join()==="08,17");
const out={W,E,S,N,k,sc,WIDTH,HEIGHT,land,coast,border:mline(frEs),prov:mline(gb)};
fs.writeFileSync("map.json",JSON.stringify(out));
console.log(WIDTH,HEIGHT,land.length,out.border.length,out.prov.length);
