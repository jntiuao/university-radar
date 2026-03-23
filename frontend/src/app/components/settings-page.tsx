import { useReducer, useMemo, useState, useCallback, useEffect } from "react";
import { motion } from "motion/react";
import { toast } from "sonner";
import {
  School,
  Bot,
  Plus,
  X,
  Save,
  Sparkles,
  Mail,
  MessageSquare,
  Check,
  Send,
  ExternalLink,
  Trash2,
  Bell,
  Wifi,
  Pencil,
  HelpCircle,
} from "lucide-react";
import { Switch } from "./ui/switch";
import { FormInput, FormSelect } from "./form-controls";
import {
  AI_PROVIDERS,
  DEGREE_TYPES,
} from "../data/mock-data";

// AI 模型联动配置表（每个服务商最新 3 个模型）
const AI_MODEL_MAP: Record<string, { models: string[], baseUrl: string }> = {
  "Google (Gemini)": {
    models: ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/"
  },
  "OpenAI (GPT)": {
    models: ["gpt-4o", "gpt-4o-mini", "chatgpt-4o-latest"],
    baseUrl: "https://api.openai.com/v1/"
  },
  "Anthropic (Claude)": {
    models: ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    baseUrl: "https://api.anthropic.com/v1/"
  },
  "DeepSeek": {
    models: ["deepseek-chat", "deepseek-reasoner"],
    baseUrl: "https://api.deepseek.com/v1/"
  },
  "火山引擎 (豆包)": {
    models: ["doubao-pro-32k", "doubao-lite-32k", "doubao-pro-128k"],
    baseUrl: "https://ark.cn-beijing.volces.com/api/v3/"
  },
  "阿里通义千问 (Qwen)": {
    models: ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-long"],
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1/"
  },
  "智谱AI (GLM)": {
    models: ["glm-4-plus", "glm-4-0520", "glm-4-flash", "glm-3-turbo"],
    baseUrl: "https://open.bigmodel.cn/api/paas/v4/"
  },
  "月之暗面 (Kimi)": {
    models: ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    baseUrl: "https://api.moonshot.cn/v1/"
  },
  "百度文心一言 (ERNIE)": {
    models: ["ERNIE-4.0-8K", "ERNIE-3.5-8K", "ERNIE-Speed-128K"],
    baseUrl: "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/"
  },
  "腾讯混元 (Hunyuan)": {
    models: ["hunyuan-pro", "hunyuan-standard", "hunyuan-lite"],
    baseUrl: "https://api.hunyuan.cloud.tencent.com/v1/"
  },
  "零一万物 (Yi)": {
    models: ["yi-large", "yi-medium", "yi-spark"],
    baseUrl: "https://api.lingyiwanwu.com/v1/"
  },
  "百川智能 (Baichuan)": {
    models: ["Baichuan4", "Baichuan3-Turbo", "Baichuan3-Turbo-128k"],
    baseUrl: "https://api.baichuan-ai.com/v1/"
  },
  "阶跃星辰 (StepFun)": {
    models: ["step-2-16k", "step-1-128k", "step-1-8k", "step-1v-8k"],
    baseUrl: "https://api.stepfun.com/v1/"
  }
};

// ─── 数据类型 ──────────────────────────────────
interface MonitorTarget {
  id: number;
  university: string;
  major: string;
  graduateUrl: string;
  departmentUrl: string;
  editing?: boolean; // 是否处于编辑模式
}

interface SettingsState {
  aiEnabled: boolean;
  aiProvider: string;
  modelVersion: string;
  baseUrl: string;
  apiKey: string;
  proxy: string;
  emailEnabled: boolean;
  emailSender: string;
  emailPassword: string;
  emailAddress: string;
  feishuEnabled: boolean;
  feishuWebhook: string;
  // Step1 输入
  inputUniversity: string;
  inputGraduateUrl: string;
  inputDepartmentUrl: string;
  inputDegreeType: string;
  inputDiscipline: string;
  inputMajor: string;
  // Step1 级联 - 省份→院校
  inputRegion: string;
  targets: MonitorTarget[];
  scanInterval: number;
}

type Action =
  | { type: "SET_FIELD"; field: keyof SettingsState; value: any }
  | { type: "ADD_TARGET"; target: MonitorTarget }
  | { type: "REMOVE_TARGET"; id: number }
  | { type: "UPDATE_TARGET"; id: number; field: string; value: string }
  | { type: "TOGGLE_EDIT"; id: number }
  | { type: "RESET_INPUT" }
  | { type: "LOAD_CONFIG"; payload: any };

const initialState: SettingsState = {
  aiEnabled: true,
  aiProvider: "Google (Gemini)",
  modelVersion: "gemini-2.5-flash",
  baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
  apiKey: "",
  proxy: "",
  emailEnabled: false,
  emailSender: "",
  emailPassword: "",
  emailAddress: "",
  feishuEnabled: false,
  feishuWebhook: "",
  inputUniversity: "",
  inputGraduateUrl: "",
  inputDepartmentUrl: "",
  inputDegreeType: "",
  inputDiscipline: "",
  inputMajor: "",
  inputRegion: "",
  targets: [],
  scanInterval: 15,
};

function reducer(state: SettingsState, action: Action): SettingsState {
  switch (action.type) {
    case "SET_FIELD": {
      const next: any = { ...state, [action.field]: action.value };
      if (action.field === "inputDegreeType") { next.inputDiscipline = ""; next.inputMajor = ""; }
      else if (action.field === "inputDiscipline") { next.inputMajor = ""; }
      else if (action.field === "inputRegion") { next.inputUniversity = ""; }
      if (action.field === "aiProvider") {
        const mapping = AI_MODEL_MAP[action.value];
        if (mapping) { next.modelVersion = mapping.models[0]; next.baseUrl = mapping.baseUrl; }
      }
      return next;
    }
    case "ADD_TARGET":
      return { ...state, targets: [...state.targets, action.target] };
    case "REMOVE_TARGET":
      return { ...state, targets: state.targets.filter((t) => t.id !== action.id) };
    case "UPDATE_TARGET":
      return { ...state, targets: state.targets.map(t => t.id === action.id ? { ...t, [action.field]: action.value } : t) };
    case "TOGGLE_EDIT":
      return { ...state, targets: state.targets.map(t => t.id === action.id ? { ...t, editing: !t.editing } : t) };
    case "RESET_INPUT":
      return { ...state, inputUniversity: "", inputGraduateUrl: "", inputDepartmentUrl: "", inputRegion: "" };
    case "LOAD_CONFIG": {
      const data = action.payload;
      const next = { ...state };
      if (data.api_key) next.apiKey = data.api_key;
      if (data.proxy) next.proxy = data.proxy;
      if (data.base_url) next.baseUrl = data.base_url;
      if (data.ai_provider) next.aiProvider = data.ai_provider;
      if (data.model_version) next.modelVersion = data.model_version;
      if (data.scan_interval) next.scanInterval = data.scan_interval;
      
      const notifs = data.notifications || [];
      const feishu = notifs.find((n: any) => n.channel === 'feishu');
      if (feishu) { next.feishuEnabled = true; next.feishuWebhook = feishu.token; }
      const email = notifs.find((n: any) => n.channel === 'email');
      if (email) {
        next.emailEnabled = true;
        const pts = email.token.split('|');
        if (pts.length === 3) { next.emailSender = pts[0]; next.emailPassword = pts[1]; next.emailAddress = pts[2]; }
        else { next.emailAddress = email.token; }
      }
      
      const unis = data.selected_universities || [];
      const majs = data.selected_majors || [];
      const gradUrls = data.graduate_urls || [];
      const deptUrls = data.department_urls || [];
      next.targets = unis.map((u: string, i: number) => ({
        id: i, university: u, major: majs[i] || "", graduateUrl: gradUrls[i] || "", departmentUrl: deptUrls[i] || "", editing: false
      }));
      return next;
    }
    default:
      return state;
  }
}

function StepBadge({ step }: { step: number }) {
  return (
    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#6c5ce7] to-[#a29bfe] flex items-center justify-center text-white text-[12px] shrink-0" style={{ fontWeight: 700 }}>
      {step}
    </div>
  );
}

export function SettingsPage() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [saving, setSaving] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);
  const [testingFeishu, setTestingFeishu] = useState(false);
  const [testingApi, setTestingApi] = useState(false);
  const [testingNotice, setTestingNotice] = useState(false);

  const [backendMajors, setBackendMajors] = useState<Record<string, any>>({});
  const [backendRegions, setBackendRegions] = useState<Record<string, string[]>>({});

  const set = useCallback(
    (field: keyof SettingsState) => (value: any) =>
      dispatch({ type: "SET_FIELD", field, value }),
    []
  );

  // 省份列表
  const regionNames = useMemo(() => Object.keys(backendRegions).sort(), [backendRegions]);
  // 省份下的院校
  const regionUnis = useMemo(() => {
    if (!state.inputRegion) return [];
    return backendRegions[state.inputRegion] || [];
  }, [state.inputRegion, backendRegions]);

  // 学科门类基于学位类型
  const disciplines = useMemo(() => {
    if (!state.inputDegreeType) return [];
    const group = backendMajors[state.inputDegreeType];
    if (!group || typeof group !== 'object') return [];
    return Object.keys(group).sort().map((name: string) => ({ name, majors: group[name] || [] }));
  }, [backendMajors, state.inputDegreeType]);

  const majors = useMemo(() => {
    const disc = disciplines.find((d) => d.name === state.inputDiscipline);
    return disc?.majors ?? [];
  }, [disciplines, state.inputDiscipline]);

  useEffect(() => {
    fetch('/api/config').then(r => r.json()).then(data => dispatch({ type: "LOAD_CONFIG", payload: data })).catch(() => toast.error("加载配置失败"));
    fetch('/api/majors').then(r => r.json()).then(data => setBackendMajors(data || {})).catch(() => {});
    fetch('/api/universities').then(r => r.json()).then(data => setBackendRegions(data.grouped || {})).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    const notifications: any[] = [];
    if (state.feishuEnabled && state.feishuWebhook) notifications.push({ channel: "feishu", token: state.feishuWebhook });
    if (state.emailEnabled && state.emailAddress) notifications.push({ channel: "email", token: `${state.emailSender}|${state.emailPassword}|${state.emailAddress}` });

    const payload = {
      api_key: state.apiKey, proxy: state.proxy, base_url: state.baseUrl, ai_provider: state.aiProvider, model_version: state.modelVersion, scan_interval: state.scanInterval,
      notifications,
      selected_universities: state.targets.map(t => t.university),
      selected_majors: state.targets.map(t => t.major),
      graduate_urls: state.targets.map(t => t.graduateUrl),
      department_urls: state.targets.map(t => t.departmentUrl)
    };
    try {
      const res = await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (res.ok) toast.success("配置已保存", { description: `已保存 ${state.targets.length} 个监控目标` });
      else toast.error("保存失败");
    } catch { toast.error("网络错误"); }
    finally { setSaving(false); }
  };

  // API 连通性测试
  const handleTestApi = async () => {
    setTestingApi(true);
    try {
      const res = await fetch('/api/test-api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: state.aiProvider, api_key: state.apiKey, base_url: state.baseUrl, model: state.modelVersion, proxy: state.proxy })
      });
      const data = await res.json();
      if (data.status === 'ok') toast.success("连通成功 ✓", { description: data.message });
      else toast.error("连通失败", { description: data.message });
    } catch { toast.error("测试请求失败"); }
    finally { setTestingApi(false); }
  };

  const handleTestNotice = async () => {
    setTestingNotice(true);
    toast.info("正在发送测试通知...");
    try {
      const res = await fetch('/api/test-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (data.status === 'ok') toast.success("测试通知已加入推送队列！");
      else toast.error("测试通知推送失败", { description: data.message });
    } catch { toast.error("测试通知发送异常"); }
    finally { setTestingNotice(false); }
  };

  const handleAddTarget = () => {
    if (!state.inputUniversity) { toast.error("请填写或选择院校名称"); return; }
    if (!state.inputMajor) { toast.error("请选择目标专业"); return; }
    if (state.targets.some(t => t.university === state.inputUniversity && t.major === state.inputMajor)) { toast.warning("该目标已存在"); return; }
    dispatch({
      type: "ADD_TARGET",
      target: { id: Date.now(), university: state.inputUniversity, major: state.inputMajor, graduateUrl: state.inputGraduateUrl, departmentUrl: state.inputDepartmentUrl },
    });
    dispatch({ type: "RESET_INPUT" });
    toast.success("添加成功", { description: `${state.inputUniversity} 已加入监控列表` });
  };

  return (
    <div className="p-6 max-w-[960px] mx-auto space-y-6">
      {/* Page header */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center gap-3 mb-1">
          <School className="w-6 h-6 text-[#6c5ce7]" />
          <h1>院校与系统设置</h1>
        </div>
        <p className="text-[13px] text-muted-foreground ml-9">按步骤配置您的监控目标和通知渠道。</p>
      </motion.div>

      {/* ═══ Step 1: 添加目标院校 ═══ */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }} className="bg-card rounded-2xl border border-border overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-gradient-to-r from-[#6c5ce7]/5 to-transparent">
          <div className="flex items-center gap-3">
            <StepBadge step={1} />
            <div>
              <h3>添加目标院校</h3>
              <p className="text-[12px] text-muted-foreground">可从省份级联选择院校，或直接手动输入院校名称。</p>
            </div>
          </div>
        </div>
        <div className="px-6 py-5 space-y-5">
          {/* 院校选择：省份级联 OR 手动输入 */}
          <div className="grid grid-cols-3 gap-5">
            <FormSelect
              label="省份（可选）"
              value={state.inputRegion}
              onChange={(e) => set("inputRegion")(e.target.value)}
              placeholderOption="-- 选择省份 --"
              options={regionNames.map((r: string) => ({ value: r, label: r }))}
            />
            <FormSelect
              label="从列表选择院校"
              value={state.inputUniversity}
              onChange={(e) => set("inputUniversity")(e.target.value)}
              disabled={!state.inputRegion}
              placeholderOption={state.inputRegion ? "-- 选择院校 --" : "-- 先选省份 --"}
              options={regionUnis.map((u: string) => ({ value: u, label: u }))}
            />
            <FormInput
              label="或手动输入院校名"
              type="text"
              value={state.inputUniversity}
              onChange={(e) => set("inputUniversity")(e.target.value)}
              placeholder="直接输入院校全称"
            />
          </div>
          <div className="grid grid-cols-2 gap-5">
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-[13px] text-foreground" style={{ fontWeight: 500 }}>
                研究生院通知页网址
                <div className="group relative flex items-center">
                  <HelpCircle className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help hover:text-[#0984e3] transition-colors" />
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-[240px] p-2 bg-popover text-popover-foreground text-[12px] rounded-lg shadow-xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-50 border border-border">
                    请填入发布复试通知、录取名单等公告的<strong>具体列表页面</strong>网址，而不是研究生院首页网址。
                    <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 border-popover border-t-4 border-l-4 border-r-4 border-l-transparent border-r-transparent"></div>
                  </div>
                </div>
              </div>
              <input type="text" value={state.inputGraduateUrl} onChange={(e) => set("inputGraduateUrl")(e.target.value)} placeholder="https://yjsy.xxx.edu.cn/tzgg/" className="w-full h-10 px-3 py-2 rounded-xl border border-input bg-background text-[13px] focus:border-[#0984e3] focus:ring-1 focus:ring-[#0984e3]/30 transition-all outline-none placeholder:text-muted-foreground/50" />
            </div>
            
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-[13px] text-foreground" style={{ fontWeight: 500 }}>
                专业所属学院通知页网址
                <div className="group relative flex items-center">
                  <HelpCircle className="w-3.5 h-3.5 text-muted-foreground/60 cursor-help hover:text-[#6c5ce7] transition-colors" />
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-[240px] p-2 bg-popover text-popover-foreground text-[12px] rounded-lg shadow-xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-50 border border-border">
                    请填入具体招生学院发布信息的公告页面。由于学院级通知往往比学校级更早、更详细，所以雷达会重点扫描。
                    <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 border-popover border-t-4 border-l-4 border-r-4 border-l-transparent border-r-transparent"></div>
                  </div>
                </div>
              </div>
              <input type="text" value={state.inputDepartmentUrl} onChange={(e) => set("inputDepartmentUrl")(e.target.value)} placeholder="https://xxx.xxx.edu.cn/notice/" className="w-full h-10 px-3 py-2 rounded-xl border border-input bg-background text-[13px] focus:border-[#6c5ce7] focus:ring-1 focus:ring-[#6c5ce7]/30 transition-all outline-none placeholder:text-muted-foreground/50" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-5">
            <FormSelect label="学位类型" value={state.inputDegreeType} onChange={(e) => set("inputDegreeType")(e.target.value)} placeholderOption="-- 学硕/专硕 --" options={DEGREE_TYPES.map((d: string) => ({ value: d, label: d }))} />
            <FormSelect label="学科门类" value={state.inputDiscipline} onChange={(e) => set("inputDiscipline")(e.target.value)} disabled={!state.inputDegreeType} placeholderOption={state.inputDegreeType ? "-- 选择学科 --" : "-- 先选学位 --"} options={disciplines.map((d) => ({ value: d.name, label: d.name }))} />
            <FormSelect label="目标专业" value={state.inputMajor} onChange={(e) => set("inputMajor")(e.target.value)} disabled={!state.inputDiscipline} placeholderOption={state.inputDiscipline ? "-- 选择专业 --" : "-- 先选学科 --"} options={majors.map((m: string) => ({ value: m, label: m }))} />
          </div>
          <div className="flex justify-end">
            <button onClick={handleAddTarget} className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#6c5ce7] to-[#a29bfe] text-white text-[13px] hover:shadow-lg hover:shadow-[#6c5ce7]/30 transition-all active:scale-[0.98]">
              <Plus className="w-4 h-4" />
              加入监控列表
            </button>
          </div>
        </div>
      </motion.div>

      {/* ═══ Step 2: 通知设置 ═══ */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.15 }} className="bg-card rounded-2xl border border-border overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-gradient-to-r from-[#0984e3]/5 to-transparent">
          <div className="flex items-center gap-3">
            <StepBadge step={2} />
            <div><h3>通知接收设置</h3><p className="text-[12px] text-muted-foreground">配置情报推送渠道。</p></div>
          </div>
        </div>
        <div className="px-6 py-5 space-y-6">
          {/* Email */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#e17055]/10 flex items-center justify-center"><Mail className="w-4 h-4 text-[#e17055]" /></div>
                <div><div className="text-[13px]" style={{ fontWeight: 600 }}>邮件通知</div><div className="text-[11px] text-muted-foreground">新情报将发送至您的邮箱</div></div>
              </div>
              <Switch checked={state.emailEnabled} onCheckedChange={set("emailEnabled")} />
            </div>
            {state.emailEnabled && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} transition={{ duration: 0.25 }} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <FormInput label="发件箱账号" type="email" value={state.emailSender} onChange={(e) => set("emailSender")(e.target.value)} placeholder="sender@qq.com" accent="blue" />
                  <FormInput label="SMTP 授权码" type="password" value={state.emailPassword} onChange={(e) => set("emailPassword")(e.target.value)} placeholder="xxxxxxxxxxxxx" accent="blue" />
                </div>
                <div className="flex items-end gap-3">
                  <div className="flex-1"><FormInput label="接收邮箱地址" type="email" value={state.emailAddress} onChange={(e) => set("emailAddress")(e.target.value)} placeholder="your-email@example.com" accent="blue" /></div>
                  <button onClick={async () => { setTestingEmail(true); try { await handleSave(); const res = await fetch('/api/test-data', { method: 'POST' }); const data = await res.json(); toast.success("测试邮件已发送", { description: data.message }); } catch { toast.error("发送失败"); } finally { setTestingEmail(false); } }} disabled={testingEmail || !state.emailAddress} className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-[12px] bg-[#e17055]/10 text-[#e17055] hover:bg-[#e17055]/20 transition-colors disabled:opacity-40 shrink-0 mb-[1px]">
                    <Send className="w-3.5 h-3.5" />{testingEmail ? "发送中..." : "测试"}
                  </button>
                </div>
              </motion.div>
            )}
          </div>
          <div className="border-t border-border" />
          {/* Feishu */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#0984e3]/10 flex items-center justify-center"><MessageSquare className="w-4 h-4 text-[#0984e3]" /></div>
                <div><div className="text-[13px]" style={{ fontWeight: 600 }}>飞书通知</div><div className="text-[11px] text-muted-foreground">通过飞书 Webhook 推送</div></div>
              </div>
              <Switch checked={state.feishuEnabled} onCheckedChange={set("feishuEnabled")} />
            </div>
            {state.feishuEnabled && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} transition={{ duration: 0.25 }}>
                <div className="flex items-end gap-3">
                  <div className="flex-1"><FormInput label="飞书 Webhook 地址" type="text" value={state.feishuWebhook} onChange={(e) => set("feishuWebhook")(e.target.value)} placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx" accent="blue" /></div>
                  <button onClick={async () => { setTestingFeishu(true); try { await handleSave(); const res = await fetch('/api/test-data', { method: 'POST' }); const data = await res.json(); toast.success("测试通知已发送", { description: data.message }); } catch { toast.error("发送失败"); } finally { setTestingFeishu(false); } }} disabled={testingFeishu || !state.feishuWebhook} className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-[12px] bg-[#0984e3]/10 text-[#0984e3] hover:bg-[#0984e3]/20 transition-colors disabled:opacity-40 shrink-0 mb-[1px]">
                    <Send className="w-3.5 h-3.5" />{testingFeishu ? "发送中..." : "测试"}
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>

      {/* ═══ Step 3: AI 解析设置 ═══ */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 }} className="bg-card rounded-2xl border border-border overflow-hidden">
        <div className="px-6 py-5 flex items-center justify-between border-b border-border bg-gradient-to-r from-[#6c5ce7]/5 to-transparent">
          <div className="flex items-center gap-3">
            <StepBadge step={3} />
            <div>
              <h3 className="flex items-center gap-2">AI 智能解析 <Sparkles className="w-4 h-4 text-[#fdcb6e]" /></h3>
              <p className="text-[12px] text-muted-foreground">启用后自动提取公告摘要并评估相关度。</p>
            </div>
          </div>
          <Switch checked={state.aiEnabled} onCheckedChange={set("aiEnabled")} />
        </div>
        {state.aiEnabled && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} transition={{ duration: 0.3 }} className="px-6 py-5 space-y-5">
            <div className="grid grid-cols-2 gap-5">
              <FormSelect label="AI 模型服务商" value={state.aiProvider} onChange={(e) => set("aiProvider")(e.target.value)} options={AI_PROVIDERS.map((p: string) => ({ value: p, label: p }))} />
              <FormSelect label="模型版本" value={state.modelVersion} onChange={(e) => set("modelVersion")(e.target.value)} options={(AI_MODEL_MAP[state.aiProvider]?.models || []).map((m: string) => ({ value: m, label: m }))} placeholderOption="-- 请选择模型 --" />
            </div>
            <div className="grid grid-cols-2 gap-5">
              <FormInput label="接口地址 (Base URL)" type="text" value={state.baseUrl} onChange={(e) => set("baseUrl")(e.target.value)} />
              <div className="flex items-end gap-3">
                <div className="flex-1"><FormInput label="AI 密钥 (API KEY)" type="password" value={state.apiKey} onChange={(e) => set("apiKey")(e.target.value)} placeholder="sk-xxxxxxxx" /></div>
                <button onClick={handleTestApi} disabled={testingApi || !state.apiKey} className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-[12px] bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 transition-colors disabled:opacity-40 shrink-0 mb-[1px]">
                  <Wifi className="w-3.5 h-3.5" />{testingApi ? "测试中..." : "测试连通"}
                </button>
              </div>
            </div>
            <FormInput label="全局代理 (Proxy) —— 【已开启翻墙软件系统代理时，通常无需填写】" type="text" value={state.proxy} onChange={(e) => set("proxy")(e.target.value)} placeholder="例: http://127.0.0.1:7890 (国内直连模型无需代理)" />
          </motion.div>
        )}
      </motion.div>

      {/* ═══ Step 4: 已保存院校列表 (可编辑表格) ═══ */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.3 }} className="bg-card rounded-2xl border border-border overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-gradient-to-r from-emerald-500/5 to-transparent">
          <div className="flex items-center gap-3">
            <StepBadge step={4} />
            <div><h3 className="text-emerald-600">已保存的监控列表</h3><p className="text-[12px] text-muted-foreground">共 {state.targets.length} 个目标 · 点击编辑按钮可修改</p></div>
          </div>
        </div>
        <div className="p-0">
          {state.targets.length === 0 ? (
            <div className="py-12 text-center text-[13px] text-muted-foreground">暂无监控目标，请在 Step 1 中添加。</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="px-4 py-3 text-left text-muted-foreground" style={{ fontWeight: 600 }}>院校</th>
                    <th className="px-4 py-3 text-left text-muted-foreground" style={{ fontWeight: 600 }}>专业</th>
                    <th className="px-4 py-3 text-left text-muted-foreground" style={{ fontWeight: 600 }}>研究生院网址</th>
                    <th className="px-4 py-3 text-left text-muted-foreground" style={{ fontWeight: 600 }}>学院网址</th>
                    <th className="px-4 py-3 text-center text-muted-foreground" style={{ fontWeight: 600, width: 80 }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {state.targets.map((target) => (
                    <tr key={target.id} className="border-b border-border last:border-b-0 hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-2.5">
                        <span className="text-[#6c5ce7]" style={{ fontWeight: 600 }}>{target.university}</span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span>{target.major}</span>
                      </td>
                      <td className="px-4 py-2.5">
                        {target.editing ? (
                          <input type="text" value={target.graduateUrl} onChange={(e) => dispatch({ type: "UPDATE_TARGET", id: target.id, field: "graduateUrl", value: e.target.value })} className="w-full px-2 py-1.5 rounded-lg border border-border bg-background text-[12px] focus:border-[#6c5ce7] focus:outline-none" placeholder="https://..." />
                        ) : target.graduateUrl ? (
                          <a href={target.graduateUrl} target="_blank" rel="noopener noreferrer" className="text-[#0984e3] hover:underline inline-flex items-center gap-1">
                            <ExternalLink className="w-3 h-3" />
                            {(() => { try { return new URL(target.graduateUrl).hostname; } catch { return target.graduateUrl; } })()}
                          </a>
                        ) : <span className="text-muted-foreground">未设置</span>}
                      </td>
                      <td className="px-4 py-2.5">
                        {target.editing ? (
                          <input type="text" value={target.departmentUrl} onChange={(e) => dispatch({ type: "UPDATE_TARGET", id: target.id, field: "departmentUrl", value: e.target.value })} className="w-full px-2 py-1.5 rounded-lg border border-border bg-background text-[12px] focus:border-[#6c5ce7] focus:outline-none" placeholder="https://..." />
                        ) : target.departmentUrl ? (
                          <a href={target.departmentUrl} target="_blank" rel="noopener noreferrer" className="text-[#0984e3] hover:underline inline-flex items-center gap-1">
                            <ExternalLink className="w-3 h-3" />
                            {(() => { try { return new URL(target.departmentUrl).hostname; } catch { return target.departmentUrl; } })()}
                          </a>
                        ) : <span className="text-muted-foreground">未设置</span>}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => dispatch({ type: "TOGGLE_EDIT", id: target.id })}
                            className={`w-7 h-7 rounded-lg flex items-center justify-center transition-all ${target.editing ? "bg-emerald-500/10 text-emerald-600" : "text-muted-foreground hover:bg-[#6c5ce7]/10 hover:text-[#6c5ce7]"}`}
                          >
                            {target.editing ? <Check className="w-3.5 h-3.5" /> : <Pencil className="w-3.5 h-3.5" />}
                          </button>
                          <button
                            onClick={() => { dispatch({ type: "REMOVE_TARGET", id: target.id }); toast("已移除", { description: target.university }); }}
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-[#ff4757]/10 hover:text-[#ff4757] transition-all"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        
        {/* === 监控频率设置 === */}
        <div className="px-6 py-5 border-t border-border bg-muted/10 flex items-center justify-between">
          <div>
            <span className="text-[13px] font-medium text-foreground">后台监控频率</span>
            <p className="text-[11px] text-muted-foreground mt-0.5">多久执行一次全局扫描。频率太高可能触发反爬，推荐 15 - 30 分钟。</p>
          </div>
          <div className="w-[180px]">
             <select
                 className="w-full px-3 py-2 rounded-lg border border-border bg-background text-[13px] text-foreground focus:border-[#6c5ce7] focus:ring-1 focus:ring-[#6c5ce7] focus:outline-none transition-all"
                 value={state.scanInterval}
                 onChange={(e) => set("scanInterval")(parseInt(e.target.value, 10))}
             >
                 <option value={5}>每 5 分钟 (激进)</option>
                 <option value={10}>每 10 分钟</option>
                 <option value={15}>每 15 分钟 (推荐)</option>
                 <option value={30}>每 30 分钟</option>
                 <option value={60}>每 60 分钟 (慢速)</option>
             </select>
          </div>
        </div>
      </motion.div>

      {/* Save */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.4 }} className="flex justify-center pb-4 gap-4">
        <button onClick={handleSave} disabled={saving} className={`flex items-center gap-2 px-8 py-3 rounded-xl text-white text-[14px] transition-all active:scale-[0.98] ${saving ? "bg-gradient-to-r from-emerald-500 to-emerald-600" : "bg-gradient-to-r from-[#6c5ce7] to-[#a29bfe] hover:shadow-xl hover:shadow-[#6c5ce7]/30"}`}>
          {saving ? (<><Check className="w-4 h-4 animate-pulse" />保存中...</>) : (<><Save className="w-4 h-4" />保存配置</>)}
        </button>
        <button onClick={handleTestNotice} disabled={testingNotice} className={`flex items-center gap-2 px-6 py-3 rounded-xl text-[#0984e3] bg-[#0984e3]/10 border border-[#0984e3]/20 hover:bg-[#0984e3]/20 text-[14px] transition-all active:scale-[0.98] ${testingNotice ? "opacity-50" : ""}`}>
          <Mail className="w-4 h-4" />发送测试通知
        </button>
      </motion.div>
    </div>
  );
}
