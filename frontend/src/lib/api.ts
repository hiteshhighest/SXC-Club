export type User = { id:number; username:string; first_name:string; last_name:string; email:string; name:string; is_admin?:boolean; memberships?:Membership[] }
export type Club = { id:number; name:string; abbreviation:string; category:string; description:string; logo:string|null; banner:string|null; status:string; contact_email?:string; contact_url?:string; member_count?:number }
export type Membership = { id?:number; club_id:number; club__name:string; club__abbreviation:string; role_name:string; permissions:string[] }
export type Event = { id:number; club:number; club_name:string; title:string; description:string; starts_at:string; venue:string; status:string; category:string }
export type Announcement = { id:number; club:number; club_name:string; title:string; content:string; attachment?:string|null; status:string; published_at:string|null; author_name:string }
export type Notification = { id:number; kind:string; message:string; read_at:string|null; created_at:string }
const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/+$/, '')
let csrf = ''
function cookie(name:string) { return document.cookie.split('; ').find(row=>row.startsWith(name+'='))?.split('=')[1] ?? '' }
export async function initCsrf() {
  const res=await fetch(`${base}/csrf/`,{credentials:'include'})
  const data=await res.json().catch(()=>({}))
  csrf=data.csrfToken||decodeURIComponent(cookie('csrftoken'))
}
export async function api<T>(path:string, options:RequestInit={}):Promise<T> {
  const method=(options.method??'GET').toUpperCase()
  if (!['GET','HEAD','OPTIONS'].includes(method) && !csrf) await initCsrf()
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type','application/json')
  if (!['GET','HEAD','OPTIONS'].includes(method)) headers.set('X-CSRFToken',csrf)
  const res=await fetch(`${base}${path}`,{...options,headers,credentials:'include'})
  csrf=decodeURIComponent(cookie('csrftoken'))||csrf
  if (res.status===204) return undefined as T
  const data=await res.json().catch(()=>({detail:'Unexpected server response'}))
  if (!res.ok) throw new Error(typeof data.detail==='string'?data.detail:Object.values(data).flat().join(' '))
  return data as T
}
export const json=(method:string,data?:unknown):RequestInit=>({method,body:data===undefined?undefined:JSON.stringify(data)})
export const media=(path:string)=>path.startsWith('http')?path:`${base.replace('/api','')}${path}`
