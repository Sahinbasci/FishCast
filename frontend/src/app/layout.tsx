import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FishCast — Istanbul Kıyı Balıkçılığı",
  description: "Istanbul Boğazı kıyı balıkçıları için veri temelli av karar destek sistemi",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className={`${inter.className} antialiased`}>
        {/* Fixed scenic background — Istanbul Bosphorus */}
        <div className="fixed inset-0 z-0">
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{
              backgroundImage:
                "url('https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=1920&q=80')",
              backgroundAttachment: "fixed",
              backgroundColor: "#060c1f",
            }}
          />
          {/* Dark overlay for readability */}
          <div className="absolute inset-0 bg-slate-900/65" />
        </div>

        {/* All content above background */}
        <div className="relative z-10 min-h-screen">
          {/* Nav Bar — glass */}
          <header className="nav-glass sticky top-0 z-40">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-6">
              {/* Logo */}
              <a href="/" className="flex items-center gap-2.5 flex-shrink-0">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: "var(--gradient-ocean)" }}
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
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

              {/* Left Nav Tabs */}
              <nav className="flex items-center gap-1">
                <a href="/" className="nav-tab nav-tab-active">
                  Karar
                </a>
                <a href="/#harita" className="nav-tab nav-tab-inactive">
                  Harita
                </a>
              </nav>

              {/* Right: nav + user icon */}
              <div className="ml-auto flex items-center gap-3">
                <a href="/" className="nav-tab nav-tab-inactive hidden sm:block">
                  Karar
                </a>
                <a href="/#harita" className="nav-tab nav-tab-inactive hidden sm:block">
                  Harita
                </a>
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center"
                  style={{
                    background: "var(--glass-bg-elevated)",
                    border: "1px solid var(--glass-border)",
                  }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--text-muted)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
              </div>
            </div>
          </header>
          <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
