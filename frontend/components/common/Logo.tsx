import { cn } from "@/lib/cn";

type LogoProps = {
  className?: string;
  size?: "sm" | "md" | "lg";
  collapsed?: boolean;
};

const sizes = {
  sm: { iconHeight: 22, fontSize: 13, gap: 10 },
  md: { iconHeight: 26, fontSize: 15, gap: 11 },
  lg: { iconHeight: 32, fontSize: 19, gap: 13 },
};

export function Logo({ className, size = "md", collapsed = false }: LogoProps) {
  const { iconHeight, fontSize, gap } = sizes[size];

  const iconMark = (
    <img
      aria-hidden={!collapsed}
      aria-label={collapsed ? "DigitalSprint AI" : undefined}
      className="shrink-0 rounded-sm"
      src="/assets/logo-digitalsprint-main.png"
      alt={collapsed ? "DigitalSprint AI" : ""}
      style={{ height: iconHeight, width: "auto", objectFit: "contain" }}
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
          fontWeight: 500,
          fontSize: fontSize - 2,
          color: "var(--text-subtle)",
          letterSpacing: "0.02em",
        }}
        aria-label="Knowledge RAG"
      >
        Knowledge RAG
      </span>
    </div>
  );
}
