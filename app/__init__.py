import logging
from flask import Flask
from dotenv import load_dotenv

def create_app():
    load_dotenv()
    
    app = Flask(__name__, template_folder='../frontend/dist', static_folder='../frontend/dist/assets', static_url_path='/assets')
    app.secret_key = 'exam-radar-local'
    app.config['TEMPLATES_AUTO_RELOAD'] = True  # 禁用模板缓存，确保每次都加载最新的 HTML
    
    # 确保日志目录存在
    import os
    os.makedirs("logs", exist_ok=True)

    # 配置日志 (双向输出：控制台 + 文件)
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/radar.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    
    # 注册蓝图
    from .routes import bp
    app.register_blueprint(bp)
    
    return app
