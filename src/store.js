import { reactive } from 'vue'

export const store = reactive({
  tab: 'charts',
  search: '',
  meta: {},
  user: null,       // { username, role }，登录后由 /api/me 填充
  authReady: false, // 是否已完成会话检查（决定显示登录页还是闪屏）
  airports: [],
  details: {},
  airport: null,
  charts: [],
  flatCharts: [],
  curChart: -1,
  viewer: null,
  dataTab: 'vor',
})

export const dataURL = (...parts) =>
  '/data/NAIP2610/' + parts.map(encodeURIComponent).join('/')

export async function loadJSON(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}

export function fmtCoord(lat, lon) {
  if (!lat || !lon) return ''
  const f = (v) => {
    const m = v.match(/^([NSWE])(\d{2,3})(\d{2})(\d{2})$/)
    return m ? `${m[1]}${m[2]}°${m[3]}′${m[4]}″` : v
  }
  return f(lat) + ' ' + f(lon)
}

export const CHART_GROUPS = [
  ['机场细则', ['机场细则']],
  ['机场图 / 停机位', ['机场图_停机位置图']],
  ['离场图 (SID)', ['标准仪表离场图']],
  ['进场图 (STAR)', ['标准仪表进场图']],
  ['进近图 (ILS)', ['仪表进近图_ILS']],
  ['进近图 (VOR)', ['仪表进近图_VOR']],
  ['进近图 (NDB)', ['仪表进近图_NDB']],
  ['进近图 (RNP/RNAV)', ['进近图_RNAV_RNP_RADAR_GPS_GNSS']],
  ['目视进近图', ['目视进近图']],
  ['障碍物 / 地形图', ['机场障碍物图_精密进近地形图']],
  ['放油区 / 最低监视引导高度图', ['最低监视引导高度图_放油区图']],
  ['其他', ['其他']],
]
