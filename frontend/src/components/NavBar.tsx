"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useState } from "react";

export default function NavBar() {
  const { user, loading, signInWithGoogle, signOut, isConfigured } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="nav-glass sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-6">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5 flex-shrink-0">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "var(--gradient-ocean)" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6.5 12C6.5 12 8 9 12 9C16 9 17.5 12 17.5 12" />
              <path d="M12 9V3" />
              <path d="M12 9C12 9 10 13 7 16" />
              <path d="M12 9C12 9 14 13 17 16" />
            </svg>
          </div>
          <span className="text-lg font-bold text-white tracking-tight">
            FishCast
          </span>
        </a>

        {/* Nav Tabs */}
        <nav className="flex items-center gap-1">
          <a href="/" className="nav-tab nav-tab-active">Karar</a>
          <a href="/#harita" className="nav-tab nav-tab-inactive">Harita</a>
          {user && (
            <a href="/catches" className="nav-tab nav-tab-inactive">Raporlarım</a>
          )}
        </nav>

        {/* Right: auth */}
        <div className="ml-auto flex items-center gap-3 relative">
          {loading ? (
            <div className="w-8 h-8 rounded-full bg-[var(--glass-bg-elevated)] animate-pulse" />
          ) : user ? (
            <>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="w-8 h-8 rounded-full flex items-center justify-center overflow-hidden"
                style={{
                  background: "var(--glass-bg-elevated)",
                  border: "1px solid var(--glass-border)",
                }}
              >
                {user.photoURL ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={user.photoURL} alt="" className="w-full h-full object-cover" />
                ) : (
                  <span className="text-xs font-bold text-white">
                    {(user.displayName || user.email || "U")[0].toUpperCase()}
                  </span>
                )}
              </button>
              {menuOpen && (
                <div
                  className="absolute right-0 top-12 w-48 rounded-[var(--radius-md)] p-2 space-y-1"
                  style={{
                    background: "var(--glass-bg-strong)",
                    border: "1px solid var(--glass-border)",
                    backdropFilter: "blur(20px)",
                  }}
                >
                  <div className="px-3 py-2 text-xs text-[var(--text-muted)] truncate">
                    {user.email}
                  </div>
                  <a
                    href="/catches"
                    className="block px-3 py-2 text-sm text-[var(--text-secondary)] hover:text-white rounded-[var(--radius-sm)] hover:bg-white/5 transition-colors"
                  >
                    Raporlarım
                  </a>
                  <button
                    onClick={() => { signOut(); setMenuOpen(false); }}
                    className="w-full text-left px-3 py-2 text-sm text-[var(--red-light)] hover:bg-white/5 rounded-[var(--radius-sm)] transition-colors"
                  >
                    Cikis Yap
                  </button>
                </div>
              )}
            </>
          ) : (
            <button
              onClick={isConfigured ? signInWithGoogle : undefined}
              disabled={!isConfigured}
              className="flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius-md)] text-sm font-medium transition-all"
              style={{
                background: isConfigured ? "var(--gradient-ocean)" : "var(--glass-bg-elevated)",
                color: isConfigured ? "white" : "var(--text-dim)",
                border: isConfigured ? "none" : "1px solid var(--glass-border)",
              }}
              title={isConfigured ? "Google ile giris yap" : "Firebase yapilandirilmamis"}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
              Giris Yap
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
