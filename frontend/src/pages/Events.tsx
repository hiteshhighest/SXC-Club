import { useEffect, useState } from 'react'
import { CalendarDays, Clock3, MapPin } from 'lucide-react'
import { api, json, type Event } from '../lib/api'
import { Badge, Button, Card, Input, PageTitle } from '../components/ui'

type DashboardData = { clubs: { id: number; name: string; permissions: string[] }[]; upcoming_events: Event[] }

function nepalDateKey(value:string) {
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kathmandu',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(value))
  const get=(type:string)=>parts.find(part=>part.type===type)?.value??''
  return `${get('year')}-${get('month')}-${get('day')}`
}

export function Events() {
  const [clubs, setClubs] = useState<DashboardData['clubs']>([])
  const [events, setEvents] = useState<Event[]>([])
  const [compose, setCompose] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ club: '', title: '', starts_at: '', venue: '', description: '', publish: false })
  useEffect(() => {
    api<DashboardData>('/dashboard/').then(data => {
      setClubs(data.clubs)
      setEvents(data.upcoming_events.filter(event => event.status === 'published').sort((a, b) => a.starts_at.localeCompare(b.starts_at)))
    }).catch(error=>setError(error.message))
  }, [])
  const dates = Array.from(new Set(events.map(event => nepalDateKey(event.starts_at)))).sort()
  const nowNepal=new Date(new Date().toLocaleString('en-US',{timeZone:'Asia/Kathmandu'}))
  const currentMonthKey=`${nowNepal.getFullYear()}-${String(nowNepal.getMonth()+1).padStart(2,'0')}`
  const eventClubCount = clubs.filter(club => events.some(event => event.club === club.id)).length
  const createClubs = clubs.filter(club => club.permissions.includes('events.create'))
  async function createEvent(e: React.FormEvent) {
    e.preventDefault(); setError('')
    try {
      const clubId = Number(form.club)
      const created = await api<Event>(`/clubs/${clubId}/events/`, json('POST', { title: form.title, description: form.description, venue: form.venue, starts_at: new Date(`${form.starts_at}:00+05:45`).toISOString() }))
      if (form.publish) await api(`/clubs/${clubId}/events/${created.id}/publish/`, json('POST'))
      if (form.publish) setEvents(current => [...current, { ...created, status: 'published' }].sort((a, b) => a.starts_at.localeCompare(b.starts_at)))
      setCompose(false); setForm({ club: '', title: '', starts_at: '', venue: '', description: '', publish: false })
    } catch (err) { setError((err as Error).message) }
  }
  return <>
    <PageTitle eyebrow="MAKE A PLAN" title="Campus, in motion." description="Meet up, try something new, and make a memory." action={createClubs.length > 0 ? <Button onClick={() => { setForm(f => ({ ...f, club: String(createClubs[0].id) })); setCompose(!compose) }}>＋ Create event</Button> : undefined} />
    {compose && <Card className="compose-card"><h2>Plan something good.</h2><form onSubmit={createEvent} className="compose-form"><label>Club<select className="input" required value={form.club} onChange={e => setForm({ ...form, club: e.target.value })}>{createClubs.map(c => <option value={c.id} key={c.id}>{c.name}</option>)}</select></label><label>Event title<Input required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label><label>Date and time<Input required type="datetime-local" value={form.starts_at} onChange={e => setForm({ ...form, starts_at: e.target.value })} /></label><label>Venue<Input value={form.venue} onChange={e => setForm({ ...form, venue: e.target.value })} /></label><label className="compose-wide">Description<textarea className="input" rows={3} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>{createClubs.find(c => c.id === Number(form.club))?.permissions.includes('events.publish') && <label className="publish-check"><input type="checkbox" checked={form.publish} onChange={e => setForm({ ...form, publish: e.target.checked })} /> Publish as soon as it’s created</label>}{error && <p className="error-text compose-wide">{error}</p>}<Button type="submit">Save event</Button></form></Card>}
    {error&&<p className="error-text" role="alert">{error}</p>}
    <div className="event-calendar-layout"><section className="event-feed">
      <div className="section-heading compact"><div><h2>Upcoming events</h2><p className="muted">Dates and times shown in Nepal time</p></div><Badge color="mint">Asia / Kathmandu · {eventClubCount} clubs</Badge></div>
      {dates.length ? dates.map(date => <section className="date-group" key={date}>
        <div className="date-heading"><span className="date-dot" /><b>{new Date(`${date}T12:00:00+05:45`).toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric',timeZone:'Asia/Kathmandu' })}</b></div>
        {events.filter(event => nepalDateKey(event.starts_at)===date).map((event, i) => <Card className="event-card" key={event.id}>
          <div className={`event-color-bar bar-${['violet', 'coral', 'mint', 'sun'][i % 4]}`} /><div className="event-card-content">
            <div className="event-card-meta"><Badge color={['violet', 'coral', 'mint', 'sun'][i % 4]}>{event.category || event.club_name}</Badge><span><Clock3 size={14} />{new Date(event.starts_at).toLocaleTimeString('en', { hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kathmandu' })}</span></div>
            <h3>{event.title}</h3><p className="event-description">{event.description || 'Come join your campus community.'}</p>
            <div className="event-bottom"><span><MapPin size={15} />{event.venue || 'Venue to be announced'}</span><span className="event-host">Hosted by <b>{event.club_name}</b></span></div>
          </div>
        </Card>)}
      </section>) : <Card className="empty-card"><CalendarDays /><h3>Your calendar is clear</h3><p>Published events from your clubs show up here.</p></Card>}
    </section><aside className="calendar-aside"><Card className="calendar-card">
      <div className="calendar-month"><b>{nowNepal.toLocaleDateString('en', { month: 'long', year: 'numeric' })}</b></div>
      <div className="calendar-grid">{['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => <span className="calendar-week" key={i}>{day}</span>)}
        {Array.from({ length: new Date(nowNepal.getFullYear(),nowNepal.getMonth(),1).getDay() }, (_, i) => <span key={`blank${i}`} />)}
        {Array.from({ length: new Date(nowNepal.getFullYear(), nowNepal.getMonth() + 1, 0).getDate() }, (_, i) => { const day=i+1; const key=`${currentMonthKey}-${String(day).padStart(2,'0')}`; const hasEvent=events.some(event=>nepalDateKey(event.starts_at)===key); return <span className={`${day===nowNepal.getDate()?'today':''} ${hasEvent?'has-event':''}`} key={day}>{day}</span> })}
      </div><div className="calendar-legend"><i /> Event day</div>
    </Card><Card className="calendar-note"><span>✳</span><div><b>Show up as you are.</b><p>Every event is a chance to meet someone new.</p></div></Card></aside></div>
  </>
}
