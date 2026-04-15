import { cn } from "@/lib/cn";

type SidebarSectionProps = {
  title: string;
  children: React.ReactNode;
};

export function SidebarSection({ title, children }: SidebarSectionProps) {
  return (
    <div>
      <p
        className="px-3 mb-1.5 text-ds-label font-semibold uppercase tracking-widest"
        style={{ color: "var(--text-faint)" }}
      >
        {title}
      </p>
      {children}
    </div>
  );
}
