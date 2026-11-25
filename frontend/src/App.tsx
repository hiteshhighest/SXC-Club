import { useEffect, useState } from 'react'
import { Bell, CheckCheck } from 'lucide-react'
import { AppShell } from './components/AppShell'
import { Brand } from './components/Brand'
import { Login } from './components/Login'
import { Button, Card, Input, PageTitle } from './components/ui'
import { api, json, type User } from './lib/api'
import { Dashboard } from './pages/Dashboard'
import { ClubDetail } from './pages/ClubDetail'
import { Events } from './pages/Events'
import { Announcements } from './pages/Announcements'
import { Members } from './pages/Members'
import { Admin } from './pages/Admin'
import { JoinCodes } from './pages/JoinCodes'
import { RedeemJoinCode } from './pages/RedeemJoinCode'

function Notifications(){
  const [rows,setRows]=useState<any[]>([])
  const load=()=>api<any>('/notifications/').then(r=>setRows(r.results??r))
  useEffect(()=>{load()},[])
  async function read(id:number){await api(`/notifications/${id}/read/`,json('POST'));load()}
  return <><PageTitle eyebrow="UPDATES" title="Notifications" description="Recent updates from your clubs." action={<Button variant="outline" onClick={()=>api('/notifications/read_all/',json('POST')).then(load)}><CheckCheck size={16}/> Mark all read</Button>}/><Card className="notification-list">{rows.length?rows.map(n=><button className={`notification-row ${n.read_at?'':'unread'}`} key={n.id} onClick={()=>read(n.id)}><div className="notification-icon"><Bell size={17}/></div><div><b>{n.message}</b><span>{new Date(n.created_at).toLocaleString()}</span></div>{!n.read_at&&<i/>}</button>):<div className="quiet-empty"><span>You’re all caught up.</span></div>}</Card></>
}

function ResetPassword(){
  const params=new URLSearchParams(location.search); const [password,setPassword]=useState(''); const [message,setMessage]=useState(''); const [error,setError]=useState('')
  async function submit(e:React.FormEvent){e.preventDefault();try{const r=await api<{detail:string}>('/auth/password-reset/confirm/',json('POST',{uid:params.get('reset_uid'),token:params.get('reset_token'),password}));setMessage(r.detail);history.replaceState({},'',location.pathname)}catch(e){setError((e as Error).message)}}
  return <main className="simple-login-page"><section className="simple-login-card"><Brand/><span className="eyebrow">ACCOUNT RECOVERY</span><h1>Choose a new password</h1><p className="muted">Use a strong password you haven’t used here before.</p><form className="form-stack" onSubmit={submit}><label>New password<Input type="password" required minLength={10} value={password} onChange={e=>setPassword(e.target.value)}/></label>{error&&<p className="error-text">{error}</p>}{message&&<p className="success-text">{message}</p>}<Button type="submit" className="w-full justify-center">Update password</Button></form></section></main>
}

export function App(){
  const mode: 'student'|'admin' = location.pathname.replace(/\/$/,'')==='/admin'?'admin':'student'
  const [user,setUser]=useState<User|null>(null); const [loading,setLoading]=useState(true); const [page,setPage]=useState(mode==='admin'?'admin':'overview'); const [unread,setUnread]=useState(0)
  const resetMode=new URLSearchParams(location.search).has('reset_uid')
  useEffect(()=>{if(resetMode){setLoading(false);return}api<User>(mode==='admin'?'/auth/admin/me/':'/auth/student/me/').then(setUser).catch(()=>setUser(null)).finally(()=>setLoading(false))},[mode,resetMode])
  useEffect(()=>{if(user)api<any>('/notifications/').then(r=>{const rows=r.results??r;setUnread(rows.filter((n:any)=>!n.read_at).length)}).catch(()=>{})},[user,page])
  async function logout(){await api('/auth/logout/',json('POST')).catch(()=>{});setUser(null);setPage(mode==='admin'?'admin':'overview')}
  if(loading)return <div className="loading-screen"><Brand/><span>Loading…</span></div>
  if(resetMode)return <ResetPassword/>
  if(!user)return <Login mode={mode} onLogin={u=>{setUser(u);if(mode==='admin')setPage('admin')}}/>
  const go=(key:string)=>setPage(key)
  let content
  if(page.startsWith('club:'))content=<ClubDetail id={page.split(':')[1]} currentUserId={user.id} onBack={()=>go(mode==='admin'?'admin':'overview')}/>
  else switch(page){
    case 'overview':content=<Dashboard onNavigate={go}/>;break
    case 'redeem-code':content=<RedeemJoinCode onNavigate={go}/>;break
    case 'events':content=<Events/>;break
    case 'announcements':content=<Announcements isAdmin={!!user.is_admin}/>;break
    case 'members':content=<Members/>;break
    case 'admin':content=user.is_admin?<Admin onNavigate={go}/>:<Dashboard onNavigate={go}/>;break
    case 'join-codes':content=user.is_admin?<JoinCodes/>:<Dashboard onNavigate={go}/>;break
    case 'notifications':content=<Notifications/>;break
    default:content=<Dashboard onNavigate={go}/>
  }
  return <AppShell user={user} page={page} onNavigate={go} onLogout={logout} unread={unread}>{content}</AppShell>
}
