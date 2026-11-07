<template>
  <div class="admin-panel">
    <div class="admin-head">
      <span>账号管理</span>
      <span class="admin-tip">仅管理员可见；至少需保留一个管理员账号</span>
    </div>

    <form class="admin-add" @submit.prevent="add">
      <input v-model="newName" placeholder="用户名（2-32 位字母/数字/_-）">
      <input v-model="newPwd" type="password" placeholder="密码（至少 6 位）">
      <select v-model="newRole">
        <option value="user">普通用户</option>
        <option value="admin">管理员</option>
      </select>
      <button type="submit" :disabled="busy">添加账号</button>
    </form>
    <p class="admin-err" v-if="error">{{ error }}</p>

    <table class="dtable">
      <thead>
        <tr><th>用户名</th><th>角色</th><th>创建时间</th><th>修改密码</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="u in users" :key="u.username">
          <td class="mono">
            {{ u.username }}
            <span v-if="u.username === store.user.username" class="tag mod">当前</span>
          </td>
          <td>
            <select :value="u.role" :disabled="busy || roleLocked(u)"
                    @change="changeRole(u, $event.target.value)">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </td>
          <td>{{ (u.createdAt || '').slice(0, 10) }}</td>
          <td>
            <div class="pwd-edit">
              <input v-model="u._pwd" type="password" placeholder="新密码" :disabled="busy">
              <button :disabled="busy || !u._pwd" @click="changePwd(u)">保存</button>
            </div>
          </td>
          <td>
            <button class="danger" :disabled="busy || delLocked(u)" @click="remove(u)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import { store } from '../store.js'

const users = ref([])
const newName = ref('')
const newPwd = ref('')
const newRole = ref('user')
const error = ref('')
const busy = ref(false)

function roleLocked(u) {
  // 不能把自己的管理员角色改掉导致没有管理员
  return u.role === 'admin' && users.value.filter(x => x.role === 'admin').length === 1
}
function delLocked(u) {
  return u.username === store.user.username || roleLocked(u)
}

async function run(fn) {
  error.value = ''
  busy.value = true
  try { await fn() } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function reload() { users.value = await api.users() }

function add() {
  run(async () => {
    await api.addUser(newName.value.trim(), newPwd.value, newRole.value)
    newName.value = newPwd.value = ''
    newRole.value = 'user'
    await reload()
  })
}
function changePwd(u) {
  run(async () => {
    await api.updateUser(u.username, { password: u._pwd })
    u._pwd = ''
  })
}
function changeRole(u, role) {
  run(async () => { await api.updateUser(u.username, { role }); await reload() })
}
function remove(u) {
  run(async () => { await api.deleteUser(u.username); await reload() })
}

onMounted(reload)
</script>
