import os
import yaml
import time
import asyncio
import logging
from flask import Blueprint, render_template, jsonify, request, redirect, make_response

from app.utils import PRESET_MAJORS, load_config, save_config, load_university_db, UNI_DB_PATH
from app.services.scheduler import scanner_state, start_scan_job, stop_scan_job
from app.services.pusher import push_to_channel
from database import DatabaseManager

logger = logging.getLogger('RadarApp')
DB_PATH = 'radar_platform.db'

bp = Blueprint('main', __name__)

@bp.route('/terminal/', defaults={'path': ''})
@bp.route('/terminal/<path:path>')
def terminal(path):
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@bp.route('/login', methods=['GET'])
def login_page():
    # 如果没设密码，直接进系统
    if not os.getenv("AUTH_PASSWORD"):
        return redirect('/terminal')
    return render_template('login.html')

@bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    password = data.get('password')
    correct_password = os.getenv("AUTH_PASSWORD")
    
    if correct_password and password == correct_password:
        session['is_authenticated'] = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "密码错误"}), 401

@bp.route('/api/universities', methods=['GET'])
def get_universities():
    db = load_university_db()
    unis = db.get('universities', [])
    
    # 构建按省份分类的字典
    grouped = {}
    for u in unis:
        prov = u.get('province', '其他')
        if prov not in grouped:
            grouped[prov] = []
        grouped[prov].append(u['name'])
    
    # 排序省份和学校
    sorted_grouped = {k: sorted(v) for k, v in sorted(grouped.items())}
    
    return jsonify({
        "grouped": sorted_grouped,
        "all_names": sorted([u['name'] for u in unis])
    })

@bp.route('/api/majors', methods=['GET'])
def get_majors():
    return jsonify(PRESET_MAJORS)

@bp.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@bp.route('/api/config/modules', methods=['GET'])
def get_config_modules():
    """返回已选院校的所有情报源模块（含网址），供前端展示官网链接"""
    cfg = load_config()
    selected_unis = cfg.get('selected_universities', [])
    graduate_urls = cfg.get('graduate_urls', [])
    department_urls = cfg.get('department_urls', [])
    db = load_university_db()
    all_unis = db.get('universities', [])
    result = {}
    
    for i, uni_name in enumerate(selected_unis):
        u = next((u for u in all_unis if u['name'] == uni_name), {})
        mods = [{'name': m.get('name', ''), 'url': m.get('url', '')} for m in u.get('modules', [])]
        
        grad_url = graduate_urls[i] if i < len(graduate_urls) else ''
        dept_url = department_urls[i] if i < len(department_urls) else ''
        
        # 把用户设置的链接当作最高优先级加入
        if grad_url and not any(m['url'] == grad_url for m in mods):
            mods.insert(0, {'name': '研究生院(用户配置)', 'url': grad_url})
        if dept_url and not any(m['url'] == dept_url for m in mods):
            mods.insert(0, {'name': '学院通知(用户配置)', 'url': dept_url})
            
        result[uni_name] = mods
    return jsonify(result)

@bp.route('/api/config', methods=['POST'])
def update_config():
    data = request.json
    
    # ⚠️ 从本地加载现有配置，保留前端未发送的后端专享隐藏设置
    existing_cfg = load_config()
    if 'relevance_threshold' in existing_cfg:
        data['relevance_threshold'] = existing_cfg['relevance_threshold']
        
    save_config(data)
    
    # 同步更新环境变量
    if data.get('api_key'): os.environ["OPENAI_API_KEY"] = data['api_key']
    if data.get('proxy'): os.environ["HTTP_PROXY"] = data['proxy']
    else: os.environ.pop("HTTP_PROXY", None)

    # 生成 scanner 的 universities.yaml（支持用户手动填入的网址）
    selected_unis = data.get('selected_universities', [])
    graduate_urls = data.get('graduate_urls', [])
    department_urls = data.get('department_urls', [])
    db = load_university_db()
    all_unis = db.get('universities', [])
    
    result_unis = []
    for i, uni_name in enumerate(selected_unis):
        # 先从数据库中查找
        db_entry = next((u for u in all_unis if u['name'] == uni_name), None)
        if db_entry:
            entry = dict(db_entry)
        else:
            entry = {'name': uni_name, 'modules': [], 'province': '', 'region': ''}
        
        # 剔除历史的用户配置模块，确保只保留本次提交的最新 URL
        modules = [m for m in entry.get('modules', []) if m.get('name') not in ['研究生院(用户配置)', '学院通知(用户配置)']]
        grad_url = graduate_urls[i] if i < len(graduate_urls) else ''
        dept_url = department_urls[i] if i < len(department_urls) else ''
        
        if grad_url and not any(m.get('url') == grad_url for m in modules):
            modules.append({'name': '研究生院(用户配置)', 'url': grad_url, 'selector': ''})
        if dept_url and not any(m.get('url') == dept_url for m in modules):
            modules.append({'name': '学院通知(用户配置)', 'url': dept_url, 'selector': ''})
        
        entry['modules'] = modules
        result_unis.append(entry)

    with open('universities.yaml', 'w', encoding='utf-8') as f:
        yaml.dump({"universities": result_unis}, f, allow_unicode=True, default_flow_style=False)

    return jsonify({"status": "ok", "message": "配置已保存！"})

@bp.route('/api/archives/stats', methods=['GET'])
def get_archive_stats():
    """获取历史档案的统计概览数据"""
    db = DatabaseManager(DB_PATH)
    c = db._get_conn().cursor()
    
    # 统计每年、每种类型的数量
    query = '''
        SELECT target_year, category, COUNT(*) as count 
        FROM global_announcements 
        WHERE target_year IS NOT NULL 
        GROUP BY target_year, category
        ORDER BY target_year DESC
    '''
    c.execute(query)
    rows = [dict(row) for row in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/scan/start', methods=['POST'])
def start_scan():
    if start_scan_job():
        interval = load_config().get('scan_interval', 15)
        return jsonify({"status": "started", "message": f"深海潜航计划已启动，每 {interval} 分钟扫描一次"})
    return jsonify({"status": "running", "message": "监控已在运行中"})

@bp.route('/api/scan/stop', methods=['POST'])
def stop_scan():
    stop_scan_job()
    return jsonify({"status": "stopped", "message": "监控已停止"})

@bp.route('/api/scan/status', methods=['GET'])
def scan_status():
    state_copy = dict(scanner_state)
    state_copy['logs'] = scanner_state['logs'][-100:]
    return jsonify(state_copy)

@bp.route('/api/intel/discover', methods=['GET'])
def api_discover_intel():
    # 延迟导入：防止模块缺失导致整个应用崩溃
    try:
        from intelligence_discovery import IntelligenceDiscoverer
    except ImportError:
        return jsonify({"status": "error", "message": "智能探测模块 (intelligence_discovery) 未安装"}), 501

    uni_name = request.args.get('university')
    if not uni_name:
        return jsonify({"error": "Missing university parameter"}), 400
    
    logger.info(f"🔍 收到智能探测请求: {uni_name}")
    
    async def run_discovery():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            discoverer = IntelligenceDiscoverer()
            result = await discoverer.perform_full_discovery(uni_name, context)
            await browser.close()
            return result
            
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_discovery())
        loop.close()
        
        if result:
            try:
                db_data = load_university_db()
                uni_found = False
                for u in db_data.get('universities', []):
                    if u['name'] == uni_name:
                        uni_found = True
                        if 'modules' not in u: u['modules'] = []
                        if not any(m['url'] == result['url'] for m in u['modules']):
                            u['modules'].append(result)
                
                if uni_found:
                    with open(UNI_DB_PATH, 'w', encoding='utf-8') as f:
                        yaml.dump(db_data, f, allow_unicode=True, default_flow_style=False)
                    
                    cfg = load_config()
                    if uni_name in cfg.get('selected_universities', []):
                        filtered = [u for u in db_data.get('universities', []) if u['name'] in cfg['selected_universities']]
                        with open('universities.yaml', 'w', encoding='utf-8') as f:
                            yaml.dump({"universities": filtered}, f, allow_unicode=True, default_flow_style=False)
            except Exception as save_err:
                logger.error(f"持久化信源失败: {save_err}")

            return jsonify({"status": "success", "university": uni_name, "module": result})
        return jsonify({"status": "not_found", "message": "未能锁定有效的情报入口"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/api/test-data', methods=['POST'])
def inject_test_data():
    db = DatabaseManager(DB_PATH)
    config = load_config()
    selected_unis = config.get('selected_universities', [])
    notifications = config.get('notifications', [])
    proxy = os.getenv("HTTP_PROXY")

    if not notifications:
        return jsonify({"status": "error", "message": "请先配置并启用至少一种通知渠道"})

    push_count = 0
    
    # 构造两条测试数据，一条没 AI 面板，一条有 AI 面板
    uni = selected_unis[0] if selected_unis else "湖南师范大学"
    graduate_urls = config.get('graduate_urls', [])
    uni_index = selected_unis.index(uni) if uni in selected_unis else -1
    link = graduate_urls[uni_index] if uni_index >= 0 and uni_index < len(graduate_urls) and graduate_urls[uni_index] else "https://yjsy.hunnu.edu.cn/zsks/sszk1/zkdt1.htm"
    
    base_event = {
        "university": uni, "module": "研究生院", 
        "link": link, "publish_date": time.strftime("%Y-%m-%d"),
        "category": "测试", "major": "测试专业", "urgency": "中"
    }
    
    event_raw = dict(base_event)
    event_raw["title"] = "【测试通知-纯原文】2026年硕士研究生招生简章公布"
    event_raw["ai_summary"] = ""
    event_raw["ai_action"] = ""
    event_raw["relevance_score"] = 0
    
    event_ai = dict(base_event)
    event_ai["title"] = "【测试通知-含AI解析】关于开展2026年研招复试工作的通知"
    event_ai["relevance_score"] = 95
    event_ai["ai_summary"] = "【核心要点】\n1. 复试时间：3月20日-25日\n2. 复试方式：全部采用线下现场复试\n3. 成绩权重：初试占比60%，复试占比40%\n\n【关键变化】\n今年特别加强了心理测评环节，请考生务必在复试前完成线上测试。"
    event_ai["ai_action"] = "1. 立即登录研招网查看复试名单\n2. 准备相关资格审查材料（身份证、准考证、学历证明等）\n3. 提前预定考点周边酒店"

    for ch in notifications:
        if push_to_channel(ch, event_raw, proxy): push_count += 1
        if push_to_channel(ch, event_ai, proxy): push_count += 1

    return jsonify({"status": "ok", "message": f"成功推送了 {push_count} 条双版本测试通知"})

@bp.route('/api/test-api', methods=['POST'])
def test_api_connectivity():
    data = request.json
    provider = data.get('provider')
    api_key = data.get('api_key')
    base_url = data.get('base_url')
    model = data.get('model')
    proxy = data.get('proxy')
    
    if not api_key:
        return jsonify({"status": "error", "message": "请先输入 API 密钥"})
        
    try:
        import requests
        
        # 补全代理 Schema 避免小白填错
        if proxy and not proxy.startswith('http') and not proxy.startswith('socks'):
            proxy = "http://" + proxy
        proxies = {"http": proxy, "https": proxy} if proxy else None
        
        # 与 ai_analyzer.py 对齐：系统全量使用 OpenAI 兼容协议（包含各种 OneAPI 等中转映射）
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = base_url.rstrip('/') + "/chat/completions"
        payload = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5}
        
        res = requests.post(url, headers=headers, json=payload, proxies=proxies, timeout=10)
        
        # Parse JSON and check for typical error structures
        try:
            resp_data = res.json()
            if isinstance(resp_data, list) and len(resp_data) > 0:
                resp_data = resp_data[0]
            if not isinstance(resp_data, dict):
                resp_data = {}
        except:
            resp_data = {}

        if "error" in resp_data:
            err = resp_data["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            return jsonify({"status": "error", "message": f"API 返回错误: {msg}"})

        if res.status_code == 200:
            if not resp_data:
                return jsonify({"status": "error", "message": f"遭遇网络假阳性: 返回了 HTTP 200 但报体无效或被拦截。"})
            if "choices" not in resp_data:
                return jsonify({"status": "error", "message": f"无效的 OpenAI 兼容响应报文，可能是代理伪造了成功响应或网关异常。"})
            return jsonify({"status": "ok", "message": f"成功连接至 {model}"})
        else:
            msg = resp_data.get("error", {}).get("message") if isinstance(resp_data.get("error"), dict) else res.text[:100]
            if not msg: msg = res.text[:100]
            return jsonify({"status": "error", "message": f"HTTP {res.status_code}: {msg}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"请求异常: {str(e)}"})

@bp.route('/api/events', methods=['GET'])
def get_events():
    db = DatabaseManager(DB_PATH)
    # 不再剥除前后空格，直接匹配；因为之前抓取可能写了包含空格的值，这里就做个容错
    config_unis = load_config().get('selected_universities', [])
    selected_unis = [u for u in config_unis if u]
    if not selected_unis: return jsonify([])

    c = db._get_conn().cursor()
    clean_unis = [u.replace(" ", "") for u in selected_unis]
    placeholders = ','.join(['?'] * len(clean_unis))
    # 💡 使用 created_at（入库时间）作为主排序键
    # publish_date 不可靠（可能为 NULL 或兜底值），created_at 更真实反映新旧顺序
    query = f"SELECT * FROM global_announcements WHERE REPLACE(university, ' ', '') IN ({placeholders}) ORDER BY created_at DESC, id DESC LIMIT 200"
    
    c.execute(query, clean_unis)
    rows = [dict(row) for row in c.fetchall()]

    # 直接按时间降序返回，前端负责按类别分组展示
    return jsonify(rows)
