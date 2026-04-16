"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  maxWidth?: "sm" | "md" | "lg";
  children: React.ReactNode;
};

const widths = { sm: "420px", md: "560px", lg: "720px" };

export function Modal({ open, onClose, title, description, maxWidth = "md", children }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    if (open) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "var(--overlay-bg)", backdropFilter: "blur(8px)" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="w-full animate-scale-in"
        style={{
          maxWidth: widths[maxWidth],
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-bright)",
          borderRadius: "20px",
          boxShadow: "var(--shadow-modal)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between px-6 py-5"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div>
            <h2
              id="modal-title"
              className="text-ds-h6 font-bold"
              style={{
                color: "var(--text)",
                fontFamily: "Syne, system-ui, sans-serif",
                letterSpacing: "-0.02em",
              }}
            >
              {title}
            </h2>
            {description && (
              <p className="text-ds-sm mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {description}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="h-7 w-7 flex items-center justify-center rounded-ds-md transition-all duration-150 focus:outline-none shrink-0 ml-4"
            style={{ color: "var(--text-faint)" }}
            onMouseEnter={e => {
              e.currentTarget.style.background = "var(--bg-glass)";
              e.currentTarget.style.color = "var(--text)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "";
              e.currentTarget.style.color = "var(--text-faint)";
            }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
