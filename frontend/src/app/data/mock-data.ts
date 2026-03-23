import {
  School,
  Eye,
  BarChart3,
  Clock,
  BookOpen,
  GraduationCap,
  Globe,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

// ─── Types ───────────────────────────────────────
export interface NotificationItem {
  id: string;
  university: string;
  department: string;
  date: string;
  title: string;
  desc: string;
  isNew: boolean;
  link?: string;
}

export interface NotificationGroup {
  category: string;
  categoryLabel: string;
  categoryColor: string;
  categoryIcon: LucideIcon;
  items: NotificationItem[];
}

export interface ConsoleLog {
  time: string;
  type: "SYSTEM" | "CONSOLE";
  icon: string;
  msg: string;
}

export interface StatCard {
  label: string;
  value: string;
  icon: LucideIcon;
  color: string;
}

export interface CategoryFilter {
  key: string;
  label: string;
  icon: LucideIcon | null;
}

// ─── Cascading Data ──────────────────────────────
export interface UniversityInfo {
  name: string;
  disciplines: {
    name: string;
    majors: string[];
  }[];
}

export interface RegionData {
  universities: UniversityInfo[];
}

export const CASCADING_DATA: Record<string, RegionData> = {
  天津: {
    universities: [
      {
        name: "天津师范大学",
        disciplines: [
          { name: "教育学", majors: ["0401 教育学", "0454 应用心理", "0453 汉语国际教育"] },
          { name: "心理学", majors: ["0402 心理学", "0454 应用心理"] },
          { name: "文学", majors: ["0501 中国语言文学", "0502 外国语言文学"] },
        ],
      },
      {
        name: "天津大学",
        disciplines: [
          { name: "工学", majors: ["0801 力学", "0812 计算机科学与技术", "0854 电子信息"] },
          { name: "管理学", majors: ["1201 管理科学与工程", "1252 工商管理"] },
          { name: "心理学", majors: ["0454 应用心理"] },
        ],
      },
      {
        name: "南开大学",
        disciplines: [
          { name: "经济学", majors: ["0201 理论经济学", "0202 应用经济学", "0251 金融"] },
          { name: "数学", majors: ["0701 数学", "0714 统计学"] },
        ],
      },
    ],
  },
  北京: {
    universities: [
      {
        name: "北京大学",
        disciplines: [
          { name: "哲学", majors: ["0101 哲学"] },
          { name: "法学", majors: ["0301 法学", "0351 法律"] },
        ],
      },
      {
        name: "清华大学",
        disciplines: [
          { name: "工学", majors: ["0812 计算机科学与技术", "0854 电子信息"] },
          { name: "管理学", majors: ["1201 管理科学与工程", "1251 工商管理"] },
        ],
      },
    ],
  },
  上海: {
    universities: [
      {
        name: "复旦大学",
        disciplines: [
          { name: "医学", majors: ["1001 基础医学", "1002 临床医学"] },
          { name: "经济学", majors: ["0201 理论经济学", "0251 金融"] },
        ],
      },
    ],
  },
  江苏: {
    universities: [
      {
        name: "南京大学",
        disciplines: [
          { name: "文学", majors: ["0501 中国语言文学"] },
          { name: "天文学", majors: ["0704 天文学"] },
        ],
      },
    ],
  },
  浙江: {
    universities: [
      {
        name: "浙江大学",
        disciplines: [
          { name: "工学", majors: ["0812 计算机科学与技术", "0831 生物医学工程"] },
          { name: "农学", majors: ["0901 作物学"] },
        ],
      },
    ],
  },
  广东: {
    universities: [
      {
        name: "中山大学",
        disciplines: [
          { name: "医学", majors: ["1002 临床医学"] },
          { name: "管理学", majors: ["1204 公共管理"] },
        ],
      },
    ],
  },
};

export const REGIONS = ["天津", "北京", "上海", "江苏", "浙江", "广东"];
export const DEGREE_TYPES = ["学术学位 (学硕)", "专业学位 (专硕)"];
export const AI_PROVIDERS = [
  "Google (Gemini)", 
  "OpenAI (GPT)", 
  "Anthropic (Claude)", 
  "DeepSeek", 
  "火山引擎 (豆包)", 
  "阿里通义千问 (Qwen)", 
  "智谱AI (GLM)", 
  "月之暗面 (Kimi)", 
  "百度文心一言 (ERNIE)", 
  "腾讯混元 (Hunyuan)", 
  "零一万物 (Yi)", 
  "百川智能 (Baichuan)",
  "阶跃星辰 (StepFun)"
];

// ─── Notification page data ─────────────────────
export const UNIVERSITIES = ["全部院校"];

export const CATEGORIES: CategoryFilter[] = [
  { key: "all", label: "全部数据", icon: null },
  { key: "graduate", label: "研究生院", icon: GraduationCap },
  { key: "department", label: "学院/学部", icon: BookOpen },
];

export const NOTIFICATIONS: NotificationGroup[] = [
  {
    category: "graduate",
    categoryLabel: "研究生院",
    categoryColor: "#0984e3",
    categoryIcon: GraduationCap,
    items: [],
  },
  {
    category: "department",
    categoryLabel: "学院/学部通知",
    categoryColor: "#6c5ce7",
    categoryIcon: BookOpen,
    items: [],
  },
];

export const INITIAL_CONSOLE_LOGS: ConsoleLog[] = [];

export const SCAN_LOGS: ConsoleLog[] = [];

export const STATS: StatCard[] = [
  { label: "关注院校", value: "2", icon: School, color: "#6c5ce7" },
  { label: "今日情报", value: "0", icon: Eye, color: "#0984e3" },
  { label: "高匹配率", value: "4%", icon: BarChart3, color: "#00b894" },
  { label: "最近探测", value: "00:38", icon: Clock, color: "#e17055" },
];

// Count total new notifications
export function getNewNotificationCount(): number {
  return NOTIFICATIONS.reduce(
    (acc, group) => acc + group.items.filter((item) => item.isNew).length,
    0
  );
}
