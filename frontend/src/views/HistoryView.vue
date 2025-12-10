<template>
  <div class="container" style="max-width: 1200px;">

    <!-- Header Area -->
    <div class="page-header">
      <div>
        <h1 class="page-title">我的创作</h1>
      </div>
      <div style="display: flex; gap: 10px;">
        <button
          class="btn"
          @click="handleScanAll"
          :disabled="isScanning"
          style="border: 1px solid var(--border-color);"
        >
          <svg v-if="!isScanning" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
          <div v-else class="spinner-small" style="margin-right: 6px;"></div>
          {{ isScanning ? '同步中...' : '同步历史' }}
        </button>
        <button class="btn btn-primary" @click="router.push('/')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          新建图文
        </button>
      </div>
    </div>

    <!-- Stats Overview -->
    <StatsOverview v-if="stats" :stats="stats" />

    <!-- Toolbar: Tabs & Search -->
    <div class="toolbar-wrapper">
      <div class="tabs-container" style="margin-bottom: 0; border-bottom: none;">
        <div
          class="tab-item"
          :class="{ active: currentTab === 'all' }"
          @click="switchTab('all')"
        >
          全部
        </div>
        <div
          class="tab-item"
          :class="{ active: currentTab === 'completed' }"
          @click="switchTab('completed')"
        >
          已完成
        </div>
        <div
          class="tab-item"
          :class="{ active: currentTab === 'draft' }"
          @click="switchTab('draft')"
        >
          草稿箱
        </div>
        <div
          class="tab-item"
          :class="{ active: currentTab === 'archived' }"
          @click="switchTab('archived')"
        >
          已归档
        </div>
        <div
          v-if="orphanTasks.length > 0"
          class="tab-item orphan-tab"
          :class="{ active: currentTab === 'orphan' }"
          @click="switchTab('orphan')"
        >
          孤立任务
          <span class="orphan-badge">{{ orphanTasks.length }}</span>
        </div>
      </div>

      <div class="search-mini">
        <svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索标题..."
          @keyup.enter="handleSearch"
        />
      </div>
    </div>

    <!-- Content Area -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="currentTab === 'orphan'" class="orphan-tasks-container">
      <div class="orphan-header">
        <div class="orphan-info">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
          <span>这些任务在磁盘上有图片文件，但没有关联的历史记录</span>
        </div>
      </div>
      <div class="orphan-grid">
        <div
          v-for="task in orphanTasks"
          :key="task.task_id"
          class="orphan-card"
        >
          <div class="orphan-card-header">
            <span class="orphan-task-id">{{ task.task_id.substring(0, 8) }}...</span>
            <span class="orphan-image-count">{{ task.images_count }} 张图片</span>
          </div>
          <div class="orphan-images-preview">
            <img
              v-for="(img, idx) in task.images.slice(0, 4)"
              :key="idx"
              :src="`/api/images/${task.task_id}/${img}?thumbnail=true`"
              class="orphan-thumb"
              @click="viewOrphanTask(task)"
            />
            <div v-if="task.images.length > 4" class="orphan-more">
              +{{ task.images.length - 4 }}
            </div>
          </div>
          <div class="orphan-card-actions">
            <button class="btn btn-sm" @click="viewOrphanTask(task)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
              查看
            </button>
            <button class="btn btn-sm btn-danger" @click="deleteOrphanTask(task)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="records.length === 0" class="empty-state-large">
      <div class="empty-img">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
      </div>
      <h3>暂无相关记录</h3>
      <p class="empty-tips">去创建一个新的作品吧</p>
    </div>

    <div v-else class="gallery-grid">
      <GalleryCard
        v-for="record in records"
        :key="record.id"
        :record="record"
        @preview="viewImages"
        @edit="loadRecord"
        @delete="confirmDelete"
        @archive="handleArchive"
        @unarchive="handleUnarchive"
      />
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination-wrapper">
       <button class="page-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">Previous</button>
       <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
       <button class="page-btn" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">Next</button>
    </div>

    <!-- Image Viewer Modal -->
    <ImageGalleryModal
      v-if="viewingRecord"
      :visible="!!viewingRecord"
      :record="viewingRecord"
      :regeneratingImages="regeneratingImages"
      @close="closeGallery"
      @showOutline="showOutlineModal = true"
      @regenerate="regenerateHistoryImage"
      @downloadAll="downloadAllImages"
      @download="downloadImage"
    />

    <!-- 大纲查看模态框 -->
    <OutlineModal
      v-if="showOutlineModal && viewingRecord"
      :visible="showOutlineModal"
      :recordId="viewingRecord.id"
      @close="showOutlineModal = false"
    />

    <!-- 孤立任务图片查看器 -->
    <div v-if="viewingOrphanTask" class="orphan-viewer-overlay" @click.self="closeOrphanViewer">
      <div class="orphan-viewer-modal">
        <div class="orphan-viewer-header">
          <h3>孤立任务图片</h3>
          <span class="orphan-viewer-id">{{ viewingOrphanTask.task_id }}</span>
          <button class="close-btn" @click="closeOrphanViewer">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
        <div class="orphan-viewer-body">
          <div class="orphan-viewer-grid">
            <div
              v-for="(img, idx) in viewingOrphanTask.images"
              :key="idx"
              class="orphan-viewer-item"
            >
              <img :src="`/api/images/${viewingOrphanTask.task_id}/${img}?thumbnail=false`" />
              <div class="orphan-viewer-item-info">
                <span>第 {{ idx + 1 }} 页</span>
                <a :href="`/api/images/${viewingOrphanTask.task_id}/${img}?thumbnail=false`" download class="download-link">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  getHistoryList,
  getHistoryStats,
  searchHistory,
  deleteHistory,
  archiveHistory,
  unarchiveHistory,
  getHistory,
  type HistoryRecord,
  regenerateImage as apiRegenerateImage,
  updateHistory,
  scanAllTasks
} from '../api'
import { useGeneratorStore } from '../stores/generator'

// 引入组件
import StatsOverview from '../components/history/StatsOverview.vue'
import GalleryCard from '../components/history/GalleryCard.vue'
import ImageGalleryModal from '../components/history/ImageGalleryModal.vue'
import OutlineModal from '../components/history/OutlineModal.vue'

const router = useRouter()
const route = useRoute()
const store = useGeneratorStore()

// 数据状态
const records = ref<HistoryRecord[]>([])
const loading = ref(false)
const stats = ref<any>(null)
const currentTab = ref('all')
const searchKeyword = ref('')
const currentPage = ref(1)
const totalPages = ref(1)

// 孤立任务状态
interface OrphanTask {
  task_id: string
  images_count: number
  images: string[]
}
const orphanTasks = ref<OrphanTask[]>([])

// 查看器状态
const viewingRecord = ref<any>(null)
const regeneratingImages = ref<Set<number>>(new Set())
const showOutlineModal = ref(false)
const isScanning = ref(false)

/**
 * 加载历史记录列表
 */
async function loadData() {
  loading.value = true
  try {
    // 归档标签页特殊处理
    if (currentTab.value === 'archived') {
      const res = await getHistoryList(currentPage.value, 12, undefined, true, true)
      if (res.success) {
        records.value = res.records
        totalPages.value = res.total_pages
      }
    } else {
      let statusFilter = currentTab.value === 'all' ? undefined : currentTab.value
      // 非归档标签页默认不显示已归档记录
      const res = await getHistoryList(currentPage.value, 12, statusFilter, false, false)
      if (res.success) {
        records.value = res.records
        totalPages.value = res.total_pages
      }
    }
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

/**
 * 加载统计数据
 */
async function loadStats() {
  try {
    const res = await getHistoryStats()
    if (res.success) stats.value = res
  } catch(e) {}
}

/**
 * 切换标签页
 */
function switchTab(tab: string) {
  currentTab.value = tab
  currentPage.value = 1
  loadData()
}

/**
 * 搜索历史记录
 */
async function handleSearch() {
  if (!searchKeyword.value.trim()) {
    loadData()
    return
  }
  loading.value = true
  try {
    const res = await searchHistory(searchKeyword.value)
    if (res.success) {
      records.value = res.records
      totalPages.value = 1
    }
  } catch(e) {} finally {
    loading.value = false
  }
}

/**
 * 加载记录并跳转到编辑页
 */
async function loadRecord(id: string) {
  const res = await getHistory(id)
  if (res.success && res.record) {
    store.setTopic(res.record.title)
    store.setOutline(res.record.outline.raw, res.record.outline.pages)
    store.recordId = res.record.id
    if (res.record.images.generated.length > 0) {
      store.taskId = res.record.images.task_id
      store.images = res.record.outline.pages.map((page, idx) => {
        const filename = res.record!.images.generated[idx]
        return {
          index: idx,
          url: filename ? `/api/images/${res.record!.images.task_id}/${filename}` : '',
          status: filename ? 'done' : 'error',
          retryable: !filename
        }
      })
    }
    router.push('/outline')
  }
}

/**
 * 查看图片
 */
async function viewImages(id: string) {
  const res = await getHistory(id)
  if (res.success) viewingRecord.value = res.record
}

/**
 * 关闭图片查看器
 */
function closeGallery() {
  viewingRecord.value = null
  showOutlineModal.value = false
}

/**
 * 确认删除（可能变成归档）
 */
async function confirmDelete(record: any) {
  if(confirm('确定删除吗？')) {
    const result = await deleteHistory(record.id)
    if (result.success) {
      // 如果实际执行的是归档操作，提示用户
      if (result.action === 'archived') {
        alert(result.message || '记录已归档')
      }
      loadData()
      loadStats()
    }
  }
}

/**
 * 归档记录
 */
async function handleArchive(record: any) {
  if(confirm('确定归档此记录吗？')) {
    const result = await archiveHistory(record.id)
    if (result.success) {
      loadData()
      loadStats()
    } else {
      alert('归档失败: ' + (result.error || '未知错误'))
    }
  }
}

/**
 * 取消归档
 */
async function handleUnarchive(record: any) {
  const result = await unarchiveHistory(record.id)
  if (result.success) {
    loadData()
    loadStats()
  } else {
    alert('取消归档失败: ' + (result.error || '未知错误'))
  }
}

/**
 * 切换页码
 */
function changePage(p: number) {
  currentPage.value = p
  loadData()
}

/**
 * 重新生成历史记录中的图片
 */
async function regenerateHistoryImage(index: number) {
  if (!viewingRecord.value || !viewingRecord.value.images.task_id) {
    alert('无法重新生成：缺少任务信息')
    return
  }

  const page = viewingRecord.value.outline.pages[index]
  if (!page) return

  regeneratingImages.value.add(index)

  try {
    const context = {
      fullOutline: viewingRecord.value.outline.raw || '',
      userTopic: viewingRecord.value.title || ''
    }

    const result = await apiRegenerateImage(
      viewingRecord.value.images.task_id,
      page,
      true,
      context
    )

    if (result.success && result.image_url) {
      const filename = result.image_url.split('/').pop()
      viewingRecord.value.images.generated[index] = filename

      // 刷新图片
      const timestamp = Date.now()
      const imgElements = document.querySelectorAll(`img[src*="${viewingRecord.value.images.task_id}/${filename}"]`)
      imgElements.forEach(img => {
        const baseUrl = (img as HTMLImageElement).src.split('?')[0]
        ;(img as HTMLImageElement).src = `${baseUrl}?t=${timestamp}`
      })

      await updateHistory(viewingRecord.value.id, {
        images: {
          task_id: viewingRecord.value.images.task_id,
          generated: viewingRecord.value.images.generated
        }
      })

      regeneratingImages.value.delete(index)
    } else {
      regeneratingImages.value.delete(index)
      alert('重新生成失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    regeneratingImages.value.delete(index)
    alert('重新生成失败: ' + String(e))
  }
}

/**
 * 下载单张图片
 */
function downloadImage(filename: string, index: number) {
  if (!viewingRecord.value) return
  const link = document.createElement('a')
  link.href = `/api/images/${viewingRecord.value.images.task_id}/${filename}?thumbnail=false`
  link.download = `page_${index + 1}.png`
  link.click()
}

/**
 * 打包下载所有图片
 */
function downloadAllImages() {
  if (!viewingRecord.value) return
  const link = document.createElement('a')
  link.href = `/api/history/${viewingRecord.value.id}/download`
  link.click()
}

/**
 * 扫描所有任务并同步
 */
async function handleScanAll() {
  isScanning.value = true
  try {
    const result = await scanAllTasks()
    if (result.success) {
      let message = `扫描完成！\n`
      message += `- 总任务数: ${result.total_tasks || 0}\n`
      message += `- 同步成功: ${result.synced || 0}\n`
      message += `- 同步失败: ${result.failed || 0}\n`

      // 从 results 中提取孤立任务的详细信息
      if (result.results) {
        const orphans = result.results.filter((r: any) => r.no_record && r.images_count > 0)
        orphanTasks.value = orphans.map((r: any) => ({
          task_id: r.task_id,
          images_count: r.images_count,
          images: r.images || []
        }))
      }

      if (result.orphan_tasks && result.orphan_tasks.length > 0) {
        message += `- 孤立任务（无记录）: ${result.orphan_tasks.length} 个\n`
      }

      alert(message)
      await loadData()
      await loadStats()
    } else {
      alert('扫描失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    console.error('扫描失败:', e)
    alert('扫描失败: ' + String(e))
  } finally {
    isScanning.value = false
  }
}

/**
 * 查看孤立任务图片
 */
const viewingOrphanTask = ref<OrphanTask | null>(null)

function viewOrphanTask(task: OrphanTask) {
  viewingOrphanTask.value = task
}

function closeOrphanViewer() {
  viewingOrphanTask.value = null
}

/**
 * 删除孤立任务
 */
async function deleteOrphanTask(task: OrphanTask) {
  if (!confirm(`确定要删除这个孤立任务吗？\n\n任务ID: ${task.task_id}\n图片数量: ${task.images_count} 张\n\n此操作将永久删除磁盘上的图片文件！`)) {
    return
  }

  try {
    const response = await fetch(`/api/history/orphan/${task.task_id}`, {
      method: 'DELETE'
    })
    const result = await response.json()

    if (result.success) {
      orphanTasks.value = orphanTasks.value.filter(t => t.task_id !== task.task_id)
      alert('孤立任务已删除')
    } else {
      alert('删除失败: ' + (result.error || '未知错误'))
    }
  } catch (e) {
    console.error('删除孤立任务失败:', e)
    alert('删除失败: ' + String(e))
  }
}

onMounted(async () => {
  await loadData()
  await loadStats()

  // 检查路由参数，如果有 ID 则自动打开图片查看器
  if (route.params.id) {
    await viewImages(route.params.id as string)
  }

  // 自动执行一次扫描（静默，不显示结果）
  try {
    const result = await scanAllTasks()
    if (result.success) {
      // 提取孤立任务信息
      if (result.results) {
        const orphans = result.results.filter((r: any) => r.no_record && r.images_count > 0)
        orphanTasks.value = orphans.map((r: any) => ({
          task_id: r.task_id,
          images_count: r.images_count,
          images: r.images || []
        }))
      }
      if ((result.synced || 0) > 0) {
        await loadData()
        await loadStats()
      }
    }
  } catch (e) {
    console.error('自动扫描失败:', e)
  }
})
</script>

<style scoped>
/* Small Spinner */
.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Toolbar */
.toolbar-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0;
}

.search-mini {
  position: relative;
  width: 240px;
  margin-bottom: 10px;
}

.search-mini input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border-radius: 100px;
  border: 1px solid var(--border-color);
  font-size: 14px;
  background: white;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-mini input:focus {
  border-color: var(--primary);
  outline: none;
  box-shadow: 0 0 0 3px var(--primary-light);
}

.search-mini .icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #ccc;
}

/* Gallery Grid */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
  margin-bottom: 40px;
}

/* Pagination */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 40px;
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: white;
  border-radius: 6px;
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Empty State */
.empty-state-large {
  text-align: center;
  padding: 80px 0;
  color: var(--text-sub);
}

.empty-img {
  font-size: 64px;
  opacity: 0.5;
}

.empty-state-large .empty-tips {
  margin-top: 10px;
  color: var(--text-placeholder);
}

/* Orphan Tasks Styles */
.orphan-tab {
  display: flex;
  align-items: center;
  gap: 6px;
}

.orphan-badge {
  background: #ff4d4f;
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
}

.orphan-tasks-container {
  padding: 0;
}

.orphan-header {
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 24px;
}

.orphan-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #d46b08;
  font-size: 14px;
}

.orphan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.orphan-card {
  background: white;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  overflow: hidden;
  transition: all 0.2s;
}

.orphan-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.orphan-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid var(--border-color);
}

.orphan-task-id {
  font-family: monospace;
  font-size: 13px;
  color: var(--text-sub);
}

.orphan-image-count {
  font-size: 12px;
  color: var(--text-placeholder);
}

.orphan-images-preview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 8px;
  min-height: 80px;
}

.orphan-thumb {
  width: 100%;
  aspect-ratio: 9/16;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.orphan-thumb:hover {
  opacity: 0.8;
}

.orphan-more {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border-radius: 4px;
  color: var(--text-sub);
  font-size: 12px;
}

.orphan-card-actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-danger {
  background: #fff1f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.btn-danger:hover {
  background: #ff4d4f;
  color: white;
}

/* Orphan Viewer Modal */
.orphan-viewer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.orphan-viewer-modal {
  background: white;
  border-radius: 16px;
  max-width: 1200px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.orphan-viewer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
}

.orphan-viewer-header h3 {
  margin: 0;
  font-size: 18px;
}

.orphan-viewer-id {
  font-family: monospace;
  font-size: 13px;
  color: var(--text-sub);
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 4px;
}

.orphan-viewer-header .close-btn {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-sub);
  padding: 4px;
}

.orphan-viewer-header .close-btn:hover {
  color: var(--text-main);
}

.orphan-viewer-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.orphan-viewer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.orphan-viewer-item {
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
}

.orphan-viewer-item img {
  width: 100%;
  aspect-ratio: 9/16;
  object-fit: cover;
}

.orphan-viewer-item-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-sub);
}

.download-link {
  color: var(--text-sub);
  transition: color 0.2s;
}

.download-link:hover {
  color: var(--primary);
}
</style>
