"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { ErrorBoundary } from "./error-boundary";

export function TranslatedErrorBoundary({ children }: { children: ReactNode }) {
  const t = useTranslations();

  return (
    <ErrorBoundary
      translations={{
        title: t("common.error_title"),
        guidance: t("common.error_guidance"),
        retry: t("common.try_again"),
      }}
    >
      {children}
    </ErrorBoundary>
  );
}
