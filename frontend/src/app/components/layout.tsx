import { Outlet, NavLink, useLocation } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { Radar, Bell, Settings, Zap } from "lucide-react";
import { getNewNotificationCount } from "../data/mock-data";

export function Layout() {
  const location = useLocation();
  const isNotifications = location.pathname === "/" || location.pathname === "/notifications";
  const pageTitle = isNotifications ? "实时通知 / 观测" : "院校设置 / 管理";
  const newCount = getNewNotificationCount();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="w-[220px] shrink-0 border-r border-border bg-card flex flex-col">
        {/* Logo */}
        <div className="px-5 py-6 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#6c5ce7] to-[#a29bfe] flex items-center justify-center shadow-md shadow-[#6c5ce7]/20">
            <Radar className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="text-[15px] tracking-tight" style={{ fontWeight: 600 }}>
              院校雷达
            </div>
            <div className="text-[10px] text-muted-foreground tracking-widest uppercase">
              Intelligence Terminal
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 mt-2 space-y-1">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                isActive
                  ? "bg-gradient-to-r from-[#6c5ce7] to-[#a29bfe] text-white shadow-md shadow-[#6c5ce7]/20"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Bell className="w-[18px] h-[18px]" />
                <span className="text-[14px] flex-1">实时通知</span>
                {/* #11: Notification badge */}
                {newCount > 0 && (
                  <span
                    className={`min-w-[18px] h-[18px] rounded-full flex items-center justify-center text-[10px] px-1 ${
                      isActive
                        ? "bg-white/25 text-white"
                        : "bg-[#ff4757] text-white"
                    }`}
                    style={{ fontWeight: 700 }}
                  >
                    {newCount}
                  </span>
                )}
              </>
            )}
          </NavLink>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                isActive
                  ? "bg-gradient-to-r from-[#6c5ce7] to-[#a29bfe] text-white shadow-md shadow-[#6c5ce7]/20"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`
            }
          >
            <Settings className="w-[18px] h-[18px]" />
            <span className="text-[14px]">院校设置</span>
          </NavLink>
        </nav>

        {/* Status */}
        <div className="px-5 py-4 border-t border-border">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-[12px] text-muted-foreground">系统运行中...</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-[60px] shrink-0 border-b border-border bg-card/80 backdrop-blur-sm flex items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <span className="text-[14px] text-muted-foreground">{pageTitle}</span>
          </div>
        </header>

        {/* #15: Page content with transition */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="h-[40px] shrink-0 border-t border-border bg-card/50 flex items-center justify-between px-6">
          <span className="text-[11px] text-muted-foreground">下次预定巡查: 00:38:28</span>
          <span className="text-[11px] text-muted-foreground flex items-center gap-1.5">
            <Zap className="w-3 h-3 text-[#6c5ce7]" />
            院校雷达终端内核 v4.0.0
          </span>
        </footer>
      </div>
    </div>
  );
}