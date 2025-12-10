<template>
  <!-- 大纲查看模态框 -->
  <div v-if="visible" class="outline-modal-overlay" @click="handleClose">
    <div class="outline-modal-content" @click.stop>
      <div class="outline-modal-header">
        <h3>完整大纲</h3>
        <div class="header-right">
          <span v-if="loading" class="loading-indicator">
            <span class="spinner-mini"></span>
            加载中...
          </span>
          <span v-else-if="streamingPages.length > 0" class="page-counter">
            {{ streamingPages.length }} 页
          </span>
          <button class="close-icon" @click="handleClose">×</button>
        </div>
      </div>
      <div class="outline-modal-body">
        <!-- 加载状态 -->
        <div v-if="loading && streamingPages.length === 0" class="loading-state">
          <div class="spinner"></div>
          <p>正在加载大纲...</p>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="error" class="error-state">
          <p>{{ error }}</p>
        </div>

        <!-- 流式内容 -->
        <div v-else>
          <div
            v-for="(page, idx) in streamingPages"
            :key="idx"
            class="outline-page-card"
            :class="{ 'streaming': page.streaming }"
          >
            <div class="outline-page-card-header">
              <span class="page-badge">P{{ idx + 1 }}</span>
              <span class="page-type-badge" :class="page.type">{{ getPageTypeName(page.type) }}</span>
              <span class="word-count">{{ page.content.length }} 字</span>
              <span v-if="page.streaming" class="streaming-indicator">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
              </span>
            </div>
            <div class="outline-page-card-content">
              {{ page.content }}<span v-if="page.streaming" class="cursor">|</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 大纲查看模态框组件（流式版本）
 *
 * 通过 SSE 流式获取大纲内容，实时显示加载进度
 * - 支持逐页、逐字显示
 * - 自动忽略心跳包
 * - 关闭时自动中断请求
 */

import { ref, watch, onUnmounted } from 'vue'
import { streamOutline } from '../../api'

// 定义流式页面类型
interface StreamingPage {
  type: 'cover' | 'content' | 'summary'
  content: string
  streaming: boolean
}

// 定义 Props
const props = defineProps<{
  visible: boolean
  recordId: string | null
}>()

// 定义 Emits
const emit = defineEmits<{
  (e: 'close'): void
}>()

// 状态
const streamingPages = ref<StreamingPage[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let abortFn: (() => void) | null = null

/**
 * 获取页面类型的中文名称
 */
function getPageTypeName(type: string): string {
  const names: Record<string, string> = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type] || '内容'
}

/**
 * 开始流式获取大纲
 */
function startStreaming() {
  if (!props.recordId) return

  // 重置状态
  streamingPages.value = []
  loading.value = true
  error.value = null

  const { abort } = streamOutline(props.recordId, {
    onStart: () => {
      loading.value = true
    },
    onPageStart: (index, type) => {
      // 确保数组有足够的长度
      while (streamingPages.value.length <= index) {
        streamingPages.value.push({
          type: 'content',
          content: '',
          streaming: false
        })
      }
      streamingPages.value[index] = {
        type: type as 'cover' | 'content' | 'summary',
        content: '',
        streaming: true
      }
    },
    onChunk: (index, content) => {
      if (streamingPages.value[index]) {
        streamingPages.value[index].content += content
      }
    },
    onPageDone: (index) => {
      if (streamingPages.value[index]) {
        streamingPages.value[index].streaming = false
      }
    },
    onDone: () => {
      loading.value = false
    },
    onError: (err) => {
      loading.value = false
      error.value = err
    }
  })

  abortFn = abort
}

/**
 * 停止流式获取
 */
function stopStreaming() {
  if (abortFn) {
    abortFn()
    abortFn = null
  }
}

/**
 * 关闭模态框
 */
function handleClose() {
  stopStreaming()
  emit('close')
}

// 监听 visible 变化
watch(
  () => props.visible,
  (visible) => {
    if (visible && props.recordId) {
      startStreaming()
    } else {
      stopStreaming()
    }
  },
  { immediate: true }
)

// 组件卸载时清理
onUnmounted(() => {
  stopStreaming()
})
</script>

<style scoped>
/* 模态框遮罩层 */
.outline-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

/* 模态框内容容器 */
.outline-modal-content {
  background: white;
  width: 100%;
  max-width: 800px;
  max-height: 85vh;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* 模态框头部 */
.outline-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.outline-modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666;
}

.page-counter {
  font-size: 13px;
  color: #999;
}

/* 关闭按钮 */
.close-icon {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}

.close-icon:hover {
  color: #333;
}

/* 模态框主体（可滚动） */
.outline-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #f9fafb;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #666;
}

.loading-state p {
  margin-top: 16px;
  font-size: 14px;
}

/* 错误状态 */
.error-state {
  padding: 40px;
  text-align: center;
  color: #dc3545;
}

/* 旋转器 */
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #eee;
  border-top-color: var(--primary, #ff2442);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-mini {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #ddd;
  border-top-color: var(--primary, #ff2442);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 大纲页面卡片 */
.outline-page-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.outline-page-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #d1d5db;
}

.outline-page-card:last-child {
  margin-bottom: 0;
}

.outline-page-card.streaming {
  border-color: var(--primary, #ff2442);
  border-width: 2px;
}

/* 卡片头部 */
.outline-page-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5e7eb;
}

/* 页码标识 */
.page-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 24px;
  padding: 0 8px;
  background: var(--primary, #ff2442);
  color: white;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
}

/* 页面类型标识 */
.page-type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: #e9ecef;
  color: #6c757d;
}

.page-type-badge.cover {
  background: #e3f2fd;
  color: #1976d2;
}

.page-type-badge.content {
  background: #f3e5f5;
  color: #7b1fa2;
}

.page-type-badge.summary {
  background: #e8f5e9;
  color: #388e3c;
}

/* 字数统计 */
.word-count {
  margin-left: auto;
  font-size: 11px;
  color: #999;
}

/* 流式加载指示器 */
.streaming-indicator {
  display: flex;
  gap: 3px;
  margin-left: 8px;
}

.streaming-indicator .dot {
  width: 4px;
  height: 4px;
  background: var(--primary, #ff2442);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite both;
}

.streaming-indicator .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.streaming-indicator .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* 卡片内容 */
.outline-page-card-content {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
}

/* 光标闪烁效果 */
.cursor {
  animation: blink 1s step-end infinite;
  color: var(--primary, #ff2442);
  font-weight: bold;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

/* 响应式布局 */
@media (max-width: 768px) {
  .outline-modal-overlay {
    padding: 20px;
  }

  .outline-modal-content {
    max-height: 90vh;
  }

  .outline-modal-header {
    padding: 16px 20px;
  }

  .outline-modal-body {
    padding: 16px 20px;
  }
}
</style>
