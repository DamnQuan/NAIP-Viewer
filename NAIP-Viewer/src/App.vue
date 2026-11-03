<template>
  <div class="shell">
    <!-- 左侧图标栏 -->
    <nav class="rail">
      <button :class="{ on: store.tab === 'charts' }" @click="store.tab = 'charts'" title="机场航图">
        <VIcon name="chart" :size="18"/>
      </button>
      <button :class="{ on: store.tab === 'docs' }" @click="store.tab = 'docs'" title="NAIP 总资料">
        <VIcon name="book" :size="18"/>
      </button>
      <button :class="{ on: store.tab === 'data' }" @click="store.tab = 'data'" title="航路数据">
        <VIcon name="table" :size="18"/>
      </button>
      <div class="spring"/>
      <button @click="toggleTheme" :title="theme === 'dark' ? '切换浅色' : '切换深色'">
        <VIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="17"/>
      </button>
    </nav>

    <!-- 侧栏（数据页隐藏） -->
    <aside class="sidebar" v-if="store.tab !== 'data'">
      <div class="search-wrap" v-if="store.tab !== 'data'">
        <input v-model="store.search"
               :placeholder="store.tab === 'charts' ? '搜索机场 — ICAO / 名称' : '搜索资料文件'"
               @keydown.esc="store.search = ''">
      </div>
      <AirportPanel v-if="store.tab === 'charts'"/>
      <DocsPanel v-else ref="docsPanel"/>
    </aside>

    <!-- 主区 -->
    <div class="main">
      <header class="topbar">
        <div class="wordmark">NAIP<span>-Viewer</span></div>
        <span class="ver">{{ store.meta.DataVersion }} · EFF {{ store.meta.EffectiveDate }}</span>
        <div class="vtitle">{{ store.viewer?.title }}</div>
      </header>
      <PdfViewer v-if="store.tab !== 'data'" style="flex:1"/>
      <DataPanel v-else/>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import VIcon from './components/VIcon.vue'
import AirportPanel from './components/AirportPanel.vue'
import DocsPanel from './components/DocsPanel.vue'
import DataPanel from './components/DataPanel.vue'
import PdfViewer from './components/PdfViewer.vue'
import { store, loadJSON, dataURL } from './store.js'

const theme = ref(document.documentElement.dataset.theme || 'dark')
const docsPanel = ref(null)

// 总资料页：侧栏搜索框内容同步给 DocsPanel
watch(() => store.tab, (t) => { if (t === 'docs') docsPanel.value?.setSearch('') })
watch(() => store.search, (v) => { if (store.tab === 'docs') docsPanel.value?.setSearch(v) })

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('naip-theme', theme.value)
}

// PgUp / PgDn 在航图间切换
function onKey(e) {
  if (e.target.tagName === 'INPUT') return
  if (store.tab !== 'charts' || store.curChart < 0) return
  if (e.key === 'PageUp') { e.preventDefault(); pdfNav(-1) }
  if (e.key === 'PageDown') { e.preventDefault(); pdfNav(1) }
}
function pdfNav(delta) {
  const idx = store.curChart + delta
  const c = store.flatCharts[idx]
  if (!c || !c.f) return
  store.curChart = idx
  store.viewer = {
    url: dataURL('Terminal', store.airport.icao, c.f),
    title: `${store.airport.icao} ${store.airport.name} — ${c.n.trim()}${c.p ? '  ·  ' + c.p : ''}`,
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    store.meta = await loadJSON('/data/index/meta.json')
  } catch {}
  store.airports = await loadJSON('/data/index/airports.json')
  store.details = await loadJSON('/data/index/airport_details.json')
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>
