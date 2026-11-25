import { useEffect, useState } from 'react'
import { Copy, KeyRound, Plus, RotateCcw } from 'lucide-react'
import { api, json, type Club } from '../lib/api'
import { Button, Card, Input, PageTitle } from '../components/ui'
import { PermissionPicker, type PermissionGroups } from '../components/PermissionPicker'

const permissionKeys={
  Events:['events.view','events.create','events.edit','events.delete','events.publish','events.unpublish'],
  Announcements:['announcements.view','announcements.create','announcements.edit','announcements.delete','announcements.publish','announcements.unpublish'],
  Membership:['members.view','members.invite','members.remove','members.change_role'],
  'Club tools':['club.edit','club.resources','join_codes.generate','join_codes.revoke','executives.permissions'],
}
const groups:PermissionGroups=Object.fromEntries(Object.entries(permissionKeys).map(([group,keys])=>[group,keys.map(key=>({key,label:key.split('.').at(-1)!.replaceAll('_',' ')}))]))

export function JoinCodes(){
  const [clubs,setClubs]=useState<Club[]>([]);const [codes,setCodes]=useState<any[]>([])
  const [form,setForm]=useState({club:'',role_name:'Member',max_uses:'',expires_at:''})
  const [perms,setPerms]=useState<string[]>([]);const [generated,setGenerated]=useState('');const [error,setError]=useState('')
  const load=()=>{
    api<any>('/clubs/').then(r=>{const list=Array.isArray(r)?r:r.results;setClubs(list);if(list[0])setForm(f=>({...f,club:f.club||String(list[0].id)}))})
    api<any>('/join-codes/').then(setCodes).catch(e=>setError(e.message))
  }
  useEffect(()=>{load()},[])
  async function create(e:React.FormEvent){e.preventDefault();setError('');try{const r=await api<any>('/join-codes/create/',json('POST',{club:Number(form.club),role_name:form.role_name,permissions:perms,max_uses:form.max_uses?Number(form.max_uses):null,expires_at:form.expires_at||null}));setGenerated(r.code);load()}catch(e){setError((e as Error).message)}}
  async function revoke(id:number){try{await api(`/join-codes/${id}/revoke/`,json('POST'));load()}catch(e){setError((e as Error).message)}}
  return <>
    <PageTitle eyebrow="ACCESS" title="Join codes" description="Create a code for a club role, then choose permissions in sections or all at once."/>
    <div className="join-layout">
      <Card className="code-form-card"><div className="form-heading"><div className="code-icon"><KeyRound/></div><div><h2>Create a join code</h2><p>Role names and permissions are set independently.</p></div></div>
        <form onSubmit={create}>
          <label>Club<select className="input" required value={form.club} onChange={e=>setForm({...form,club:e.target.value})}><option value="">Select a club</option>{clubs.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
          <label>Role name<Input required value={form.role_name} onChange={e=>setForm({...form,role_name:e.target.value})} placeholder="e.g. Event coordinator"/></label>
          <div className="code-two-col"><label>Maximum uses <span className="optional">Optional</span><Input type="number" min="1" value={form.max_uses} onChange={e=>setForm({...form,max_uses:e.target.value})} placeholder="Unlimited"/></label><label>Expiry date <span className="optional">Optional</span><Input type="datetime-local" value={form.expires_at} onChange={e=>setForm({...form,expires_at:e.target.value})}/></label></div>
          <div className="permission-heading"><div><b>Permissions</b><span>Use Select all or choose individual sections.</span></div></div>
          <PermissionPicker groups={groups} value={perms} onChange={setPerms}/>
          {error&&<p className="error-text">{error}</p>}
          {generated&&<div className="generated-code"><span>New code — copy it now; it is shown only once.</span><code>{generated}</code><Button variant="outline" onClick={()=>navigator.clipboard?.writeText(generated)}><Copy size={15}/> Copy code</Button></div>}
          <Button type="submit" className="w-full justify-center"><Plus size={17}/> Generate join code</Button>
        </form>
      </Card>
      <section><div className="section-heading compact"><div><h2>Active & past codes</h2><p className="muted">The full code is shown once when created.</p></div><button className="inline-link" onClick={load}><RotateCcw size={15}/> Refresh</button></div>
        <div className="code-list">{codes.length?codes.map(c=><Card className="code-row" key={c.id}><div className="code-row-icon"><KeyRound size={18}/></div><div className="code-row-main"><b>{c.role_name} <span>· {c.club_name}</span></b><small>•••• {c.code_hint} · {c.uses}{c.max_uses?` / ${c.max_uses}`:' uses'}</small><div className="code-perms">{c.permissions.slice(0,3).map((p:string)=><span key={p}>{p.split('.').at(-1)?.replaceAll('_',' ')}</span>)}{c.permissions.length>3&&<span>+{c.permissions.length-3}</span>}</div></div>{c.revoked_at?<span className="status-pill archived">Revoked</span>:<Button variant="ghost" onClick={()=>revoke(c.id)}>Revoke</Button>}</Card>):<Card className="quiet-empty"><KeyRound/><span>No join codes yet. Generate one for a club role.</span></Card>}</div>
        <Card className="permission-note"><span>✳</span><p><b>Least access, by design.</b><br/>Members receive only the permissions selected here. Role names never grant access automatically.</p></Card>
      </section>
    </div>
  </>
}
