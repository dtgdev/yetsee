"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import StudyIndependencePanel, { type StudyIndependenceSummary } from "./StudyIndependencePanel";
import StudyQualityPanel, { type StudyQualitySummary } from "./StudyQualityPanel";
import QuestionEvidenceHierarchyPanel, { type QuestionEvidenceHierarchySummary } from "./QuestionEvidenceHierarchyPanel";
import ContradictionIntelligencePanel, { type ContradictionSummary } from "./ContradictionIntelligencePanel";

export default function StudyQualityLoader({investigationId}:{investigationId:string}){
  const [quality,setQuality]=useState<StudyQualitySummary|null>(null);
  const [independence,setIndependence]=useState<StudyIndependenceSummary|null>(null);
  const [hierarchy,setHierarchy]=useState<QuestionEvidenceHierarchySummary|null>(null);
  const [contradiction,setContradiction]=useState<ContradictionSummary|null>(null);
  const [qualityStatus,setQualityStatus]=useState<"loading"|"ready"|"error">("loading");
  const [independenceStatus,setIndependenceStatus]=useState<"loading"|"ready"|"error">("loading");
  const [hierarchyStatus,setHierarchyStatus]=useState<"loading"|"ready"|"error">("loading");
  const [contradictionStatus,setContradictionStatus]=useState<"loading"|"ready"|"error">("loading");

  useEffect(()=>{
    let active=true;
    apiGet<StudyQualitySummary>(`/api/v1/investigations/${investigationId}/study-quality`)
      .then(result=>{if(active){setQuality(result);setQualityStatus("ready")}})
      .catch(()=>{if(active)setQualityStatus("error")});
    apiGet<StudyIndependenceSummary>(`/api/v1/investigations/${investigationId}/study-independence`)
      .then(result=>{if(active){setIndependence(result);setIndependenceStatus("ready")}})
      .catch(()=>{if(active)setIndependenceStatus("error")});
    apiGet<QuestionEvidenceHierarchySummary>(`/api/v1/investigations/${investigationId}/question-evidence-hierarchy`)
      .then(result=>{if(active){setHierarchy(result);setHierarchyStatus("ready")}})
      .catch(()=>{if(active)setHierarchyStatus("error")});
    apiGet<ContradictionSummary>(`/api/v1/investigations/${investigationId}/contradiction-intelligence`)
      .then(result=>{if(active){setContradiction(result);setContradictionStatus("ready")}})
      .catch(()=>{if(active)setContradictionStatus("error")});
    return()=>{active=false};
  },[investigationId]);

  return <>
    {qualityStatus==="loading"&&<section className="studyQuality studyQualityLoading"><span className="studyQualityEyebrow">Derived evidence intelligence</span><p>Loading study-quality assessment…</p></section>}
    {qualityStatus==="error"&&<section className="studyQuality studyQualityUnavailable"><span className="studyQualityEyebrow">Derived evidence intelligence</span><h2>Study Quality Intelligence</h2><p>Study-quality assessment is temporarily unavailable. Canonical evidence and synthesis remain unchanged.</p></section>}
    {qualityStatus==="ready"&&quality&&<StudyQualityPanel summary={quality}/>} 

    {hierarchyStatus==="loading"&&<section className="questionHierarchy"><span className="questionHierarchyEyebrow">Question-specific evidence intelligence</span><p>Loading question-specific evidence hierarchy…</p></section>}
    {hierarchyStatus==="error"&&<section className="questionHierarchy"><span className="questionHierarchyEyebrow">Question-specific evidence intelligence</span><h2>Evidence Hierarchy for This Question</h2><p>Question-specific hierarchy is temporarily unavailable. Generic study quality and canonical evidence remain unchanged.</p></section>}
    {hierarchyStatus==="ready"&&hierarchy&&<QuestionEvidenceHierarchyPanel summary={hierarchy}/>} 

    {independenceStatus==="loading"&&<section className="studyIndependence studyIndependenceLoading"><span className="studyIndependenceEyebrow">Derived replication intelligence</span><p>Loading study-independence assessment…</p></section>}
    {independenceStatus==="error"&&<section className="studyIndependence studyIndependenceUnavailable"><span className="studyIndependenceEyebrow">Derived replication intelligence</span><h2>Study Independence</h2><p>Study-independence assessment is temporarily unavailable. Canonical evidence remains unchanged.</p></section>}
    {independenceStatus==="ready"&&independence&&<StudyIndependencePanel summary={independence}/>} 
    {contradictionStatus==="loading"&&<section className="contradictionIntel"><span className="contradictionIntelEyebrow">Derived consistency intelligence</span><p>Loading contradiction assessment…</p></section>}
    {contradictionStatus==="error"&&<section className="contradictionIntel"><span className="contradictionIntelEyebrow">Derived consistency intelligence</span><h2>Contradiction Intelligence</h2><p>Contradiction assessment is temporarily unavailable. Canonical evidence remains unchanged.</p></section>}
    {contradictionStatus==="ready"&&contradiction&&<ContradictionIntelligencePanel summary={contradiction}/>} 
  </>;
}
