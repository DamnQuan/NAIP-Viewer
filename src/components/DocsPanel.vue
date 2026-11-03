<template>
  <div class="docs-panel">
    <div class="list">
      <template v-if="q">
        <!-- 搜索：平铺全部匹配 -->
        <div v-for="n in flat" :key="n.p" class="row"
             :class="{ active: store.viewer?.url === docURL(n) }" @click="open(n)">
          <VIcon name="doc" :size="13" class="ico"/>
          <span class="name">{{ n.t }}</span>
        </div>
        <div class="count" v-if="!flat.length">无匹配文件</div>
      </template>
      <template v-else>
        <!-- 目录树（两级） -->
        <template v-for="n in tree" :key="n.p || n.t">
          <div class="row" :class="{ active: store.viewer?.url === docURL(n) }" @click="open(n)">
            <VIcon name="doc" :size="14" class="ico"/>
            <span class="name">{{ n.t }}</span>
          </div>
          <div v-for="c in n.c" :key="c.p" class="row sub" @click="open(c)">
            <VIcon name="doc" :size="13" class="ico"/>
            <span class="name">{{ c.t }}</span>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VIcon from './VIcon.vue'
import { store, loadJSON, dataURL } from '../store.js'

const tree = ref([])
const q = ref('')
onMounted(async () => { tree.value = await loadJSON('/data/index/docs.json') })

// 递归平铺，供搜索
const flat = computed(() => {
  const s = q.value.trim().toLowerCase()
  const out = []
  const walk = (nodes) => {
    for (const n of nodes) {
      if (n.p && n.t.toLowerCase().includes(s)) out.push(n)
      if (n.c?.length) walk(n.c)
    }
  }
  walk(tree.value)
  return out
})

const docURL = (n) => dataURL('GeneralDoc', n.p)

function open(n) {
  // 每次新对象，失败可重试
  store.viewer = { url: docURL(n), title: 'NAIP 总资料 — ' + n.t }
}

// 搜索框由 App 侧栏提供，双向同步
function setSearch(v) { q.value = v }
defineExpose({ setSearch })
</script>
