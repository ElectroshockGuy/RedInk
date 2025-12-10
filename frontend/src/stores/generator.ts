import { defineStore } from 'pinia'
import type { Page } from '../api'

export interface GeneratedImage {
  index: number
  url: string
  status: 'generating' | 'done' | 'error' | 'retrying'
  error?: string
  retryable?: boolean
}

export interface GeneratorState {
  // 当前阶段
  stage: 'input' | 'outline' | 'generating' | 'result'

  // 用户输入
  topic: string

  // 大纲数据
  outline: {
    raw: string
    pages: Page[]
  }

  // 生成进度
  progress: {
    current: number
    total: number
    status: 'idle' | 'generating' | 'done' | 'error'
  }

  // 生成结果
  images: GeneratedImage[]

  // 任务ID
  taskId: string | null

  // 历史记录ID
  recordId: string | null

  // 用户上传的图片（用于图片生成参考）
  userImages: File[]

  // === 任务队列相关 ===
  // 当前活跃的请求ID（用于校验SSE事件归属）
  currentRequestId: string | null

  // 队列是否正在处理
  queueRunning: boolean

  // === 流式生成大纲相关 ===
  // 是否正在流式生成大纲
  isStreamingOutline: boolean
  // 流式生成的临时内容
  streamingOutlineContent: string
  // 流式生成的页数参数
  streamingPageCount: number | null
}

const STORAGE_KEY = 'generator-state'

// 从 localStorage 加载状态
function loadState(): Partial<GeneratorState> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载状态失败:', e)
  }
  return {}
}

// 保存状态到 localStorage
function saveState(state: GeneratorState) {
  try {
    // 只保存关键数据，不保存 userImages（文件对象无法序列化）
    const toSave = {
      stage: state.stage,
      topic: state.topic,
      outline: state.outline,
      progress: state.progress,
      images: state.images,
      taskId: state.taskId,
      recordId: state.recordId
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
  } catch (e) {
    console.error('保存状态失败:', e)
  }
}

export const useGeneratorStore = defineStore('generator', {
  state: (): GeneratorState => {
    const saved = loadState()
    return {
      stage: saved.stage || 'input',
      topic: saved.topic || '',
      outline: saved.outline || {
        raw: '',
        pages: []
      },
      progress: saved.progress || {
        current: 0,
        total: 0,
        status: 'idle'
      },
      images: saved.images || [],
      taskId: saved.taskId || null,
      recordId: saved.recordId || null,
      userImages: [],  // 不从 localStorage 恢复
      // 任务队列相关
      currentRequestId: null,
      queueRunning: false,
      // 流式生成大纲相关
      isStreamingOutline: false,
      streamingOutlineContent: '',
      streamingPageCount: null
    }
  },

  actions: {
    // 设置主题
    setTopic(topic: string) {
      this.topic = topic
    },

    // 设置大纲
    setOutline(raw: string, pages: Page[]) {
      this.outline.raw = raw
      this.outline.pages = pages
      this.stage = 'outline'
      // 清除流式生成状态
      this.isStreamingOutline = false
      this.streamingOutlineContent = ''
    },

    // 开始流式生成大纲
    startStreamingOutline(topic: string, pageCount: number | null, userImages: File[]) {
      this.topic = topic
      this.streamingPageCount = pageCount
      this.userImages = userImages
      this.isStreamingOutline = true
      this.streamingOutlineContent = ''
      this.outline = { raw: '', pages: [] }
      this.recordId = null
    },

    // 追加流式内容
    appendStreamingContent(content: string) {
      this.streamingOutlineContent += content
    },

    // 完成流式生成大纲
    finishStreamingOutline(raw: string, pages: Page[]) {
      this.outline.raw = raw
      this.outline.pages = pages
      this.stage = 'outline'
      this.isStreamingOutline = false
      this.streamingOutlineContent = ''
    },

    // 流式生成大纲出错
    errorStreamingOutline() {
      this.isStreamingOutline = false
    },

    // 更新页面
    updatePage(index: number, content: string) {
      const page = this.outline.pages.find(p => p.index === index)
      if (page) {
        page.content = content
        // 同步更新 raw 文本
        this.syncRawFromPages()
      }
    },

    // 根据 pages 重新生成 raw 文本
    syncRawFromPages() {
      this.outline.raw = this.outline.pages
        .map(page => page.content)
        .join('\n\n<page>\n\n')
    },

    // 删除页面
    deletePage(index: number) {
      this.outline.pages = this.outline.pages.filter(p => p.index !== index)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 添加页面
    addPage(type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: this.outline.pages.length,
        type,
        content
      }
      this.outline.pages.push(newPage)
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 插入页面
    insertPage(afterIndex: number, type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: afterIndex + 1,
        type,
        content
      }
      this.outline.pages.splice(afterIndex + 1, 0, newPage)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 移动页面 (拖拽排序)
    movePage(fromIndex: number, toIndex: number) {
      const pages = [...this.outline.pages]
      const [movedPage] = pages.splice(fromIndex, 1)
      pages.splice(toIndex, 0, movedPage)

      // 重新索引
      pages.forEach((page, idx) => {
        page.index = idx
      })

      this.outline.pages = pages
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 开始生成 - 返回唯一请求ID
    startGeneration(): string {
      // 生成唯一请求ID
      const requestId = `req_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
      this.currentRequestId = requestId
      this.queueRunning = true

      this.stage = 'generating'
      this.progress.current = 0
      this.progress.total = this.outline.pages.length
      this.progress.status = 'generating'
      this.images = this.outline.pages.map(page => ({
        index: page.index,
        url: '',
        status: 'generating'
      }))

      return requestId
    },

    // 验证请求ID是否为当前活跃请求
    isActiveRequest(requestId: string): boolean {
      return this.currentRequestId === requestId
    },

    // 更新进度（带请求ID校验）
    updateProgressWithValidation(
      requestId: string,
      index: number,
      status: 'generating' | 'done' | 'error',
      url?: string,
      error?: string
    ): boolean {
      // 校验请求ID
      if (!this.isActiveRequest(requestId)) {
        console.warn(`[Generator] 忽略过期请求的事件: ${requestId}, 当前请求: ${this.currentRequestId}`)
        return false
      }

      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = status
        if (url) image.url = url
        if (error) image.error = error
      }
      if (status === 'done') {
        this.progress.current++
      }
      return true
    },

    // 更新进度
    updateProgress(index: number, status: 'generating' | 'done' | 'error', url?: string, error?: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = status
        if (url) image.url = url
        if (error) image.error = error
      }
      if (status === 'done') {
        this.progress.current++
      }
    },

    updateImage(index: number, newUrl: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        const timestamp = Date.now()
        image.url = `${newUrl}?t=${timestamp}`
        image.status = 'done'
        delete image.error
      }
    },

    // 更新图片（带请求ID校验）
    updateImageWithValidation(requestId: string, index: number, newUrl: string): boolean {
      if (!this.isActiveRequest(requestId)) {
        console.warn(`[Generator] 忽略过期请求的图片更新: ${requestId}`)
        return false
      }

      const image = this.images.find(img => img.index === index)
      if (image) {
        const timestamp = Date.now()
        image.url = `${newUrl}?t=${timestamp}`
        image.status = 'done'
        delete image.error
      }
      return true
    },

    // 完成生成
    finishGeneration(taskId: string) {
      this.taskId = taskId
      this.stage = 'result'
      this.progress.status = 'done'
      this.queueRunning = false
    },

    // 完成生成（带请求ID校验）
    finishGenerationWithValidation(requestId: string, taskId: string): boolean {
      if (!this.isActiveRequest(requestId)) {
        console.warn(`[Generator] 忽略过期请求的完成事件: ${requestId}`)
        return false
      }

      this.taskId = taskId
      this.stage = 'result'
      this.progress.status = 'done'
      this.queueRunning = false
      return true
    },

    // 设置单个图片为重试中状态
    setImageRetrying(index: number) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = 'retrying'
      }
    },

    // 获取失败的图片列表
    getFailedImages() {
      return this.images.filter(img => img.status === 'error')
    },

    // 获取失败图片对应的页面
    getFailedPages() {
      const failedIndices = this.images
        .filter(img => img.status === 'error')
        .map(img => img.index)
      return this.outline.pages.filter(page => failedIndices.includes(page.index))
    },

    // 检查是否有失败的图片
    hasFailedImages() {
      return this.images.some(img => img.status === 'error')
    },

    // 重置
    reset() {
      this.stage = 'input'
      this.topic = ''
      this.outline = {
        raw: '',
        pages: []
      }
      this.progress = {
        current: 0,
        total: 0,
        status: 'idle'
      }
      this.images = []
      this.taskId = null
      this.recordId = null
      this.userImages = []
      // 任务队列相关
      this.currentRequestId = null
      this.queueRunning = false
      // 流式生成大纲相关
      this.isStreamingOutline = false
      this.streamingOutlineContent = ''
      this.streamingPageCount = null
      // 清除 localStorage
      localStorage.removeItem(STORAGE_KEY)
    },

    // 保存当前状态
    saveToStorage() {
      saveState(this)
    }
  }
})

// 监听状态变化并自动保存（使用 watch）
import { watch } from 'vue'

export function setupAutoSave() {
  const store = useGeneratorStore()

  // 监听关键字段变化并自动保存
  watch(
    () => ({
      stage: store.stage,
      topic: store.topic,
      outline: store.outline,
      progress: store.progress,
      images: store.images,
      taskId: store.taskId,
      recordId: store.recordId
    }),
    () => {
      store.saveToStorage()
    },
    { deep: true }
  )
}
