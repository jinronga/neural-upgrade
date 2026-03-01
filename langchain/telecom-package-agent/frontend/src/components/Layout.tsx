import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Layout as AntLayout, Menu, Select, Spin } from "antd";
import { Link, useLocation } from "react-router-dom";
import { useUser } from "@/contexts/UserContext";
import { ApiUser, getUserInfo, getUsersPage } from "@/services/api";

const { Header, Content } = AntLayout;
const USER_PAGE_SIZE = 20;

const items = [
  { key: "/chat", label: <Link to="/chat">对话</Link> },
  { key: "/dashboard", label: <Link to="/dashboard">仪表盘</Link> },
  { key: "/users", label: <Link to="/users">手机号管理</Link> },
  { key: "/packages", label: <Link to="/packages">套餐列表</Link> },
  { key: "/benefits", label: <Link to="/benefits">权益中心</Link> },
];

interface Props {
  children: React.ReactNode;
}

const mergeUsers = (current: ApiUser[], incoming: ApiUser[]) => {
  const merged = [...current];
  const indexMap = new Map<number, number>();
  merged.forEach((item, idx) => indexMap.set(item.id, idx));

  for (const item of incoming) {
    const existingIndex = indexMap.get(item.id);
    if (existingIndex === undefined) {
      indexMap.set(item.id, merged.length);
      merged.push(item);
      continue;
    }
    merged[existingIndex] = item;
  }

  return merged;
};

const Layout: React.FC<Props> = ({ children }) => {
  const location = useLocation();
  const { userId, setUserId } = useUser();
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState("");
  const [loadingUsers, setLoadingUsers] = useState(false);
  const loadingUsersRef = useRef(false);

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith("/dashboard")) return "/dashboard";
    if (location.pathname.startsWith("/users")) return "/users";
    if (location.pathname.startsWith("/packages")) return "/packages";
    if (location.pathname.startsWith("/benefits")) return "/benefits";
    return "/chat";
  }, [location.pathname]);

  const hasMoreUsers = users.length < total;

  const loadUsers = useCallback(
    async (nextPage: number, nextKeyword: string, reset: boolean) => {
      if (loadingUsersRef.current) return;
      loadingUsersRef.current = true;
      setLoadingUsers(true);
      try {
        const result = await getUsersPage({
          page: nextPage,
          page_size: USER_PAGE_SIZE,
          keyword: nextKeyword || undefined,
        });
        setTotal(result.total);
        setPage(result.page);
        setUsers((prev) => (reset ? result.items : mergeUsers(prev, result.items)));
      } finally {
        loadingUsersRef.current = false;
        setLoadingUsers(false);
      }
    },
    []
  );

  useEffect(() => {
    void loadUsers(1, "", true);
  }, [loadUsers]);

  useEffect(() => {
    const handleUsersUpdated = () => {
      void loadUsers(1, keyword, true);
    };
    window.addEventListener("telecom-users-updated", handleUsersUpdated);
    return () => {
      window.removeEventListener("telecom-users-updated", handleUsersUpdated);
    };
  }, [keyword, loadUsers]);

  useEffect(() => {
    if (!userId || users.some((item) => String(item.id) === userId)) return;

    void getUserInfo(userId)
      .then((user) => {
        setUsers((prev) => mergeUsers(prev, [user]));
      })
      .catch(() => undefined);
  }, [userId, users]);

  const userOptions = useMemo(
    () =>
      users.map((item) => ({
        value: item.id,
        label: `${item.phone_number}${
          item.name ? ` · ${item.name}` : ""
        } (ID:${item.id})`,
      })),
    [users]
  );

  return (
    <AntLayout className="min-h-screen bg-slate-100">
      <Header className="sticky top-0 z-20 flex h-auto items-center gap-4 border-b border-white/10 bg-slate-900/90 px-6 py-3 backdrop-blur">
        <div className="mr-2">
          <div className="text-[11px] uppercase tracking-[0.2em] text-cyan-300/90">
            Telecom Ops
          </div>
          <div className="text-sm font-semibold text-white">
            流量套餐 AI 助手
          </div>
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={items}
          className="min-w-0 flex-1 bg-transparent"
        />
        <div className="flex items-center gap-2 rounded-full border border-cyan-200/30 bg-white/10 px-2 py-1">
          <span className="text-xs text-cyan-100">用户</span>
          <Select
            value={Number(userId)}
            options={userOptions}
            onChange={(nextUserId) => setUserId(String(nextUserId))}
            showSearch
            filterOption={false}
            placeholder="选择手机号"
            onSearch={(nextKeyword) => {
              const normalized = nextKeyword.trim();
              setKeyword(normalized);
              void loadUsers(1, normalized, true);
            }}
            onPopupScroll={(e) => {
              const target = e.target as HTMLDivElement;
              const nearBottom =
                target.scrollHeight - target.scrollTop - target.clientHeight < 24;
              if (nearBottom && hasMoreUsers && !loadingUsers) {
                void loadUsers(page + 1, keyword, false);
              }
            }}
            notFoundContent={loadingUsers ? <Spin size="small" /> : "暂无用户"}
            className="w-56"
            size="small"
            dropdownStyle={{ maxHeight: 280, overflow: "auto" }}
          />
        </div>
      </Header>
      <Content className="mx-auto w-full max-w-7xl p-4 md:p-6">{children}</Content>
    </AntLayout>
  );
};

export default Layout;
