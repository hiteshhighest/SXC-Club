import { useEffect,useState } from 'react'
import { ArrowLeft,CalendarDays,MapPin } from 'lucide-react'
import { api,type Club,type Event,type Announcement } from '../lib/api'
import { Badge,Button,Card,PageTitle } from '../components/ui'
import { ClubChat } from './ClubChat'

type Detail={club:Club;my_membership:any;can_chat:boolean;executives:any[];members_count:number;upcoming_events:Event[];announcements:Announcement[]}

export function ClubDetail({id,onBack,currentUserId}:{id:string;onBack:()=>void;currentUserId:number}) {
  const [detail,setDetail]=useState<Detail|null>(null)
  const [error,setError]=useState('')
  useEffect(()=>{
    let active=true
    api<Detail>(`/clubs/${id}/dashboard/`).then(data=>{if(active)setDetail(data)}).catch(e=>{if(active)setError(e.message)})
    return ()=>{active=false}
  },[id])
  if(!detail)return <div className="loading-view">{error||'Loading club information…'}</div>
  const {club}=detail
  return <>
    <button className="back-link" onClick={onBack}><ArrowLeft size={16}/> Back</button>
    <PageTitle eyebrow={club.category||'CLUB'} title={club.name} description={club.description||'Club information, events and announcements.'} action={<Button variant="outline" onClick={()=>navigator.clipboard?.writeText(club.name)}>Share club</Button>}/>
    <div className="club-detail-grid">
      <div className="club-detail-main">
        <section><div className="section-heading compact"><div><h2>Upcoming events</h2><p className="muted">What this club is up to</p></div></div>
          <Card className="list-card">{detail.upcoming_events.length?detail.upcoming_events.map(event=><div className="event-row" key={event.id}><div className="date-tile date-violet"><span>{new Date(event.starts_at).toLocaleDateString('en',{month:'short',timeZone:'Asia/Kathmandu'})}</span><b>{new Date(event.starts_at).toLocaleDateString('en',{day:'2-digit',timeZone:'Asia/Kathmandu'})}</b></div><div className="event-info"><h3>{event.title}</h3><p><MapPin size={13}/>{event.venue||'Venue to be announced'}</p></div></div>):<div className="quiet-empty"><CalendarDays/><span>No events announced yet.</span></div>}</Card>
        </section>
        <section className="club-announcements"><div className="section-heading compact"><div><h2>Latest announcements</h2></div></div>
          <Card className="list-card">{detail.announcements.length?detail.announcements.map(item=><div className="note-row" key={item.id}><div className="note-mark note-coral">✳</div><div><span className="note-club">{item.author_name}</span><h3>{item.title}</h3><p>{item.content}</p></div></div>):<div className="quiet-empty">No announcements just yet.</div>}</Card>
        </section>
        {detail.can_chat&&<ClubChat clubId={club.id} currentUserId={currentUserId}/>}
      </div>
      <aside><Card className="about-card"><h3>About the club</h3><p>{club.description||'A welcoming community on campus.'}</p><div className="about-divider"/><span className="side-label">CLUB DETAILS</span><div className="about-detail"><span>Category</span><b>{club.category||'Student community'}</b></div><div className="about-detail"><span>Members</span><b>{detail.members_count}</b></div>{detail.my_membership&&<><div className="about-divider"/><span className="side-label">YOUR MEMBERSHIP</span><div className="about-detail"><span>Your role</span><b>{detail.my_membership.role_name}</b></div><Badge color="mint">Active member</Badge></>}</Card>{!detail.my_membership&&!detail.can_chat&&<Card className="join-card"><span className="join-spark">✳</span><h3>Want to join?</h3><p>Ask a club executive for a join code to become a member.</p></Card>}</aside>
    </div>
  </>
}
