<template>
  <!-- 会话检查中 -->
  <div class="login" v-if="!store.authReady"><div class="home-bg"></div></div>

  <!-- 未登录 -->
  <LoginPage v-else-if="!store.user"/>

  <!-- 主页 -->
  <HomePage v-else-if="atHome" :theme="theme" @enter="enterApp" @toggleTheme="toggleTheme"/>

  <!-- 工作台 -->
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
      <button v-if="isAdmin" :class="{ on: store.tab === 'admin' }" @click="store.tab = 'admin'">
        <VIcon name="users" :size="18"/>
        <span class="lbl">账号管理</span>
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
      <button @click="logout">
        <VIcon name="logout" :size="17"/>
        <span class="lbl">退出登录</span>
      </button>
    </nav>

    <aside class="sidebar" v-show="sidebarOpen && isViewerTab">
      <div class="search-wrap" v-if="isViewerTab">
        <input v-model="store.search"
               :placeholder="store.tab === 'charts' ? '搜索机场 — ICAO / 名称' : '搜索资料文件'"
               @keydown.esc="store.search = ''">
      </div>
      <AirportPanel v-if="store.tab === 'charts'"/>
      <DocsPanel v-else-if="store.tab === 'docs'" ref="docsPanel"/>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="wordmark">NAIP<span>-Viewer</span></div>
        <span class="ver">{{ store.meta.DataVersion }} · EFF {{ store.meta.EffectiveDate }}</span>
        <div class="vtitle">{{ store.viewer?.title }}</div>
        <span class="whoami" v-if="store.user">
          {{ store.user.username }}
          <i v-if="isAdmin">管理员</i>
        </span>
      </header>
      <PdfViewer v-if="isViewerTab" style="flex:1"/>
      <DataPanel v-else-if="store.tab === 'data'"/>
      <AdminPanel v-else-if="store.tab === 'admin'"/>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import VIcon from './components/VIcon.vue'
import LoginPage from './components/LoginPage.vue'
import HomePage from './components/HomePage.vue'
import AirportPanel from './components/AirportPanel.vue'
import DocsPanel from './components/DocsPanel.vue'
import DataPanel from './components/DataPanel.vue'
import AdminPanel from './components/AdminPanel.vue'
import PdfViewer from './components/PdfViewer.vue'
import { store, loadJSON, dataURL } from './store.js'
import { api } from './api.js'

const theme = ref(document.documentElement.dataset.theme || 'dark')
const docsPanel = ref(null)

const isAdmin = computed(() => store.user?.role === 'admin')
const isViewerTab = computed(() => ['charts', 'docs'].includes(store.tab))

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

watch(() => store.tab, (t) => {
  if (t === 'docs') docsPanel.value?.setSearch('')
  if (t === 'admin' || t === 'data') sidebarOpen.value = true
})
watch(() => store.search, (v) => { if (store.tab === 'docs') docsPanel.value?.setSearch(v) })

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem('naip-theme', theme.value)
}

async function logout() {
  try { await api.logout() } catch {}
  store.user = null
  store.tab = 'charts'
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
    store.user = await api.me()
  } catch { store.user = null } finally {
    store.authReady = true
  }
  if (store.user) await loadAppData()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

// 登录成功后加载航图索引数据
watch(() => store.user, (u) => { if (u) loadAppData() })

async function loadAppData() {
  if (store.airports.length) return
  try {
    store.meta = await loadJSON('/data/index/meta.json')
  } catch {}
  store.airports = await loadJSON('/data/index/airports.json')
  store.details = await loadJSON('/data/index/airport_details.json')
}
</script>
