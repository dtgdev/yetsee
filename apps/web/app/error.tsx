"use client";
import { StudioFrame } from "../components/StudioChrome";
export default function Error({error,reset}:{error:Error;reset:()=>void}){return <StudioFrame><div className="researchWorkspace"><section className="studioErrorState"><span>!</span><div><p className="researchEyebrow">Studio Error</p><h1>Something did not load.</h1><p>{error.message}</p><div><button onClick={()=>reset()}>Try again</button><a href="/">Return home</a></div></div></section></div></StudioFrame>}
