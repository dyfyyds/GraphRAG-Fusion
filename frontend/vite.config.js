import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          const normalized = id.replace(/\\/g, '/')
          if (normalized.includes('/echarts/')) return 'chart-vendor'
          if (
            normalized.includes('/three/') ||
            normalized.includes('/d3') ||
            normalized.includes('/gsap/')
          ) return 'graph-vendor'
          if (
            normalized.includes('/markdown-it/') ||
            normalized.includes('/highlight.js/')
          ) return 'markdown-vendor'
          if (
            normalized.includes('/element-plus/') ||
            normalized.includes('/@element-plus/')
          ) return 'element-vendor'
          if (
            normalized.includes('/vue/') ||
            normalized.includes('/vue-router/') ||
            normalized.includes('/pinia/') ||
            normalized.includes('/@vue/')
          ) return 'vue-vendor'
          return 'vendor'
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
