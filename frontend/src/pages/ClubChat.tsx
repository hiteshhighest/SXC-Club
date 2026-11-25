import { FormEvent, useEffect, useRef, useState } from 'react'
import { MessageCircle, Send } from 'lucide-react'
import { api, json } from '../lib/api'
import { Button, Card, Input } from '../components/ui'

type Message={id:number;club:number;sender_id:number;sender_name:string;content:string;created_at:string}

export function ClubChat({clubId,currentUserId}:{clubId:number;currentUserId:number}) {
  const [messages,setMessages]=useState<Message[]>([])
  const [content,setContent]=useState('')
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(true)
  const [sending,setSending]=useState(false)
  const lastId=useRef(0)
  const scrollRef=useRef<HTMLDivElement>(null)

  useEffect(()=>{
    let active=true
    const refresh=async()=>{
      try {
        const path=lastId.current?`/clubs/${clubId}/chat/?after=${lastId.current}`:`/clubs/${clubId}/chat/`
        const fresh=await api<Message[]>(path)
        if(!active)return
        if(fresh.length){
          lastId.current=Math.max(lastId.current,...fresh.map(message=>message.id))
          setMessages(current=>{const byId=new Map(current.map(message=>[message.id,message]));fresh.forEach(message=>byId.set(message.id,message));return [...byId.values()].sort((a,b)=>a.id-b.id).slice(-100)})
        }
        setError('')
      } catch(e) { if(active)setError((e as Error).message) }
      finally { if(active)setLoading(false) }
    }
    refresh();const timer=window.setInterval(refresh,5000)
    return ()=>{active=false;window.clearInterval(timer)}
  },[clubId])
  useEffect(()=>{scrollRef.current?.scrollTo({top:scrollRef.current.scrollHeight,behavior:'smooth'})},[messages])

  async function send(e:FormEvent){
    e.preventDefault();const message=content.trim();if(!message||sending)return
    setSending(true);setError('')
    try {
      const created=await api<Message>(`/clubs/${clubId}/chat/`,json('POST',{content:message}))
      lastId.current=Math.max(lastId.current,created.id)
      setMessages(current=>[...current.filter(item=>item.id!==created.id),created].sort((a,b)=>a.id-b.id).slice(-100))
      setContent('')
    } catch(e) { setError((e as Error).message) }
    finally { setSending(false) }
  }

  return <section className="club-chat-section">
    <div className="section-heading compact"><div><h2>Club chat</h2><p className="muted">A space for members to talk</p></div><span className="chat-live"><i/> Live</span></div>
    <Card className="club-chat-card">
      <div className="chat-messages" ref={scrollRef} aria-live="polite">
        {loading&&!messages.length?<div className="chat-empty">Loading chat…</div>:messages.length?messages.map(message=>{
          const mine=message.sender_id===currentUserId
          return <div className={`chat-message ${mine?'mine':''}`} key={message.id}><div className="chat-message-author">{mine?'You':message.sender_name}<time>{new Date(message.created_at).toLocaleTimeString('en',{hour:'numeric',minute:'2-digit',timeZone:'Asia/Kathmandu'})}</time></div><div className="chat-bubble">{message.content}</div></div>
        }):<div className="chat-empty"><MessageCircle size={23}/><span>Start the conversation with your club.</span></div>}
      </div>
      {error&&<p className="error-text chat-error" role="alert">{error}</p>}
      <form className="chat-composer" onSubmit={send}><Input aria-label="Message" maxLength={2000} value={content} onChange={e=>setContent(e.target.value)} placeholder="Write a message…"/><Button type="submit" disabled={!content.trim()||sending} aria-label="Send message"><Send size={16}/><span>Send</span></Button></form>
    </Card>
  </section>
}
