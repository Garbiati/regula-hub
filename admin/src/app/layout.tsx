import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { SelectionSyncProvider } from "@/components/shared/selection-sync-provider";
import { TranslatedErrorBoundary } from "@/components/shared/translated-error-boundary";
import { I18nProvider } from "@/providers/i18n-provider";
import { QueryProvider } from "@/providers/query-provider";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "RegulaHub Admin",
  description: "Admin panel for RegulaHub integration platform",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const messages = (await import("../../public/locales/pt-BR.json")).default;

  return (
    <html lang="pt-BR">
      <body className={`${inter.variable} font-sans antialiased`}>
        <I18nProvider initialMessages={messages}>
          <QueryProvider>
            <TooltipProvider>
              <SelectionSyncProvider>
                <div className="flex h-screen">
                  <Sidebar />
                  <div className="flex flex-1 flex-col overflow-hidden">
                    <Header />
                    <main className="flex-1 overflow-y-auto px-4 py-4 lg:px-6 lg:py-5">
                      <TranslatedErrorBoundary>{children}</TranslatedErrorBoundary>
                    </main>
                  </div>
                </div>
              </SelectionSyncProvider>
            </TooltipProvider>
          </QueryProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
