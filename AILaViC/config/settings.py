
class Settings:
    # 物理限制
    MAX_SPEED_KNOTS = 35  # 最大速度 (节)
    MAX_ACCELERATION_G = 9.0  # 最大加速度 (G)
    
    # 资源检查
    REQUIRED_RESOURCE_FILES = ["simulation.json"]
    
    # 临时文件路径
    TEMP_DIR = "temp_audit"

    # API 文档与规范参考
    API_REFS = {
        "swagger_core": "http://api.lavic.cn/swagger-ui.html?urls.primaryName=core",
        "doc_ui": "http://api.lavic.cn/doc.html"
    }

settings = Settings()
