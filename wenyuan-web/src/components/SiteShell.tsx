import { BookOpenText, LogOut, MessageSquareText, ScrollText } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { QuoteTicker } from "./QuoteTicker";

export function SiteShell() {
  const { isAuthed, username, logout } = useAuth();

  return (
    <div className="appShell">
      <header className="topbar">
        <Link className="brand" to="/">
          <ScrollText size={26} aria-hidden="true" />
          <span>文渊问史</span>
        </Link>
        <nav className="nav">
          <NavLink to="/">
            <BookOpenText size={18} aria-hidden="true" />
            介绍
          </NavLink>
          {isAuthed && (
            <NavLink to="/chat">
              <MessageSquareText size={18} aria-hidden="true" />
              问答
            </NavLink>
          )}
        </nav>
        <div className="userArea">
          {isAuthed ? (
            <>
              <span className="username">{username}</span>
              <button className="iconButton" type="button" onClick={logout} title="退出登录">
                <LogOut size={18} aria-hidden="true" />
              </button>
            </>
          ) : (
            <>
              <Link className="textLink" to="/login">
                登录
              </Link>
              <Link className="primarySmall" to="/register">
                注册
              </Link>
            </>
          )}
        </div>
      </header>
      <main className="mainSurface">
        <Outlet />
      </main>
      <QuoteTicker />
    </div>
  );
}
