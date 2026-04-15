"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Modal } from "@/components/common/Modal";
import { Button } from "@/components/common/Button";
import { FileDropZone } from "@/components/modal/FileDropZone";
import { UploadFileRow } from "@/components/modal/UploadFileRow";
import type { Collection, UploadFile, UploadStatus } from "@/lib/types";
import { uploadDocument, watchUploadEvents } from "@/lib/api-client";

type UploadModalProps = {
  open: boolean;
  onClose: () => void;
  collectionName: string;
  collections: Collection[];
};

let nextId = 0;
const uid = () => `f${++nextId}`;

const STAGE_TO_STATUS: Record<string, UploadStatus> = {
  parsing:    "parsing",
  chunking:   "parsing",
  embedding:  "parsing",
  indexing:   "parsing",
  searchable: "done",
  error:      "error",
};

const STAGE_TO_PROGRESS: Record<string, number> = {
  parsing:    20,
  chunking:   40,
  embedding:  60,
  indexing:   80,
  searchable: 100,
  error:      0,
};

export function UploadModal({ open, onClose, collectionName: _collectionName, collections }: UploadModalProps) {
  const [files, setFiles]           = useState<UploadFile[]>([]);
  const [targetColl, setTargetColl] = useState<string>(collections[1]?.id ?? collections[0]?.id ?? "");
  const cleanupRef = useRef<Array<() => void>>([]);

  useEffect(() => {
    if (!open) {
      cleanupRef.current.forEach((fn) => fn());
      cleanupRef.current = [];
      setFiles([]);
    }
  }, [open]);

  const handleFiles = useCallback((incoming: File[]) => {
    const newFiles: UploadFile[] = incoming.map(f => ({
      id: uid(),
      file: f,
      status: "queued" as UploadStatus,
      progress: 0,
    }));
    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const handleRemove = useCallback((id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  }, []);

  const handleUpload = useCallback(async () => {
    const pending = files.filter(f => f.status === "queued");
    if (pending.length === 0) return;

    // Mark all as uploading
    setFiles(prev =>
      prev.map(f => pending.find(p => p.id === f.id) ? { ...f, status: "uploading", progress: 5 } : f),
    );

    const collId = targetColl || "all";

    for (const uf of pending) {
      try {
        const accepted = await uploadDocument(uf.file, collId);

        setFiles(prev =>
          prev.map(f => f.id === uf.id ? { ...f, progress: 10, status: "parsing" } : f),
        );

        const cleanup = watchUploadEvents(
          accepted.doc_id,
          (evt) => {
            setFiles(prev =>
              prev.map(f => {
                if (f.id !== uf.id) return f;
                return {
                  ...f,
                  status: STAGE_TO_STATUS[evt.stage] ?? f.status,
                  progress: STAGE_TO_PROGRESS[evt.stage] ?? f.progress,
                  errorMsg: evt.error,
                };
              }),
            );
          },
          () => {
            setFiles(prev =>
              prev.map(f => f.id === uf.id ? { ...f, status: "done", progress: 100 } : f),
            );
          },
          (msg) => {
            setFiles(prev =>
              prev.map(f => f.id === uf.id ? { ...f, status: "error", errorMsg: msg } : f),
            );
          },
        );

        cleanupRef.current.push(cleanup);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        setFiles(prev =>
          prev.map(f => f.id === uf.id ? { ...f, status: "error", errorMsg: msg } : f),
        );
      }
    }
  }, [files, targetColl]);

  const allDone   = files.length > 0 && files.every(f => f.status === "done");
  const anyActive = files.some(f => f.status === "uploading" || f.status === "parsing");

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Upload Documents"
      description="Files will be added to your knowledge base and indexed for search."
      maxWidth="md"
    >
      {/* Collection selector */}
      <div className="mb-4">
        <label
          className="block text-ds-sm font-medium mb-2"
          style={{ color: "var(--text-muted)" }}
        >
          Add to collection
        </label>
        <select
          value={targetColl}
          onChange={e => setTargetColl(e.target.value)}
          className="w-full rounded-ds-lg px-3 py-2 text-ds-sm focus:outline-none transition-all duration-150"
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            color: "var(--text)",
          }}
          onFocus={e => (e.currentTarget.style.borderColor = "var(--border-brand)")}
          onBlur={e => (e.currentTarget.style.borderColor = "var(--border-bright)")}
        >
          {collections.filter(c => c.id !== "all").map(c => (
            <option key={c.id} value={c.id} style={{ background: "var(--bg-elevated)" }}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {/* Drop zone */}
      <FileDropZone
        onFiles={handleFiles}
        accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.rst"
        disabled={anyActive}
      />

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-4">
          {files.map(f => (
            <UploadFileRow key={f.id} file={f} onRemove={handleRemove} />
          ))}
        </div>
      )}

      {/* Footer */}
      <div
        className="flex items-center justify-between gap-3 mt-5 pt-4"
        style={{ borderTop: "1px solid var(--border)" }}
      >
        <p className="text-ds-xs" style={{ color: "var(--text-faint)" }}>
          {files.length === 0
            ? "No files selected"
            : `${files.length} file${files.length > 1 ? "s" : ""} selected`}
        </p>
        <div className="flex items-center gap-2">
          <Button variant="warm-sand" size="sm" onClick={onClose} disabled={anyActive}>
            {allDone ? "Close" : "Cancel"}
          </Button>
          {!allDone && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleUpload}
              disabled={files.length === 0 || anyActive}
              loading={anyActive}
            >
              {anyActive ? "Processing…" : "Upload & Index"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
