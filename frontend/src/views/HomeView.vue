<template>
  <div class="container home-container">
    <!-- 图片网格轮播背景 -->
    <ShowcaseBackground />

    <!-- Hero Area -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="brand-pill">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
          AI 驱动的红墨创作助手
        </div>
        <div class="platform-slogan">
          让传播不再需要门槛，让创作从未如此简单
        </div>
        <h1 class="page-title">灵感一触即发</h1>
        <p class="page-subtitle">输入你的创意主题，让 AI 帮你生成爆款标题、正文和封面图</p>
      </div>

      <!-- 主题输入组合框 -->
      <ComposerInput
        ref="composerRef"
        v-model="topic"
        :loading="loading"
        @generate="handleGenerate"
        @imagesChange="handleImagesChange"
        @pageCountChange="handlePageCountChange"
      />

      <!-- 流式生成预览区域 -->
      <div v-if="loading" class="streaming-preview">
        <div class="streaming-header">
          <div class="streaming-indicator">
            <span class="dot"></span>
            正在生成大纲...
          </div>
        </div>
        <div class="streaming-content" ref="streamingContentRef">
          <pre v-if="streamingContent">{{ streamingContent }}</pre>
          <div v-else class="streaming-placeholder">等待 AI 响应中...</div>
        </div>
      </div>
    </div>

    <!-- 版权信息 -->
    <div class="page-footer">
      <div class="footer-copyright">
        © 2025 <a href="https://github.com/HisMax/RedInk" target="_blank" rel="noopener noreferrer">RedInk</a> by 默子 (Histone)
      </div>
      <div class="footer-license">
        Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { generateOutlineStream } from '../api'

// 引入组件
import ShowcaseBackground from '../components/home/ShowcaseBackground.vue'
import ComposerInput from '../components/home/ComposerInput.vue'

const router = useRouter()
const store = useGeneratorStore()

// 状态
const topic = ref('')
const loading = ref(false)
const error = ref('')
const composerRef = ref<InstanceType<typeof ComposerInput> | null>(null)
const streamingContentRef = ref<HTMLElement | null>(null)

// 上传的图片文件
const uploadedImageFiles = ref<File[]>([])

// 指定的页数
const pageCount = ref(0) // 0 表示自动

// 流式生成内容
const streamingContent = ref('')

// 流式生成控制器
let streamAbortController: { abort: () => void } | null = null

/**
 * 处理图片变化
 */
function handleImagesChange(images: File[]) {
  uploadedImageFiles.value = images
}

/**
 * 处理页数变化
 */
function handlePageCountChange(count: number) {
  pageCount.value = count
}

/**
 * 自动滚动到底部
 */
function scrollToBottom() {
  nextTick(() => {
    if (streamingContentRef.value) {
      streamingContentRef.value.scrollTop = streamingContentRef.value.scrollHeight
    }
  })
}

/**
 * 生成大纲（流式）
 */
async function handleGenerate() {
  if (!topic.value.trim()) return

  loading.value = true
  error.value = ''
  streamingContent.value = ''

  const imageFiles = uploadedImageFiles.value
  const targetPageCount = composerRef.value?.getPageCount() || pageCount.value

  // 使用流式生成
  streamAbortController = generateOutlineStream(
    topic.value.trim(),
    imageFiles.length > 0 ? imageFiles : undefined,
    targetPageCount > 0 ? targetPageCount : undefined,
    {
      onChunk: (content) => {
        streamingContent.value += content
        scrollToBottom()
      },
      onDone: (result) => {
        loading.value = false
        streamingContent.value = ''
        streamAbortController = null

        store.setTopic(topic.value.trim())
        store.setOutline(result.outline || '', result.pages)
        store.recordId = null

        // 保存用户上传的图片到 store
        if (imageFiles.length > 0) {
          store.userImages = imageFiles
        } else {
          store.userImages = []
        }

        // 清理 ComposerInput 的预览
        composerRef.value?.clearPreviews()
        uploadedImageFiles.value = []

        router.push('/outline')
      },
      onError: (errorMsg) => {
        loading.value = false
        streamingContent.value = ''
        streamAbortController = null
        error.value = errorMsg || '生成大纲失败'
      }
    }
  )
}
</script>

<style scoped>
.home-container {
  max-width: 1100px;
  padding-top: 10px;
  position: relative;
  z-index: 1;
}

/* Hero Section */
.hero-section {
  text-align: center;
  margin-bottom: 40px;
  padding: 50px 60px;
  animation: fadeIn 0.6s ease-out;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(10px);
}

.hero-content {
  margin-bottom: 36px;
}

.brand-pill {
  display: inline-block;
  padding: 6px 16px;
  background: rgba(255, 36, 66, 0.08);
  color: var(--primary);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;
  letter-spacing: 0.5px;
}

.platform-slogan {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 24px;
  line-height: 1.6;
  letter-spacing: 0.5px;
}

.page-subtitle {
  font-size: 16px;
  color: var(--text-sub);
  margin-top: 12px;
}

/* Page Footer */
.page-footer {
  text-align: center;
  padding: 24px 0 16px;
  margin-top: 20px;
}

.footer-copyright {
  font-size: 15px;
  color: #333;
  font-weight: 500;
  margin-bottom: 6px;
}

.footer-copyright a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.footer-copyright a:hover {
  text-decoration: underline;
}

.footer-license {
  font-size: 13px;
  color: #999;
}

.footer-license a {
  color: #666;
  text-decoration: none;
}

.footer-license a:hover {
  color: var(--primary);
}

/* Error Toast */
.error-toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  background: #FF4D4F;
  color: white;
  padding: 12px 24px;
  border-radius: 50px;
  box-shadow: 0 8px 24px rgba(255, 77, 79, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1000;
  animation: slideUp 0.3s ease-out;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Streaming Preview */
.streaming-preview {
  margin-top: 24px;
  border: 1px solid rgba(255, 36, 66, 0.2);
  border-radius: 16px;
  overflow: hidden;
  animation: fadeIn 0.3s ease-out;
}

.streaming-header {
  background: linear-gradient(135deg, rgba(255, 36, 66, 0.08), rgba(255, 36, 66, 0.04));
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 36, 66, 0.1);
}

.streaming-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--primary);
}

.streaming-indicator .dot {
  width: 8px;
  height: 8px;
  background: var(--primary);
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.streaming-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 16px;
  background: #fafafa;
}

.streaming-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-main);
  text-align: left;
}

.streaming-placeholder {
  color: #999;
  font-size: 14px;
  text-align: center;
  padding: 20px;
}

.streaming-content::-webkit-scrollbar {
  width: 6px;
}

.streaming-content::-webkit-scrollbar-track {
  background: transparent;
}

.streaming-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}

.streaming-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}
</style>
