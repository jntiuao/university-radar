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

    # 简单登录验证中间件 (针对在线化部署)
    from flask import session, request, redirect, url_for
    @app.before_request
    def check_auth():
        # 如果设置了 AUTH_PASSWORD，则启用访问限制
        auth_password = os.getenv("AUTH_PASSWORD")
        if not auth_password:
            return

        # 豁免列表：登录页面、登录 API、静态资源
        exempt_paths = ['/login', '/api/login', '/assets/']
        if any(request.path.startswith(p) for p in exempt_paths):
            return
            
        # 检查会话
        if not session.get('is_authenticated'):
            return redirect('/login')
    
    return app
