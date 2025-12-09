"""
认证相关 API 路由
"""
import logging
from flask import Blueprint, request, jsonify
from backend.config import Config

logger = logging.getLogger(__name__)


def create_auth_blueprint():
    """创建认证 API 蓝图"""
    auth_bp = Blueprint('auth', __name__)

    @auth_bp.route('/auth/login', methods=['POST'])
    def login():
        """
        登录接口

        Request Body:
            {
                "password": "管理员密码"
            }

        Response:
            成功: {"success": true, "token": "xxx"}
            失败: {"success": false, "error": "密码错误"}
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': '请求格式错误'
                }), 400

            password = data.get('password', '')
            if not password:
                return jsonify({
                    'success': False,
                    'error': '请输入密码'
                }), 400

            # 检查是否设置了管理员密码
            admin_password = Config.get_admin_password()
            if not admin_password:
                logger.error("尝试登录但未设置管理员密码")
                return jsonify({
                    'success': False,
                    'error': '系统未配置管理员密码，请联系管理员'
                }), 500

            # 验证密码
            if Config.verify_password(password):
                token = Config.generate_token()
                logger.info("用户登录成功")
                return jsonify({
                    'success': True,
                    'token': token
                })
            else:
                logger.warning("登录失败：密码错误")
                return jsonify({
                    'success': False,
                    'error': '密码错误'
                }), 401

        except Exception as e:
            logger.error(f"登录时发生错误: {e}")
            return jsonify({
                'success': False,
                'error': '登录失败，请稍后重试'
            }), 500

    @auth_bp.route('/auth/check', methods=['GET'])
    def check_auth():
        """
        验证 token 是否有效

        Headers:
            Authorization: Bearer <token>

        Response:
            {"valid": true/false}
        """
        try:
            auth_header = request.headers.get('Authorization', '')

            if not auth_header.startswith('Bearer '):
                return jsonify({'valid': False})

            token = auth_header[7:]  # 去掉 "Bearer " 前缀

            if not token:
                return jsonify({'valid': False})

            is_valid = Config.verify_token(token)
            return jsonify({'valid': is_valid})

        except Exception as e:
            logger.error(f"验证 token 时发生错误: {e}")
            return jsonify({'valid': False})

    return auth_bp
