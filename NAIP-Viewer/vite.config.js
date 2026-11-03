import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173 },
  build: {
    // 原始航图数据（public/data，体积大）不拷贝进 dist，
    // 部署时把 public/data 链接或拷贝为 dist/data 即可（见 README）
    copyPublicDir: false,
  },
})
