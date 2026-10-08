import Link from "next/link";

const nav = [
  ["⌂", "Home", "/"],
  ["▣", "Investigations", "/investigations"],
  ["⌕", "Discovery", "/discovery"],
] as const;

export function StudioSidebar({ active = "Home" }: { active?: string }) {
  return (
    <aside className="studioSidebar">
      <Link className="studioBrand" href="/">
        <span className="brandMark" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></span>
        <span><strong>YetSee</strong><small>Scientific Investigation OS</small></span>
      </Link>

      <nav className="studioNav" aria-label="Primary navigation">
        {nav.map(([icon, label, href]) => (
          <Link className={label === active ? "active" : ""} href={href} key={label}>
            <span className="navIcon">{icon}</span><span>{label}</span>
          </Link>
        ))}
      </nav>

      <details className="sidebarTools" open={active === "Operations" || active === "Agent Registry"}>
        <summary>More tools</summary>
        <Link className={active === "Operations" ? "active" : ""} href="/operations">Operations</Link>
        <Link className={active === "Agent Registry" ? "active" : ""} href="/agents">Agent Registry</Link>
        <Link href="/signal-lake">Signal Lake</Link>
        <Link href="/graph">Knowledge Graph</Link>
      </details>

      <div className="sidebarFoot">
        <div className="sidebarMotto">See Further.<br/><strong>Understand Deeper.</strong><span className="moleculeDecor" /></div>
      </div>
    </aside>
  );
}

export function StudioTopbar() {
  return (
    <header className="studioTopbar">
      <span className="topbarTitle">Research workspace</span>
      <div className="topbarActions">
        <Link href="/">Home</Link>
        <Link href="/investigations">All investigations →</Link>
        <Link href="/discovery">Discovery</Link>
      </div>
    </header>
  );
}

export function StudioFrame({ children, active }: { children: React.ReactNode; active?: string }) {
  return <div className="studioApp"><StudioSidebar active={active}/><div className="studioMain"><StudioTopbar/>{children}</div></div>;
}

