"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Modal } from "@/components/common/Modal";
import { Button } from "@/components/common/Button";
import { FileDropZone } from "@/components/modal/FileDropZone";
import { UploadFileRow } from "@/components/modal/UploadFileRow";
import type { Collection, UploadFile, UploadMetadata, UploadStatus } from "@/lib/types";
import { uploadDocument, watchUploadEvents } from "@/lib/api-client";

type UploadModalProps = {
  open: boolean;
  onClose: () => void;
  preferredCollectionId?: string;
  collections: Collection[];
};

let nextId = 0;
const uid = () => `f${++nextId}`;

const STAGE_TO_STATUS: Record<string, UploadStatus> = {
  parsing: "parsing",
  chunking: "parsing",
  embedding: "parsing",
  indexing: "parsing",
  searchable: "done",
  error: "error",
};

const STAGE_TO_PROGRESS: Record<string, number> = {
  parsing: 20,
  chunking: 40,
  embedding: 60,
  indexing: 80,
  searchable: 100,
  error: 0,
};

const ROLE_OPTIONS = [
  "HR",
  "Marketing",
  "Sales",
  "Developer",
  "Tester",
  "Architect",
  "Frontend",
  "Backend",
  "Operations",
];

const INITIAL_METADATA: UploadMetadata = {
  toolName: "",
  toolUrl: "",
  shortDescription: "",
  primaryRole: "Developer",
  audienceRoles: ["Developer"],
  importanceNote: "",
  impactNote: "",
  rating: 4,
};

export function UploadModal({ open, onClose, preferredCollectionId, collections }: UploadModalProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [targetColl, setTargetColl] = useState<string>("");
  const [metadata, setMetadata] = useState<UploadMetadata>(INITIAL_METADATA);
  const [toolSubmitState, setToolSubmitState] = useState<"idle" | "saving" | "done" | "error">("idle");
  const [toolSubmitError, setToolSubmitError] = useState("");
  const cleanupRef = useRef<Array<() => void>>([]);
  const uploadCollections = useMemo(
    () => collections.filter((collection) => collection.id !== "all"),
    [collections],
  );
  const selectedCollection = useMemo(
    () => uploadCollections.find((collection) => collection.id === targetColl),
    [targetColl, uploadCollections],
  );
  const groupedCollections = useMemo(
    () =>
      uploadCollections.reduce<Record<string, Collection[]>>((acc, collection) => {
        const section = collection.section ?? "Other";
        acc[section] ??= [];
        acc[section].push(collection);
        return acc;
      }, {}),
    [uploadCollections],
  );

  useEffect(() => {
    if (!open) {
      cleanupRef.current.forEach((fn) => fn());
      cleanupRef.current = [];
      setFiles([]);
      setMetadata(INITIAL_METADATA);
      setToolSubmitState("idle");
      setToolSubmitError("");
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const fallbackCollectionId = uploadCollections[0]?.id ?? "";
    setTargetColl(
      preferredCollectionId && preferredCollectionId !== "all"
        ? preferredCollectionId
        : fallbackCollectionId,
    );
  }, [open, preferredCollectionId, uploadCollections]);

  const resetSubmitState = useCallback(() => {
    setToolSubmitState("idle");
    setToolSubmitError("");
  }, []);

  const updateMetadata = useCallback(
    <K extends keyof UploadMetadata>(key: K, value: UploadMetadata[K]) => {
      resetSubmitState();
      setMetadata((prev) => ({ ...prev, [key]: value }));
    },
    [resetSubmitState],
  );

  const handleFiles = useCallback(
    (incoming: File[]) => {
      resetSubmitState();
      const newFiles: UploadFile[] = incoming.map((file) => ({
        id: uid(),
        file,
        status: "queued" as UploadStatus,
        progress: 0,
      }));
      setFiles((prev) => [...prev, ...newFiles]);
    },
    [resetSubmitState],
  );

  const handleRemove = useCallback(
    (id: string) => {
      resetSubmitState();
      setFiles((prev) => prev.filter((file) => file.id !== id));
    },
    [resetSubmitState],
  );

  const toggleAudienceRole = useCallback(
    (role: string) => {
      resetSubmitState();
      setMetadata((prev) => {
        const exists = prev.audienceRoles.includes(role);
        const audienceRoles = exists
          ? prev.audienceRoles.filter((item) => item !== role)
          : [...prev.audienceRoles, role];
        return {
          ...prev,
          audienceRoles: audienceRoles.length > 0 ? audienceRoles : [prev.primaryRole],
        };
      });
    },
    [resetSubmitState],
  );

  const handleUpload = useCallback(async () => {
    const pending = files.filter((file) => file.status === "queued");
    const collId = targetColl || uploadCollections[0]?.id || "";
    if (!collId) return;
    if (!metadata.toolName.trim() || !metadata.importanceNote.trim() || !metadata.impactNote.trim()) {
      return;
    }

    resetSubmitState();

    const payload = {
      collectionId: collId,
      department: selectedCollection?.name ?? "General",
      toolName: metadata.toolName.trim(),
      toolUrl: metadata.toolUrl.trim(),
      shortDescription: metadata.shortDescription.trim(),
      primaryRole: metadata.primaryRole,
      audienceRoles: metadata.audienceRoles,
      importanceNote: metadata.importanceNote.trim(),
      impactNote: metadata.impactNote.trim(),
      rating: metadata.rating,
    };

    if (pending.length === 0) {
      try {
        setToolSubmitState("saving");
        await uploadDocument(null, payload);
        setToolSubmitState("done");
      } catch (err) {
        setToolSubmitState("error");
        setToolSubmitError(err instanceof Error ? err.message : "Tool save failed");
      }
      return;
    }

    setFiles((prev) =>
      prev.map((file) =>
        pending.find((pendingFile) => pendingFile.id === file.id)
          ? { ...file, status: "uploading", progress: 5 }
          : file,
      ),
    );

    for (const queuedFile of pending) {
      try {
        const accepted = await uploadDocument(queuedFile.file, payload);

        setFiles((prev) =>
          prev.map((file) =>
            file.id === queuedFile.id ? { ...file, progress: 10, status: "parsing" } : file,
          ),
        );

        const cleanup = watchUploadEvents(
          accepted.doc_id,
          (evt) => {
            setFiles((prev) =>
              prev.map((file) => {
                if (file.id !== queuedFile.id) return file;
                return {
                  ...file,
                  status: STAGE_TO_STATUS[evt.stage] ?? file.status,
                  progress: STAGE_TO_PROGRESS[evt.stage] ?? file.progress,
                  errorMsg: evt.error,
                };
              }),
            );
          },
          () => {
            setFiles((prev) =>
              prev.map((file) =>
                file.id === queuedFile.id ? { ...file, status: "done", progress: 100 } : file,
              ),
            );
          },
          (msg) => {
            setFiles((prev) =>
              prev.map((file) =>
                file.id === queuedFile.id ? { ...file, status: "error", errorMsg: msg } : file,
              ),
            );
          },
        );

        cleanupRef.current.push(cleanup);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        setFiles((prev) =>
          prev.map((file) =>
            file.id === queuedFile.id ? { ...file, status: "error", errorMsg: msg } : file,
          ),
        );
      }
    }
  }, [files, metadata, resetSubmitState, selectedCollection?.name, targetColl, uploadCollections]);

  const allDone =
    (files.length > 0 && files.every((file) => file.status === "done")) ||
    (files.length === 0 && toolSubmitState === "done");
  const anyActive =
    files.some((file) => file.status === "uploading" || file.status === "parsing") ||
    toolSubmitState === "saving";
  const formValid =
    Boolean(targetColl) &&
    Boolean(metadata.toolName.trim()) &&
    Boolean(metadata.importanceNote.trim()) &&
    Boolean(metadata.impactNote.trim()) &&
    metadata.rating >= 1 &&
    metadata.rating <= 5 &&
    metadata.audienceRoles.length > 0;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add Tool"
      maxWidth="xl"
    >
      <div className="mb-4">
        <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
          Add to collection
        </label>
        <select
          value={targetColl}
          onChange={(e) => {
            resetSubmitState();
            setTargetColl(e.target.value);
          }}
          className="w-full rounded-ds-lg px-3 py-2 text-ds-sm focus:outline-none transition-all duration-150"
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-bright)",
            color: "var(--text)",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "var(--border-brand)")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-bright)")}
        >
          {Object.entries(groupedCollections).map(([section, sectionCollections]) => (
            <optgroup key={section} label={section}>
              {sectionCollections.map((collection) => (
                <option
                  key={collection.id}
                  value={collection.id}
                  style={{ background: "var(--bg-elevated)" }}
                >
                  {collection.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
            Tool or AI name
          </label>
          <input
            value={metadata.toolName}
            onChange={(e) => updateMetadata("toolName", e.target.value)}
            placeholder="GitHub Copilot, Notion AI, Jira, Linear..."
            className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-bright)",
              color: "var(--text)",
            }}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:col-span-2">
          <div>
            <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
              Tool link
            </label>
            <input
              value={metadata.toolUrl}
              onChange={(e) => updateMetadata("toolUrl", e.target.value)}
              placeholder="https://..."
              className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-bright)",
                color: "var(--text)",
              }}
            />
          </div>

          <div>
            <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
              Short description
            </label>
            <input
              value={metadata.shortDescription}
              onChange={(e) => updateMetadata("shortDescription", e.target.value)}
              placeholder="One-line summary of what the tool does"
              className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-bright)",
                color: "var(--text)",
              }}
            />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:col-span-2">
          <div>
            <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
              Primary role
            </label>
            <select
              value={metadata.primaryRole}
              onChange={(e) => {
                resetSubmitState();
                setMetadata((prev) => {
                  const primaryRole = e.target.value;
                  const audienceRoles = prev.audienceRoles.includes(primaryRole)
                    ? prev.audienceRoles
                    : [...prev.audienceRoles, primaryRole];
                  return { ...prev, primaryRole, audienceRoles };
                });
              }}
              className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-bright)",
                color: "var(--text)",
              }}
            >
              {ROLE_OPTIONS.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
              Rating
            </label>
            <select
              value={String(metadata.rating)}
              onChange={(e) => updateMetadata("rating", Number(e.target.value))}
              className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-bright)",
                color: "var(--text)",
              }}
            >
              {[5, 4, 3, 2, 1].map((value) => (
                <option key={value} value={value}>
                  {value}/5
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="lg:col-span-2">
          <p className="mb-2 text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
            Helpful for teams
          </p>
          <div className="flex flex-wrap gap-2">
            {ROLE_OPTIONS.map((role) => {
              const selected = metadata.audienceRoles.includes(role);
              return (
                <button
                  key={role}
                  type="button"
                  onClick={() => toggleAudienceRole(role)}
                  className="rounded-md border px-3 py-1.5 text-xs transition"
                  style={{
                    borderColor: selected ? "var(--accent-strong)" : "var(--border-bright)",
                    background: selected ? "rgba(16,163,127,0.12)" : "transparent",
                    color: "var(--text)",
                  }}
                >
                  {role}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
            Why is this tool important?
          </label>
          <textarea
            value={metadata.importanceNote}
            onChange={(e) => updateMetadata("importanceNote", e.target.value)}
            rows={3}
            placeholder="What problem does it solve, and why should the team care?"
            className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-bright)",
              color: "var(--text)",
            }}
          />
        </div>

        <div>
          <label className="mb-2 block text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
            How does it help?
          </label>
          <textarea
            value={metadata.impactNote}
            onChange={(e) => updateMetadata("impactNote", e.target.value)}
            rows={3}
            placeholder="What outcomes, workflow improvements, or time savings does it create?"
            className="w-full rounded-lg px-3 py-2 text-sm focus:outline-none"
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-bright)",
              color: "var(--text)",
            }}
          />
        </div>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-ds-sm font-medium" style={{ color: "var(--text-muted)" }}>
          Supporting documents
        </p>
        <p className="mb-3 text-ds-xs" style={{ color: "var(--text-faint)" }}>
          Optional. Add PDFs or notes when you want retrieval grounded in attached files.
        </p>
        <FileDropZone
          onFiles={handleFiles}
          accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.rst"
          disabled={anyActive}
        />
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          {files.map((file) => (
            <UploadFileRow key={file.id} file={file} onRemove={handleRemove} />
          ))}
        </div>
      )}

      <div
        className="sticky bottom-0 -mx-6 mt-5 flex items-center justify-between gap-3 border-t border-[var(--border)] bg-[var(--bg-elevated)] px-6 py-4"
      >
        <div>
          <p className="text-ds-xs" style={{ color: toolSubmitState === "error" ? "var(--error)" : "var(--text-faint)" }}>
            {allDone
              ? "Successfully saved and indexed."
              : toolSubmitState === "error"
                ? toolSubmitError
                : files.length === 0
                  ? "No files selected. This will save a tool-only entry."
                  : `${files.length} file${files.length > 1 ? "s" : ""} selected`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="warm-sand" size="sm" onClick={onClose} disabled={anyActive}>
            {allDone ? "Close" : "Cancel"}
          </Button>
          {!allDone && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleUpload}
              disabled={anyActive || !formValid}
              loading={anyActive}
            >
              {anyActive ? "Processing..." : files.length === 0 ? "Save Tool" : "Upload & Index"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
