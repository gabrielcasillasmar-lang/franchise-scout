import { useState } from "react";

const WEBHOOK = "https://script.google.com/macros/s/AKfycbzhYysv7B_MZpdWz8_30PaIzGG5yIO3KFMIIvsCvn3Abq-BL3poheydyp910IkcfHJVYw/exec";

async function analyzeUrl(url) {
  const apiKey = process.env.REACT_APP_ANTHROPIC_KEY;
  const prompt = "Analiza esta empresa española y su programa de franquicias: " + url + "\n\nBusca en la web y responde SOLO con este JSON sin texto extra ni markdown:\n\n{\"company_name\":\"\",\"url\":\"" + url + "\",\"franchise_keywords\":[],\"has_franchise_section\":false,\"franchise_section_url\":null,\"has_franchise_form\":false,\"franchise_form_description\":null,\"linkedin_url\":null,\"email_general\":null,\"email_franchise\":null,\"phone_general\":null,\"investment_amount\":null,\"num_locations\":null,\"icp_fit\":\"bajo\",\"notes\":null}\n\nicp_fit: alto si inversión menor 150000 euros y expansión activa; medio si sin datos; bajo si mayor 150000 euros o sin franquicias. notes máx 10 palabras.";
  let messages = [{ role: "user", content: prompt }];
  for (let turn = 0; turn < 8; turn++) {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": apiKey, "anthropic-version": "2023-06-01", "anthropic-dangerous-direct-browser-access": "true" },
      body: JSON.stringify({ model: "claude-haiku-4-5-20251001", max_tokens: 1500, tools: [{ type: "web_search_20250305", name: "web_search" }], messages })
    });
    if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error("API " + res.status + ": " + (e.error?.message || res.statusText)); }
    const d = await res.json();
    messages.push({ role: "assistant", content: d.content });
    if (d.stop_reason === "end_turn") {
      const txt = (d.content||[]).filter(b=>b.type==="text").map(b=>b.text).join("\n");
      if (txt.trim()) return parseJson(txt, url);
      throw new Error("Respuesta vacía");
    }
    if (d.stop_reason === "tool_use") {
      messages.push({ role: "user", content: (d.content||[]).filter(b=>b.type==="tool_use").map(b=>({ type: "tool_result", tool_use_id: b.id, content: "OK" })) });
    }
  }
  throw new Error("Sin respuesta");
}

function parseJson(text, url) {
  try { const s=text.indexOf("{"),e=text.lastIndexOf("}"); if(s>=0&&e>s) return JSON.parse(text.substring(s,e+1)); } catch(e){}
  return { company_name: new URL(url).hostname, url, franchise_keywords:[], has_franchise_section:false, franchise_section_url:null, has_franchise_form:false, franchise_form_description:null, linkedin_url:null, email_general:null, email_franchise:null, phone_general:null, investment_amount:null, num_locations:null, icp_fit:"medio", notes:"Revisar manualmente" };
}

async function sendToSheet(data) {
  try { await fetch(WEBHOOK, { method:"POST", mode:"no-cors", headers:{"Content-Type":"text/plain"}, body:JSON.stringify(data) }); return true; } catch(e) { return false; }
}

const fitStyle = f => ({ display:"inline-block", padding:"2px 8px", borderRadius:20, fontSize:10, fontWeight:600, background:f==="alto"?"rgba(76,175,137,.2)":f==="medio"?"rgba(240,160,75,.2)":"rgba(255,92,108,.2)", color:f==="alto"?"#4caf89":f==="medio"?"#f0a04b":"#ff5c6c" });
const ynStyle = v => ({ display:"inline-block", padding:"2px 7px", borderRadius:20, fontSize:10, fontWeight:600, background:v?"rgba(76,175,137,.2)":"rgba(255,92,108,.2)", color:v?"#4caf89":"#ff5c6c" });
const TD = { padding:"9px 10px", borderBottom:"1px solid #2a2a3a", verticalAlign:"top" };

export default function App() {
  const [urls, setUrls] = useState("");
  const [results, setResults] = useState([]);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [sent, setSent] = useState(0);
  const done = results.filter(r => r.status === "done");

  async function start() {
    const list = urls.split("\n").map(u=>u.trim()).filter(u=>u.startsWith("http"));
    if (!list.length) { setStatus("Introduce URLs que empiecen por https://"); return; }
    setRunning(true); setSent(0); setProgress(0);
    setResults(list.map(url => ({ url, status:"loading", data:null, error:null, inSheet:false })));
    let s = 0;
    for (let i = 0; i < list.length; i++) {
      setStatus("Analizando " + (i+1) + "/" + list.length + ": " + list[i]);
      setProgress(Math.round(i / list.length * 100));
      try {
        const data = await analyzeUrl(list[i]);
        const ok = await sendToSheet(data);
        if (ok) { s++; setSent(s); }
        setResults(prev => prev.map((r,idx) => idx===i ? {...r, status:"done", data, inSheet:ok} : r));
      } catch(err) {
        setResults(prev => prev.map((r,idx) => idx===i ? {...r, status:"error", error:err.message} : r));
      }
    }
    setProgress(100); setStatus(""); setRunning(false);
  }

  function exportCSV() {
    const cols = ["Empresa","URL","Keywords","Seccion","Formulario","LinkedIn","Email","Telefono","Inversion","Locales","Fit ICP","Notas"];
    const rows = done.map(r => {
      const d = r.data;
      return [d.company_name, d.url, (d.franchise_keywords||[]).join("; "), d.has_franchise_section?"Si":"No", d.has_franchise_form?"Si":"No", d.linkedin_url, d.email_general||d.email_franchise, d.phone_general, d.investment_amount, d.num_locations, d.icp_fit, d.notes]
        .map(v=>"\""+String(v||"").replace(/"/g,'\"\"")+"\"").join(",");
    });
    const blob = new Blob(["\ufeff"+[cols.join(","),...rows].join("\n")], {type:"text/csv;charset=utf-8;"});
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "franchise-scout.csv"; a.click();
  }

  return (
    <div style={{background:"#0a0a0f",minHeight:"100vh",color:"#e8e8f0",fontFamily:"system-ui,sans-serif",padding:20,fontSize:14}}>
      <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:24}}>
        <div style={{width:36,height:36,background:"linear-gradient(135deg,#6c63ff,#ff6584)",borderRadius:8,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18}}>🔍</div>
        <div>
          <div style={{fontSize:20,fontWeight:700}}>Franchise <span style={{color:"#6c63ff"}}>Scout</span></div>
          <div style={{color:"#8888aa",fontSize:12}}>Análisis automatizado · Google Sheets en tiempo real</div>
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"270px 1fr",gap:16,alignItems:"start"}}>
        <div>
          <div style={{background:"#13131a",border:"1px solid #2a2a3a",borderRadius:10,padding:16}}>
            <div style={{fontSize:10,textTransform:"uppercase",letterSpacing:1,color:"#8888aa",marginBottom:8,fontWeight:600}}>URLs a analizar</div>
            <textarea value={urls} onChange={e=>setUrls(e.target.value)} placeholder={"https://levaduramadre.es\nhttps://no-mas-vello.com"} style={{width:"100%",background:"#1c1c27",border:"1px solid #2a2a3a",borderRadius:6,color:"#e8e8f0",padding:"8px 10px",fontSize:12,fontFamily:"inherit",outline:"none",resize:"vertical",minHeight:150,lineHeight:1.6,boxSizing:"border-box"}} />
            <button onClick={start} disabled={running} style={{background:running?"#333":"#6c63ff",color:running?"#666":"#fff",border:"none",borderRadius:7,padding:"10px 16px",fontSize:13,fontWeight:600,cursor:running?"not-allowed":"pointer",width:"100%",marginTop:12}}>{running?"⏳ Analizando...":"⚡ Analizar y exportar"}</button>
          </div>
          {results.length > 0 && (
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginTop:12}}>
              {[["Analizadas",done.length],["Con sección",done.filter(r=>r.data?.has_franchise_section).length],["Formulario",done.filter(r=>r.data?.has_franchise_form).length],["Fit alto",done.filter(r=>r.data?.icp_fit==="alto").length]].map(([l,v])=>(
                <div key={l} style={{background:"#13131a",border:"1px solid #2a2a3a",borderRadius:8,padding:"8px 10px",textAlign:"center"}}>
                  <div style={{fontSize:22,fontWeight:700,color:"#6c63ff"}}>{v}</div>
                  <div style={{fontSize:10,color:"#8888aa"}}>{l}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10}}>
            <div style={{fontSize:10,textTransform:"uppercase",letterSpacing:1,color:"#8888aa",fontWeight:600}}>Resultados {sent>0&&<span style={{color:"#4caf89",textTransform:"none",fontWeight:400,marginLeft:6}}>· {sent} en Sheets ✓</span>}</div>
            {done.length>0&&<button onClick={exportCSV} style={{fontSize:12,padding:"5px 10px",background:"#1c1c27",color:"#e8e8f0",border:"1px solid #2a2a3a",borderRadius:6,cursor:"pointer",fontWeight:600}}>⬇ CSV</button>}
          </div>
          {status&&<div style={{fontSize:11,color:"#8888aa",marginBottom:6}}>{status}</div>}
          {running&&<div style={{height:3,background:"#1c1c27",borderRadius:2,overflow:"hidden",marginBottom:8}}><div style={{height:"100%",background:"linear-gradient(90deg,#6c63ff,#ff6584)",width:progress+"%",transition:"width .4s"}}/></div>}
          {results.length===0?(
            <div style={{textAlign:"center",padding:48,color:"#8888aa",background:"#13131a",borderRadius:10,border:"1px solid #2a2a3a"}}>
              <div style={{fontSize:36,marginBottom:10}}>🏪</div>
              <div>Pega las URLs a la izquierda y lanza el análisis.</div>
            </div>
          ):(
            <div style={{overflowX:"auto",borderRadius:8,border:"1px solid #2a2a3a"}}>
              <table style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:800}}>
                <thead><tr style={{background:"#1c1c27"}}>{["Empresa","Keywords","Sección","Formulario","LinkedIn","Email","Inversión","Locales","Fit ICP","Notas"].map(c=><th key={c} style={{padding:"8px 10px",textAlign:"left",fontSize:10,textTransform:"uppercase",color:"#8888aa",fontWeight:600,borderBottom:"1px solid #2a2a3a",whiteSpace:"nowrap"}}>{c}</th>)}</tr></thead>
                <tbody>
                  {results.map((item,idx)=>{
                    if(item.status==="loading") return <tr key={idx}><td colSpan={10} style={{...TD,textAlign:"center",color:"#8888aa"}}>⏳ {item.url}</td></tr>;
                    if(item.status==="error") return <tr key={idx}><td colSpan={10} style={TD}><div style={{background:"rgba(255,92,108,.08)",border:"1px solid rgba(255,92,108,.3)",borderRadius:6,padding:"6px 10px",color:"#ff5c6c",fontSize:11}}>❌ {item.url} — {item.error}</div></td></tr>;
                    const d=item.data;
                    return <tr key={idx}>
                      <td style={TD}><strong>{d.company_name||"—"}</strong>{item.inSheet&&<span style={{color:"#4caf89",fontSize:10,marginLeft:4}}>✓</span>}</td>
                      <td style={TD}><div style={{display:"flex",flexWrap:"wrap",gap:2}}>{(d.franchise_keywords||[]).slice(0,3).map(k=><span key={k} style={{background:"rgba(108,99,255,.12)",color:"#6c63ff",padding:"1px 5px",borderRadius:3,fontSize:10}}>{k}</span>)}</div></td>
                      <td style={TD}><span style={ynStyle(d.has_franchise_section)}>{d.has_franchise_section?"Sí":"No"}</span></td>
                      <td style={TD}><span style={ynStyle(d.has_franchise_form)}>{d.has_franchise_form?"Sí":"No"}</span></td>
                      <td style={TD}>{d.linkedin_url?<a href={d.linkedin_url} target="_blank" rel="noreferrer" style={{color:"#6c63ff",textDecoration:"none",fontSize:11}}>LinkedIn ↗</a>:"—"}</td>
                      <td style={{...TD,fontSize:11}}>{d.email_general||d.email_franchise||"—"}</td>
                      <td style={TD}>{d.investment_amount||"—"}</td>
                      <td style={{...TD,textAlign:"center"}}>{d.num_locations||"—"}</td>
                      <td style={TD}><span style={fitStyle(d.icp_fit)}>{d.icp_fit||"—"}</span></td>
                      <td style={{...TD,fontSize:11,maxWidth:130}}>{d.notes||"—"}</td>
                    </tr>;
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}