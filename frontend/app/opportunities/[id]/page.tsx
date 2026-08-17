'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8100'
type Signal={id:string;source:string;topic:string;metric:string;value:number;observed_at:string;evidence:{title?:string;url?:string;live?:boolean;demo?:boolean}}
type Investigation={opportunity:{id:string;type:string;title:string;thesis:string;score:number;confidence:number;stage:string};trend:{name:string;stage:string;momentum:number;confidence:number;thesis:string}|null;evidence:Signal[];supporting_sources:number;risks:string[];score_components:Record<string,unknown>}

export default function InvestigationPage({params}:{params:Promise<{id:string}>}){
  const [data,setData]=useState<Investigation|null>(null)
  const [error,setError]=useState('')
  useEffect(()=>{params.then(({id})=>fetch(`${API}/api/v1/opportunities/${id}/investigation`,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`API ${r.status}`);return r.json()}).then(setData).catch(e=>setError(e.message)))},[params])
  if(error) return <main><Link href="/" className="back">← Opportunity feed</Link><div className="notice">{error}</div></main>
  if(!data) return <main><div className="eyebrow">Loading investigation…</div></main>
  const {opportunity,trend}=data
  return <main>
    <Link href="/" className="back">← Opportunity feed</Link>
    <section className="investigationHero"><div><span className="pill">{opportunity.type}</span><h1 className="detailTitle">{opportunity.title}</h1><p>{opportunity.thesis}</p></div><div className="scoreBox"><span>Opportunity score</span><strong>{Math.round(opportunity.score)}</strong><small>{Math.round(opportunity.confidence*100)}% confidence</small></div></section>
    <section className="detailGrid">
      <article className="panel"><div className="eyebrow">What changed</div><h2>{trend?.name ?? 'Emerging change'}</h2><p>{trend?.thesis}</p><dl><div><dt>Stage</dt><dd>{trend?.stage}</dd></div><div><dt>Momentum</dt><dd>{trend?Math.round(trend.momentum*100):'—'}%</dd></div><div><dt>Sources</dt><dd>{data.supporting_sources}</dd></div></dl></article>
      <article className="panel"><div className="eyebrow">What could weaken it</div><h2>Counter-thesis</h2>{data.risks.map(r=><p className="risk" key={r}>— {r}</p>)}</article>
    </section>
    <section className="evidenceSection"><div className="sectionTitle"><h2>Evidence trail</h2><span>{data.evidence.length} observations</span></div><div className="evidenceList">{data.evidence.map(e=><article key={e.id}><div><span className="source">{e.source.replaceAll('_',' ')}</span><strong>{e.evidence.title || e.metric.replaceAll('_',' ')}</strong><small>{new Date(e.observed_at).toLocaleString()}</small></div>{e.evidence.url?<a href={e.evidence.url} target="_blank" rel="noreferrer">Source ↗</a>:<span className="meta">{e.metric}</span>}</article>)}</div></section>
  </main>
}
