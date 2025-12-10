"""
历史记录相关 API 路由

包含功能：
- 创建/获取/更新/删除历史记录 (CRUD)
- 归档/取消归档历史记录
- 搜索历史记录
- 获取统计信息
- 扫描和同步任务图片
- 打包下载图片
"""

import os
import io
import json
import time
import zipfile
import logging
from flask import Blueprint, request, jsonify, send_file, Response
from backend.services.history import get_history_service
from backend.config import Config

logger = logging.getLogger(__name__)


def create_history_blueprint():
    """创建历史记录路由蓝图（工厂函数，支持多次调用）"""
    history_bp = Blueprint('history', __name__)

    # ==================== CRUD 操作 ====================

    @history_bp.route('/history', methods=['POST'])
    def create_history():
        """
        创建历史记录

        请求体：
        - topic: 主题标题（必填）
        - outline: 大纲内容（必填）
        - task_id: 关联的任务 ID（可选）

        返回：
        - success: 是否成功
        - record_id: 新创建的记录 ID
        """
        try:
            data = request.get_json()
            topic = data.get('topic')
            outline = data.get('outline')
            task_id = data.get('task_id')

            if not topic or not outline:
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 和 outline 不能为空。\n请提供主题和大纲内容。"
                }), 400

            history_service = get_history_service()
            record_id = history_service.create_record(topic, outline, task_id)

            return jsonify({
                "success": True,
                "record_id": record_id
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"创建历史记录失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history', methods=['GET'])
    def list_history():
        """
        获取历史记录列表（分页）

        查询参数：
        - page: 页码（默认 1）
        - page_size: 每页数量（默认 20）
        - status: 状态过滤（可选：all/completed/draft）
        - include_archived: 是否包含已归档记录（默认 true）
        - archived_only: 仅显示已归档记录（默认 false）

        返回：
        - success: 是否成功
        - records: 记录列表
        - total: 总数
        - total_pages: 总页数
        """
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            status = request.args.get('status')
            include_archived = request.args.get('include_archived', 'true').lower() == 'true'
            archived_only = request.args.get('archived_only', 'false').lower() == 'true'

            history_service = get_history_service()
            result = history_service.list_records(
                page,
                page_size,
                status,
                include_archived=include_archived,
                archived_only=archived_only
            )

            return jsonify({
                "success": True,
                **result
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取历史记录列表失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/<record_id>', methods=['GET'])
    def get_history(record_id):
        """
        获取历史记录详情

        路径参数：
        - record_id: 记录 ID

        返回：
        - success: 是否成功
        - record: 完整的记录数据
        """
        try:
            history_service = get_history_service()
            record = history_service.get_record(record_id)

            if not record:
                return jsonify({
                    "success": False,
                    "error": f"历史记录不存在：{record_id}\n可能原因：记录已被删除或ID错误"
                }), 404

            return jsonify({
                "success": True,
                "record": record
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取历史记录详情失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/<record_id>', methods=['PUT'])
    def update_history(record_id):
        """
        更新历史记录

        路径参数：
        - record_id: 记录 ID

        请求体（均为可选）：
        - outline: 大纲内容
        - images: 图片信息
        - status: 状态
        - thumbnail: 缩略图文件名

        返回：
        - success: 是否成功
        """
        try:
            data = request.get_json()
            outline = data.get('outline')
            images = data.get('images')
            status = data.get('status')
            thumbnail = data.get('thumbnail')

            history_service = get_history_service()
            success = history_service.update_record(
                record_id,
                outline=outline,
                images=images,
                status=status,
                thumbnail=thumbnail
            )

            if not success:
                return jsonify({
                    "success": False,
                    "error": f"更新历史记录失败：{record_id}\n可能原因：记录不存在或数据格式错误"
                }), 404

            return jsonify({
                "success": True
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"更新历史记录失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/<record_id>', methods=['DELETE'])
    def delete_history(record_id):
        """
        删除历史记录

        路径参数：
        - record_id: 记录 ID

        说明：
        - 如果 ALLOW_DELETE=false（默认），则执行归档操作
        - 如果 ALLOW_DELETE=true，则执行永久删除

        返回：
        - success: 是否成功
        - action: 执行的操作（archived/deleted）
        """
        try:
            history_service = get_history_service()

            # 检查是否允许删除
            if not Config.ALLOW_DELETE:
                # 禁用删除时，执行归档操作
                success = history_service.archive_record(record_id)

                if not success:
                    return jsonify({
                        "success": False,
                        "error": f"归档历史记录失败：{record_id}\n可能原因：记录不存在或ID错误"
                    }), 404

                return jsonify({
                    "success": True,
                    "action": "archived",
                    "message": "记录已归档（删除功能已禁用）"
                }), 200

            # 允许删除时，执行永久删除
            success = history_service.delete_record(record_id)

            if not success:
                return jsonify({
                    "success": False,
                    "error": f"删除历史记录失败：{record_id}\n可能原因：记录不存在或ID错误"
                }), 404

            return jsonify({
                "success": True,
                "action": "deleted"
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"删除历史记录失败。\n错误详情: {error_msg}"
            }), 500

    # ==================== 归档操作 ====================

    @history_bp.route('/history/<record_id>/archive', methods=['POST'])
    def archive_history(record_id):
        """
        归档历史记录

        路径参数：
        - record_id: 记录 ID

        返回：
        - success: 是否成功
        """
        try:
            history_service = get_history_service()
            success = history_service.archive_record(record_id)

            if not success:
                return jsonify({
                    "success": False,
                    "error": f"归档历史记录失败：{record_id}\n可能原因：记录不存在或ID错误"
                }), 404

            return jsonify({
                "success": True
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"归档历史记录失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/<record_id>/unarchive', methods=['POST'])
    def unarchive_history(record_id):
        """
        取消归档历史记录

        路径参数：
        - record_id: 记录 ID

        返回：
        - success: 是否成功
        """
        try:
            history_service = get_history_service()
            success = history_service.unarchive_record(record_id)

            if not success:
                return jsonify({
                    "success": False,
                    "error": f"取消归档失败：{record_id}\n可能原因：记录不存在或ID错误"
                }), 404

            return jsonify({
                "success": True
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"取消归档失败。\n错误详情: {error_msg}"
            }), 500

    # ==================== 搜索和统计 ====================

    @history_bp.route('/history/search', methods=['GET'])
    def search_history():
        """
        搜索历史记录

        查询参数：
        - keyword: 搜索关键词（必填）

        返回：
        - success: 是否成功
        - records: 匹配的记录列表
        """
        try:
            keyword = request.args.get('keyword', '')

            if not keyword:
                return jsonify({
                    "success": False,
                    "error": "参数错误：keyword 不能为空。\n请提供搜索关键词。"
                }), 400

            history_service = get_history_service()
            results = history_service.search_records(keyword)

            return jsonify({
                "success": True,
                "records": results
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"搜索历史记录失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/stats', methods=['GET'])
    def get_history_stats():
        """
        获取历史记录统计信息

        返回：
        - success: 是否成功
        - total: 总记录数
        - by_status: 按状态分组的统计
        """
        try:
            history_service = get_history_service()
            stats = history_service.get_statistics()

            return jsonify({
                "success": True,
                **stats
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取历史记录统计失败。\n错误详情: {error_msg}"
            }), 500

    # ==================== 扫描和同步 ====================

    @history_bp.route('/history/scan/<task_id>', methods=['GET'])
    def scan_task(task_id):
        """
        扫描单个任务并同步图片列表

        路径参数：
        - task_id: 任务 ID

        返回：
        - success: 是否成功
        - images: 同步后的图片列表
        """
        try:
            history_service = get_history_service()
            result = history_service.scan_and_sync_task_images(task_id)

            if not result.get("success"):
                return jsonify(result), 404

            return jsonify(result), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"扫描任务失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/scan-all', methods=['POST'])
    def scan_all_tasks():
        """
        扫描所有任务并同步图片列表

        返回：
        - success: 是否成功
        - total_tasks: 扫描的任务总数
        - synced: 成功同步的任务数
        - failed: 失败的任务数
        - orphan_tasks: 孤立任务列表（有图片但无记录）
        """
        try:
            history_service = get_history_service()
            result = history_service.scan_all_tasks()

            if not result.get("success"):
                return jsonify(result), 500

            return jsonify(result), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"扫描所有任务失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/orphan/<task_id>', methods=['DELETE'])
    def delete_orphan_task(task_id):
        """
        删除孤立任务（只有文件夹，无历史记录）

        路径参数：
        - task_id: 任务 ID

        返回：
        - success: 是否成功
        - message: 结果消息
        """
        import shutil

        try:
            history_service = get_history_service()

            # 验证这确实是个孤立任务（没有关联的历史记录）
            index = history_service._load_index()
            for rec in index.get("records", []):
                if rec.get("task_id") == task_id:
                    return jsonify({
                        "success": False,
                        "error": "此任务有关联的历史记录，不是孤立任务"
                    }), 400

            # 构建任务目录路径
            task_dir = os.path.join(history_service.history_dir, task_id)

            if not os.path.exists(task_dir):
                return jsonify({
                    "success": False,
                    "error": "任务目录不存在"
                }), 404

            # 删除整个任务目录
            shutil.rmtree(task_dir)

            return jsonify({
                "success": True,
                "message": f"孤立任务 {task_id} 已删除"
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"删除孤立任务失败: {error_msg}"
            }), 500

    # ==================== 下载功能 ====================

    @history_bp.route('/history/<record_id>/outline/stream', methods=['GET'])
    def stream_outline(record_id):
        """
        流式返回大纲内容（SSE）

        路径参数：
        - record_id: 记录 ID

        返回：
        - SSE 事件流，包含大纲页面内容
        - 事件类型：page（页面数据）、done（完成）、error（错误）
        - 心跳包：heartbeat 事件
        """
        def generate():
            try:
                history_service = get_history_service()
                record = history_service.get_record(record_id)

                if not record:
                    yield f"event: error\ndata: {json.dumps({'error': '记录不存在'})}\n\n"
                    return

                outline = record.get('outline', {})
                pages = outline.get('pages', [])

                if not pages:
                    yield f"event: error\ndata: {json.dumps({'error': '大纲内容为空'})}\n\n"
                    return

                # 发送总页数信息
                yield f"event: start\ndata: {json.dumps({'total': len(pages)})}\n\n"

                # 逐页流式发送
                for idx, page in enumerate(pages):
                    # 发送心跳包
                    yield f"event: heartbeat\ndata: {json.dumps({'ts': int(time.time() * 1000)})}\n\n"

                    # 流式发送页面内容（按字符分块）
                    content = page.get('content', '')
                    page_type = page.get('type', 'content')
                    chunk_size = 20  # 每次发送的字符数

                    # 先发送页面开始事件
                    yield f"event: page_start\ndata: {json.dumps({'index': idx, 'type': page_type, 'total_length': len(content)})}\n\n"

                    # 分块发送内容
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        yield f"event: chunk\ndata: {json.dumps({'index': idx, 'content': chunk, 'offset': i})}\n\n"
                        time.sleep(0.02)  # 20ms 延迟，模拟打字效果

                    # 发送页面完成事件
                    yield f"event: page_done\ndata: {json.dumps({'index': idx})}\n\n"

                # 发送完成事件
                yield f"event: done\ndata: {json.dumps({'success': True, 'total': len(pages)})}\n\n"

            except Exception as e:
                logger.error(f"流式返回大纲失败: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    @history_bp.route('/history/<record_id>/download', methods=['GET'])
    def download_history_zip(record_id):
        """
        下载历史记录的所有图片为 ZIP 文件

        路径参数：
        - record_id: 记录 ID

        返回：
        - 成功：ZIP 文件下载
        - 失败：JSON 错误信息
        """
        try:
            history_service = get_history_service()
            record = history_service.get_record(record_id)

            if not record:
                return jsonify({
                    "success": False,
                    "error": f"历史记录不存在：{record_id}"
                }), 404

            task_id = record.get('images', {}).get('task_id')
            if not task_id:
                return jsonify({
                    "success": False,
                    "error": "该记录没有关联的任务图片"
                }), 404

            # 获取任务目录
            task_dir = os.path.join(history_service.history_dir, task_id)
            if not os.path.exists(task_dir):
                return jsonify({
                    "success": False,
                    "error": f"任务目录不存在：{task_id}"
                }), 404

            # 创建内存中的 ZIP 文件
            zip_buffer = _create_images_zip(task_dir)

            # 生成安全的下载文件名
            title = record.get('title', 'images')
            safe_title = _sanitize_filename(title)
            filename = f"{safe_title}.zip"

            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"下载失败。\n错误详情: {error_msg}"
            }), 500

    return history_bp


def _create_images_zip(task_dir: str) -> io.BytesIO:
    """
    创建包含所有图片的 ZIP 文件

    Args:
        task_dir: 任务目录路径

    Returns:
        io.BytesIO: 内存中的 ZIP 文件
    """
    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 遍历任务目录中的所有图片（排除缩略图）
        for filename in os.listdir(task_dir):
            # 跳过缩略图文件
            if filename.startswith('thumb_'):
                continue

            if filename.endswith(('.png', '.jpg', '.jpeg')):
                file_path = os.path.join(task_dir, filename)

                # 生成归档文件名（page_N.png 格式）
                try:
                    index = int(filename.split('.')[0])
                    archive_name = f"page_{index + 1}.png"
                except ValueError:
                    archive_name = filename

                zf.write(file_path, archive_name)

    # 将指针移到开始位置
    memory_file.seek(0)
    return memory_file


def _sanitize_filename(title: str) -> str:
    """
    清理文件名中的非法字符

    Args:
        title: 原始标题

    Returns:
        str: 安全的文件名
    """
    # 只保留字母、数字、空格、连字符和下划线
    safe_title = "".join(
        c for c in title
        if c.isalnum() or c in (' ', '-', '_', '\u4e00-\u9fff')
    ).strip()

    return safe_title if safe_title else 'images'
