import logging
import json
import os
import re
from openai import OpenAI
import httpx

logger = logging.getLogger('AIAnalyzer')

class AIAnalyzer:
    def __init__(self, ai_config=None, proxy=None):
        self.config = ai_config or {}
        self.proxy = proxy
        self.enabled = self.config.get('enabled', False)
        # 统一 provider 名称为小写，兼容 "Google (Gemini)" 等格式
        raw_provider = self.config.get('provider', 'google')
        self.provider = raw_provider.lower().split('(')[0].split(' ')[0].strip()
        self.api_key = self.config.get('api_key', '')
        self.base_url = self.config.get('base_url', '')
        self.model = self.config.get('model', '')
        
        # 初始化 OpenAI 客户端
        http_client = None
        if self.proxy:
            http_client = httpx.Client(proxy=self.proxy)
            
        if self.enabled:
            # 优先从配置或环境变量获取 Key
            final_api_key = self.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
            
            # 如果配置中没填 base_url 或 model，这里提供默认兜底
            if not self.base_url:
                if self.provider == 'google': self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                elif self.provider == 'deepseek': self.base_url = "https://api.deepseek.com"
                elif self.provider == 'aliyun': self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                elif self.provider == 'zhipu': self.base_url = "https://open.bigmodel.cn/api/paas/v4/"
                elif self.provider == 'kimi': self.base_url = "https://api.moonshot.cn/v1"
                else: self.base_url = "https://api.openai.com/v1"
            
            if not self.model:
                if self.provider == 'google': self.model = "gemini-1.5-flash"
                elif self.provider == 'deepseek': self.model = "deepseek-chat"
                elif self.provider == 'aliyun': self.model = "qwen-plus"
                elif self.provider == 'zhipu': self.model = "glm-4-flash"
                elif self.provider == 'kimi': self.model = "moonshot-v1-8k"
                else: self.model = "gpt-3.5-turbo"

            if final_api_key:
                self.client = OpenAI(
                    api_key=final_api_key,
                    base_url=self.base_url,
                    http_client=http_client
                )
                logger.info(f"AI 分析引擎已初始化 (提供商: {self.provider}, 模型: {self.model}, 节点: {self.base_url})")
            else:
                self.client = None
                logger.warning("AI 分析引擎初始化失败: 未找到有效的 API Key")
        else:
            self.client = None
            logger.info("AI 分析引擎已初始化 (基础规则模式)")

    def _fallback_analyze(self, title):
        urgency = "中"
        if any(k in title for k in ["复试", "调剂", "成绩", "拟录取", "紧急"]):
            urgency = "高"
        
        # 往年数据检测（考研资讯最怕旧闻）
        import datetime
        current_year = datetime.datetime.now().year
        import re
        years = re.findall(r'20\d\d', title)
        is_historical = False
        if years:
            # 只有当标题中所有的年份都小于当前年份时，才判定为彻底的历史文件
            if all(int(y) < current_year for y in years):
                is_historical = True

        # 考研特征强过滤
        exam_keywords = ["考研", "研究生", "招生", "复试", "调剂", "录取", "硕士", "博士", "保研", "推免", "夏令营", "大纲", "成绩", "考点", "专项计划", "分数", "初试", "面试", "笔试"]
        is_exam_related = any(k in title for k in exam_keywords)

        score = 60
        category = "考研情报"
        reason = "系统极速捕获，匹配基础规则"

        if is_historical:
            score = 10
            category = "历史归档"
            reason = "往年历史归档数据"
        elif not is_exam_related:
            score = 50
            category = "常规通知"
            reason = "未匹配强特征，为防漏报予以保留"
        else:
            category = "考研情报 / 官方动态"

        return {
            "category": category,
            "major": "未解析(触发降级)",
            "urgency": "低" if (is_historical or not is_exam_related) else urgency,
            "relevance_score": score,
            "relevance_reason": reason,
            "summary": f"💡 由于底层解析延迟，这是由极速雷达捕获的原文简报。请以此信息为提示，点击直达官方页面查看完整附件和要求详情。",
            "action": "点击下方按钮查阅官方原文"
        }

    async def analyze_content(self, uni, module, title, content, user_majors=[], historical_context=None):
        """
        对标题和【正文内容】进行深度 AI 分析，并结合【往年数据】进行纵向对比。
        """
        if not self.enabled or not self.client:
            return self._fallback_analyze(title)

        majors_str = "、".join(user_majors) if user_majors else "所有专业"
        
        # 💡 对正文进行二次清洗，去除可能干扰 AI 的特殊 HTML 片段或超长链接
        content_preview = re.sub(r'<[^>]+>', '', content[:1500]) if content else "无正文内容"
        content_preview = re.sub(r'http[s]?://\S+', '[URL]', content_preview)

        system_prompt = f"""你是一个专业的考研情报深度解析 AI。
【用户的目标监控专业为: {majors_str}】

你的任务是根据给定的【大学】、【发文模块】、【标题】和【正文内容】，提取核心干货。
必须以纯 JSON 格式输出，不要有任何废话。
JSON 字段严格包含：
- category: 复合分类标签(必须精炼直白地体现这篇通知的**性质和具体对象**，如"推免名单 / 调剂信息 / 复试大纲"，可用 "/" 分隔2-3个词)
- major: 重点涉及的具体**目标专业或学院**(若没有局限则填 "全校通用"，请尽量识别暗含的专业属性)
- target_year: 识别该通告针对的考研年份(如 2026)，若未明确则填 null
- urgency: 紧急程度("高", "中", "低")
- relevance_score: 0-100的整数。0代表纯杂七杂八的新闻/历史无关通告；60代表一般考研通知；90+代表非常重要的高优情报！
  🚨【极其重要/双重拦截】：
  1. 如果该通知明确属于**其他毫无关联的具体专业**（且不包含 {majors_str}），请务必给出 relevance_score: 10 分以触发拦截！
  2. 如果该通知明确属于**博士研究生（考博/申博）**等非硕士层级的通知，也务必给出 relevance_score: 10 分直接拦截抛弃！ 
  3. 如果它是面向硕士的全校通用性考研通知（如全校招生简章、统考复试线），则正常打高分。
- relevance_reason: 一句话解释为何给出这个分数
- summary: 深度干货总结。务必提取：截止时间、分数线、名额、关键要求（若与 {majors_str} 相关请重点提取）。
- action: 下一步行动建议，分号 ";" 隔开。

【重要：纵向对比指令】
若下方提供了 [往年参考数据]，请务必对比今年与去年的名额、政策异动。
在 summary 中以 “[数据异动: 相比往年...]” 格式置顶标注。
"""
        
        comparison_prompt = f"\n\n[往年参考数据]:\n{historical_context}" if historical_context else ""

        user_prompt = f"""
院校：{uni}
模块：{module}
标题：{title}
{comparison_prompt}

正文截取：
{content_preview}
"""

        try:
            # 💡 使用 httpx 直接请求 OpenAI 兼容端点
            api_url = self.base_url.rstrip('/') + "/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 🛡️ 将 system prompt 合并到 user prompt 中
            combined_prompt = f"[系统指令]\n{system_prompt}\n\n[用户输入]\n{user_prompt}"
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": combined_prompt}
                ],
                "temperature": 0.3
            }

            # 🚀 [绝对关键]：使用 AsyncClient 和 await 解除线程霸占死锁
            async with httpx.AsyncClient(proxy=self.proxy if self.proxy else None, timeout=30.0) as client:
                resp = await client.post(api_url, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.error(f"AI API 返回 HTTP {resp.status_code}，响应体: {resp.text[:500]}")
                resp.raise_for_status()
                resp_json = resp.json()

            content_res = resp_json.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not content_res:
                raise ValueError("AI 返回内容为空（可能被底层安全机制拦截或模型无响应）")
            
            # 使用正则提取 JSON 块，提高容错性
            json_match = re.search(r'\{.*\}', content_res, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                result = json.loads(content_res)
                
            return result

        except Exception as e:
            logger.error(f"AI 深度分析失败: {e}")
            return self._fallback_analyze(title)