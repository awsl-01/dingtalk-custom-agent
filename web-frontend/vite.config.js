import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',  // 使用相对路径
  server: {
    port: 9981,
    proxy: {
      '/api': {
        target: 'http://localhost:8913',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: '../web/static',
    emptyOutDir: true,
  }
})
