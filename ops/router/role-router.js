import express from 'express'
import crypto from 'crypto'
import fs from 'fs'
import path from 'path'

const app = express()
app.use(express.json())

const REPO_ROOT = process.cwd()
const STATUS_FILE = path.join(REPO_ROOT, 'ops/github/project_status.json')
const LOG_FILE = path.join(REPO_ROOT, 'docs/LOG.md')
const SECRET = process.env.ROUTER_SIGNING_SECRET || ''

const allowed = ['Frank','AI1','AI2','AI3','AI4']
const allowedTransitions = new Set([
  'Frank->AI1','AI1->AI2','AI2->AI3','AI3->AI4','AI4->Frank'
])

function hmacOk(raw, sig){
  if(!SECRET) return true
  const mac = 'sha256=' + crypto.createHmac('sha256', SECRET).update(raw).digest('hex')
  return crypto.timingSafeEqual(Buffer.from(mac), Buffer.from(sig||mac))
}

function currentStatus(){
  try{ return JSON.parse(fs.readFileSync(STATUS_FILE,'utf-8')) }catch(e){
    return { state: 'Frank Reviewing', last_role: null, next_role: 'AI1', last_commit: null, ts: new Date().toISOString() }
  }
}

function writeStatus(obj){
  fs.mkdirSync(path.dirname(STATUS_FILE), { recursive: true })
  fs.writeFileSync(STATUS_FILE, JSON.stringify(obj, null, 2))
}

function appendLog(line){
  fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true })
  fs.appendFileSync(LOG_FILE, `
${new Date().toISOString()} ${line}`)
}

app.post('/ingest', (req,res)=>{
  const raw = JSON.stringify(req.body)
  if(!hmacOk(raw, req.headers['x-signature'])) return res.status(401).json({error:'bad signature'})

  const { channel, ts, user, text } = req.body
  const m = /^\[(Frank|AI1|AI2|AI3|AI4)\]\s*(.*)$/.exec(text||'')
  if(!m) return res.status(400).json({error:'missing role tag'})
  const role = m[1]; const payload = m[2]
  if(!allowed.includes(role)) return res.status(400).json({error:'role not allowed'})

  const st = currentStatus()
  const transition = `${st.last_role||'Frank'}->${role}`
  if(!allowedTransitions.has(transition)) {
    appendLog(`[BLOCK] ${transition} not allowed | ${payload}`)
    return res.status(409).json({error:'transition not allowed', expected: st.next_role})
  }

  const next = role==='Frank' ? 'AI1' : role==='AI1' ? 'AI2' : role==='AI2' ? 'AI3' : role==='AI3' ? 'AI4' : 'Frank'
  const newState = role==='AI4' ? 'Frank Reviewing' : role==='Frank' ? 'AI 1 Reviewing' : role==='AI1' ? 'AI 2 Validating' : role==='AI2' ? 'AI 3 Computing' : 'AI 4 Building'

  const newStatus = { ...st, last_role: role, next_role: next, state: newState, ts: new Date().toISOString() }
  writeStatus(newStatus)
  appendLog(`[OK] ${role}: ${payload}`)
  return res.json({ ok:true, next_role: next, state: newState })
})

app.listen(process.env.PORT||3000, ()=> console.log('role-router up'))
