import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    proxy: {
      // SSE 流式端点 - 需要特殊配置禁用缓冲
      '/api/outline/stream': {
        target: 'http://localhost:12398',
        changeOrigin: true,
        // 关闭代理超时，避免长连接被中断
        timeout: 0,
        proxyTimeout: 0,
        configure: (proxy) => {
          // 禁用响应缓冲
          proxy.on('proxyRes', (proxyRes, _req, res) => {
            // 确保响应头正确
            proxyRes.headers['X-Accel-Buffering'] = 'no'
            proxyRes.headers['Cache-Control'] = 'no-cache'
            proxyRes.headers['Connection'] = 'keep-alive'
            // 禁用 Node.js 的响应缓冲
            if (res && typeof res.flushHeaders === 'function') {
              res.flushHeaders()
            }
          })
        }
      },
      // 图片生成流式端点
      '/api/generate': {
        target: 'http://localhost:12398',
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0
      },
      // 历史记录大纲流式端点
      '/api/history': {
        target: 'http://localhost:12398',
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0
      },
      // 其他 API 端点
      '/api': {
        target: 'http://localhost:12398',
        changeOrigin: true
      }
    }
  }
})
