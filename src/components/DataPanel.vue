<template>
  <div class="data-panel">
    <div class="dtabs">
      <button v-for="[k, label] in DATA_TABS" :key="k"
              class="dtab" :class="{ on: store.dataTab === k }"
              @click="switchTab(k)">{{ label }}</button>
      <div class="dsearch">
        <input v-model="search" placeholder="搜索 — 编号 / 名称 / 航路点" @keydown.esc="search = ''">
      </div>
    </div>
    <div class="list" v-if="rows">
      <table class="dtable" v-if="paged.length">
        <thead>
          <tr><th v-for="h in cols.head" :key="h">{{ h }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in paged" :key="i">
            <td v-for="(cell, ci) in cols.row(r)" :key="ci"
                :class="{ mono: ci === 0, wrap: typeof cell === 'string' && cell.length > 60 }"
                v-html="cell"></td>
          </tr>
        </tbody>
      </table>
      <div class="count" v-else>无匹配结果</div>
      <div class="pager" v-if="pages > 1">
        <button @click="page--" :disabled="page <= 1">‹ 上一页</button>
        <span>{{ page }} / {{ pages }}</span>
        <button @click="page++" :disabled="page >= pages">下一页 ›</button>
      </div>
      <div class="count" v-if="filteredRows.length">{{ filteredRows.length }} 条记录</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { store, loadJSON, fmtCoord } from '../store.js'

const DATA_TABS = [
  ['vor', 'VOR/DME'], ['ndb', 'NDB'], ['dpt', '航路点'],
  ['routes', '航路'], ['airline', '班机航线'], ['airspace', '空域'],
  ['airports', '机场跑道'], ['holds', '等待程序'],
]

const cache = {}
const PAGE_SIZE = 100
const rows = ref(null)
const page = ref(1)
const search = ref('')

async function getData(key) {
  const need = {
    vor: ['nav'], ndb: ['nav'], dpt: ['nav'],
    routes: ['routes'], airline: ['airline'], airspace: ['airspace'],
    airports: ['airports', 'details'], holds: ['holds'],
  }[key]
  const files = {
    nav: 'navdata.json', routes: 'routes.json', airline: 'airline_routes.json',
    airspace: 'airspaces.json', details: 'airport_details.json', airports: 'airports.json',
    holds: 'holdings.json',
  }
  for (const f of need) if (!cache[f]) cache[f] = await loadJSON('/data/index/' + files[f])
  return {
    vor: () => cache.nav.vor,
    ndb: () => cache.nav.ndb,
    dpt: () => cache.nav.dpt,
    routes: () => cache.routes.routes,
    airline: () => cache.airline,
    airspace: () => [
      ...cache.airspace.ctr.map(x => ({ ...x, kind: '管制扇区' })),
      ...cache.airspace.res.map(x => ({ ...x, kind: '限制区' })),
      ...cache.airspace.spc.map(x => ({ ...x, kind: '等待空域' })),
      ...cache.airspace.fir.map(x => ({ ...x, kind: '飞行情报区' })),
    ],
    airports: () => cache.airports,
    holds: () => cache.holds,
  }[key]()
}

const TABLES = {
  vor: {
    q: (r, u) => r.id.toUpperCase().includes(u) || r.name.includes(u),
    head: ['编号', '名称', '类型', '频道', '频率', '坐标', '情报区'],
    row: r => [r.id, r.name, r.type, r.ch, r.freq, fmtCoord(r.lat, r.lon), r.fir],
  },
  ndb: {
    q: (r, u) => r.id.toUpperCase().includes(u) || r.name.includes(u),
    head: ['编号', '名称', '频率', '坐标', '情报区'],
    row: r => [r.id, r.name, r.freq, fmtCoord(r.lat, r.lon), r.fir],
  },
  dpt: {
    q: (r, u) => r.id.toUpperCase().includes(u) || r.name.includes(u),
    head: ['代码', '名称', '类型', '坐标', '情报区'],
    row: r => [r.id, r.name, r.type, fmtCoord(r.lat, r.lon), r.fir],
  },
  routes: {
    q: (r, u) => r.desig.toUpperCase().includes(u) || r.pts.some(p => p.toUpperCase().includes(u)),
    head: ['航路', '类型', '长度 km / NM', 'MOCA', '航路点序列'],
    row: r => [r.desig, r.type, [r.len, r.lenSM].filter(Boolean).join(' / '), r.moca,
      r.pts.map(p => `<span class="pt">${p}</span>`).join('<i>–</i>')],
  },
  airline: {
    q: (r, u) => r.name.toUpperCase().includes(u) || r.route.includes(u) || (r.from + r.to).includes(u),
    head: ['航线', '类型', '起点', '终点', '距离 km', 'MSA', '航路描述'],
    row: r => [r.name, r.type, r.from, r.to, r.dist, r.msa, r.route],
  },
  airspace: {
    q: (r, u) => r.name.includes(u) || r.id.toUpperCase().includes(u) || (r.rmk || '').includes(u),
    head: ['识别', '名称', '类别', '垂直范围', '原因 / 时间', '频率', '水平范围'],
    row: r => [r.id, r.name, r.kind, (r.cls || []).join('；'),
      [r.reason, r.time].filter(Boolean).join(' / '), (r.radio || []).join('；'), r.h],
  },
  airports: {
    q: (r, u) => r.icao.includes(u) || r.name.includes(u),
    head: ['ICAO', '名称', '管理局', '标高', '磁差', '过渡高度 / 层', '跑道'],
    row: r => {
      const d = cache.details[r.icao] || {}
      return [r.icao, r.name, r.bureau,
        d.elev ? d.elev + (d.uom || '') : '',
        d.magvar ? d.magvar + '°' : '',
        [d.transAlt && 'ALT ' + d.transAlt, d.transLvl && 'FL ' + d.transLvl].filter(Boolean).join(' / '),
        (d.rwys || []).map(x => x.desig.trim()).join(' / ')]
    },
  },
  holds: {
    q: (r, u) => (r.name || '').includes(u) || (r.rmk || '').includes(u),
    head: ['名称', '类型', '坐标', '说明'],
    row: r => [r.name, r.type, fmtCoord(r.lat, r.lon), r.rmk],
  },
}

const cols = computed(() => TABLES[store.dataTab])
const filteredRows = computed(() => {
  if (!rows.value) return []
  const q = search.value.trim().toUpperCase()
  if (!q) return rows.value
  return rows.value.filter(r => cols.value.q(r, q))
})
const pages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / PAGE_SIZE)))
const paged = computed(() =>
  filteredRows.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))

function switchTab(k) { store.dataTab = k }

watch(() => store.dataTab, async (k) => {
  rows.value = null
  page.value = 1
  rows.value = await getData(k)
}, { immediate: true })

watch(search, () => { page.value = 1 })
</script>
