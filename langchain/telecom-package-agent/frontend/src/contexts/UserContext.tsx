import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getUserInfo } from "@/services/api";

const STORAGE_KEY = "telecom.active_user_id";

interface UserContextValue {
  userId: string;
  userPhone?: string;
  setUserId: (next: string) => void;
}

const UserContext = createContext<UserContextValue | null>(null);

const getInitialUserId = () => {
  const stored = localStorage.getItem(STORAGE_KEY)?.trim();
  if (stored && /^\d+$/.test(stored)) {
    return stored;
  }
  return "1";
};

export const UserProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [userId, setUserIdState] = useState<string>(getInitialUserId);
  const [userPhone, setUserPhone] = useState<string | undefined>(undefined);

  const setUserId = (next: string) => {
    const normalized = next.trim();
    if (!normalized || !/^\d+$/.test(normalized)) return;
    if (normalized === userId) return;
    setUserIdState(normalized);
    setUserPhone(undefined);
    localStorage.setItem(STORAGE_KEY, normalized);
  };

  useEffect(() => {
    let cancelled = false;
    void getUserInfo(userId)
      .then((user) => {
        if (cancelled) return;
        setUserPhone(user.phone_number || undefined);
      })
      .catch(() => {
        if (cancelled) return;
        setUserPhone(undefined);
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const value = useMemo(
    () => ({
      userId,
      userPhone,
      setUserId,
    }),
    [userId, userPhone]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
};

export const useUser = () => {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error("useUser must be used within UserProvider");
  }
  return ctx;
};
