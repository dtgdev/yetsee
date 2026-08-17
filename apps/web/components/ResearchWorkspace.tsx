import Link from "next/link";

export function ResearchPage({
  children,
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  children: React.ReactNode;
  eyebrow: string;
  title: string;
  subtitle: string;
  actions?: React.ReactNode;
}) {
  return <div className="researchWorkspace">
    <header className="researchPageHeader">
      <div>
        <p className="researchEyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {actions && <div className="researchHeaderActions">{actions}</div>}
    </header>
    {children}
  </div>;
}

export function ResearchMetrics({ children }: { children: React.ReactNode }) {
  return <section className="researchMetrics">{children}</section>;
}

export function Metric({ label, value, note, tone = "blue" }: { label: string; value: React.ReactNode; note?: string; tone?: "blue"|"green"|"amber"|"red"|"violet" }) {
  return <div className="researchMetric">
    <span className={`metricGlyph tone-${tone}`}>◆</span>
    <div><p>{label}</p><strong>{value}</strong>{note && <small>{note}</small>}</div>
  </div>;
}

export function ResearchPanel({
  title,
  subtitle,
  children,
  action,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return <section className={`researchPanel ${className}`}>
    <div className="researchPanelHead"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
    {children}
  </section>;
}

export function ResearchTable({ children }: { children: React.ReactNode }) {
  return <div className="researchTable">{children}</div>;
}

export function StatusPill({ children, tone = "blue" }: { children: React.ReactNode; tone?: "blue"|"green"|"amber"|"red"|"slate"|"violet" }) {
  return <span className={`researchPill pill-${tone}`}>{children}</span>;
}

export function TinyLink({ href, children }: { href: string; children: React.ReactNode }) {
  return <Link className="tinyLink" href={href}>{children} →</Link>;
}
