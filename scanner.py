import asyncio
import httpx
import json
import logging
import os
import yaml
import hashlib
import re
import datetime
import urllib.parse
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser
from playwright.async_api import async_playwright, TimeoutError
from urllib.parse import urljoin
from dotenv import load_dotenv

from database import DatabaseManager
from ai_analyzer import AIAnalyzer

logger = logging.getLogger('ExamRadar')

class ContentExtractor:
    """负责从各种信源提取纯净正文或解析附件"""
    
    @staticmethod
    async def extract_from_html(html_content):
        if not html_content: return ""
        parser = HTMLParser(html_content)
        
        # 移除干扰标签
        for tag in parser.css('script, style, nav, footer, header, aside, iframe, noscript'):
            tag.decompose()
            
        # 常见正文容器定位
        main_selectors = ['article', '.content', '#content', '.post-content', '.article-body', 'main', '.page-content']
        for selector in main_selectors:
            node = parser.css_first(selector)
            if node:
                return node.text(separator=" ", strip=True)
                
        # 兜底：获取 body 内所有文本
        body = parser.css_first('body')
        if body:
            return body.text(separator=" ", strip=True)
        return ""

    @staticmethod
    async def extract_from_pdf(pdf_bytes):
        """解析 PDF 字节流提取前几页文本用于分析"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            # 只取前 5 页，防止解析过长
            for i in range(min(len(doc), 5)):
                text_parts.append(doc[i].get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF 解析失败: {e}")
            return "[PDF 内容解析异常]"

class UniversityScanner:
    def __init__(self, config_path):
        load_dotenv()
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        with open('config.yaml', 'r', encoding='utf-8') as f:
            main_config = yaml.safe_load(f) or {}

        self.proxy_url = main_config.get('proxy') or os.getenv("HTTP_PROXY")
        self.db = DatabaseManager()
        self.selected_majors = main_config.get('selected_majors', [])
        self.selected_universities = main_config.get('selected_universities', [])
        
        # 增加全局 AI 开关支持
        self.use_ai = main_config.get('use_ai', True)

        ai_config = {
            'enabled': self.use_ai,
            'api_key': main_config.get('api_key', ''),
            'provider': main_config.get('ai_provider', 'DeepSeek'),
            'model': main_config.get('model_version', 'deepseek-chat'),
            'base_url': main_config.get('base_url', 'https://api.deepseek.com/v1/')
        }

        self.ai = AIAnalyzer(ai_config=ai_config, proxy=self.proxy_url)        
        self.yzw_map = {}
        if os.path.exists('yzw_university_map.json'):
            with open('yzw_university_map.json', 'r', encoding='utf-8') as f:
                self.yzw_map = json.load(f)
        
        self.semaphore = None # 延迟初始化
        self.http_client = httpx.AsyncClient(
            proxy=self.proxy_url,
            verify=False, 
            timeout=10.0, 
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
        )

    async def _get_content_with_engine(self, url, browser_context, force_browser=False):
        """
        双擎机制：优先极速 httpx，必要时降级 Playwright。
        """
        if not force_browser:
            try:
                resp = await self.http_client.get(url)
                if resp.status_code == 200:
                    ct = resp.headers.get('content-type', '').lower()
                    if 'application/pdf' in ct:
                        return resp.content, "httpx_pdf"
                    
                    # 💡 优化：如果 HTML 内容过短（可能是在 JS 渲染中），判定为失败
                    if len(resp.text) < 500 and '<html' in resp.text.lower():
                        logger.debug(f"httpx 抓取内容过短，疑似需要渲染: {url}")
                    else:
                        return resp.text, "httpx_html"
            except Exception as e:
                logger.debug(f"极速引擎失效 ({e})，准备呼叫浏览器: {url}")

        # 降级为 Playwright
        page = await browser_context.new_page()
        try:
            # 性能优化：拦截多余资源（图片、字体、CSS、追踪脚本）
            def should_abort(request):
                resource_type = request.resource_type
                if resource_type in ["image", "font", "stylesheet"]:
                    return True
                url = request.url.lower()
                if any(k in url for k in ["google-analytics", "hm.baidu", "stat", "collect"]):
                    return True
                return False

            await page.route("**/*", lambda route: route.abort() if should_abort(route.request) else route.continue_())
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            content = await page.content()
            return content, "playwright_render"
        except Exception as e:
            logger.error(f"浏览器抓取失败: {url} -> {e}")
            return None, "failed"
        finally:
            await page.close()

    async def close(self):
        """释放资源"""
        await self.http_client.aclose()

    def _calc_hash(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def scan_module(self, browser_context, uni_name, module):
        async with self.semaphore:
            m_name = module['name']
            m_url = module['url']
            m_selector = module.get('selector', '').strip()  # 防御空 selector

            raw_data, method = await self._get_content_with_engine(m_url, browser_context)
            if not raw_data: return

            # 🛡️ 优先使用 lxml，失败则降级到内置解析器
            try:
                soup = BeautifulSoup(raw_data if isinstance(raw_data, str) else raw_data.decode('utf-8', 'ignore'), 'lxml')
            except Exception:
                soup = BeautifulSoup(raw_data if isinstance(raw_data, str) else raw_data.decode('utf-8', 'ignore'), 'html.parser')
            
            # ✅ 兼容空 selector：自动提取全页包含关键词的链接
            if not m_selector:
                logger.info(f"[{uni_name}] 模块 『{m_name}』 未配置 selector，使用全页自动提取模式")
                KEYWORDS = ['通知', '公告', '招生', '录取', '复试', '简章', '名单', '方案', '要求', '成绩', '分数', '调剂', '面试', '笔试', '初试', '一志愿', '研究生', '硕士', '博士', '大纲', '推免', '夏令营', '报名', '解答', '说明', '安排']
                items = []
                base_parsed = urllib.parse.urlparse(m_url)
                
                # 💡 剔除常见的导航栏、侧边栏、底部件干扰，防止把栏目按钮当成通知
                for noise_tag in soup.find_all(['nav', 'header', 'footer', 'aside']):
                    noise_tag.decompose()
                for noise_class in soup.find_all(class_=re.compile(r'nav|menu|sidebar|footer|header|links', re.I)):
                    noise_class.decompose()
                    
                for a in soup.find_all('a', href=True):
                    text = a.get_text(strip=True)
                    href = a.get('href')
                    if any(kw in text for kw in KEYWORDS) and len(text) > 5:
                        # URL 过滤：防止无关连接 (如页脚外链)
                        if href.startswith('http'):
                            href_parsed = urllib.parse.urlparse(href)
                            # 必须在同一域名下，并且路径不能是首页
                            if href_parsed.netloc != base_parsed.netloc: continue
                        items.append(a)
            else:
                items = soup.select(m_selector)
            
            # 💡 Bug Fix: 如果列表为空且之前用的是极速引擎，可能是 JS 动态加载，强制用浏览器重试
            if len(items) == 0 and method.startswith("httpx"):
                logger.debug(f"[{uni_name}] 列表为空，怀疑动态加载，触发浏览器补扫: {m_url}")
                raw_data, method = await self._get_content_with_engine(m_url, browser_context, force_browser=True)
                if raw_data:
                    try:
                        soup = BeautifulSoup(raw_data if isinstance(raw_data, str) else raw_data.decode('utf-8', 'ignore'), 'lxml')
                    except Exception:
                        soup = BeautifulSoup(raw_data if isinstance(raw_data, str) else raw_data.decode('utf-8', 'ignore'), 'html.parser')
                    if not m_selector:
                        base_parsed = urllib.parse.urlparse(m_url)
                        for noise_tag in soup.find_all(['nav', 'header', 'footer', 'aside']):
                            noise_tag.decompose()
                        for noise_class in soup.find_all(class_=re.compile(r'nav|menu|sidebar|footer|header|links', re.I)):
                            noise_class.decompose()

                        for a in soup.find_all('a', href=True):
                            text = a.get_text(strip=True)
                            href = a.get('href')
                            if any(kw in text for kw in KEYWORDS) and len(text) > 5:
                                if href.startswith('http'):
                                    href_parsed = urllib.parse.urlparse(href)
                                    if href_parsed.netloc != base_parsed.netloc: continue
                                items.append(a)
                    else:
                        items = soup.select(m_selector)

            for item in items:
                a = item if item.name == 'a' else item.find('a')
                if not a: continue
                
                title = a.get_text(strip=True)
                href = a.get('href')
                if not title or not href: continue

                # 补全 URL
                link = urljoin(m_url, href)
                
                # 尝试从列表项提取日期 (支持 YYYY-MM-DD, YYYY/MM/DD, YYYY年MM月DD日)
                publish_date = None
                current_year = datetime.datetime.now().year
                
                # 先尝试从 item 本身或父元素提取日期
                search_text = item.get_text() if hasattr(item, 'get_text') else str(item)
                if a.parent and hasattr(a.parent, 'get_text'):
                    search_text = a.parent.get_text()
                
                date_match = re.search(r'(\d{4})[-/年\.](\d{1,2})[-/月\.](\d{1,2})', search_text)
                short_match = re.search(r'(\d{2})[-/月\.](\d{2})', search_text)
                
                y = m = d = None
                if date_match:
                    y, m, d = date_match.groups()
                    publish_date = f"{y}-{int(m):02d}-{int(d):02d}"
                elif short_match:
                    m_short, d_short = short_match.groups()
                    # 如果匹配到MM-DD，再看标题里有没有年份
                    y_match = re.search(r'(20\d{2})', title)
                    y = y_match.group(1) if y_match else current_year
                    publish_date = f"{y}-{int(m_short):02d}-{int(d_short):02d}"
                else:
                    # 如果完全没日期格式，检查标题里是否有年份
                    y_match = re.search(r'(20\d{2})', title)
                    if y_match:
                        y = int(y_match.group(1))
                        # ⚠️ 只有年份无具体日期时，不设兜底日期
                        # 让 publish_date 保持 None，后续用 created_at 排序
                        publish_date = None

                # 💡 年份过滤：如果通知的年份超过1年前，则抛弃（不爬取远古坟贴）
                if y is not None and int(y) < current_year - 1:
                    logger.debug(f"[{uni_name}] 跳过陈旧通知: {title} ({y}年)")
                    continue

                # 💡 15天时间窗口过滤：有精确日期时，超过15天前的通知直接跳过
                if publish_date and '-' in str(publish_date):
                    try:
                        pub_dt = datetime.datetime.strptime(str(publish_date), '%Y-%m-%d')
                        days_ago = (datetime.datetime.now() - pub_dt).days
                        if days_ago > 15:
                            logger.debug(f"[{uni_name}] 跳过超过15天的通知: {title} ({publish_date})")
                            continue
                    except ValueError:
                        pass

                # 判定是否存在
                old_hash = self.db.is_link_scanned(link)
                
                # 情况 A：全新链接 -> 深度深度解析
                if old_hash is None:
                    # 如果标题又是重复的（同模块内跨页面同步），除非哈希不同，否则通常跳过
                    if self.db.check_duplicate_title(uni_name, title, module=m_name):
                        continue
                    
                    logger.info(f"✨ [{uni_name}] 发现新情报: {title[:20]}...")
                    await self._deep_process_item(uni_name, m_name, title, link, browser_context, is_new=True, list_date=publish_date)

                # 情况 B：老链接 -> 触发异动监测频率逻辑
                else:
                    # 每轮都对老链接进行一次 Hash 比对以实现“异动监测”
                    # 只有处于前两页左右的列表项才会被扫描到，性能损耗可控
                    await self._deep_process_item(uni_name, m_name, title, link, browser_context, is_new=False)

    async def _deep_process_item(self, uni_name, module_name, title, link, browser_context, is_new=True, list_date="N/A"):
        """执行抓取正文、算 Hash、AI 摘要、入库全流程"""
        try:
            raw_content, method = await self._get_content_with_engine(link, browser_context)
            if not raw_content: return

            is_pdf = method == 'httpx_pdf' or link.lower().endswith('.pdf')
            
            # 提取正文
            if is_pdf:
                full_text = await ContentExtractor.extract_from_pdf(raw_content if isinstance(raw_content, bytes) else b"")
            else:
                full_text = await ContentExtractor.extract_from_html(raw_content)

            new_hash = self._calc_hash(full_text)
            
            # 如果是老链接且 Hash 没变，返回
            if not is_new and new_hash == self.db.is_link_scanned(link):
                return

            # 尝试弥合完全缺失的日期：若列表页没提日期，从正文头部萃取
            if not list_date:
                # 官方通报常见于文首或文末落款，因此检查头部和尾部
                search_scope = title + " " + full_text[:1000] + " " + full_text[-1000:]
                body_date_match = re.search(r'(20\d{2})[-/年\.](\d{1,2})[-/月\.](\d{1,2})', search_scope)
                if body_date_match:
                    by, bm, bd = body_date_match.groups()
                    list_date = f"{by}-{int(bm):02d}-{int(bd):02d}"
            
            # 💡 终极兜底 15天过滤：如果依然找不到日期，或者日期超过15天，彻底遗弃
            if list_date:
                try:
                    pub_dt = datetime.datetime.strptime(str(list_date), '%Y-%m-%d')
                    if (datetime.datetime.now() - pub_dt).days > 15:
                        logger.debug(f"[{uni_name}] 正文判定为逾期 (>15天) 陈旧通知，已拦截: {title} ({list_date})")
                        return
                except ValueError:
                    pass
            else:
                logger.debug(f"[{uni_name}] 原文及正文均无法提取生效日期，视为非公告页面，已拦截: {title}")
                return

            # 第一步：初步猜测年份
            detected_year = datetime.datetime.now().year
            year_match = re.search(r'(20\d\d)', title + full_text[:200])
            if year_match:
                detected_year = int(year_match.group(1))

            # --- AI 缓存层优化 ---
            ai_data = self.db.get_ai_cache(new_hash)
            if ai_data:
                logger.info(f"  └─ ⚡ 命中本地 AI 语义缓存，跳过 API 调用。")
            else:
                # AI 深度分析
                logger.info(f"  └─ 🚀 AI 正在深度阅读全文并启动纵向对比...")

                # 第二步：获取历史参照物
                category_guess = "通知"
                if "复试" in title: category_guess = "复试通知"
                elif "拟录取" in title or "名单" in title: category_guess = "拟录取名单"
                
                historical_item = self.db.get_historical_match(uni_name, category_guess, "", detected_year)
                hist_context = historical_item['ai_summary'] if historical_item else None
                
                if self.use_ai:
                    # 💡 精准获取当前学校对应的用户设置专业
                    target_majors = []
                    if hasattr(self, 'selected_universities') and uni_name in self.selected_universities:
                        idx = self.selected_universities.index(uni_name)
                        if idx < len(self.selected_majors):
                            target_majors = [self.selected_majors[idx]]

                    ai_data = await self.ai.analyze_content(
                        uni_name, module_name, title, full_text, 
                        user_majors=target_majors,
                        historical_context=hist_context
                    )
                    if historical_item:
                        ai_data['historical_ref_id'] = historical_item['id']
                else:
                    ai_data = self.ai._fallback_analyze(title)
                    ai_data['ai_summary'] = ""
                    ai_data['ai_action'] = ""

            if not ai_data.get('target_year'):
                ai_data['target_year'] = detected_year

            if is_new:
                self.db.save_announcement(
                    university=uni_name, module=module_name, title=title, 
                    link=link, date=list_date, ai_data=ai_data, is_pdf=is_pdf,
                    full_text=full_text, content_hash=new_hash
                )
            else:
                self.db.update_content(link, full_text, new_hash, ai_data)
                logger.warning(f"🚨 [{uni_name}] 检测到页面内容发生【异动暗改】: {title[:20]}")

        except Exception as e:
            logger.error(f"深度解析数据项出错 ({link}): {e}")

    async def scan(self):
        logger.info("============== 启动院校公告监控引擎 ==============")
        self.semaphore = asyncio.Semaphore(3)
        async with async_playwright() as p:
            proxy_cfg = {"server": self.proxy_url} if self.proxy_url else None
            browser = await p.chromium.launch(headless=True, proxy=proxy_cfg)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
            
            # 第一阶段：学校官网全量扫描
            tasks = []
            for uni in self.config.get('universities', []):
                for module in uni.get('modules', []):
                    tasks.append(self.scan_module(context, uni['name'], module))
            
            # 第二阶段：研招网全量监控（如果开启）
            if self.config.get('enable_yzw_all', False):
                for name, path in self.yzw_map.items():
                    yzw_module = {"name": "研招网", "url": "https://yz.chsi.com.cn" + path, "selector": ".news-list li"}
                    tasks.append(self.scan_module(context, name, yzw_module))

            if tasks:
                logger.info(f"已拉起 {len(tasks)} 个并行扫描协程...")
                await asyncio.gather(*tasks)
            
            await browser.close()
            logger.info("============== 本轮院校公告扫描结束 ==============")

if __name__ == "__main__":
    # 💡 恢复为 universities.yaml (这是 Web 端生成的实时清单)
    scanner = UniversityScanner('universities.yaml')
    asyncio.run(scanner.scan())
