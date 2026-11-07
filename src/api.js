// 登录后端 API 封装（/api 由 Vite 代理或生产环境同源提供）
async function req(method, url, body) {
  const r = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.error || `请求失败 (${r.status})`)
  return data
}

export const api = {
  me: () => req('GET', '/api/me'),
  login: (username, password) => req('POST', '/api/login', { username, password }),
  logout: () => req('POST', '/api/logout'),
  users: () => req('GET', '/api/users'),
  addUser: (username, password, role) => req('POST', '/api/users', { username, password, role }),
  updateUser: (username, patch) => req('PUT', '/api/users/' + encodeURIComponent(username), patch),
  deleteUser: (username) => req('DELETE', '/api/users/' + encodeURIComponent(username)),
}
