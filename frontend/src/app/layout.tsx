import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import NavBar from "@/components/NavBar";

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
        <AuthProvider>
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
            <div className="absolute inset-0 bg-slate-900/65" />
          </div>

          <div className="relative z-10 min-h-screen">
            <NavBar />
            <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
              {children}
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
