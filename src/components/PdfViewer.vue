<template>
  <div class="viewer">
    <div class="toolbar">
      <div class="tool-group" v-if="store.tab === 'charts' && store.curChart >= 0">
        <button class="tb" @click="navChart(-1)" title="上一张 (PgUp)"><VIcon name="left" :size="14"/> 上一张</button>
        <button class="tb" @click="navChart(1)" title="下一张 (PgDn)">下一张 <VIcon name="right" :size="14"/></button>
        <span class="vline"/>
      </div>
      <button class="tb icon" @click="zoom(1/1.25)" title="缩小"><VIcon name="zoomOut" :size="15"/></button>
      <span class="zoom">{{ Math.round(scale * 100) }}%</span>
      <button class="tb icon" @click="zoom(1.25)" title="放大"><VIcon name="zoomIn" :size="15"/></button>
      <button class="tb" :class="{ on: fit === 'width' }" @click="fit = 'width'">适宽</button>
      <button class="tb" :class="{ on: fit === 'page' }" @click="fit = 'page'">适页</button>
      <span class="vline"/>
      <button class="tb icon" @click="goto(-1)" :disabled="pageNum <= 1"><VIcon name="left" :size="14"/></button>
      <span class="pageno">{{ pdf ? pageNum + ' / ' + pdf.numPages : '–' }}</span>
      <button class="tb icon" @click="goto(1)" :disabled="!pdf || pageNum >= pdf.numPages"><VIcon name="right" :size="14"/></button>
      <div class="grow"/>
      <a class="tb" :href="store.viewer?.url" target="_blank" v-if="store.viewer"><VIcon name="external" :size="14"/> 原始 PDF</a>
      <button class="tb" @click="print" v-if="store.viewer"><VIcon name="print" :size="14"/> 打印</button>
    </div>
    <div class="stage" ref="stageEl">
      <div v-if="!pdf" class="empty">
        <VIcon name="plane" :size="40"/>
        <p v-if="loading">加载中…</p>
        <p v-else-if="loadError" class="err">{{ loadError }}</p>
        <p v-else-if="store.tab === 'charts'">选择机场与航图</p>
        <p v-else-if="store.tab === 'docs'">选择资料文件</p>
        <p v-else>在下方浏览数据</p>
      </div>
      <div v-else class="paper-wrap">
        <div class="paper"><canvas ref="canvasEl"/></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, shallowRef, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?worker'
import VIcon from './VIcon.vue'
import { store, dataURL } from '../store.js'

const stageEl = ref(null)
const canvasEl = ref(null)
const pdf = shallowRef(null) // shallowRef 避免 Vue 代理破坏 pdf.js 内部私有字段
const loading = ref(false)
const pageNum = ref(1)
const scale = ref(1)
const fit = ref('width')
const loadError = ref('')
let rendering = false
let pendingRender = false
let loadSeq = 0

async function open(url) {
  const seq = ++loadSeq
  try { pdf.value?.destroy() } catch {}
  pdf.value = null
  pageNum.value = 1
  loadError.value = ''
  loading.value = true
  const worker = new PdfWorker()
  try {
    const pdfWorker = new pdfjsLib.PDFWorker({ port: worker })
    try {
      const doc = await pdfjsLib.getDocument({ url, worker: pdfWorker }).promise
      if (seq !== loadSeq) { try { doc.destroy() } catch {}; return }
      pdf.value = doc
      await nextTick()
      await render()
    } finally {
      pdfWorker.destroy()
    }
  } catch (e) {
    if (seq !== loadSeq) return
    console.error('PDF 加载失败:', e)
    loadError.value = '加载失败：' + (e?.message || e) + '（点击左侧航图重试）'
  } finally {
    worker.terminate()
    if (seq === loadSeq) loading.value = false
  }
}

async function render() {
  if (rendering) { pendingRender = true; return }
  rendering = true
  try {
    while (pendingRender || pdf.value) {
      pendingRender = false
      if (!pdf.value || !canvasEl.value) break
      await renderOnce()
      if (!pendingRender) break
    }
  } finally { rendering = false }
}

async function renderOnce() {
  const page = await pdf.value.getPage(pageNum.value)
  const base = page.getViewport({ scale: 1 })
  const availW = stageEl.value.clientWidth - 36
  const availH = stageEl.value.clientHeight - 36
  let s
  if (fit.value === 'width') s = availW / base.width
  else if (fit.value === 'page') s = Math.min(availW / base.width, availH / base.height)
  else s = scale.value
  scale.value = Math.max(0.1, Math.min(8, s))
  const vp = page.getViewport({ scale: scale.value * devicePixelRatio })
  const canvas = canvasEl.value
  canvas.width = Math.floor(vp.width)
  canvas.height = Math.floor(vp.height)
  canvas.style.width = Math.floor(vp.width / devicePixelRatio) + 'px'
  canvas.style.height = Math.floor(vp.height / devicePixelRatio) + 'px'
  await page.render({ canvasContext: canvas.getContext('2d'), viewport: vp }).promise
}

function navChart(delta) {
  const idx = store.curChart + delta
  if (idx < 0 || idx >= store.flatCharts.length) return
  const c = store.flatCharts[idx]
  if (!c || !c.f) return
  store.curChart = idx
  store.viewer = {
    url: dataURL('Terminal', store.airport.icao, c.f),
    title: `${store.airport.icao} ${store.airport.name} — ${c.n.trim()}${c.p ? '  ·  ' + c.p : ''}`,
  }
}

function zoom(d) { fit.value = 'custom'; scale.value *= d; render() }
function goto(d) {
  if (!pdf.value) return
  pageNum.value = Math.min(Math.max(1, pageNum.value + d), pdf.value.numPages)
  render()
}
function print() {
  const c = canvasEl.value
  if (!c?.width) return
  const w = window.open('', '_blank')
  w.document.write(`<title>打印</title><body style="margin:0"><img src="${c.toDataURL()}" style="width:100%" onload="window.print()">`)
  w.document.close()
}

watch(() => store.viewer, async (v) => {
  if (!v?.url) { try { pdf.value?.destroy() } catch {}; pdf.value = null; return }
  await nextTick()
  open(v.url)
})
watch(fit, () => render())

let rt
const onResize = () => { clearTimeout(rt); rt = setTimeout(() => render(), 200) }
onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>
