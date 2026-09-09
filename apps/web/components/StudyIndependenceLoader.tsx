"use client";

import {useEffect,useState} from "react";
import {apiGet} from "../lib/api";
import StudyIndependencePanel,{type StudyIndependenceSummary} from "./StudyIndependencePanel";

export default function StudyIndependenceLoader({investigationId}:{investigationId:string}){
  const [summary,setSummary]=useState<StudyIndependenceSummary|null>(null);
  const [status,setStatus]=useState<"loading"|"ready"|"error">("loading");
  useEffect(()=>{
    let active=true;
    apiGet<StudyIndependenceSummary>(`/api/v1/investigations/${investigationId}/study-independence`).then(result=>{if(active){setSummary(result);setStatus("ready")}}).catch(()=>{if(active)setStatus("error")});
    return()=>{active=false};
  },[investigationId]);
  if(status==="loading")return <section className="studyIndependence studyIndependenceLoading"><span className="studyIndependenceEyebrow">Derived replication intelligence</span><p>Loading study-independence assessment…</p></section>;
  if(status==="error")return <section className="studyIndependence studyIndependenceUnavailable"><span className="studyIndependenceEyebrow">Derived replication intelligence</span><h2>Study Independence</h2><p>Study-independence assessment is temporarily unavailable. Canonical evidence remains unchanged.</p></section>;
  return summary?<StudyIndependencePanel summary={summary}/>:null;
}
