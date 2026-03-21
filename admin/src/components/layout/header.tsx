"use client";

import { Menu } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { getStoredLocale } from "@/i18n/config";
import { useProfileStore } from "@/stores/profile-store";
import { Logo } from "@/components/shared/logo";

import { Badge } from "../ui/badge";
import { Sheet, SheetContent, SheetTrigger } from "../ui/sheet";
import { Sidebar } from "./sidebar";

function Clock() {
  const [time, setTime] = useState("");

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const local = now.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      const offset = -now.getTimezoneOffset() / 60;
      const sign = offset >= 0 ? "+" : "";
      setTime(`${local} (UTC${sign}${offset})`);
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return <span className="text-xs text-[var(--text-tertiary)] hidden sm:inline">{time}</span>;
}

function LanguageSelector() {
  const t = useTranslations();
  const [locale] = useState(getStoredLocale);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLocale = e.target.value;
    localStorage.setItem("regulahub-locale", newLocale);
    window.location.reload();
  };

  return (
    <select
      value={locale}
      onChange={handleChange}
      className="rounded-[var(--radius-input)] border-none bg-[rgba(120,120,128,0.08)] px-2 py-1 text-xs font-medium text-[var(--text-secondary)] outline-none focus:ring-2 focus:ring-[var(--accent-indigo-ring)]"
      aria-label={t("common.language")}
    >
      <option value="pt-BR">PT-BR</option>
      <option value="en-US">EN-US</option>
      <option value="es-AR">ES-AR</option>
    </select>
  );
}

export function Header() {
  const system = useProfileStore((s) => s.system);
  const state = useProfileStore((s) => s.state);
  const profile = useProfileStore((s) => s.profile);

  const label = [system, state, profile].filter(Boolean).join(" \u00B7 ");

  return (
    <header className="mx-3 mt-3 flex h-11 items-center glass-floating rounded-2xl px-4 gap-4">
      <Sheet>
        <SheetTrigger className="lg:hidden" aria-label="Menu" render={<button />}>
          <Menu className="h-5 w-5 text-[var(--text-secondary)]" />
        </SheetTrigger>
        <SheetContent side="left" className="w-[75vw] max-w-60 p-0">
          <Sidebar />
        </SheetContent>
      </Sheet>
      <div className="flex items-center gap-2 lg:hidden">
        <Logo size="sm" showText={true} />
      </div>
      <div className="flex-1" />
      <Clock />
      <LanguageSelector />
      <Badge variant="default">
        {label}
      </Badge>
    </header>
  );
}
