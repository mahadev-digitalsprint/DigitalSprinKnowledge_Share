"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { UploadModal } from "@/components/modal/UploadModal";
import { mockCollections } from "@/lib/mock-data";

type AppShellProps = {
  children: React.ReactNode;
  activeCollectionId?: string;
  onCollectionChange?: (id: string) => void;
};

export function AppShell({ children, activeCollectionId = "all", onCollectionChange }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploadOpen,  setUploadOpen]  = useState(false);

  const activeCollection = mockCollections.find(c => c.id === activeCollectionId);

  return (
    <div className="flex h-screen overflow-hidden bg-ds-bg">
      <Sidebar
        collections={mockCollections}
        recentChats={[]}
        activeCollectionId={activeCollectionId}
        activeChatId={undefined}
        onCollectionChange={onCollectionChange ?? (() => {})}
        onSelectChat={() => {}}
        onNewChat={() => {}}
        searchOpen={false}
        searchQuery=""
        onSearchOpen={() => {}}
        onSearchClose={() => {}}
        onSearchQueryChange={() => {}}
        onOpenUpload={() => setUploadOpen(true)}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {children}
      </main>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        preferredCollectionId={activeCollection?.id}
        collections={mockCollections}
      />
    </div>
  );
}
