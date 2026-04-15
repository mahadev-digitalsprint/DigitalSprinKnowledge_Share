import { cn } from "@/lib/cn";

type LogoProps = {
  className?: string;
  size?: "sm" | "md" | "lg";
  collapsed?: boolean;
};

const sizes = {
  sm: { iconSize: 28, fontSize: 13, gap: 10 },
  md: { iconSize: 32, fontSize: 15, gap: 11 },
  lg: { iconSize: 40, fontSize: 19, gap: 13 },
};

export function Logo({ className, size = "md", collapsed = false }: LogoProps) {
  const { iconSize, fontSize, gap } = sizes[size];

  const iconMark = (
    <div
      aria-hidden={!collapsed}
      aria-label={collapsed ? "Knowledge RAG" : undefined}
      className="flex items-center justify-center rounded-xl bg-[var(--accent-strong)] text-white"
      style={{ width: iconSize, height: iconSize }}
    >
      <span style={{ fontSize: iconSize / 2.35, fontWeight: 700 }}>K</span>
    </div>
  );

  if (collapsed) {
    return <div className={cn("flex items-center justify-center", className)}>{iconMark}</div>;
  }

  return (
    <div className={cn("flex items-center", className)} style={{ gap }}>
      {iconMark}
      <span
        style={{
          fontWeight: 700,
          fontSize,
          color: "var(--text-main)",
        }}
        aria-label="Knowledge RAG"
      >
        Knowledge RAG
      </span>
    </div>
  );
}
