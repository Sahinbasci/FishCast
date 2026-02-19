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
      <body className={`${inter.className} antialiased bg-gray-50 text-gray-900`}>
        <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2">
              <span className="text-2xl">&#x1F3A3;</span>
              <span className="text-xl font-bold text-blue-700">FishCast</span>
            </a>
            <nav className="text-sm text-gray-500 space-x-4">
              <a href="/" className="hover:text-blue-600 transition">Karar</a>
              <a href="/#harita" className="hover:text-blue-600 transition">Harita</a>
            </nav>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
