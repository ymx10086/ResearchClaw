import type { ReactNode } from "react";

/* ---------- Page Header ---------- */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div className="page-header-copy">
        {eyebrow && <div className="page-eyebrow">{eyebrow}</div>}
        <div className="page-header-heading">
          <div>
            <h2>{title}</h2>
            {description && <p>{description}</p>}
          </div>
          {meta && <div className="page-header-meta">{meta}</div>}
        </div>
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </div>
  );
}

/* ---------- Stat Card ---------- */
export function StatCard({
  label,
  value,
  icon,
  variant = "brand",
}: {
  label: string;
  value: string | number;
  icon: ReactNode;
  variant?: "brand" | "success" | "warning" | "info" | "danger";
}) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${variant}`}>{icon}</div>
      <div className="stat-content">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
      </div>
    </div>
  );
}

/* ---------- Badge ---------- */
export function Badge({
  children,
  variant = "neutral",
}: {
  children: ReactNode;
  variant?: "success" | "warning" | "danger" | "info" | "neutral";
}) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function MetricPill({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="metric-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function SurfaceCard({
  title,
  description,
  actions,
  children,
  className = "",
}: {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`surface-card${className ? ` ${className}` : ""}`}>
      {(title || description || actions) && (
        <div className="surface-card-head">
          <div>
            {title && <h3>{title}</h3>}
            {description && <p>{description}</p>}
          </div>
          {actions && <div className="surface-card-actions">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

/* ---------- Toggle ---------- */
export function Toggle({
  checked,
  onChange,
  disabled = false,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="toggle">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="toggle-track" />
    </label>
  );
}

/* ---------- Empty State ---------- */
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

/* ---------- Loading ---------- */
export function Loading({ text = "加载中..." }: { text?: string }) {
  return (
    <div className="loading-overlay">
      <div className="spinner" />
      <span>{text}</span>
    </div>
  );
}

/* ---------- Data Row ---------- */
export function DataRow({
  title,
  meta,
  badge,
  actions,
}: {
  title: string;
  meta?: string;
  badge?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="data-row">
      <div className="data-row-info">
        <div className="data-row-title">
          {title} {badge}
        </div>
        {meta && <div className="data-row-meta">{meta}</div>}
      </div>
      {actions && <div className="data-row-actions">{actions}</div>}
    </div>
  );
}

/* ---------- Detail Modal ---------- */
export function DetailModal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="detail-panel-header">
          <h3>{title}</h3>
          <button className="btn-ghost btn-sm" onClick={onClose}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
