import { createBrowserRouter } from "react-router";
import { Layout } from "./components/layout";
import { NotificationsPage } from "./components/notifications-page";
import { SettingsPage } from "./components/settings-page";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: NotificationsPage },
      { path: "settings", Component: SettingsPage },
    ],
  },
], { basename: '/terminal' });
