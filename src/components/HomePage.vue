<template>
  <div class="home">
    <div class="home-bg" aria-hidden="true"></div>
    <button class="theme-btn" @click="$emit('toggleTheme')" :title="theme === 'dark' ? '切换浅色' : '切换深色'">
      <VIcon :name="theme === 'dark' ? 'sun' : 'moon'" :size="17"/>
    </button>

    <main class="home-center">
      <h1>NAIP<span>-Viewer</span></h1>
      <p class="sub">中国民航国内航空资料汇编</p>

      <div class="meta">
        <span>{{ store.meta.DataVersion }}</span>
        <i/>
        <span>生效日期 {{ store.meta.EffectiveDate }}</span>
        <i/>
        <span>{{ store.airports.length }} 个机场</span>
      </div>

      <button class="enter" @click="$emit('enter')">
        立即进入
        <VIcon name="right" :size="15"/>
      </button>
    </main>
  </div>
</template>

<script setup>
import VIcon from './VIcon.vue'
import { store } from '../store.js'

defineProps({ theme: String })
defineEmits(['enter', 'toggleTheme'])
</script>
