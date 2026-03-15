"use client";

import { NextIntlClientProvider } from "next-intl";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { defaultLocale, getStoredLocale, type Locale } from "@/i18n/config";
import { flatToNested } from "@/i18n/flat-to-nested";

export function I18nProvider({
  children,
  initialMessages,
}: {
  children: ReactNode;
  initialMessages: Record<string, string>;
}) {
  const [locale, setLocale] = useState<Locale>(() => getStoredLocale());
  const [messages, setMessages] = useState(() => flatToNested(initialMessages));

  useEffect(() => {
    const stored = getStoredLocale();
    if (stored !== locale) {
      setLocale(stored);
    }
  }, [locale]);

  useEffect(() => {
    if (locale === defaultLocale) return;
    import(`../../public/locales/${locale}.json`).then((mod) => {
      setMessages(flatToNested(mod.default));
    });
  }, [locale]);

  const handleError = useCallback((error: Error) => {
    if (process.env.NODE_ENV === "development") {
      console.warn("[i18n]", error.message);
    }
  }, []);

  return (
    <NextIntlClientProvider locale={locale} messages={messages} onError={handleError}>
      {children}
    </NextIntlClientProvider>
  );
}

export function setAppLocale(newLocale: Locale) {
  localStorage.setItem("regulahub-locale", newLocale);
  window.dispatchEvent(new StorageEvent("storage", { key: "regulahub-locale", newValue: newLocale }));
  window.location.reload();
}
