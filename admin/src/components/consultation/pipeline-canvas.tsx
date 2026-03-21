"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Minus, Plus, Maximize2 } from "lucide-react";

import { cn } from "@/lib/utils";

interface PipelineCanvasProps {
  contentWidth: number;
  contentHeight: number;
  children: ReactNode;
}

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 2;
const FIT_MAX_ZOOM = 1.0;
const ZOOM_STEP = 0.2;
const FIT_PADDING = 24;

export function PipelineCanvas({ contentWidth, contentHeight, children }: PipelineCanvasProps) {
  const t = useTranslations();
  const containerRef = useRef<HTMLDivElement>(null);

  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const pinchStart = useRef({ dist: 0, zoom: 1 });

  // ── Fit-to-view ──
  const fitToView = useCallback(() => {
    const el = containerRef.current;
    if (!el || el.clientWidth === 0) return;
    const { clientWidth, clientHeight } = el;
    const scaleX = (clientWidth - FIT_PADDING * 2) / contentWidth;
    const scaleY = (clientHeight - FIT_PADDING * 2) / contentHeight;
    const effectiveScale = Math.min(scaleX, scaleY);
    const newZoom = Math.min(Math.max(effectiveScale, MIN_ZOOM), FIT_MAX_ZOOM);
    const newPanX = (clientWidth - contentWidth * newZoom) / 2;
    const newPanY = (clientHeight - contentHeight * newZoom) / 2;
    setZoom(newZoom);
    setPanX(newPanX);
    setPanY(newPanY);
  }, [contentWidth, contentHeight]);

  // Auto-fit on mount, content change, AND container resize (e.g. after modal animation)
  useEffect(() => {
    fitToView();

    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      fitToView();
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [fitToView]);

  // ── Pointer (mouse) pan ──
  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      // Only pan with primary button, ignore clicks on interactive elements
      if (e.button !== 0) return;
      const target = e.target as HTMLElement;
      if (target.closest("button")) return;

      setIsDragging(true);
      dragStart.current = { x: e.clientX, y: e.clientY, panX, panY };
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    },
    [panX, panY],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      setPanX(dragStart.current.panX + dx);
      setPanY(dragStart.current.panY + dy);
    },
    [isDragging],
  );

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // ── Wheel zoom (zoom toward cursor) ──
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const cursorX = e.clientX - rect.left;
      const cursorY = e.clientY - rect.top;
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      const newZoom = Math.min(Math.max(zoom + delta, MIN_ZOOM), MAX_ZOOM);
      const ratio = newZoom / zoom;

      setPanX(cursorX - (cursorX - panX) * ratio);
      setPanY(cursorY - (cursorY - panY) * ratio);
      setZoom(newZoom);
    },
    [zoom, panX, panY],
  );

  // ── Touch: 2-finger pinch ──
  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 2) {
        const t0 = e.touches[0];
        const t1 = e.touches[1];
        if (!t0 || !t1) return;
        const dx = t0.clientX - t1.clientX;
        const dy = t0.clientY - t1.clientY;
        pinchStart.current = { dist: Math.hypot(dx, dy), zoom };
      }
    },
    [zoom],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        const t0 = e.touches[0];
        const t1 = e.touches[1];
        if (!t0 || !t1) return;
        const dx = t0.clientX - t1.clientX;
        const dy = t0.clientY - t1.clientY;
        const dist = Math.hypot(dx, dy);
        const scale = dist / pinchStart.current.dist;
        const newZoom = Math.min(Math.max(pinchStart.current.zoom * scale, MIN_ZOOM), MAX_ZOOM);
        setZoom(newZoom);
      }
    },
    [],
  );

  // ── Zoom buttons ──
  const zoomIn = useCallback(() => {
    setZoom((z) => Math.min(z + ZOOM_STEP, MAX_ZOOM));
  }, []);

  const zoomOut = useCallback(() => {
    setZoom((z) => Math.max(z - ZOOM_STEP, MIN_ZOOM));
  }, []);

  return (
    <div className="relative flex-1 min-h-0 overflow-hidden" data-testid="pipeline-canvas">
      {/* Pannable / zoomable surface */}
      <div
        ref={containerRef}
        className={cn("w-full h-full", isDragging ? "cursor-grabbing" : "cursor-grab")}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onWheel={handleWheel}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        style={{ touchAction: "none" }}
      >
        <div
          style={{
            transform: `translate(${panX}px, ${panY}px) scale(${zoom})`,
            transformOrigin: "0 0",
            willChange: "transform",
            width: contentWidth,
            height: contentHeight,
            position: "relative",
          }}
        >
          {children}
        </div>
      </div>

      {/* Zoom controls — bottom-right corner */}
      <div className="absolute bottom-2 right-2 flex items-center gap-1 p-1 rounded-xl bg-[var(--glass-surface-strong)] border border-[var(--glass-border)] shadow-[var(--glass-shadow)]">
        <button
          type="button"
          onClick={zoomOut}
          className="p-1.5 rounded-lg hover:bg-[var(--glass-surface-hover)] transition-colors"
          aria-label={t("pipeline.zoom_out")}
          data-testid="pipeline-zoom-out"
        >
          <Minus className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
        </button>
        <span className="text-[10px] font-medium text-[var(--text-tertiary)] min-w-[36px] text-center tabular-nums">
          {Math.round(zoom * 100)}%
        </span>
        <button
          type="button"
          onClick={zoomIn}
          className="p-1.5 rounded-lg hover:bg-[var(--glass-surface-hover)] transition-colors"
          aria-label={t("pipeline.zoom_in")}
          data-testid="pipeline-zoom-in"
        >
          <Plus className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
        </button>
        <div className="w-px h-4 bg-[var(--glass-border)]" />
        <button
          type="button"
          onClick={fitToView}
          className="p-1.5 rounded-lg hover:bg-[var(--glass-surface-hover)] transition-colors"
          aria-label={t("pipeline.zoom_reset")}
          data-testid="pipeline-zoom-reset"
        >
          <Maximize2 className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
        </button>
      </div>
    </div>
  );
}
