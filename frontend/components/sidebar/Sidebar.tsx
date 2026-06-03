"use client";

import { MessageSquarePlus, Upload, X, Settings } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { Logo } from "@/components/common/Logo";
import { IconButton } from "@/components/common/IconButton";
import { SidebarSection } from "@/components/sidebar/SidebarSection";
import { RecentChats } from "@/components/sidebar/RecentChats";
import type { RecentChat } from "@/lib/types";

type SidebarProps = {
  recentChats: RecentChat[];
  activeChatId?: string;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onOpenUpload: () => void;
  isOpen: boolean;
  onClose: () => void;
};

export function Sidebar({
  recentChats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onOpenUpload,
  isOpen,
  onClose,
}: SidebarProps) {
  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex h-full w-[280px] shrink-0 flex-col border-r border-[var(--border-subtle)] bg-[var(--sidebar-bg)] transition-transform duration-300 ease-out md:relative md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <Logo size="sm" />
          <IconButton label="Close sidebar" onClick={onClose} className="md:hidden" variant="ghost">
            <X size={15} />
          </IconButton>
        </div>

        <div className="px-3 pb-2">
          <button
            onClick={onNewChat}
            className="flex h-10 w-full items-center gap-2 rounded-lg bg-[var(--surface-secondary)] px-3 text-sm font-medium text-[var(--text-main)] transition hover:bg-[var(--surface-tertiary)]"
          >
            <MessageSquarePlus size={15} />
            New chat
          </button>
        </div>

        <nav className="scrollbar-thin flex-1 overflow-y-auto px-2 py-2 space-y-5">
          <SidebarSection title="Recent">
            <RecentChats
              chats={recentChats}
              activeChatId={activeChatId}
              onSelect={onSelectChat}
            />
          </SidebarSection>
        </nav>

        <div className="space-y-1 border-t border-[var(--border-subtle)] px-3 py-3">
          <button
            onClick={onOpenUpload}
            className="flex h-9 w-full items-center gap-2 rounded-lg px-3 text-sm text-[var(--text-subtle)] transition hover:bg-[var(--surface-primary)] hover:text-[var(--text-main)]"
          >
            <Upload size={14} />
            Add files
          </button>

          <Link href="/settings" className="block">
            <button className="flex h-9 w-full items-center gap-2 rounded-lg px-3 text-sm text-[var(--text-subtle)] transition hover:bg-[var(--surface-primary)] hover:text-[var(--text-main)]">
              <Settings size={14} />
              Settings
            </button>
          </Link>
        </div>
      </aside>
    </>
  );
}
