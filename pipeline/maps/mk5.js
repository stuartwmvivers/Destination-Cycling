const fs=require("fs");
const D={...JSON.parse(fs.readFileSync("data.json")),...JSON.parse(fs.readFileSync("data2.json")),...JSON.parse(fs.readFileSync("data3.json"))};
const rows=[];for(const [id,v] of Object.entries(D)){for(let i=0;i<108;i++){rows.push({place:id,year:2017+Math.floor(i/12),month:i%12+1,tmax:v.tx[i],tmin:v.tn[i],rain:v.r[i],wet:v.wet[i],ride:v.ride[i],warm:v.comf[i],hot:v.hot[i],frost:v.fr[i],tram:v.tram[i]});}}
fs.writeFileSync("up/climate-spain-2017-2025.json",JSON.stringify(rows));
const meta={
begur:["Costa Brava","Coast","Hilltop village; data at about 200 m"],llanca:["Costa Brava","Coast","North coast, in the Tramuntana corridor"],roses:["Costa Brava","Coast","Bay of Roses"],lescala:["Costa Brava","Coast","Central coast"],palamos:["Costa Brava","Coast","Southern-central coast"],tossa:["Costa Brava","Coast","South coast"],figueres:["Costa Brava","Inland","Empordà plain"],girona:["Costa Brava","Inland","City"],olot:["Costa Brava","Hills","Volcanic hills, 440 m"],
nerja:["Costa del Sol","Coast","Axarquía coast, east of Málaga"],torrox:["Costa del Sol","Coast","Coast just west of Nerja"],frigiliana:["Costa del Sol","Hills","Hill village above Nerja at about 320 m; shares Nerja's rain and wind"],marbella:["Costa del Sol","Coast","Western Costa del Sol"],estepona:["Costa del Sol","Coast","Near Gibraltar; open to the Levante wind"],
alicante:["Costa Blanca","Coast","City, southern Costa Blanca"],altea:["Costa Blanca","Coast","Below the Sierra de Bernia"],javea:["Costa Blanca","Coast","Northern Costa Blanca, by Cap de la Nau"],
palma:["Mallorca","Coast","City, Bay of Palma"],soller:["Mallorca","Hills","Valley in the Serra de Tramuntana; the 9 km grid smooths the mountains"],pollensa:["Mallorca","Coast","North-east; Mallorca's cycling hub"],
dunning:["UK","Home","Perthshire, Scotland"],bristol:["UK","Home","South-west England"]};
const AREA={dunning:"Scotland",bristol:"England"};
const order=["begur","llanca","roses","lescala","palamos","tossa","figueres","girona","olot","nerja","torrox","frigiliana","marbella","estepona","alicante","altea","javea","palma","soller","pollensa","dunning","bristol"];
fs.writeFileSync("up/places-spain.json",JSON.stringify(order.map(id=>({place:id,name:D[id].name,lat:D[id].lat,lon:D[id].lon,elevation_m:D[id].elev,region:meta[id][0],setting:meta[id][1],note:meta[id][2],...(AREA[id]?{area:AREA[id]}:{})}))));
const M=JSON.parse(fs.readFileSync("map.json")),S=JSON.parse(fs.readFileSync("spainmap.json")),C=JSON.parse(fs.readFileSync("closeups.json"));
const fr=(name,f)=>({frame:name,W:f.W,E:f.E,S:f.S,N:f.N,k:f.k,scale:f.sc,width:f.WIDTH,height:f.HEIGHT});
const out=[];
for(const l of ["land","coast","border","prov"])out.push({...fr("brava",M),layer:l,path:M[l]});
for(const l of ["others","spain","borders","frame"])out.push({...fr("spain",S),layer:l,path:S[l]});
for(const [n,f] of Object.entries(C))out.push({...fr(n,f),layer:"land",path:f.land});
fs.writeFileSync("up/map-outlines-spain.json",JSON.stringify(out));
for(const n of ["climate-spain-2017-2025.json","places-spain.json","map-outlines-spain.json"])console.log(n,fs.statSync("up/"+n).size);
