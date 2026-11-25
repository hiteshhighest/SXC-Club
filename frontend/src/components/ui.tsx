import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, PropsWithChildren } from 'react'
import { LoaderCircle } from 'lucide-react'
export function Button({children,className='',variant='primary',...props}:PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>&{variant?:'primary'|'outline'|'ghost'|'danger'}>){return <button className={`btn btn-${variant} ${className}`} {...props}>{children}</button>}
export function Card({children,className='',...props}:PropsWithChildren<HTMLAttributes<HTMLDivElement>>){return <div className={`card ${className}`} {...props}>{children}</div>}
export function Input(props:InputHTMLAttributes<HTMLInputElement>){return <input className={`input ${props.className??''}`} {...props}/>}
export function Spinner(){return <LoaderCircle className="animate-spin" size={18}/>}
export function PageTitle({eyebrow,title,description,action}:{eyebrow?:string;title:string;description?:string;action?:React.ReactNode}){return <div className="page-title"><div>{eyebrow&&<p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description&&<p className="muted mt-1">{description}</p>}</div>{action}</div>}
export function Badge({children,color='violet'}:PropsWithChildren<{color?:string}>){return <span className={`badge badge-${color}`}>{children}</span>}
