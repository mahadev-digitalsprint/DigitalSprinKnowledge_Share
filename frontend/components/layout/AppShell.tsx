"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { UploadModal } from "@/components/modal/UploadModal";
import { mockCollections } from "@/lib/mock-data";

type AppShellProps = {
  children: React.ReactNode;
  activeCollectionId?: string;
};

export function AppShell({ children, activeCollectionId = "all" }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploadOpen,  setUploadOpen]  = useState(false);

  const activeCollection = mockCollections.find(c => c.id === activeCollectionId);

  return (
    <div className="flex h-screen overflow-hidden bg-ds-bg">
      <Sidebar
        recentChats={[]}
        activeChatId={undefined}
        onSelectChat={() => {}}
        onNewChat={() => {}}
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
