import { useEffect, useState } from 'react'
import { ArrowRight, CalendarDays, ChevronRight, Clock3, KeyRound, MapPin, Sparkles, UsersRound } from 'lucide-react'
import { api, type Announcement, type Event } from '../lib/api'
import { Badge, Button, Card, PageTitle } from '../components/ui'

type Data = {
  clubs: { id:number; name:string; abbreviation:string; category:string; role_name:string; member_count:number }[]
  upcoming_events: Event[]
  announcements: Announcement[]
  notifications: { id:number; message:string; read_at:string|null }[]
}
const colors = ['violet','coral','mint','sun']

export function Dashboard({onNavigate}:{onNavigate:(key:string)=>void}) {
  const [data,setData] = useState<Data|null>(null)
  const [error,setError] = useState('')
  useEffect(()=>{api<Data>('/dashboard/').then(setData).catch(e=>setError(e.message))},[])
  const greet = new Intl.DateTimeFormat('en',{weekday:'long',month:'long',day:'numeric',timeZone:'Asia/Kathmandu'}).format(new Date())

  return <>
    <PageTitle eyebrow={greet} title="A little more connected." description="Here’s what’s happening in your campus community." action={<Button variant="outline" onClick={()=>onNavigate('redeem-code')}><KeyRound size={16}/> Use join code</Button>}/>
    {error&&<p className="error-text">{error}</p>}
    <div className="section-heading"><div><h2>Your clubs</h2><p className="muted">Communities you’re a part of</p></div></div>
    <div className="club-grid">
      {data?.clubs.length ? data.clubs.slice(0,3).map((club,i)=><Card key={club.id} className="club-card">
        <div className={`club-symbol symbol-${colors[i%4]}`}>{club.abbreviation.slice(0,2)}</div>
        <div className="club-card-copy"><Badge color={colors[i%4]}>{club.category||'Community'}</Badge><h3>{club.name}</h3><p>{club.member_count} members <span>·</span> {club.role_name}</p></div>
        <button className="round-arrow" onClick={()=>onNavigate(`club:${club.id}`)} aria-label={`Open ${club.name}`}><ChevronRight size={19}/></button>
      </Card>) : <Card className="empty-card"><div className="empty-icon"><UsersRound/></div><h3>No club memberships yet</h3><p>Have a join code? Use it to join one of your college clubs.</p><Button variant="outline" onClick={()=>onNavigate('redeem-code')}><KeyRound size={16}/> Use join code</Button></Card>}
    </div>
    <div className="home-columns">
      <section>
        <div className="section-heading compact"><div><h2>Coming up</h2><p className="muted">Events from your clubs</p></div><button className="inline-link" onClick={()=>onNavigate('events')}>All events <ArrowRight size={15}/></button></div>
        <Card className="list-card">{data?.upcoming_events.length ? data.upcoming_events.slice(0,4).map((event,i)=><div className="event-row" key={event.id}>
          <div className={`date-tile date-${colors[i%4]}`}><span>{new Date(event.starts_at).toLocaleDateString('en',{month:'short',timeZone:'Asia/Kathmandu'})}</span><b>{new Date(event.starts_at).toLocaleDateString('en',{day:'2-digit',timeZone:'Asia/Kathmandu'})}</b></div>
          <div className="event-info"><h3>{event.title}</h3><p>{event.club_name}</p><div className="event-meta"><span><Clock3 size={13}/>{new Date(event.starts_at).toLocaleTimeString('en',{hour:'numeric',minute:'2-digit',timeZone:'Asia/Kathmandu'})}</span><span><MapPin size={13}/>{event.venue||'Venue to be announced'}</span></div></div><ChevronRight size={17} className="row-chevron"/>
        </div>) : <div className="quiet-empty"><CalendarDays/><span>No upcoming events yet.<br/>Check back soon!</span></div>}</Card>
      </section>
      <section>
        <div className="section-heading compact"><div><h2>Latest notes</h2><p className="muted">News from your clubs</p></div><button className="inline-link" onClick={()=>onNavigate('announcements')}>All news <ArrowRight size={15}/></button></div>
        <Card className="list-card notes-card">{data?.announcements.length ? data.announcements.slice(0,4).map((item,i)=><div className="note-row" key={item.id}>
          <div className={`note-mark note-${colors[i%4]}`}>✳</div><div><span className="note-club">{item.club_name}</span><h3>{item.title}</h3><p>{item.content.slice(0,88)}{item.content.length>88?'…':''}</p><small>{item.published_at?new Date(item.published_at).toLocaleDateString():''}</small></div>
        </div>) : <div className="quiet-empty"><Sparkles/><span>Nothing new in your clubs.<br/>All caught up!</span></div>}</Card>
      </section>
    </div>
  </>
}
