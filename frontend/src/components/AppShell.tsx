import { useState } from 'react'
import { Bell, CalendarDays, ChevronDown, Compass, LayoutDashboard, LogOut, Menu, Settings2, UsersRound, X, Megaphone, ShieldCheck } from 'lucide-react'
import type { User } from '../lib/api'
import { Brand } from './Brand'

const links=[['overview','Overview',LayoutDashboard],['clubs','Discover clubs',Compass],['events','Events & calendar',CalendarDays],['announcements','Announcements',Megaphone],['members','My memberships',UsersRound]] as const

export function AppShell({user,page,onNavigate,onLogout,children,unread=0}:{user:User;page:string;onNavigate:(key:string)=>void;onLogout:()=>void;children:React.ReactNode;unread?:number}) {
  const [open,setOpen]=useState(false)
  return <div className="app-frame">
    <aside className={`sidebar ${open?'sidebar-open':''}`}>
      <div className="sidebar-brand"><Brand compact/><button className="mobile-close" onClick={()=>setOpen(false)} aria-label="Close menu"><X size={20}/></button></div>
      <div className="side-label">YOUR SPACE</div>
      <nav>{links.map(([key,label,Icon])=><button key={key} onClick={()=>{onNavigate(key);setOpen(false)}} className={`nav-link ${page===key?'active':''}`}><Icon size={19}/><span>{label}</span>{key==='announcements'&&unread>0&&<i className="nav-dot"/>}</button>)}</nav>
      {user.is_admin&&<><div className="side-label side-label-gap">ADMINISTRATION</div><nav>
        <button className={`nav-link ${page==='admin'?'active':''}`} onClick={()=>{onNavigate('admin');setOpen(false)}}><ShieldCheck size={19}/><span>Admin dashboard</span></button>
        <button className={`nav-link ${page==='join-codes'?'active':''}`} onClick={()=>{onNavigate('join-codes');setOpen(false)}}><Settings2 size={19}/><span>Join codes</span></button>
      </nav></>}
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon">✳</div><b>Your campus community</b><p>Find clubs and updates in one place.</p><button onClick={()=>onNavigate('clubs')}>Explore clubs <span>↗</span></button></div>
        <div className="profile"><div className="profile-avatar">{(user.first_name||user.username).slice(0,1).toUpperCase()}</div><div className="profile-text"><b>{user.name}</b><span>{user.is_admin?'Administrator':'Student'}</span></div><button className="icon-button" onClick={onLogout} title="Log out"><LogOut size={17}/></button></div>
      </div>
    </aside>
    {open&&<button className="sidebar-backdrop" onClick={()=>setOpen(false)} aria-label="Close menu"/>}
    <main className="main-shell"><header className="topbar"><div className="topbar-left"><button className="menu-button" onClick={()=>setOpen(true)} aria-label="Open menu"><Menu size={20}/></button><span className="crumb">SXC Clubs <span>/</span> {links.find(l=>l[0]===page)?.[1]??(page==='admin'?'Admin dashboard':'Join codes')}</span></div>
      <div className="topbar-right"><button className="notification-button" onClick={()=>onNavigate('notifications')} aria-label="Notifications"><Bell size={19}/>{unread>0&&<i/>}</button><div className="top-user"><div className="profile-avatar small">{(user.first_name||user.username).slice(0,1).toUpperCase()}</div><span>{user.first_name||user.username}</span><ChevronDown size={15}/></div></div>
    </header><div className="page-content">{children}</div></main>
  </div>
}
