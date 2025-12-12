# 红墨 API 文档

本文件说明如何直接调用后端 API（默认地址 `http://localhost:12398/api`）。所有接口均为 JSON，除文件上传需使用 `multipart/form-data`，流式接口通过 SSE 返回。部署为 Docker 时，请替换为容器对外暴露的地址。

## 鉴权
- 可选登录：后端支持简单的密码登录，设置环境变量 `ADMIN_PASSWORD`（或编辑 `auth.yaml`）后生效。
- 获取 token：`POST /api/auth/login`，请求体 `{ "password": "your-password" }`，成功返回 `{ "success": true, "token": "..." }`。
- 校验 token：`GET /api/auth/check`，`Authorization: Bearer <token>`，返回 `{ "valid": true/false }`。目前其他接口默认未强制校验，可按需在网关/反向代理层限制。

## 通用约定
- Base URL：`/api`
- Content-Type：默认 `application/json`；上传图片请用 `multipart/form-data`。
- 图片地址：形如 `/api/images/<task_id>/<filename>`，`?thumbnail=true|false` 控制缩略图。
- 错误结构：`{ "success": false, "error": "错误原因" }`。
- SSE 监听：使用 `curl -N` 或浏览器 `EventSource`；事件名见各接口说明。

## 大纲接口

### 1) 生成大纲
- `POST /api/outline`
- JSON 请求：`{ "topic": "秋季显白美甲", "images": ["<base64...>"], "page_count": 12 }`
- 或 `multipart/form-data`：字段 `topic`，可多文件 `images`，可选 `page_count`。
- 返回：
```json
{
  "success": true,
  "outline": "完整文本...",
  "pages": [
    {"index": 0, "type": "cover", "content": "..."},
    {"index": 1, "type": "content", "content": "..."}
  ],
  "has_images": true
}
```

### 2) 流式生成大纲（SSE）
- `POST /api/outline/stream`
- JSON 请求同上。
- 事件：
  - `start`：流开始
  - `chunk`：`{ "content": "分片文本" }`
  - `heartbeat`：保持连接
  - `done`：`{ "outline": "...", "pages": [...], "has_images": true }`
  - `error`：`{ "error": "原因" }`
- 示例：
```bash
curl -N -X POST http://localhost:12398/api/outline/stream \
  -H "Content-Type: application/json" \
  -d '{"topic":"秋季显白美甲","page_count":8}'
```

## 图片生成接口

### 1) 批量生成图片（SSE）
- `POST /api/generate`
- 请求体示例：
```json
{
  "task_id": "task_abc123",          // 可选，不传则自动生成
  "pages": [
    {"index":0,"type":"cover","content":"封面描述"},
    {"index":1,"type":"content","content":"页面描述"}
  ],
  "full_outline": "完整大纲文本",     // 可选，用于保持风格一致
  "user_topic": "用户原始输入",       // 可选
  "user_images": ["<base64 png/jpg>"] // 可选，参考图
}
```
- 事件：
  - `progress`：`{ index, status, current, total, phase }`
  - `complete`：`{ index, status:"done", image_url, phase }`
  - `error`：`{ index, status:"error", message, retryable, phase }`
  - `finish`：`{ success, task_id, images:[filename...], total, completed, failed, failed_indices }`
- 示例监听：
```bash
curl -N -X POST http://localhost:12398/api/generate \
  -H "Content-Type: application/json" \
  -d '{"pages":[{"index":0,"type":"cover","content":"封面"}]}'
```

### 2) 获取图片
- `GET /api/images/<task_id>/<filename>?thumbnail=true|false`
- 默认返回缩略图；`thumbnail=false` 返回原图。404 时返回错误 JSON。

### 3) 重试/重新生成
- 单张重试：`POST /api/retry`
```json
{ "task_id": "task_abc123", "page": {"index":1,"type":"content","content":"..."},
  "use_reference": true }
```
- 批量重试失败（SSE）：`POST /api/retry-failed`，请求体 `{ "task_id": "...", "pages": [<page对象>...] }`，事件包含 `retry_start`、`complete`、`error`、`retry_finish`。
- 重新生成（即便已成功）：`POST /api/regenerate`，字段同单张重试，并可携带 `full_outline`、`user_topic`。

### 4) 任务状态
- `GET /api/task/<task_id>`
- 返回示例：
```json
{
  "success": true,
  "state": {
    "generated": {"0":"0.png"},
    "failed": {"2":"错误信息"},
    "has_cover": true
  }
}
```

### 5) 健康检查
- `GET /api/health` -> `{ "success": true, "message": "服务正常运行" }`

## 历史记录接口

### CRUD
- 创建：`POST /api/history`，`{ "topic": "标题", "outline": { ... }, "task_id": "可选任务ID" }`，返回 `{ "record_id": "..." }`
- 列表：`GET /api/history?page=1&page_size=20&status=all&include_archived=true&archived_only=false`
- 详情：`GET /api/history/<record_id>`
- 更新：`PUT /api/history/<record_id>`，可带 `outline` / `images` / `status` / `thumbnail`
- 删除：`DELETE /api/history/<record_id>`（若 `ALLOW_DELETE=false`，实际执行归档）

### 归档
- 归档：`POST /api/history/<record_id>/archive`
- 取消归档：`POST /api/history/<record_id>/unarchive`

### 搜索与统计
- 搜索：`GET /api/history/search?keyword=xxx`
- 统计：`GET /api/history/stats` -> `{ "total": 10, "by_status": {...} }`

### 扫描与清理
- 同步单任务图片：`GET /api/history/scan/<task_id>`
- 扫描全部：`POST /api/history/scan-all`
- 删除孤立任务目录：`DELETE /api/history/orphan/<task_id>`（仅对无记录的任务有效）

### 下载与流式大纲
- 流式返回大纲：`GET /api/history/<record_id>/outline/stream`，事件 `start`（总页数）、`heartbeat`、`page_start`、`chunk`、`page_done`、`done`、`error`。
- 打包下载图片：`GET /api/history/<record_id>/download`，返回 ZIP。

## 配置接口
- 获取配置：`GET /api/config`，返回当前启用的文本/图片服务商及脱敏后的配置。
- 更新配置：`POST /api/config`，请求体示例：
```json
{
  "text_generation": {
    "active_provider": "openai",
    "providers": { "openai": { "type":"openai_compatible","api_key":"sk-xxx","base_url":"https://api.openai.com/v1","model":"gpt-4o" } }
  },
  "image_generation": {
    "active_provider": "gemini",
    "providers": { "gemini": { "type":"google_genai","api_key":"AIza...","model":"gemini-3-pro-image-preview" } }
  }
}
```
- 测试服务商连接：`POST /api/config/test`，字段 `type`（google_genai/google_gemini/openai_compatible/image_api）、`provider_name`（可选，从配置读取 key）、可选 `api_key`/`base_url`/`model`。

## 调用流程示例
1. 选用文本/图片服务商，使用 `/api/config` 写入或直接编辑 YAML。
2. 可登录获取 token（如需自行在网关校验）。
3. 调用 `/api/outline` 或 `/api/outline/stream` 获取大纲。
4. 将返回的 `pages` 传给 `/api/generate`，监听 SSE 获取图片 URL。
5. 失败图片用 `/api/retry` 或 `/api/retry-failed` 处理；完成后用 `/api/task/<task_id>` 或历史记录接口管理与下载。
