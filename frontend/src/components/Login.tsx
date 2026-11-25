import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Button, Input } from './ui'
import { api, initCsrf, json, type User } from '../lib/api'
import { Brand } from './Brand'

export function Login({onLogin,mode='student'}:{onLogin:(user:User)=>void;mode?:'student'|'admin'}) {
  const [username,setUsername]=useState(''); const [password,setPassword]=useState('')
  const [error,setError]=useState(''); const [busy,setBusy]=useState(false)
  const [reset,setReset]=useState(false); const [notice,setNotice]=useState('')
  const admin=mode==='admin'
  async function submit(e:React.FormEvent){
    e.preventDefault();setBusy(true);setError('')
    try { await initCsrf(); onLogin(await api<User>(admin?'/auth/admin-login/':'/auth/login/',json('POST',{username,password}))) }
    catch(err){setError((err as Error).message)} finally{setBusy(false)}
  }
  async function resetPassword(e:React.FormEvent){
    e.preventDefault();setError('')
    try{await api('/auth/password-reset/',json('POST',{email:username}));setNotice('If the account exists, reset instructions will be sent to its email.')}
    catch(err){setError((err as Error).message)}
  }
  return <main className="simple-login-page"><section className="simple-login-card">
    <Brand/><span className="eyebrow">{reset?'ACCOUNT RECOVERY':admin?'ADMINISTRATOR ACCESS':'STUDENT ACCESS'}</span>
    <h1>{reset?'Reset your password':admin?'Admin sign in':'Student sign in'}</h1>
    <p className="muted">{reset?'Enter your account email to get a reset link.':admin?'Sign in with your SXC Clubs administrator account.':'Sign in with the student account provided by your club or college administrator.'}</p>
    <form onSubmit={reset?resetPassword:submit} className="form-stack">
      <label>{reset?'Email address':'Username'}<Input required autoComplete={reset?'email':'username'} type={reset?'email':'text'} value={username} onChange={e=>setUsername(e.target.value)} placeholder={reset?'you@example.com':'Enter your username'}/></label>
      {!reset&&<label>Password<Input required autoComplete="current-password" type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password"/></label>}
      {error&&<p className="error-text">{error}</p>}{notice&&<p className="success-text">{notice}</p>}
      <Button type="submit" disabled={busy} className="w-full justify-center">{busy?'Please wait':reset?'Send reset link':'Sign in'} <ArrowRight size={17}/></Button>
    </form>
    <button className="text-link" onClick={()=>{setReset(!reset);setError('');setNotice('')}}>{reset?'Back to sign in':'Forgot password?'}</button>
    <p className="login-foot">Accounts are created by SXC Clubs administrators.</p>
  </section></main>
}
