import { useEffect, useState } from 'react'
import { ArrowDownRight, ArrowUpRight, Building2, CalendarDays, Plus, UserPlus, UsersRound, Archive } from 'lucide-react'
import { api, json, type Club } from '../lib/api'
import { Badge, Button, Card, Input, PageTitle } from '../components/ui'
import { PermissionPicker, type PermissionGroups } from '../components/PermissionPicker'

type AccountForm={username:string;email:string;first_name:string;last_name:string;password:string;club:string;role_name:string}
const icons=[Building2,UsersRound,UsersRound,CalendarDays]
const labels=['Active clubs','Students','Memberships','Upcoming events']
const blankAccount:AccountForm={username:'',email:'',first_name:'',last_name:'',password:'',club:'',role_name:'Member'}

export function Admin({onNavigate}:{onNavigate:(p:string)=>void}){
  const [stats,setStats]=useState<any>(null);const [clubs,setClubs]=useState<Club[]>([]);const [students,setStudents]=useState<any[]>([])
  const [catalog,setCatalog]=useState<PermissionGroups>({});const [showClub,setShowClub]=useState(false);const [showAccount,setShowAccount]=useState(false)
  const [clubForm,setClubForm]=useState({name:'',abbreviation:'',category:'',description:''});const [account,setAccount]=useState<AccountForm>(blankAccount)
  const [permissions,setPermissions]=useState<string[]>([]);const [error,setError]=useState('');const [notice,setNotice]=useState('')
  function refresh(){
    api<any>('/admin/stats/').then(setStats).catch(e=>setError(e.message))
    api<any>('/clubs/').then(r=>{const list=Array.isArray(r)?r:r.results;setClubs(list);if(list[0])setAccount(a=>({...a,club:a.club||String(list[0].id)}))}).catch(()=>{})
    api<any>('/admin/users/').then(r=>setStudents(r.results??r)).catch(()=>{})
    api<PermissionGroups>('/permissions/').then(setCatalog).catch(()=>{})
  }
  useEffect(()=>{refresh()},[])
  async function createClub(e:React.FormEvent){e.preventDefault();setError('');setNotice('');try{await api('/clubs/',json('POST',clubForm));setShowClub(false);setClubForm({name:'',abbreviation:'',category:'',description:''});setNotice('Club created.');refresh()}catch(e){setError((e as Error).message)}}
  async function createAccount(e:React.FormEvent){e.preventDefault();setError('');setNotice('');try{const result=await api<any>('/admin/accounts/',json('POST',{...account,club:Number(account.club),permissions}));setNotice(`Created the ${result.membership.role_name} account for ${result.user.name}. Share the sign-in details directly with the student.`);setStudents(current=>[result.user,...current]);setAccount({...blankAccount,club:account.club});setPermissions([])}catch(e){setError((e as Error).message)}}
  async function archiveClub(club:Club){setError('');try{await api(`/clubs/${club.id}/`,json('DELETE'));refresh()}catch(e){setError((e as Error).message)}}
  const values=stats?[stats.total_clubs,stats.total_students,stats.total_memberships,stats.upcoming_events]:['—','—','—','—']
  return <>
    <PageTitle eyebrow="ADMINISTRATION" title="College dashboard" description="Manage clubs, student accounts and access." action={<div className="admin-page-actions"><Button variant="outline" onClick={()=>{setShowAccount(!showAccount);setShowClub(false)}}><UserPlus size={16}/> Create club account</Button><Button onClick={()=>{setShowClub(!showClub);setShowAccount(false)}}><Plus size={17}/> New club</Button></div>}/>
    {error&&<p className="error-text">{error}</p>}{notice&&<p className="success-text admin-notice">{notice}</p>}
    <div className="stats-grid">{labels.map((label,i)=>{const Icon=icons[i];return <Card className={`stat-card stat-${['violet','coral','mint','sun'][i]}`} key={label}><div className="stat-top"><span>{label}</span><Icon size={19}/></div><b>{values[i]}</b><span className="stat-caption">SXC Clubs</span></Card>})}</div>
    {showClub&&<Card className="admin-form-card"><h3>Create a club</h3><form onSubmit={createClub} className="admin-create-form"><Input required placeholder="Club name" value={clubForm.name} onChange={e=>setClubForm({...clubForm,name:e.target.value})}/><Input required placeholder="Abbreviation" value={clubForm.abbreviation} onChange={e=>setClubForm({...clubForm,abbreviation:e.target.value.toUpperCase()})}/><Input placeholder="Category" value={clubForm.category} onChange={e=>setClubForm({...clubForm,category:e.target.value})}/><Input placeholder="Short description" value={clubForm.description} onChange={e=>setClubForm({...clubForm,description:e.target.value})}/><Button type="submit">Save club</Button></form></Card>}
    {showAccount&&<Card className="account-create-card"><div className="account-create-heading"><div className="code-icon"><UserPlus/></div><div><h2>Create a student club account</h2><p>Creates the student login and club membership together.</p></div></div><form className="account-form" onSubmit={createAccount}>
      <label>First name<Input required value={account.first_name} onChange={e=>setAccount({...account,first_name:e.target.value})}/></label><label>Last name<Input value={account.last_name} onChange={e=>setAccount({...account,last_name:e.target.value})}/></label>
      <label>Username<Input required value={account.username} onChange={e=>setAccount({...account,username:e.target.value})}/></label><label>Email<Input required type="email" value={account.email} onChange={e=>setAccount({...account,email:e.target.value})}/></label>
      <label>Temporary password<Input required type="password" minLength={10} value={account.password} onChange={e=>setAccount({...account,password:e.target.value})}/></label><label>Club<select className="input" required value={account.club} onChange={e=>setAccount({...account,club:e.target.value})}>{clubs.filter(c=>c.status==='active').map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
      <label>Role name<Input required value={account.role_name} onChange={e=>setAccount({...account,role_name:e.target.value})} placeholder="Member"/></label>
      <div className="account-permissions"><div><b>Permissions</b><span>Choose access independently from the role.</span></div><PermissionPicker groups={catalog} value={permissions} onChange={setPermissions}/></div>
      <div className="account-submit"><p className="muted">The initial password is set by the administrator. Students sign in separately.</p><Button type="submit"><UserPlus size={16}/> Create account</Button></div>
    </form></Card>}
    <div className="admin-grid"><section><div className="section-heading compact"><div><h2>Clubs</h2><p className="muted">Manage the campus directory</p></div><button className="inline-link" onClick={()=>onNavigate('join-codes')}>Join codes <ArrowUpRight size={15}/></button></div><Card className="admin-clubs">{clubs.map((club,i)=><div className="admin-club-row" key={club.id}><div className={`club-symbol symbol-${['violet','coral','mint','sun'][i%4]}`}>{club.abbreviation.slice(0,2)}</div><div className="admin-club-info"><b>{club.name}</b><span>{club.category||'Campus community'} · {club.member_count??0} members</span></div><Badge color={club.status==='active'?'mint':'sun'}>{club.status}</Badge><button className="row-action" onClick={()=>onNavigate(`club:${club.id}`)} title="View club"><ArrowUpRight size={17}/></button>{club.status==='active'&&<button className="row-action archive-action" onClick={()=>archiveClub(club)} title="Archive club"><Archive size={16}/></button>}</div>)}</Card></section>
    <section><div className="section-heading compact"><div><h2>Recent activity</h2><p className="muted">Recent platform changes</p></div></div><Card className="activity-card">{stats?.recent_activity?.length?stats.recent_activity.slice(0,7).map((a:any)=><div className="activity-row" key={a.id}><div className="activity-icon"><ArrowDownRight size={16}/></div><div><b>{a.summary}</b><span>{a.actor_name} {a.club_name&&`· ${a.club_name}`}</span></div><small>{new Date(a.created_at).toLocaleDateString()}</small></div>):<div className="quiet-empty"><span>No recent activity yet.</span></div>}</Card></section></div>
    <section className="student-account-section"><div className="section-heading compact"><div><h2>Student accounts</h2><p className="muted">Administrators and students use separate sign-in pages.</p></div></div><Card className="student-account-list">{students.slice(0,8).map(student=><div className="student-account-row" key={student.id}><div className="profile-avatar small">{(student.name||student.username).slice(0,1).toUpperCase()}</div><b>{student.name||student.username}</b><span>{student.email}</span><Badge color="mint">Student</Badge></div>)}{!students.length&&<div className="quiet-empty">No student accounts yet.</div>}</Card></section>
    <Card className="admin-callout"><div><b>Manage club invitations</b><p>Create permission-based join codes for student memberships.</p><Button variant="outline" onClick={()=>onNavigate('join-codes')}>Manage join codes <ArrowUpRight size={15}/></Button></div></Card>
  </>
}
