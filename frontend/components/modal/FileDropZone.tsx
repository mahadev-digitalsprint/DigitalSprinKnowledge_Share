"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, CloudUpload } from "lucide-react";
import { cn } from "@/lib/cn";

type FileDropZoneProps = {
  onFiles: (files: File[]) => void;
  accept?: string;
  disabled?: boolean;
};

export function FileDropZone({ onFiles, accept, disabled }: FileDropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(
    (files: FileList | null) => {
      if (!files || disabled) return;
      onFiles(Array.from(files));
    },
    [onFiles, disabled],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      processFiles(e.dataTransfer.files);
    },
    [processFiles],
  );

  return (
    <div
      onDragOver={e => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={cn(
        "relative flex flex-col items-center justify-center gap-3 py-10 px-6 rounded-ds-xl cursor-pointer",
        "transition-all duration-200",
        disabled && "pointer-events-none opacity-50",
      )}
      style={{
        background: dragging ? "var(--bg-glass-active)" : "var(--bg-glass)",
        border: `2px dashed ${dragging ? "var(--border-brand)" : "var(--border-bright)"}`,
        boxShadow: dragging ? "0 0 24px rgba(167,139,250,0.12)" : undefined,
      }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        className="sr-only"
        onChange={e => processFiles(e.target.files)}
      />

      <div
        className="h-12 w-12 rounded-ds-xl flex items-center justify-center transition-all duration-200"
        style={{
          background: dragging ? "rgba(167,139,250,0.15)" : "var(--bg-elevated)",
          border: "1px solid var(--border-bright)",
          boxShadow: dragging ? "0 0 16px rgba(167,139,250,0.25)" : undefined,
        }}
      >
        <CloudUpload
          size={22}
          style={{ color: dragging ? "var(--brand)" : "var(--text-faint)" }}
        />
      </div>

      <div className="text-center">
        <p className="text-ds-body font-semibold" style={{ color: dragging ? "var(--brand)" : "var(--text)" }}>
          {dragging ? "Drop files here" : "Drop files or click to browse"}
        </p>
        <p className="text-ds-sm mt-1" style={{ color: "var(--text-faint)" }}>
          PDF, DOCX, PPTX, TXT, Markdown, CSV, HTML
        </p>
      </div>
    </div>
  );
}
