import smtplib
import logging
import socks
import socket
from urllib.parse import urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr

logger = logging.getLogger('ExamRadar-Email')

class SocksSMTP(smtplib.SMTP):
    def __init__(self, host, port, proxy_type, proxy_host, proxy_port, timeout=15):
        self.proxy_type = proxy_type
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        super().__init__(host, port, timeout=timeout)

    def _get_socket(self, host, port, timeout):
        if self.debuglevel > 0:
            self._print_debug('connect: to', (host, port), self.source_address)
        return socks.create_connection((host, port), timeout=timeout, source_address=self.source_address,
                                       proxy_type=self.proxy_type, proxy_addr=self.proxy_host, proxy_port=self.proxy_port)

class SocksSMTP_SSL(smtplib.SMTP_SSL):
    def __init__(self, host, port, proxy_type, proxy_host, proxy_port, timeout=15):
        self.proxy_type = proxy_type
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        super().__init__(host, port, timeout=timeout)

    def _get_socket(self, host, port, timeout):
        if self.debuglevel > 0:
            self._print_debug('connect: to', (host, port), self.source_address)
        return socks.create_connection((host, port), timeout=timeout, source_address=self.source_address,
                                       proxy_type=self.proxy_type, proxy_addr=self.proxy_host, proxy_port=self.proxy_port)

class EmailNotifier:
    """
    邮件推送模块 —— 永远不会挂的兜底渠道
    支持主流邮箱的 SMTP 发送
    支持通过 HTTP 代理发送（例如: Gmail 在国内的环境）无痛分流
    """
    SMTP_CONFIGS = {
        "qq.com": ("smtp.qq.com", 465, True),
        "163.com": ("smtp.163.com", 465, True),
        "126.com": ("smtp.126.com", 465, True),
        "gmail.com": ("smtp.gmail.com", 587, False),
        "outlook.com": ("smtp-mail.outlook.com", 587, False),
        "hotmail.com": ("smtp-mail.outlook.com", 587, False),
        "foxmail.com": ("smtp.qq.com", 465, True),
    }

    def __init__(self, sender_email=None, sender_password=None, smtp_host=None, smtp_port=None, proxy=None):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.proxy = proxy

        if sender_email and not smtp_host:
            domain = sender_email.split("@")[-1].lower()
            if domain in self.SMTP_CONFIGS:
                self.smtp_host, self.smtp_port, self.use_ssl = self.SMTP_CONFIGS[domain]
            else:
                self.smtp_host = f"smtp.{domain}"
                self.smtp_port = 587
                self.use_ssl = False
        else:
            self.use_ssl = (smtp_port == 465) if smtp_port else True

    def _get_server(self):
        use_proxy = False
        proxy_type = proxy_host = proxy_port = None

        # 国内邮箱直接跳过代理机制，防止被风控
        domestic_domains = ["qq.com", "163.com", "126.com", "foxmail.com", "yeah.net", "sina.com"]
        if self.sender_email:
            domain = self.sender_email.split("@")[-1].lower()
            if domain in domestic_domains:
                logger.debug(f"ℹ️ 发件邮箱为国内主机 ({domain})，已自动旁路代理直连发信")
            elif self.proxy:
                use_proxy = True

        if use_proxy:
            try:
                parsed = urlparse(self.proxy)
                proxy_type = socks.HTTP if parsed.scheme in ['http', 'https'] else socks.SOCKS5
                proxy_host = parsed.hostname
                proxy_port = parsed.port
                logger.info(f"📧 邮件模块将挂载代理: {self.proxy}")
            except Exception as e:
                logger.error(f"❌ 解析邮件代理失败: {e}")
                use_proxy = False

        if use_proxy:
            if self.use_ssl:
                server = SocksSMTP_SSL(self.smtp_host, self.smtp_port, proxy_type, proxy_host, proxy_port, timeout=15)
            else:
                server = SocksSMTP(self.smtp_host, self.smtp_port, proxy_type, proxy_host, proxy_port, timeout=15)
                server.starttls()
        else:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
                server.starttls()

        return server

    def send_message(self, to_email, title, html_content):
        if not self.sender_email or not self.sender_password:
            logger.error("❌ 邮件推送：未配置发件人信息")
            return False

        msg = MIMEMultipart("alternative")
        
        # 严格遵守 RFC5322 规范：非 ASCII 字符必须用 Base64 或 Quoted-Printable 编码
        msg["From"] = formataddr((str(Header("院校雷达", "utf-8")), self.sender_email))
        msg["To"] = to_email
        msg["Subject"] = Header(f"🎯 {title}", "utf-8")
        
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            server = self._get_server()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, to_email, msg.as_string())
            server.quit()
            logger.info(f"✅ 邮件推送成功: {title[:30]} → {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ 邮件推送失败: {e}")
            return False
