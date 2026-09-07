import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  testId?: string;
  bodyClassName?: string;
}

export function Panel({
  title,
  children,
  actions,
  className = "",
  testId,
  bodyClassName = "",
}: PanelProps) {
  return (
    <section
      className={`flex min-h-0 flex-col overflow-hidden rounded border border-line bg-panel ${className}`}
    >
      <header className="flex h-8 shrink-0 items-center justify-between gap-2 border-b border-line bg-panel-head px-2.5">
        <h2 className="text-[10px] font-semibold tracking-[0.14em] text-ink-muted uppercase">
          {title}
        </h2>
        {actions}
      </header>
      <div
        data-testid={testId}
        className={`min-h-0 flex-1 ${bodyClassName}`}
      >
        {children}
      </div>
    </section>
  );
}
