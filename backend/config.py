import logging
import os
import yaml
import secrets
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class Config:
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 12398
    CORS_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']
    OUTPUT_DIR = 'output'

    # 认证配置
    # 管理员密码：优先从环境变量 ADMIN_PASSWORD 读取，如未设置则从配置文件读取
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    # JWT 密钥：用于签名 token，如未设置则自动生成（重启后 token 失效）
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    # Token 有效期（秒），默认 7 天
    TOKEN_EXPIRY = int(os.environ.get('TOKEN_EXPIRY', 60 * 60 * 24 * 7))

    # 删除功能配置（默认禁用，只允许归档）
    # 设置为 true 允许永久删除记录，设置为 false 则删除操作会变成归档
    ALLOW_DELETE = os.environ.get('ALLOW_DELETE', 'false').lower() == 'true'

    _auth_config = None

    @classmethod
    def load_auth_config(cls):
        """加载认证配置"""
        if cls._auth_config is not None:
            return cls._auth_config

        config_path = Path(__file__).parent.parent / 'auth.yaml'
        logger.debug(f"加载认证配置: {config_path}")

        if not config_path.exists():
            logger.warning(f"认证配置文件不存在: {config_path}，请通过环境变量设置密码")
            cls._auth_config = {}
            return cls._auth_config

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._auth_config = yaml.safe_load(f) or {}
            logger.debug("认证配置加载成功")
        except yaml.YAMLError as e:
            logger.error(f"认证配置文件 YAML 格式错误: {e}")
            cls._auth_config = {}

        return cls._auth_config

    @classmethod
    def get_admin_password(cls):
        """获取管理员密码"""
        # 优先使用环境变量
        if cls.ADMIN_PASSWORD:
            return cls.ADMIN_PASSWORD

        # 从配置文件读取
        auth_config = cls.load_auth_config()
        return auth_config.get('admin_password')

    @classmethod
    def verify_password(cls, password: str) -> bool:
        """验证密码"""
        admin_password = cls.get_admin_password()
        if not admin_password:
            logger.warning("未设置管理员密码，拒绝所有登录请求")
            return False
        return password == admin_password

    @classmethod
    def generate_token(cls) -> str:
        """生成认证 token"""
        import time
        import hmac
        timestamp = str(int(time.time()))
        # 使用 HMAC 生成 token
        signature = hmac.new(
            cls.SECRET_KEY.encode(),
            timestamp.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{timestamp}.{signature}"

    @classmethod
    def verify_token(cls, token: str) -> bool:
        """验证 token"""
        import time
        import hmac
        try:
            parts = token.split('.')
            if len(parts) != 2:
                return False

            timestamp, signature = parts
            # 检查时间戳是否过期
            token_time = int(timestamp)
            if time.time() - token_time > cls.TOKEN_EXPIRY:
                logger.debug("Token 已过期")
                return False

            # 验证签名
            expected_signature = hmac.new(
                cls.SECRET_KEY.encode(),
                timestamp.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Token 验证失败: {e}")
            return False

    _image_providers_config = None
    _text_providers_config = None

    @classmethod
    def load_image_providers_config(cls):
        if cls._image_providers_config is not None:
            return cls._image_providers_config

        config_path = Path(__file__).parent.parent / 'image_providers.yaml'
        logger.debug(f"加载图片服务商配置: {config_path}")

        if not config_path.exists():
            logger.warning(f"图片配置文件不存在: {config_path}，使用默认配置")
            cls._image_providers_config = {
                'active_provider': 'google_genai',
                'providers': {}
            }
            return cls._image_providers_config

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._image_providers_config = yaml.safe_load(f) or {}
            logger.debug(f"图片配置加载成功: {list(cls._image_providers_config.get('providers', {}).keys())}")
        except yaml.YAMLError as e:
            logger.error(f"图片配置文件 YAML 格式错误: {e}")
            raise ValueError(
                f"配置文件格式错误: image_providers.yaml\n"
                f"YAML 解析错误: {e}\n"
                "解决方案：\n"
                "1. 检查 YAML 缩进是否正确（使用空格，不要用Tab）\n"
                "2. 检查引号是否配对\n"
                "3. 使用在线 YAML 验证器检查格式"
            )

        return cls._image_providers_config

    @classmethod
    def load_text_providers_config(cls):
        """加载文本生成服务商配置"""
        if cls._text_providers_config is not None:
            return cls._text_providers_config

        config_path = Path(__file__).parent.parent / 'text_providers.yaml'
        logger.debug(f"加载文本服务商配置: {config_path}")

        if not config_path.exists():
            logger.warning(f"文本配置文件不存在: {config_path}，使用默认配置")
            cls._text_providers_config = {
                'active_provider': 'google_gemini',
                'providers': {}
            }
            return cls._text_providers_config

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._text_providers_config = yaml.safe_load(f) or {}
            logger.debug(f"文本配置加载成功: {list(cls._text_providers_config.get('providers', {}).keys())}")
        except yaml.YAMLError as e:
            logger.error(f"文本配置文件 YAML 格式错误: {e}")
            raise ValueError(
                f"配置文件格式错误: text_providers.yaml\n"
                f"YAML 解析错误: {e}\n"
                "解决方案：\n"
                "1. 检查 YAML 缩进是否正确（使用空格，不要用Tab）\n"
                "2. 检查引号是否配对\n"
                "3. 使用在线 YAML 验证器检查格式"
            )

        return cls._text_providers_config

    @classmethod
    def get_active_image_provider(cls):
        config = cls.load_image_providers_config()
        active = config.get('active_provider', 'google_genai')
        logger.debug(f"当前激活的图片服务商: {active}")
        return active

    @classmethod
    def get_image_max_concurrent(cls) -> int:
        """获取图片生成全局最大并发数"""
        config = cls.load_image_providers_config()
        max_concurrent = config.get('max_concurrent', 15)
        logger.debug(f"图片生成全局最大并发数: {max_concurrent}")
        return max_concurrent

    @classmethod
    def get_image_provider_config(cls, provider_name: str = None):
        config = cls.load_image_providers_config()

        if provider_name is None:
            provider_name = cls.get_active_image_provider()

        logger.info(f"获取图片服务商配置: {provider_name}")

        providers = config.get('providers', {})
        if not providers:
            raise ValueError(
                "未找到任何图片生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加图片生成服务商\n"
                "2. 或手动编辑 image_providers.yaml 文件\n"
                "3. 确保文件中有 providers 字段"
            )

        if provider_name not in providers:
            available = ', '.join(providers.keys()) if providers else '无'
            logger.error(f"图片服务商 [{provider_name}] 不存在，可用服务商: {available}")
            raise ValueError(
                f"未找到图片生成服务商配置: {provider_name}\n"
                f"可用的服务商: {available}\n"
                "解决方案：\n"
                "1. 在系统设置页面添加该服务商\n"
                "2. 或修改 active_provider 为已存在的服务商\n"
                "3. 检查 image_providers.yaml 文件"
            )

        provider_config = providers[provider_name].copy()

        # 验证必要字段
        if not provider_config.get('api_key'):
            logger.error(f"图片服务商 [{provider_name}] 未配置 API Key")
            raise ValueError(
                f"服务商 {provider_name} 未配置 API Key\n"
                "解决方案：\n"
                "1. 在系统设置页面编辑该服务商，填写 API Key\n"
                "2. 或手动在 image_providers.yaml 中添加 api_key 字段"
            )

        provider_type = provider_config.get('type', provider_name)
        if provider_type in ['openai', 'openai_compatible', 'image_api']:
            if not provider_config.get('base_url'):
                logger.error(f"服务商 [{provider_name}] 类型为 {provider_type}，但未配置 base_url")
                raise ValueError(
                    f"服务商 {provider_name} 未配置 Base URL\n"
                    f"服务商类型 {provider_type} 需要配置 base_url\n"
                    "解决方案：在系统设置页面编辑该服务商，填写 Base URL"
                )

        logger.info(f"图片服务商配置验证通过: {provider_name} (type={provider_type})")
        return provider_config

    @classmethod
    def reload_config(cls):
        """重新加载配置（清除缓存）"""
        logger.info("重新加载所有配置...")
        cls._image_providers_config = None
        cls._text_providers_config = None
