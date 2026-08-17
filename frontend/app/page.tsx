'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'

type Opportunity = {id:string; type:string; title:string; thesis:string; score:number; confidence:number; stage:string; reasoning:Record<string,unknown>}
type RunResult = {signals:number; trends?:number; opportunities:number; topics?:string[]}
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8100'

export default function Home(){
  const [items,setItems]=useState<Opportunity[]>([])
  const [loading,setLoading]=useState(false)
  const [mode,setMode]=useState<'demo'|'live'>('live')
  const [message,setMessage]=useState('')

  async function load(){
    const r=await fetch(`${API}/api/v1/opportunities`,{cache:'no-store'})
    if(!r.ok) throw new Error(`API ${r.status}`)
    setItems(await r.json())
  }

  async function discover(){
    setLoading(true); setMessage('')
    try{
      const r=await fetch(`${API}/api/v1/discovery/${mode}`,{method:'POST'})
      if(!r.ok) throw new Error(await r.text())
      const result:RunResult=await r.json()
      await load()
      setMessage(mode==='live'
        ? `Found ${result.trends ?? 0} candidate trends from ${result.signals} evidence signals.`
        : `Demo created ${result.opportunities} opportunities.`)
    }catch(e){
      setMessage(`Discovery failed: ${e instanceof Error ? e.message : 'Unknown error'}`)
    }finally{setLoading(false)}
  }

  useEffect(()=>{load().catch(()=>setMessage('Could not reach the YetSee API.'))},[])
  return <main>
    <header>
      <div><div className="eyebrow">AI Opportunity Intelligence</div><h1>See What's Next.</h1><p>YetSee detects meaningful change, preserves the evidence, and turns emerging signals into investigations you can inspect before acting.</p></div>
      <div className="actions"><div className="segmented"><button className={mode==='live'?'active':''} onClick={()=>setMode('live')}>Live</button><button className={mode==='demo'?'active':''} onClick={()=>setMode('demo')}>Demo</button></div><button className="primary" onClick={discover} disabled={loading}>{loading?'Discovering…':'Run discovery'}</button></div>
    </header>
    {message && <div className="notice">{message}</div>}
    <section className="stats"><article><span>Opportunities</span><strong>{items.length}</strong></article><article><span>Top score</span><strong>{items[0]?.score ?? '—'}</strong></article><article><span>Stage</span><strong>{items[0]?.stage ?? '—'}</strong></article></section>
    <section><div className="sectionTitle"><h2>Investigation feed</h2><span>Evidence first</span></div><div className="grid">{items.length?items.map(x=><Link className="card" href={`/opportunities/${x.id}`} key={x.id}><div className="row"><span className="pill">{x.type}</span><strong>{Math.round(x.score)}</strong></div><h3>{x.title}</h3><p>{x.thesis}</p><div className="meta">Confidence {Math.round(x.confidence*100)}% · {x.stage} · Open investigation →</div></Link>):<article className="empty"><h3>No opportunities yet</h3><p>Run live discovery to find candidate changes from public sources, or use demo mode to verify the pipeline.</p></article>}</div></section>
  </main>
}
