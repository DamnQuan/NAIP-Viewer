<template>
  <div class="viewer">
    <div class="toolbar">
      <div class="tool-group" v-if="store.tab === 'charts' && store.curChart >= 0">
        <button class="tb" @click="navChart(-1)" title="上一张 (PgUp)"><VIcon name="left" :size="14"/> 上一张</button>
        <button class="tb" @click="navChart(1)" title="下一张 (PgDn)">下一张 <VIcon name="right" :size="14"/></button>
        <span class="vline"/>
      </div>
      <button class="tb icon" @click="zoom(1/1.25)" title="缩小"><VIcon name="zoomOut" :size="15"/></button>
      <input class="zoom-input" v-model="zoomText" @change="applyZoomText" @keydown.enter="applyZoomText"
             title="输入缩放百分比" :disabled="!pdf">%
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
        <div class="paper"><canvas :key="canvasKey" ref="canvasEl"/></div>
      </div>
      <div v-if="loadError && pdf" class="empty stage-error">
        <p class="err">{{ loadError }}</p>
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
const canvasKey = ref(0) // 每次打开换新 canvas：渲染中途销毁文档会让旧 canvas 被 pdf.js 锁死
let renderTask = null
let rendering = false
let pendingRender = false
let renderStartedAt = 0
let loadSeq = 0
let quality = 0.6 // backing 分辨率系数，按实测渲染速度自适应（0.35–1）
let currentUrl = ''

// 应用级共享 worker：显式传给 getDocument，pdf.js 便不会在文档销毁时
// 连带销毁 worker（否则连点同一文件会撞上 pendingDestroy 竞态）
let sharedWorker = null
let sharedPort = null
function makeWorker() {
  sharedPort = new PdfWorker()
  sharedWorker = new pdfjsLib.PDFWorker({ port: sharedPort })
}
makeWorker()
function resetWorker() {
  try { sharedWorker.destroy() } catch {}
  try { sharedPort.terminate() } catch {}
  makeWorker()
}

function cancelRender() {
  try { renderTask?.cancel() } catch {}
  renderTask = null
}

// worker 异常时渲染请求可能永不返回，超时熔断防止队列锁死
function withDeadline(p, ms) {
  let timer
  const t = new Promise((_, rej) => { timer = setTimeout(() => rej(new Error('渲染超时')), ms) })
  t.catch(() => {})
  return Promise.race([p, t]).finally(() => clearTimeout(timer))
}

function releaseDoc() {
  cancelRender()
  try { pdf.value?.destroy() } catch {}
  pdf.value = null
  currentUrl = ''
}

async function open(url) {
  // 同一文件重复点击且文档已就绪：无需重新加载
  if (currentUrl === url && pdf.value && !loadError.value) return
  const seq = ++loadSeq
  cancelRender()
  try { await pdf.value?.destroy() } catch {}
  pdf.value = null
  currentUrl = ''
  pageNum.value = 1
  loadError.value = ''
  loading.value = true
  canvasKey.value++
  try {
    const doc = await withDeadline(
      pdfjsLib.getDocument({ url, worker: sharedWorker }).promise, 60000)
    if (seq !== loadSeq) { try { doc.destroy() } catch {}; return }
    currentUrl = url
    pdf.value = doc
    await nextTick()
    await render()
  } catch (e) {
    if (seq !== loadSeq) return
    console.error('PDF 加载失败:', e)
    loadError.value = '加载失败：' + (e?.message || e) + '（点击左侧重试）'
    resetWorker() // worker 可能已损坏，重建以便下次加载
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

async function render() {
  if (rendering) {
    pendingRender = true
    // 渲染已进行超过 0.8s 时来了新请求：取消旧任务立即转向新参数
    if (renderStartedAt && performance.now() - renderStartedAt > 800) cancelRender()
    return
  }
  rendering = true
  const seq = loadSeq
  try {
    while (seq === loadSeq) {
      pendingRender = false
      if (!pdf.value || !canvasEl.value) break
      renderStartedAt = performance.now()
      await renderOnce()
      if (!pendingRender || seq !== loadSeq) break
    }
  } catch (e) {
    pendingRender = false
    console.error('渲染失败:', e)
    loadError.value = '渲染失败：' + (e?.message || e) + '（重新点击可重试）'
  } finally { rendering = false }
}

async function renderOnce() {
  const page = await withDeadline(pdf.value.getPage(pageNum.value), 30000)
  const base = page.getViewport({ scale: 1 })
  const availW = stageEl.value.clientWidth - 36
  const availH = stageEl.value.clientHeight - 36
  let s
  if (fit.value === 'width') s = availW / base.width
  else if (fit.value === 'page') s = Math.min(availW / base.width, availH / base.height)
  else s = scale.value
  scale.value = Math.max(0.1, Math.min(8, s))

  // 显示尺寸跟随 CSS 缩放；backing 分辨率 = CSS 尺寸 × DPR × 自适应质量，
  // 并设硬上限，避免慢环境里单次渲染耗时失控
  const cssW = Math.floor(base.width * scale.value)
  const cssH = Math.floor(base.height * scale.value)
  let bs = devicePixelRatio * quality
  if (cssW * cssH * bs * bs > 12_000_000) {
    bs = Math.max(0.4, Math.sqrt(12_000_000 / (cssW * cssH)))
  }
  const canvas = canvasEl.value
  canvas.width = Math.floor(cssW * bs)
  canvas.height = Math.floor(cssH * bs)
  canvas.style.width = cssW + 'px'
  canvas.style.height = cssH + 'px'
  const task = page.render({ canvasContext: canvas.getContext('2d'),
    viewport: page.getViewport({ scale: scale.value * bs }) })
  renderTask = task
  const t0 = performance.now()
  try {
    await withDeadline(task.promise, 90000)
    const ms = performance.now() - t0
    if (ms > 2500 && quality > 0.35) quality = Math.max(0.35, quality * 0.65)
    else if (ms < 900 && quality < 1) quality = Math.min(1, quality / 0.65)
  } catch (e) {
    if (e?.name === 'RenderingCancelledException') return
    try { task.cancel() } catch {}
    throw e
  } finally {
    if (renderTask === task) renderTask = null
  }
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

// 手动输入缩放百分比（10–800）
const zoomText = ref('100%')
watch(scale, (v) => { zoomText.value = Math.round(v * 100) + '%' })
function applyZoomText() {
  const n = parseFloat(zoomText.value)
  if (!Number.isFinite(n)) { zoomText.value = Math.round(scale.value * 100) + '%'; return }
  fit.value = 'custom'
  scale.value = Math.max(0.1, Math.min(8, n / 100))
  render()
}

// Ctrl/Cmd + 滚轮在 PDF 区域内缩放；不带 Ctrl 保持正常滚动
function onWheel(e) {
  if (!e.ctrlKey && !e.metaKey) return
  if (!pdf.value) return
  e.preventDefault()
  fit.value = 'custom'
  const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
  scale.value = Math.max(0.1, Math.min(8, scale.value * factor))
  render()
}
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
  if (!v?.url) { releaseDoc(); return }
  await nextTick()
  open(v.url)
})
watch(fit, () => render())

let rt
const onResize = () => { clearTimeout(rt); rt = setTimeout(() => render(), 200) }
onMounted(() => {
  window.addEventListener('resize', onResize)
  stageEl.value?.addEventListener('wheel', onWheel, { passive: false })
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  stageEl.value?.removeEventListener('wheel', onWheel)
  releaseDoc()
})
</script>
