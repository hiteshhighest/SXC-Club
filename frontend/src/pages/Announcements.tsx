import { useEffect, useState } from 'react'
import { Megaphone, Pencil, Plus, Trash2 } from 'lucide-react'
import { api, json, media, type Announcement } from '../lib/api'
import { Badge, Button, Card, Input, PageTitle } from '../components/ui'

type ClubOption = { id:number; name:string; status?:string; permissions:string[] }
type AnnouncementForm = { club:string; title:string; content:string; status:'draft'|'published'|'archived' }
const blankForm:AnnouncementForm = { club:'', title:'', content:'', status:'draft' }
const accents=['violet','coral','mint','sun']

async function fetchAllClubs():Promise<ClubOption[]> {
  const clubs:ClubOption[]=[]; let page=1; let count=Number.POSITIVE_INFINITY
  while(clubs.length<count&&page<=100) {
    const response=await api<any>(`/clubs/?page=${page}`)
    const rows=Array.isArray(response)?response:response.results??[]
    clubs.push(...rows); count=Array.isArray(response)?rows.length:response.count??rows.length; page++
    if(!rows.length)break
  }
  return clubs
}

async function fetchClubAnnouncements(clubId:number):Promise<Announcement[]> {
  const items:Announcement[]=[];let page=1;let count=Number.POSITIVE_INFINITY
  while(items.length<count&&page<=100) {
    const response=await api<any>(`/clubs/${clubId}/announcements/?page=${page}`)
    const rows=response.results??response
    items.push(...rows);count=response.count??rows.length;page++
    if(!rows.length)break
  }
  return items
}

export function Announcements({isAdmin=false}:{isAdmin?:boolean}) {
  const [items,setItems]=useState<Announcement[]>([])
  const [clubs,setClubs]=useState<ClubOption[]>([])
  const [compose,setCompose]=useState(false)
  const [editing,setEditing]=useState<number|null>(null)
  const [form,setForm]=useState<AnnouncementForm>(blankForm)
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(true)
  const [page,setPage]=useState(1)
  const [count,setCount]=useState(0)
  const [filter,setFilter]=useState('all')

  async function load(nextPage=page,nextFilter=filter) {
    setLoading(true); setError('')
    try {
      if(isAdmin) {
        const statusQuery=nextFilter==='all'?'':`&status=${encodeURIComponent(nextFilter)}`
        const [allClubs,response]=await Promise.all([fetchAllClubs(),api<any>(`/admin/announcements/?page=${nextPage}${statusQuery}`)])
        setClubs(allClubs)
        setItems(response.results??response); setCount(response.count??(response.results??response).length); setPage(nextPage)
      } else {
        const data=await api<any>('/dashboard/')
        setClubs(data.clubs)
        const visible=new Map<number,Announcement>()
        const lists:Announcement[][]=await Promise.all((data.clubs??[]).map((club:ClubOption)=>fetchClubAnnouncements(club.id)))
        lists.forEach(items=>items.forEach((item:Announcement)=>visible.set(item.id,item)))
        setItems([...visible.values()].sort((a,b)=>(b.published_at??'').localeCompare(a.published_at??'')))
        setCount(visible.size)
      }
    } catch(e) { setError((e as Error).message) }
    finally { setLoading(false) }
  }
  useEffect(()=>{load(1,filter)},[isAdmin,filter])

  const createClubs=isAdmin?clubs:clubs.filter(club=>club.permissions.includes('announcements.create'))
  const clubFor=(id:number)=>clubs.find(club=>club.id===id)
  const canEdit=(item:Announcement)=>isAdmin||!!clubFor(item.club)?.permissions.includes('announcements.edit')
  const canDelete=(item:Announcement)=>isAdmin||!!clubFor(item.club)?.permissions.includes('announcements.delete')
  const canSetStatus=(clubId:number,status:string)=>isAdmin||!!clubFor(clubId)?.permissions.includes(status==='published'?'announcements.publish':status==='draft'?'announcements.unpublish':'announcements.delete')
  const visibleItems=items.filter(item=>filter==='all'||item.status===filter)

  function openNew() {
    setEditing(null); setError('')
    setForm({...blankForm,club:createClubs[0]?String(createClubs[0].id):''})
    setCompose(true)
  }
  function openEdit(item:Announcement) {
    setEditing(item.id); setError('')
    setForm({club:String(item.club),title:item.title,content:item.content,status:item.status as AnnouncementForm['status']})
    setCompose(true)
  }
  async function save(e:React.FormEvent) {
    e.preventDefault(); setError('')
    try {
      if(isAdmin) {
        const payload={club:Number(form.club),title:form.title,content:form.content,status:form.status}
        if(editing) await api(`/admin/announcements/${editing}/`,json('PATCH',payload))
        else await api('/admin/announcements/',json('POST',payload))
      } else {
        const clubId=Number(form.club)
        if(editing) await api(`/clubs/${clubId}/announcements/${editing}/`,json('PATCH',{title:form.title,content:form.content,status:form.status}))
        else {
          const created=await api<Announcement>(`/clubs/${clubId}/announcements/`,json('POST',{title:form.title,content:form.content}))
          if(form.status==='published') await api(`/clubs/${clubId}/announcements/${created.id}/publish/`,json('POST'))
        }
      }
      setCompose(false);setEditing(null);setForm(blankForm);await load(isAdmin?page:1)
    } catch(e) { setError((e as Error).message) }
  }
  async function deleteItem(item:Announcement) {
    if(!window.confirm(`Delete “${item.title}”? This cannot be undone.`))return
    try {
      if(isAdmin) await api(`/admin/announcements/${item.id}/`,json('DELETE'))
      else await api(`/clubs/${item.club}/announcements/${item.id}/`,json('DELETE'))
      await load(isAdmin?page:1)
    } catch(e) { setError((e as Error).message) }
  }

  return <>
    <PageTitle eyebrow={isAdmin?'COLLEGE ADMINISTRATION':'THE LATEST'} title="Announcements" description={isAdmin?'View and manage announcements across every club.':'Updates and news from your clubs.'} action={createClubs.length>0?<Button onClick={()=>compose?setCompose(false):openNew()}><Plus size={16}/>{compose?'Close':'New announcement'}</Button>:undefined}/>
    {error&&<p className="error-text" role="alert">{error}</p>}
    {compose&&<Card className="compose-card announcement-compose"><h2>{editing?'Edit announcement':'Create an announcement'}</h2><form className="compose-form" onSubmit={save}>
      <label>Club<select className="input" required value={form.club} onChange={e=>setForm({...form,club:e.target.value})}>{createClubs.map(club=><option value={club.id} key={club.id}>{club.name}</option>)}</select></label>
      <label>Title<Input required maxLength={180} value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></label>
      <label className="compose-wide">Message<textarea className="input" rows={5} required maxLength={20000} value={form.content} onChange={e=>setForm({...form,content:e.target.value})}/></label>
      {(isAdmin||canSetStatus(Number(form.club),'published')||canSetStatus(Number(form.club),'draft'))&&<label>Status<select className="input" value={form.status} onChange={e=>setForm({...form,status:e.target.value as AnnouncementForm['status']})}><option value="draft" disabled={!canSetStatus(Number(form.club),'draft')&&form.status!=='draft'}>Save as draft</option><option value="published" disabled={!canSetStatus(Number(form.club),'published')&&form.status!=='published'}>Publish</option>{form.status==='archived'&&<option value="archived">Archived</option>}{isAdmin&&form.status!=='archived'&&<option value="archived">Archive</option>}</select></label>}
      {error&&<p className="error-text compose-wide">{error}</p>}
      <div className="compose-actions"><Button type="submit">{editing?'Save changes':form.status==='published'?'Publish announcement':'Save announcement'}</Button><Button type="button" variant="outline" onClick={()=>{setCompose(false);setEditing(null)}}>Cancel</Button></div>
    </form></Card>}
    <div className="announcement-toolbar"><div className="section-heading compact"><div><h2>{isAdmin?'All club announcements':'Latest updates'}</h2><p className="muted">{isAdmin?`${count} announcements across the college`:'Published updates from your clubs'}</p></div></div>{isAdmin&&<label className="announcement-filter">Status<select className="input" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All statuses</option><option value="published">Published</option><option value="draft">Drafts</option><option value="archived">Archived</option></select></label>}</div>
    {loading?<Card className="quiet-empty">Loading announcements…</Card>:<div className="announcement-list">{visibleItems.length?visibleItems.map((item,i)=><Card className="announcement-card" key={item.id}><div className={`announcement-accent accent-${accents[i%4]}`}/><div className="announcement-content"><div className="announcement-meta"><Badge color={accents[i%4]}>{item.club_name}</Badge><span>{item.status==='published'&&item.published_at?new Date(item.published_at).toLocaleDateString():item.status}</span></div><h2>{item.title}</h2><p>{item.content}</p>{item.attachment&&<a className="announcement-attachment" href={media(item.attachment)} target="_blank" rel="noreferrer">View attachment</a>}<div className="announcement-footer"><div className="announcement-author"><div className="profile-avatar small">{(item.author_name||'S').slice(0,1)}</div><span>Shared by <b>{item.author_name||'College administrator'}</b></span></div>{(canEdit(item)||canDelete(item))&&<div className="announcement-actions">{canEdit(item)&&<Button variant="outline" onClick={()=>openEdit(item)}><Pencil size={14}/> Edit</Button>}{canDelete(item)&&<Button variant="ghost" onClick={()=>deleteItem(item)} aria-label={`Delete ${item.title}`}><Trash2 size={15}/></Button>}</div>}</div></div></Card>):<Card className="empty-card"><div className="empty-icon"><Megaphone/></div><h3>{isAdmin?'No announcements found':'All quiet for now'}</h3><p>{isAdmin?'Create an announcement for any club.':'New announcements from your clubs will show up here.'}</p></Card>}</div>}
    {isAdmin&&<div className="table-footer announcement-pagination"><span>Page {page}</span><div><button disabled={page<=1} onClick={()=>load(page-1)}>Previous</button><button disabled={page*20>=count} onClick={()=>load(page+1)}>Next</button></div></div>}
  </>
}
