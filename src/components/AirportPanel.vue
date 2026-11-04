<template>
  <div class="airport-panel">
    <!-- 一级：机场列表 -->
    <template v-if="!store.airport">
      <div class="list" ref="listEl">
        <div v-for="a in filtered" :key="a.icao" class="row" @click="select(a)">
          <span class="code">{{ a.icao }}</span>
          <span class="name">{{ a.name }}</span>
          <span class="meta">{{ a.bureau }}</span>
        </div>
        <div class="count" v-if="filtered.length">{{ filtered.length }} 个机场</div>
      </div>
    </template>

    <!-- 二级：航图分组 -->
    <template v-else>
      <div class="back" @click="back">
        <VIcon name="left" :size="14"/>
        <span class="code">{{ store.airport.icao }}</span>
        <span class="name">{{ store.airport.name }}</span>
      </div>
      <div class="detail" v-if="detail">
        <span>标高 {{ detail.elev }}{{ detail.uom }}</span>
        <span v-if="detail.magvar">磁差 {{ detail.magvar }}°</span>
        <span v-if="detail.transAlt">过渡高度 {{ detail.transAlt }}{{ detail.uom }}</span>
        <span v-if="detail.transLvl">过渡高度层 {{ detail.transLvl }}</span>
        <span v-if="detail.intl === 'Y'" class="intl">国际</span>
        <div class="rwys" v-if="detail.rwys?.length">
          <span v-for="r in detail.rwys" :key="r.desig">
            {{ r.desig.trim() }} · {{ r.len }}m{{ r.comp ? ' ' + r.comp : '' }}
          </span>
        </div>
      </div>
      <div class="list">
        <div v-for="(g, gi) in groups" :key="g.label" class="group">
          <div class="group-h" @click="toggle(gi)">
            <span>{{ g.label }}</span>
            <span class="n">{{ g.items.length }}</span>
          </div>
          <div class="group-b" v-show="!closedSet.has(gi)">
            <div v-for="(c, ci) in g.items" :key="ci"
                 class="chart" :class="{ active: isActive(g, c) }"
                 @click="openChart(c, g)">
              <span class="pg">{{ c.p || '—' }}</span>
              <span class="cn">{{ c.n.trim() }}</span>
              <span v-if="c.s" class="tag sup">SUP</span>
              <span v-if="c.m" class="tag mod">修订</span>
              <span v-if="!c.f" class="tag nopdf">无文件</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import VIcon from './VIcon.vue'
import { store, loadJSON, dataURL, CHART_GROUPS } from '../store.js'

const closedSet = ref(null)

const filtered = computed(() => {
  const q = store.search.trim().toUpperCase()
  if (!q) return store.airports
  return store.airports.filter(a => a.icao.includes(q) || a.name.toUpperCase().includes(q))
})

const detail = computed(() => store.details[store.airport?.icao])
const groups = computed(() => {
  const byType = {}
  for (const c of store.charts) (byType[c.t] ??= []).push(c)
  const out = []
  for (const [label, types] of CHART_GROUPS) {
    const items = types.flatMap(t => byType[t] || [])
    if (items.length) out.push({ label, items })
  }
  return out
})

function toggle(gi) {
  const s = new Set(closedSet.value)
  s.has(gi) ? s.delete(gi) : s.add(gi)
  closedSet.value = s
}

watch([() => store.airport, groups], () => {
  closedSet.value = new Set(groups.value.map((_, i) => i).filter(i => i > 0))
}, { immediate: true, deep: false })

async function select(a) {
  store.airport = a
  store.charts = await loadJSON(`/data/index/charts/${encodeURIComponent(a.icao)}.json`)
  store.curChart = -1
  store.viewer = null
}

function back() {
  store.airport = null
  store.viewer = null
  store.curChart = -1
}

function flatIndex(groups, g, c) {
  let i = 0
  for (const gg of groups) {
    for (const cc of gg.items) {
      if (gg === g && cc === c) return i
      i++
    }
  }
  return -1
}

function isActive(g, c) {
  return flatIndex(groups.value, g, c) === store.curChart
}

function openChart(c, g) {
  if (!c.f) return
  store.flatCharts = groups.value.flatMap(gg => gg.items)
  store.curChart = flatIndex(groups.value, g, c)
  store.viewer = {
    url: dataURL('Terminal', store.airport.icao, c.f),
    title: `${store.airport.icao} ${store.airport.name} — ${c.n.trim()}${c.p ? '  ·  ' + c.p : ''}`,
  }
}
</script>
