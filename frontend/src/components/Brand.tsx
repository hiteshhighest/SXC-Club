import { useState } from 'react'
import { Compass } from 'lucide-react'

export function Brand({compact=false}:{compact?:boolean}) {
  const [logoFailed,setLogoFailed]=useState(false)
  return <div className={`brand-lockup ${compact?'compact':''}`}>
    {!logoFailed ? <img className="brand-logo" src="/sxc-logo.png" alt="St. Xavier’s College logo" onError={()=>setLogoFailed(true)} /> : <span className="brand-mark"><Compass size={20}/></span>}
    <span className="brand-name">SXC <b>Clubs</b></span>
  </div>
}
