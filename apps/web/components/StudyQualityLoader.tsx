"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import StudyQualityPanel, { type StudyQualitySummary } from "./StudyQualityPanel";

export default function StudyQualityLoader({investigationId}:{investigationId:string}){
  const [summary,setSummary]=useState<StudyQualitySummary|null>(null);
  const [status,setStatus]=useState<"loading"|"ready"|"error">("loading");

  useEffect(()=>{
    let active=true;
    apiGet<StudyQualitySummary>(`/api/v1/investigations/${investigationId}/study-quality`)
      .then(result=>{if(active){setSummary(result);setStatus("ready")}})
      .catch(()=>{if(active)setStatus("error")});
    return()=>{active=false};
  },[investigationId]);

  if(status==="loading") return <section className="studyQuality studyQualityLoading"><span className="studyQualityEyebrow">Derived evidence intelligence</span><p>Loading study-quality assessment…</p></section>;
  if(status==="error") return <section className="studyQuality studyQualityUnavailable"><span className="studyQualityEyebrow">Derived evidence intelligence</span><h2>Study Quality Intelligence</h2><p>Study-quality assessment is temporarily unavailable. Canonical evidence and synthesis remain unchanged.</p></section>;
  return summary?<StudyQualityPanel summary={summary}/>:null;
}
