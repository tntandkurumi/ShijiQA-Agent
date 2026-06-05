import { createContext, useContext, useMemo, useState } from "react";
import { api } from "./api";

type AuthContextValue = {
  token: string | null;
  username: string | null;
  isAuthed: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const TOKEN_KEY = "wenyuan_token";
const USER_KEY = "wenyuan_username";

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem(USER_KEY));

  async function persistAuth(action: "login" | "register", name: string, password: string) {
    const result = action === "login" ? await api.login(name, password) : await api.register(name, password);
    localStorage.setItem(TOKEN_KEY, result.access_token);
    localStorage.setItem(USER_KEY, result.username);
    setToken(result.access_token);
    setUsername(result.username);
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      username,
      isAuthed: Boolean(token),
      login: (name, password) => persistAuth("login", name, password),
      register: (name, password) => persistAuth("register", name, password),
      logout: () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setToken(null);
        setUsername(null);
      },
    }),
    [token, username],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
