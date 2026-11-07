<template>
  <div class="login">
    <div class="home-bg" aria-hidden="true"></div>
    <form class="login-card" @submit.prevent="submit">
      <h1 class="wordmark-lg">NAIP<span>-Viewer</span></h1>
      <p class="login-sub">请登录以继续</p>

      <label>
        <span>用户名</span>
        <input v-model="username" autocomplete="username" autofocus :disabled="busy">
      </label>
      <label>
        <span>密码</span>
        <input v-model="password" type="password" autocomplete="current-password" :disabled="busy">
      </label>

      <p class="login-err" v-if="error">{{ error }}</p>
      <button class="enter" type="submit" :disabled="busy">
        {{ busy ? '登录中…' : '登 录' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api.js'
import { store } from '../store.js'

const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  if (busy.value) return
  error.value = ''
  busy.value = true
  try {
    store.user = await api.login(username.value.trim(), password.value)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
