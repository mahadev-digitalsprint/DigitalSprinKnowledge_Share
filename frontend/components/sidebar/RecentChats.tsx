import { MessageSquare } from "lucide-react";
import { formatRelativeTime } from "@/lib/mock-data";
import type { RecentChat } from "@/lib/types";

type RecentChatsProps = {
  chats: RecentChat[];
  activeChatId?: string;
  onSelect: (id: string) => void;
};

export function RecentChats({ chats, activeChatId, onSelect }: RecentChatsProps) {
  if (chats.length === 0) {
    return (
      <p className="px-3 py-2 text-ds-sm italic" style={{ color: "var(--text-faint)" }}>
        No recent chats
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-0.5">
      {chats.map((chat) => {
        const isActive = chat.id === activeChatId;
        return (
          <li key={chat.id}>
            <button
              onClick={() => onSelect(chat.id)}
              className="group flex w-full items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-all duration-150 focus:outline-none"
              style={{
                background: isActive ? "var(--surface-primary)" : "transparent",
                color: isActive ? "var(--text-main)" : "var(--text-subtle)",
              }}
            >
              <MessageSquare
                size={12}
                className="shrink-0 mt-0.5"
                style={{ color: isActive ? "var(--accent-strong)" : "var(--text-muted)" }}
              />
              <div className="flex-1 min-w-0">
                <p
                  className="text-ds-sm font-medium truncate leading-tight"
                  style={{ color: isActive ? "var(--text-main)" : "var(--text-main)" }}
                >
                  {chat.title}
                </p>
                <p className="text-ds-xs truncate mt-0.5" style={{ color: "var(--text-muted)" }}>
                  {formatRelativeTime(chat.updatedAt)}
                </p>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
