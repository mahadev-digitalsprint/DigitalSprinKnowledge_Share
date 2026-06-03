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
    <img
      aria-hidden={!collapsed}
      aria-label={collapsed ? "Knowledge RAG" : undefined}
      className="rounded-xl"
      src="/assets/logo-digitalsprint-main.png"
      alt={collapsed ? "Knowledge RAG" : ""}
      style={{ width: iconSize, height: iconSize }}
    />
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
