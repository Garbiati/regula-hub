"use client";

import { AlertTriangle } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { ERROR_CODES } from "@/lib/error-codes";

interface ErrorBoundaryTranslations {
  title: string;
  guidance: string;
  retry: string;
}

interface Props {
  children: ReactNode;
  translations: ErrorBoundaryTranslations;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      const { translations } = this.props;
      return (
        <div className="mx-auto mt-12 max-w-md glass-card p-8">
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--status-danger)]/10">
              <AlertTriangle className="h-7 w-7 text-[var(--status-danger)]" />
            </div>
            <p className="mb-1 text-xs font-mono text-[var(--text-tertiary)]">
              {ERROR_CODES.GEN_UNEXPECTED}
            </p>
            <h3 className="mb-2 text-lg font-semibold text-[var(--text-primary)]">
              {translations.title}
            </h3>
            <p className="mb-2 text-sm text-[var(--text-secondary)]">
              {this.state.error?.message}
            </p>
            <p className="mb-6 text-xs text-[var(--text-tertiary)]">
              {translations.guidance}
            </p>
            <Button onClick={() => this.setState({ hasError: false, error: undefined })}>
              {translations.retry}
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
