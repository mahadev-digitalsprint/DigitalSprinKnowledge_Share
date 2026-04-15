import { FileText, FileCode, File, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { UploadFile, UploadStatus } from "@/lib/types";

type UploadFileRowProps = {
  file: UploadFile;
  onRemove: (id: string) => void;
};

function getFileIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (["py", "ts", "js", "json"].includes(ext))
    return <FileCode size={14} style={{ color: "var(--brand)" }} />;
  if (["pdf", "docx", "doc"].includes(ext))
    return <FileText size={14} style={{ color: "var(--brand)" }} />;
  return <File size={14} style={{ color: "var(--text-faint)" }} />;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024)      return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

const STATUS_LABEL: Record<UploadStatus, string> = {
  queued:    "Queued",
  uploading: "Uploading…",
  parsing:   "Parsing…",
  done:      "Ready",
  error:     "Failed",
};

export function UploadFileRow({ file, onRemove }: UploadFileRowProps) {
  const isDone   = file.status === "done";
  const isError  = file.status === "error";
  const isActive = file.status === "uploading" || file.status === "parsing";

  return (
    <div
      className="flex items-start gap-3 py-3"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div className="shrink-0 mt-0.5">{getFileIcon(file.file.name)}</div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p
            className="text-ds-sm font-medium truncate"
            style={{ color: "var(--text)" }}
          >
            {file.file.name}
          </p>
          <div className="flex items-center gap-1.5 shrink-0">
            {isDone  && <CheckCircle size={12} style={{ color: "var(--success)" }} />}
            {isError && <AlertCircle size={12} style={{ color: "var(--error)" }} />}
            {isActive && <Loader2 size={12} className="animate-spin" style={{ color: "var(--brand)" }} />}
            <span
              className="text-ds-xs font-medium"
              style={{
                color: isDone  ? "var(--success)"    :
                       isError ? "var(--error)"      :
                       isActive ? "var(--text-muted)" :
                       "var(--text-faint)",
              }}
            >
              {STATUS_LABEL[file.status]}
            </span>
          </div>
        </div>

        <p className="text-ds-xs mt-0.5" style={{ color: "var(--text-faint)" }}>
          {formatBytes(file.file.size)}
          {file.errorMsg && (
            <span className="ml-2" style={{ color: "var(--error)" }}>{file.errorMsg}</span>
          )}
        </p>

        {/* Progress bar */}
        {!isDone && !isError && (
          <div
            className="mt-2 h-0.5 rounded-full overflow-hidden"
            style={{ background: "var(--border-bright)" }}
          >
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${file.progress}%`,
                background: isActive
                  ? "linear-gradient(90deg, #7c3aed, #a78bfa)"
                  : "var(--border-bright)",
                boxShadow: isActive ? "0 0 6px rgba(167,139,250,0.5)" : undefined,
              }}
            />
          </div>
        )}
      </div>

      {!isActive && (
        <button
          aria-label={`Remove ${file.file.name}`}
          onClick={() => onRemove(file.id)}
          className="h-6 w-6 flex items-center justify-center rounded-ds-sm shrink-0 mt-0.5 transition-colors duration-150 focus:outline-none"
          style={{ color: "var(--text-faint)" }}
          onMouseEnter={e => (e.currentTarget.style.color = "var(--error)")}
          onMouseLeave={e => (e.currentTarget.style.color = "var(--text-faint)")}
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}
