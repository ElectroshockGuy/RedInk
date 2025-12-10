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
                full_text = ""
                last_heartbeat = time.time()
                heartbeat_interval = 15  # 每 15 秒发送一次心跳

                try:
                    for chunk in outline_service.generate_outline_stream(
                        topic,
                        images_data,
                        page_count=page_count
                    ):
                        full_text += chunk
                        # 发送文本片段
                        yield f"event: chunk\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

                        # 检查是否需要发送心跳
                        current_time = time.time()
                        if current_time - last_heartbeat > heartbeat_interval:
                            yield f"event: heartbeat\ndata: {{}}\n\n"
                            last_heartbeat = current_time

                    # 生成完成，解析大纲
                    pages = outline_service._parse_outline(full_text)
                    has_images = images_data is not None and len(images_data) > 0

                    logger.info(f"✅ 流式大纲生成完成，共 {len(pages)} 页")
                    yield f"event: done\ndata: {json.dumps({'outline': full_text, 'pages': pages, 'has_images': has_images}, ensure_ascii=False)}\n\n"

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"❌ 流式大纲生成失败: {error_msg}")
                    yield f"event: error\ndata: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )

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
