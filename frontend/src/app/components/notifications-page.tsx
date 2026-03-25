import { useState, useMemo, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import {
  School,
  ChevronRight,
  FileX,
  BarChart3,
  ExternalLink,
  Zap,
  Radio,
} from "lucide-react";
import {
  UNIVERSITIES,
  CATEGORIES,
  NOTIFICATIONS,
  STATS,
  type NotificationGroup
} from "../data/mock-data";

function getNowTime(): string {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
}

export function NotificationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // #7: URL-synced filter state
  const selectedUni = searchParams.get("uni") || "全部院校";
  const selectedCat = searchParams.get("cat") || "all";

  const setSelectedUni = useCallback(
    (uni: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (uni === "全部院校") next.delete("uni");
        else next.set("uni", uni);
        return next;
      });
    },
    [setSearchParams]
  );

  const setSelectedCat = useCallback(
    (cat: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (cat === "all") next.delete("cat");
        else next.set("cat", cat);
        return next;
      });
    },
    [setSearchParams]
  );

  const [notificationsData, setNotificationsData] = useState<NotificationGroup[]>(NOTIFICATIONS);
  const [dynamicUniversities, setDynamicUniversities] = useState<string[]>(UNIVERSITIES);
  const [dynamicStats, setDynamicStats] = useState(STATS);
  // 各院校的官网模块信息
  const [uniModules, setUniModules] = useState<Record<string, {name:string, url:string}[]>>({});
  const [scanning, setScanning] = useState(false);

  // Fetch real events
  useEffect(() => {
    fetch('/api/events')
      .then(res => res.json())
      .then(events => {
        const groupsMap: Record<string, NotificationGroup> = {
          graduate: { category: "graduate", categoryLabel: "研究生院", categoryColor: "#0984e3", categoryIcon: CATEGORIES.find(c=>c.key==='graduate')?.icon || School, items: [] },
          department: { category: "department", categoryLabel: "学院/学部通知", categoryColor: "#6c5ce7", categoryIcon: CATEGORIES.find(c=>c.key==='department')?.icon || School, items: [] },
        };
        
        const getModType = (m: string) => {
          if (!m) return 'graduate';
          const mod = m.toLowerCase();
          if (mod.includes('学院') || mod.includes('学部') || mod.includes('分院') || mod.includes('系') || mod.includes('研究中心')) return 'department';
          return 'graduate';
        };

        const now = Date.now();
        const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
        const unis = new Set<string>();
        let todayCount = 0;

        // 💡 改进排序：确保最新数据（ID较大或日期较新）排在前列
        // 无日期的通知视为最新，排在最前面
        const sortedEvents = [...events].sort((a, b) => {
          const dateA = a.publish_date || '9999-99-99';
          const dateB = b.publish_date || '9999-99-99';
          if (dateA !== dateB) return dateB.localeCompare(dateA);
          return (b.id || 0) - (a.id || 0);
        });

        sortedEvents.forEach((e: any) => {
          const publishDateStr = e.publish_date || null;
          let isNewItem = false;
          
          if (publishDateStr) {
            const dTime = new Date(publishDateStr).getTime();
            const now = Date.now();
            if (!isNaN(dTime) && (now - dTime) > thirtyDaysMs) return;
            isNewItem = (now - dTime) < (24 * 60 * 60 * 1000);
          }

          if (isNewItem) todayCount++;
          const catKey = getModType(e.module);
          unis.add(e.university);

          // 日期显示：优先 publish_date，其次从 created_at 提取日期
          let displayDate = e.publish_date || '';
          if (!displayDate && e.created_at) {
            displayDate = e.created_at.substring(0, 10);
          }
          if (!displayDate) displayDate = '最近更新';

          groupsMap[catKey].items.push({
            id: e.id || Math.random().toString(),
            university: e.university,
            department: e.module || '通用',
            date: displayDate,
            title: e.title,
            desc: e.ai_summary || e.abstract || '原文暂无结构化摘要。',
            isNew: isNewItem,
            link: e.link || ''
          });
        });

        // 确保每个分组内部也按最新排序（双重保障）
        Object.values(groupsMap).forEach(group => {
          group.items.sort((a, b) => {
            const dA = a.date === '最近更新' ? '9999-99-99' : a.date;
            const dB = b.date === '最近更新' ? '9999-99-99' : b.date;
            if (dA !== dB) return dB.localeCompare(dA);
            return (Number(b.id) || 0) - (Number(a.id) || 0);
          });
        });

        setNotificationsData(Object.values(groupsMap));
        
        // 我们不覆盖下拉列表，只在 config 里更新下拉列表，这里只把有数据的院校合并进去
        setDynamicUniversities(prev => {
          const set = new Set(prev);
          unis.forEach(u => set.add(u));
          return Array.from(set);
        });
        
        setDynamicStats(prev => [
          { ...prev[0], value: unis.size.toString() },
          { ...prev[1], value: events.length.toString(), label: "近期情报" },
          { ...prev[2], value: todayCount.toString(), label: "今日新增", icon: BarChart3 },
          { ...prev[3], value: getNowTime() }
        ]);
      });
  }, []);

  // 拉取各院校的官网模块链接并获取配置的初始关注院校
  const fetchConfig = useCallback(() => {
    fetch('/api/config/modules')
      .then(r => r.json())
      .then(data => setUniModules(data))
      .catch(() => {});

    fetch('/api/config')
      .then(r => r.json())
      .then(data => {
        if (data.selected_universities) {
          setDynamicUniversities(_prev => {
            const set = new Set<string>();
            set.add("全部院校");
            data.selected_universities.forEach((u: string) => set.add(u));
            return Array.from(set);
          });
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchConfig();
    // 当用户从其他页面切回来时也重新拉取配置
    const onVisible = () => { if (document.visibilityState === 'visible') fetchConfig(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [fetchConfig]);

  // #1 + category filter: apply both university AND category
  const filteredNotifications = useMemo(() => {
    let groups =
      selectedCat === "all"
        ? notificationsData
        : notificationsData.filter((g) => g.category === selectedCat);

    // 不管 selectedUni 是不是全部院校，我们都保留所有的 group
    // 当选定具体院校时，只展示该院校的 items
    if (selectedUni !== "全部院校") {
      groups = groups.map((g) => ({
        ...g,
        items: g.items.filter((item) => item.university === selectedUni),
      }));
    }

    return groups;
  }, [selectedCat, selectedUni, notificationsData]);

  // #9: 仅当下拉框里只有"全部院校"（即完全没配置任何监控目标）时，才显示全局空状态
  const totalItems = filteredNotifications.reduce((acc, g) => acc + g.items.length, 0);
  const noConfiguredUnis = dynamicUniversities.length <= 1;

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6">
      {/* 顶部操作栏 */}
      <div className="flex items-center justify-between">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 flex-1">
        {dynamicStats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.08 }}
            className="bg-card rounded-2xl p-5 border border-border hover:shadow-md hover:shadow-[#6c5ce7]/5 transition-all duration-300 group"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[28px]" style={{ fontWeight: 700, color: stat.color }}>
                  {stat.value}
                </div>
                <div className="text-[12px] text-muted-foreground mt-1">{stat.label}</div>
              </div>
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center opacity-60 group-hover:opacity-100 transition-opacity"
                style={{ backgroundColor: `${stat.color}15` }}
              >
                <stat.icon className="w-5 h-5" style={{ color: stat.color }} />
              </div>
            </div>
          </motion.div>
        ))}
        </div>
        {/* 扫描按钮 */}
        <button
          onClick={async () => {
            setScanning(true);
            toast.info("正在提交扫描任务...");
            try {
              const res = await fetch('/api/scan/start', { method: 'POST' });
              const data = await res.json();
              toast.success(data.message || "扫描已启动");
            } catch { toast.error("启动失败"); }
            setTimeout(() => setScanning(false), 3000);
          }}
          disabled={scanning}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] text-white transition-all shrink-0 ml-4 ${
            scanning
              ? "bg-gradient-to-r from-emerald-500 to-emerald-600"
              : "bg-gradient-to-r from-[#6c5ce7] to-[#a29bfe] hover:shadow-lg hover:shadow-[#6c5ce7]/30 active:scale-[0.98]"
          }`}
        >
          {scanning ? (
            <><Radio className="w-4 h-4 animate-pulse" />扫描中...</>
          ) : (
            <><Zap className="w-4 h-4" />立即扫描</>
          )}
        </button>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 gap-6">
        {/* Intelligence center */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="bg-card rounded-2xl border border-border overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-border">
            <div className="flex items-center gap-2">
              <School className="w-5 h-5 text-[#6c5ce7]" />
              <span className="text-[16px]" style={{ fontWeight: 700 }}>
                考研情报观测指挥中心
              </span>
            </div>
          </div>

          {/* Filters */}
          <div className="px-6 py-5 space-y-4 border-b border-border bg-[#fafafd]">
            {/* University filter */}
            <div className="flex items-center gap-2 flex-wrap">
              {dynamicUniversities.map((uni) => (
                <button
                  key={uni}
                  onClick={() => setSelectedUni(uni)}
                  className={`px-5 py-2 rounded-lg text-[13px] transition-all duration-200 ${
                    selectedUni === uni
                      ? "bg-[#6c5ce7] text-white shadow-sm shadow-[#6c5ce7]/20"
                      : "bg-white border border-border text-muted-foreground hover:border-[#6c5ce7]/30 hover:text-[#6c5ce7]"
                  }`}
                >
                  {uni}
                </button>
              ))}
            </div>
            {/* Category filter */}
            <div className="flex items-center gap-2 flex-wrap">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.key}
                  onClick={() => setSelectedCat(cat.key)}
                  className={`px-5 py-2 rounded-lg text-[13px] transition-all duration-200 flex items-center gap-1.5 ${
                    selectedCat === cat.key
                      ? "bg-[#6c5ce7] text-white shadow-sm shadow-[#6c5ce7]/20"
                      : "bg-white border border-border text-muted-foreground hover:border-[#6c5ce7]/30 hover:text-[#6c5ce7]"
                  }`}
                >
                  {cat.icon && <cat.icon className="w-3.5 h-3.5" />}
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* #9: Global empty state (Only when no uni configured) */}
          {noConfiguredUnis ? (
            <div className="py-16 flex flex-col items-center justify-center text-center">
              <FileX className="w-10 h-10 text-muted-foreground/40 mb-3" />
              <p className="text-[14px] text-muted-foreground" style={{ fontWeight: 500 }}>
                暂无任何院校的情报数据
              </p>
              <p className="text-[12px] text-muted-foreground/60 mt-1">
                可能您还没有在设置页配置院校，或者系统正在进行首次爬取
              </p>
            </div>
          ) : (
            /* Notifications list */
            <AnimatePresence mode="wait">
              <motion.div
                key={`${selectedCat}-${selectedUni}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {filteredNotifications.map((group) => (
                  <div key={group.category} className="border-b border-border last:border-b-0">
                    <div className="px-6 py-3">
                      <div className="flex items-center gap-2 py-2">
                        <div
                          className="w-1 h-5 rounded-full"
                          style={{ backgroundColor: group.categoryColor }}
                        />
                        <group.categoryIcon
                          className="w-4 h-4"
                          style={{ color: group.categoryColor }}
                        />
                        <span
                          className="text-[13px]"
                          style={{ fontWeight: 600, color: group.categoryColor }}
                        >
                          {group.categoryLabel}
                        </span>
                        <span className="text-[11px] text-muted-foreground ml-1">
                          ({group.items.length})
                        </span>
                        {/* 官网链接 */}
                        {(() => {
                          const allModLinks: {name:string,url:string}[] = [];
                          Object.values(uniModules).forEach(mods => {
                            mods.forEach(m => {
                              if (group.category === 'graduate' && (m.name.includes('研究生') || m.name.includes('研招') || m.name.includes('yjsy') || m.name.includes('通知公告'))) {
                                if (!m.name.includes('研招网') && !m.url.includes('chsi')) {
                                  if (!allModLinks.find(x => x.url === m.url)) allModLinks.push(m);
                                }
                              }
                              if (group.category === 'department' && (m.name.includes('学部') || m.name.includes('学院') || m.name.includes('系'))) {
                                if (!allModLinks.find(x => x.url === m.url)) allModLinks.push(m);
                              }
                              if (group.category === 'yanzhao' && (m.name.includes('研招网') || m.url.includes('chsi'))) {
                                if (!allModLinks.find(x => x.url === m.url)) allModLinks.push(m);
                              }
                            });
                          });
                          return allModLinks.slice(0, 3).map(ml => (
                            <a
                              key={ml.url}
                              href={ml.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 ml-2 text-[11px] text-[#0984e3] hover:underline"
                            >
                              <ExternalLink className="w-3 h-3" />
                              {ml.name}
                            </a>
                          ));
                        })()}
                      </div>
                    </div>
                    {group.items.length === 0 ? (
                      <div className="py-8 text-center bg-[#fafafd] border-b border-border last:border-b-0">
                        <p className="text-[13px] text-muted-foreground" style={{ fontWeight: 500 }}>近 14 天内暂无最新通告</p>
                        <p className="text-[12px] text-muted-foreground/60 mt-1">系统正在全天候监控该渠道，如有更新将第一时间推送</p>
                      </div>
                    ) : (
                      group.items.map((item) => (
                        <div
                          key={item.id} /* #2: unique key */
                          className="mx-6 mb-4 p-4 rounded-xl border border-border bg-[#fafafd] hover:shadow-sm transition-all duration-200 cursor-pointer group/card"
                          style={{
                            borderLeftWidth: 3,
                            borderLeftColor: group.categoryColor, /* #10: category accent */
                          }}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span
                                className="text-[12px]"
                                style={{ fontWeight: 600, color: group.categoryColor }}
                              >
                                {item.university}
                              </span>
                              <span className="text-[11px] px-2 py-0.5 rounded bg-muted text-muted-foreground">
                                {item.department}
                              </span>
                              {item.isNew && (
                                <span
                                  className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#ff4757]/10 text-[#ff4757]"
                                  style={{ fontWeight: 600 }}
                                >
                                  NEW
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] text-muted-foreground">{item.date}</span>
                          </div>
                          <h4
                            className="text-[13px] group-hover/card:underline flex items-center gap-1"
                            style={{ color: group.categoryColor }}
                          >
                            {item.title}
                            <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover/card:opacity-100 transition-opacity" />
                          </h4>
                          {item.link && (
                            <a
                              href={item.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 mt-1.5 text-[11px] text-[#0984e3] hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="w-3 h-3" />
                              查看原文
                            </a>
                          )}
                          <div
                            className="mt-2 pl-3 border-l-2"
                            style={{ borderLeftColor: `${group.categoryColor}33` }}
                          >
                            <p className="text-[12px] text-muted-foreground leading-relaxed">
                              {item.desc}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                ))}
              </motion.div>
            </AnimatePresence>
          )}
        </motion.div>
      </div>
    </div>
  );
}
