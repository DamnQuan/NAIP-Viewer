<template>
  <HomePage v-if="atHome" :theme="theme" @enter="enterApp" @toggleTheme="toggleTheme"/>

  <div class="shell" v-else>
    <nav class="rail" :class="{ open: navOpen }">
      <button @click="navOpen = !navOpen">
        <VIcon name="panel" :size="17"/>
        <span class="lbl">导航</span>
      </button>
      <span class="rail-line"/>
      <button :class="{ on: store.tab === 'charts' }" @click="store.tab = 'charts'">
        <VIcon name="chart" :size="18"/>
        <span class="lbl">机场航图</span>
      </button>
      <button :class="{ on: store.tab === 'docs' }" @click="store.tab = 'docs'">
        <VIcon name="book" :size="18"/>
        <span class="lbl">NAIP 总资料</span>
      </button>
      <button :class="{ on: store.tab === 'data' }" @click="store.tab = 'data'">
        <VIcon name="table" :size="18"/>
        <span class="lbl">航路数据</span>
      </button>
      <div class="spring"/>
      <button @click="goHome">
        <VIcon name="home" :size="17"/>
        <span class="lbl">回到主页</span>
      </button>
      <button @click="toggleTheme">
        <VIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="17"/>
        <span class="lbl">{{ theme === 'dark' ? '浅色模式' : '深色模式' }}</span>
      </button>
    </nav>

    <aside class="sidebar" v-show="sidebarOpen && store.tab !== 'data'">
      <div class="search-wrap" v-if="store.tab !== 'data'">
        <input v-model="store.search"
               :placeholder="store.tab === 'charts' ? '搜索机场 — ICAO / 名称' : '搜索资料文件'"
               @keydown.esc="store.search = ''">
      </div>
      <AirportPanel v-if="store.tab === 'charts'"/>
      <DocsPanel v-else ref="docsPanel"/>
    </aside>

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
import HomePage from './components/HomePage.vue'
import AirportPanel from './components/AirportPanel.vue'
import DocsPanel from './components/DocsPanel.vue'
import DataPanel from './components/DataPanel.vue'
import PdfViewer from './components/PdfViewer.vue'
import { store, loadJSON, dataURL } from './store.js'

const theme = ref(document.documentElement.dataset.theme || 'dark')
const docsPanel = ref(null)

const atHome = ref(!sessionStorage.getItem('naip-entered'))
function enterApp() {
  sessionStorage.setItem('naip-entered', '1')
  atHome.value = false
}
function goHome() {
  atHome.value = true
  sessionStorage.removeItem('naip-entered')
}

const sidebarOpen = ref(true)
const navOpen = ref(false)

watch(() => store.tab, (t) => { if (t === 'docs') docsPanel.value?.setSearch('') })
watch(() => store.search, (v) => { if (store.tab === 'docs') docsPanel.value?.setSearch(v) })

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('naip-theme', theme.value)
}

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
