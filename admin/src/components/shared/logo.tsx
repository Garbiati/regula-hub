"use client";

import { cn } from "@/lib/utils";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  showText?: boolean;
  className?: string;
}

const SIZES = {
  sm: { icon: 24, text: "text-sm" },
  md: { icon: 32, text: "text-lg" },
  lg: { icon: 48, text: "text-2xl" },
} as const;

export function Logo({ size = "md", showText = true, className }: LogoProps) {
  const { icon, text } = SIZES[size];

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="logo-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#5856D6" />
            <stop offset="100%" stopColor="#7B61FF" />
          </linearGradient>
          <linearGradient id="logo-highlight" x1="50%" y1="0%" x2="50%" y2="60%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.5)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>
        {/* Rounded hexagon */}
        <path
          d="M24 4L40.5 13.5C42.5 14.7 43.5 16.8 43.5 19V29C43.5 31.2 42.5 33.3 40.5 34.5L24 44L7.5 34.5C5.5 33.3 4.5 31.2 4.5 29V19C4.5 16.8 5.5 14.7 7.5 13.5L24 4Z"
          fill="url(#logo-gradient)"
          rx="4"
        />
        {/* Glass highlight */}
        <path
          d="M24 4L40.5 13.5C42.5 14.7 43.5 16.8 43.5 19V24H4.5V19C4.5 16.8 5.5 14.7 7.5 13.5L24 4Z"
          fill="url(#logo-highlight)"
        />
        {/* Connection lines at 120 degrees */}
        <line x1="24" y1="24" x2="24" y2="12" stroke="white" strokeWidth="2.5" strokeLinecap="round" opacity="0.9" />
        <line x1="24" y1="24" x2="13.6" y2="30" stroke="white" strokeWidth="2.5" strokeLinecap="round" opacity="0.9" />
        <line x1="24" y1="24" x2="34.4" y2="30" stroke="white" strokeWidth="2.5" strokeLinecap="round" opacity="0.9" />
        {/* Central hub dot */}
        <circle cx="24" cy="24" r="3.5" fill="white" opacity="0.95" />
        {/* Endpoint dots */}
        <circle cx="24" cy="11" r="2" fill="white" opacity="0.8" />
        <circle cx="13" cy="30.5" r="2" fill="white" opacity="0.8" />
        <circle cx="35" cy="30.5" r="2" fill="white" opacity="0.8" />
      </svg>
      {showText && (
        <span className={cn("font-bold tracking-tight text-[var(--text-primary)]", text)}>
          RegulaHub
        </span>
      )}
    </div>
  );
}
