import { useState } from 'react'
import { ArrowRight, KeyRound } from 'lucide-react'
import { api, json } from '../lib/api'
import { Button, Card, Input, PageTitle } from '../components/ui'

type MembershipResult = { club_name:string; role_name:string }

export function RedeemJoinCode({onNavigate}:{onNavigate:(page:string)=>void}) {
  const [code,setCode]=useState('')
  const [error,setError]=useState('')
  const [joined,setJoined]=useState<MembershipResult|null>(null)
  const [saving,setSaving]=useState(false)

  async function redeem(e:React.FormEvent) {
    e.preventDefault(); setError(''); setSaving(true)
    try {
      const result=await api<MembershipResult>('/join-codes/redeem/',json('POST',{code:code.trim()}))
      setJoined(result); setCode('')
    } catch (e) { setError((e as Error).message) }
    finally { setSaving(false) }
  }

  return <>
    <PageTitle eyebrow="CLUB MEMBERSHIP" title="Join a club" description="Enter the join code shared with you by a club or college administrator."/>
    <Card className="code-form-card redeem-code-card">
      {joined ? <div className="redeem-success">
        <div className="code-icon"><KeyRound/></div>
        <h2>You’re in {joined.club_name}</h2>
        <p>Your membership is active as <b>{joined.role_name}</b>. You can find the club on your overview.</p>
        <Button onClick={()=>onNavigate('overview')}>Go to overview <ArrowRight size={16}/></Button>
        <button className="inline-link" onClick={()=>setJoined(null)}>Redeem another code</button>
      </div> : <>
        <div className="form-heading"><div className="code-icon"><KeyRound/></div><div><h2>Use a join code</h2><p>Your role and access are set by the code creator.</p></div></div>
        <form className="form-stack" onSubmit={redeem}>
          <label>Join code<Input required autoComplete="off" autoCapitalize="characters" value={code} onChange={e=>setCode(e.target.value)} placeholder="Enter your code"/></label>
          {error&&<p className="error-text" role="alert">{error}</p>}
          <Button type="submit" disabled={saving||!code.trim()} className="w-full justify-center">{saving?'Checking code…':'Join club'}</Button>
        </form>
      </>}
    </Card>
  </>
}
