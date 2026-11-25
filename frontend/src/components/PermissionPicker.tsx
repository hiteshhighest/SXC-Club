import type { ReactNode } from 'react'

export type PermissionChoice = { key:string; label:string }
export type PermissionGroups = Record<string,PermissionChoice[]>

export function PermissionPicker({groups,value,onChange,grantableKeys,selectAllLabel='Select all permissions'}:{groups:PermissionGroups;value:string[];onChange:(next:string[])=>void;grantableKeys?:string[];selectAllLabel?:string}){
  const allKeys=Object.values(groups).flat().map(item=>item.key)
  const grantable=new Set(grantableKeys??allKeys)
  function toggle(keys:string[]){
    const selected=keys.every(key=>value.includes(key))
    if(selected)onChange(value.filter(key=>!keys.includes(key)))
    else onChange(Array.from(new Set([...value,...keys.filter(key=>grantable.has(key))])))
  }
  const control=(label:string,keys:string[],compact=false):ReactNode=><button type="button" className={`permission-bulk ${compact?'compact':''}`} onClick={()=>toggle(keys)}>{keys.length>0&&keys.every(key=>value.includes(key))?'Clear':'Select'} {label}</button>
  return <div className="permission-picker">
    <div className="permission-picker-toolbar"><span>{value.length} selected</span>{control(selectAllLabel,allKeys)}</div>
    <div className="permission-groups">{Object.entries(groups).map(([group,items])=>{
      const keys=items.map(item=>item.key)
      return <div className="permission-group" key={group}>
        <div className="permission-group-heading"><h4>{group}</h4>{control('section',keys,true)}</div>
        <div className="permission-checks">{items.map(item=><label key={item.key}><input type="checkbox" checked={value.includes(item.key)} disabled={!grantable.has(item.key)&&!value.includes(item.key)} onChange={e=>onChange(e.target.checked?[...value,item.key]:value.filter(key=>key!==item.key))}/><span>{item.label}</span></label>)}</div>
      </div>
    })}</div>
  </div>
}
