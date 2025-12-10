"""
大纲生成相关 API 路由

包含功能：
- 生成大纲（支持图片上传）
- 流式生成大纲（SSE）
"""

import time
import json
import base64
import logging
import threading
import queue
from flask import Blueprint, request, jsonify, Response, stream_with_context
from backend.services.outline import get_outline_service
from .utils import log_request, log_error

logger = logging.getLogger(__name__)


def create_outline_blueprint():
    """创建大纲路由蓝图（工厂函数，支持多次调用）"""
    outline_bp = Blueprint('outline', __name__)

    @outline_bp.route('/outline', methods=['POST'])
    def generate_outline():
        """
        生成大纲（支持图片上传）

        请求格式：
        1. multipart/form-data（带图片文件）
           - topic: 主题文本
           - images: 图片文件列表

        2. application/json（无图片或 base64 图片）
           - topic: 主题文本
           - images: base64 编码的图片数组（可选）

        返回：
        - success: 是否成功
        - outline: 原始大纲文本
        - pages: 解析后的页面列表
        """
        start_time = time.time()

        try:
            # 解析请求数据
            topic, images, page_count = _parse_outline_request()

            log_request('/outline', {'topic': topic, 'images': images, 'page_count': page_count})

            # 验证必填参数
            if not topic:
                logger.warning("大纲生成请求缺少 topic 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供要生成图文的主题内容。"
                }), 400

            # 调用大纲生成服务
            page_info = f"，指定页数: {page_count}" if page_count else ""
            logger.info(f"🔄 开始生成大纲，主题: {topic[:50]}...{page_info}")
            outline_service = get_outline_service()
            result = outline_service.generate_outline(
                topic, 
                images if images else None,
                page_count=page_count
            )

            # 记录结果
            elapsed = time.time() - start_time
            if result["success"]:
                logger.info(f"✅ 大纲生成成功，耗时 {elapsed:.2f}s，共 {len(result.get('pages', []))} 页")
                return jsonify(result), 200
            else:
                logger.error(f"❌ 大纲生成失败: {result.get('error', '未知错误')}")
                return jsonify(result), 500

        except Exception as e:
            log_error('/outline', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"大纲生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }), 500

    @outline_bp.route('/outline/stream', methods=['POST'])
    def generate_outline_stream():
        """
        流式生成大纲（SSE）

        请求格式：
        application/json
           - topic: 主题文本
           - images: base64 编码的图片数组（可选）
           - page_count: 指定页数（可选）

        SSE 事件：
        - chunk: 生成的文本片段 {"content": "..."}
        - done: 生成完成 {"outline": "完整大纲", "pages": [...]}
        - error: 错误 {"error": "错误信息"}
        - heartbeat: 心跳包 {}
        """
        try:
            # 解析请求数据
            topic, images, page_count = _parse_outline_request()

            # 验证必填参数
            if not topic:
                logger.warning("流式大纲生成请求缺少 topic 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 不能为空。"
                }), 400

            page_info = f"，指定页数: {page_count}" if page_count else ""
            logger.info(f"🔄 开始流式生成大纲，主题: {topic[:50]}...{page_info}")

            # 预先获取服务实例和图片数据（在请求上下文中）
            outline_service = get_outline_service()
            images_data = images if images else None

            def generate():
                """
                使用队列和后台线程实现带心跳的流式生成
                即使 AI Provider 响应慢，也会定期发送心跳保持连接
                """
                data_queue = queue.Queue()
                heartbeat_interval = 3  # 每 3 秒发送一次心跳
                stop_event = threading.Event()

                def ai_worker():
                    """后台线程：调用 AI 并将结果放入队列"""
                    try:
                        for chunk in outline_service.generate_outline_stream(
                            topic,
                            images_data,
                            page_count=page_count
                        ):
                            data_queue.put(('chunk', chunk))
                        data_queue.put(('done', None))
                    except Exception as e:
                        data_queue.put(('error', str(e)))
                    finally:
                        stop_event.set()

                # 启动后台 AI 工作线程
                worker_thread = threading.Thread(target=ai_worker, daemon=True)
                worker_thread.start()

                full_text = ""
                chunk_count = 0

                # 发送开始事件
                logger.debug("📤 发送 SSE 开始事件")
                yield f"event: start\ndata: {json.dumps({'message': 'streaming started'})}\n\n"

                # 主循环：处理队列数据，定期发送心跳
                while not stop_event.is_set() or not data_queue.empty():
                    try:
                        # 尝试从队列获取数据，最多等待 heartbeat_interval 秒
                        event_type, data = data_queue.get(timeout=heartbeat_interval)

                        if event_type == 'chunk':
                            chunk_count += 1
                            full_text += data
                            logger.debug(f"📤 发送 chunk #{chunk_count}: {len(data)} 字符")
                            yield f"event: chunk\ndata: {json.dumps({'content': data}, ensure_ascii=False)}\n\n"

                        elif event_type == 'done':
                            # 生成完成，解析大纲
                            pages = outline_service._parse_outline(full_text)
                            has_images = images_data is not None and len(images_data) > 0
                            logger.info(f"✅ 流式大纲生成完成，共 {len(pages)} 页，发送了 {chunk_count} 个 chunk")
                            yield f"event: done\ndata: {json.dumps({'outline': full_text, 'pages': pages, 'has_images': has_images}, ensure_ascii=False)}\n\n"
                            break

                        elif event_type == 'error':
                            logger.error(f"❌ 流式大纲生成失败: {data}")
                            yield f"event: error\ndata: {json.dumps({'error': data}, ensure_ascii=False)}\n\n"
                            break

                    except queue.Empty:
                        # 队列超时，发送心跳保持连接
                        logger.debug("💓 发送心跳包")
                        yield f"event: heartbeat\ndata: {{}}\n\n"

                # 等待工作线程结束
                worker_thread.join(timeout=1)

            response = Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                    'Content-Type': 'text/event-stream; charset=utf-8'
                }
            )
            response.implicit_sequence_conversion = False
            return response

        except Exception as e:
            log_error('/outline/stream', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"流式大纲生成异常。\n错误详情: {error_msg}"
            }), 500

    return outline_bp


def _parse_outline_request():
    """
    解析大纲生成请求

    支持两种格式：
    1. multipart/form-data - 用于文件上传
    2. application/json - 用于 base64 图片

    返回：
        tuple: (topic, images, page_count) - 主题、图片列表和页数
    """
    # 检查是否是 multipart/form-data（带图片文件）
    if request.content_type and 'multipart/form-data' in request.content_type:
        topic = request.form.get('topic')
        page_count_str = request.form.get('page_count')
        page_count = int(page_count_str) if page_count_str else None
        images = []

        # 获取上传的图片文件
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    image_data = file.read()
                    images.append(image_data)

        # 限制页数范围 1-100
        if page_count is not None:
            page_count = max(1, min(100, page_count))

        return topic, images, page_count

    # JSON 请求（无图片或 base64 图片）
    data = request.get_json()
    topic = data.get('topic')
    page_count = data.get('page_count')
    images = []

    # 支持 base64 格式的图片
    images_base64 = data.get('images', [])
    if images_base64:
        for img_b64 in images_base64:
            # 移除可能的 data URL 前缀
            if ',' in img_b64:
                img_b64 = img_b64.split(',')[1]
            images.append(base64.b64decode(img_b64))

    # 限制页数范围 1-100
    if page_count is not None:
        page_count = max(1, min(100, page_count))

    return topic, images, page_count
