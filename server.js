// Naip-Viewer 登录后端：零依赖，Node 内置模块实现。
// 端口 8787；开发时配合 Vite 代理 /api，生产时直接托管 dist/。
//
// 账号存 data/users.json（scrypt 散列，不入库）。首次启动自动创建默认管理员：
//   用户名 quanquan / 密码 quanquan —— 上线前务必登录后修改。
//
// 用法: node server.js [端口]
//   开发: 另开终端跑 npm run dev（Vite 5173 代理 /api 到这里）
//   生产: npm run build 后直接访问 http://127.0.0.1:8787

import http from 'node:http'
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const PORT = Number(process.argv[2] || process.env.PORT || 8787)
const HOST = process.argv[3] || process.env.HOST || '127.0.0.1' // 部署到局域网/公网用 0.0.0.0
const ROOT = path.dirname(fileURLToPath(import.meta.url))
const DIST = path.join(ROOT, 'dist')
const DATA_DIR = path.join(ROOT, 'data')
const USERS_FILE = path.join(DATA_DIR, 'users.json')

const SESSION_TTL = 7 * 24 * 3600 * 1000 // 7 天
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.pdf': 'application/pdf',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
}

// ---------- 账号存储 ----------
function hashPassword(password, salt) {
  return crypto.scryptSync(password, salt, 64).toString('hex')
}
function makeUser(username, password, role) {
  const salt = crypto.randomBytes(16).toString('hex')
  return { salt, hash: hashPassword(password, salt), role, createdAt: new Date().toISOString() }
}
function verifyPassword(u, password) {
  const h = Buffer.from(hashPassword(password, u.salt), 'hex')
  const stored = Buffer.from(u.hash, 'hex')
  return h.length === stored.length && crypto.timingSafeEqual(h, stored)
}
function loadUsers() {
  try {
    return JSON.parse(fs.readFileSync(USERS_FILE, 'utf8'))
  } catch {
    const users = { quanquan: makeUser('quanquan', 'quanquan', 'admin') }
    saveUsers(users)
    console.log('已创建默认管理员: quanquan / quanquan（请尽快修改密码）')
    return users
  }
}
function saveUsers(users) {
  fs.mkdirSync(DATA_DIR, { recursive: true })
  fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2))
}
let users = loadUsers()

// ---------- 会话 ----------
const sessions = new Map() // token -> { username, expires }
function createSession(username) {
  const token = crypto.randomBytes(32).toString('hex')
  sessions.set(token, { username, expires: Date.now() + SESSION_TTL })
  return token
}
function getSession(req) {
  const m = /(?:^|;\s*)naip_session=([a-f0-9]{64})/.exec(req.headers.cookie || '')
  if (!m) return null
  const s = sessions.get(m[1])
  if (!s || s.expires < Date.now()) { sessions.delete(m[1]); return null }
  return { token: m[1], ...s }
}
function destroySession(token) { sessions.delete(token) }

// ---------- 工具 ----------
function json(res, code, obj) {
  const body = JSON.stringify(obj)
  res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(body)
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0
    const chunks = []
    req.on('data', c => {
      size += c.length
      if (size > 10240) { reject(new Error('请求体过大')); req.destroy(); return }
      chunks.push(c)
    })
    req.on('end', () => {
      try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : {}) }
      catch { reject(new Error('JSON 格式错误')) }
    })
    req.on('error', reject)
  })
}
function fail(res, code, msg) { json(res, code, { error: msg }) }
function meOf(username) { return { username, role: users[username].role } }
function adminCount() { return Object.values(users).filter(u => u.role === 'admin').length }

// ---------- API 路由 ----------
const routes = []
function route(method, pattern, needAuth, needAdmin, handler) {
  routes.push({ method, pattern, needAuth, needAdmin, handler })
}

route('POST', '/api/login', false, false, async (req, res, params) => {
  const { username, password } = params
  if (!username || !password) return fail(res, 400, '请输入用户名和密码')
  const u = users[username]
  if (!u || !verifyPassword(u, String(password))) return fail(res, 401, '用户名或密码错误')
  const token = createSession(username)
  res.setHeader('Set-Cookie',
    `naip_session=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=${SESSION_TTL / 1000}`)
  json(res, 200, meOf(username))
})

route('POST', '/api/logout', true, false, (req, res, params, session) => {
  destroySession(session.token)
  res.setHeader('Set-Cookie', 'naip_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
  json(res, 200, {})
})

route('GET', '/api/me', true, false, (req, res, params, session) => {
  json(res, 200, meOf(session.username))
})

route('GET', '/api/users', true, true, (req, res) => {
  json(res, 200, Object.entries(users).map(([username, u]) => ({
    username, role: u.role, createdAt: u.createdAt,
  })))
})

route('POST', '/api/users', true, true, async (req, res, params) => {
  const { username, password, role } = params
  if (!username || !password) return fail(res, 400, '用户名和密码不能为空')
  if (!/^[A-Za-z0-9_-]{2,32}$/.test(username)) return fail(res, 400, '用户名仅限 2-32 位字母、数字、下划线、连字符')
  if (String(password).length < 6) return fail(res, 400, '密码至少 6 位')
  if (users[username]) return fail(res, 400, '用户名已存在')
  users[username] = makeUser(username, String(password), role === 'admin' ? 'admin' : 'user')
  saveUsers(users)
  json(res, 200, { username, role: users[username].role })
})

route('PUT', '/api/users/*', true, true, async (req, res, params, session, target) => {
  if (!users[target]) return fail(res, 404, '账号不存在')
  const { password, role } = params
  if (role && !['admin', 'user'].includes(role)) return fail(res, 400, '无效的角色')
  if (target === session.username && role && role !== 'admin' && adminCount() === 1)
    return fail(res, 400, '至少保留一个管理员')
  if (password !== undefined) {
    if (String(password).length < 6) return fail(res, 400, '密码至少 6 位')
    const salt = crypto.randomBytes(16).toString('hex')
    users[target].salt = salt
    users[target].hash = hashPassword(String(password), salt)
  }
  if (role !== undefined) users[target].role = role
  saveUsers(users)
  json(res, 200, { username: target, role: users[target].role })
})

route('DELETE', '/api/users/*', true, true, (req, res, params, session, target) => {
  if (!users[target]) return fail(res, 404, '账号不存在')
  if (target === session.username) return fail(res, 400, '不能删除当前登录的账号')
  if (users[target].role === 'admin' && adminCount() === 1)
    return fail(res, 400, '至少保留一个管理员')
  delete users[target]
  saveUsers(users)
  json(res, 200, {})
})

// ---------- 静态文件（生产模式：托管 dist） ----------
function serveStatic(req, res, pathname, session) {
  // 航图与索引数据需要登录后访问
  if (pathname.startsWith('/data/') && !session) return fail(res, 401, '未登录')
  let rel = pathname === '/' ? 'index.html' : pathname.slice(1)
  let file = path.normalize(path.join(DIST, rel))
  if (!file.startsWith(DIST)) { res.writeHead(403); return res.end() }
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    file = path.join(DIST, 'index.html') // SPA 回退
    if (!fs.existsSync(file)) { res.writeHead(404); return res.end('dist/ 不存在，请先 npm run build') }
  }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' })
  fs.createReadStream(file).pipe(res)
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`)
  const pathname = decodeURIComponent(url.pathname)

  if (!pathname.startsWith('/api/')) return serveStatic(req, res, pathname, getSession(req))

  for (const r of routes) {
    if (req.method !== r.method) continue
    let target = ''
    if (r.pattern.endsWith('/*')) {
      const base = r.pattern.slice(0, -2)
      if (!pathname.startsWith(base + '/')) continue
      target = pathname.slice(base.length + 1)
    } else if (r.pattern !== pathname) continue

    const session = getSession(req)
    if (r.needAuth && !session) return fail(res, 401, '未登录')
    if (r.needAdmin && users[session.username]?.role !== 'admin') return fail(res, 403, '需要管理员权限')

    let params = {}
    if (req.method === 'POST' || req.method === 'PUT') {
      try { params = await readBody(req) }
      catch (e) { return fail(res, 400, e.message) }
    }
    try { return await r.handler(req, res, params, session, target) }
    catch (e) { console.error(e); return fail(res, 500, '服务器内部错误') }
  }
  fail(res, 404, '接口不存在')
})

server.listen(PORT, HOST, () => {
  console.log(`NAIP-Viewer 后端已启动: http://127.0.0.1:${PORT}`)
  console.log('  开发模式: npm run dev（Vite 会把 /api 代理到这里）')
  console.log(`  账号数据: ${USERS_FILE}`)
})
