import Link from "next/link";

const nav = [
  ["⌂", "Home", "/"],
  ["▣", "Investigations", "/investigations"],
  ["⌕", "Discovery", "/discovery"],
  ["⊙", "Operations", "/operations"],
  ["♙", "Agent Registry", "/agents"],
] as const;

const collections = ["Lifestyle & Health", "Technology", "Markets", "Science"];

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
            {label === "Investigations" && <em>1</em>}
            {label === "Agent Registry" && <em>10</em>}
          </Link>
        ))}
      </nav>

      <div className="navGroupLabel">Collections</div>
      <div className="collectionList">
        {collections.map((item) => <div key={item}><span>⌗</span>{item}<b>⌄</b></div>)}
      </div>

      <div className="sidebarFoot">
        <Link href="/">▣ Documentation</Link>
        <Link href="/operations">⚙ Settings</Link>
        <div className="sidebarMotto">See Further.<br/><strong>Understand Deeper.</strong><span className="moleculeDecor" /></div>
      </div>
    </aside>
  );
}

export function StudioTopbar() {
  return (
    <header className="studioTopbar">
      <div className="globalSearch"><span>⌕</span><span>Search investigations, concepts, evidence... or type a command</span><kbd>⌘ K</kbd></div>
      <div className="topbarActions">
        <span className="healthPill"><i /> System Health</span>
        <button aria-label="Theme">☼</button>
        <button className="notificationButton" aria-label="Notifications">♧<b>3</b></button>
        <span className="avatar">DG</span>
      </div>
    </header>
  );
}

export function StudioFrame({ children, active }: { children: React.ReactNode; active?: string }) {
  return <div className="studioApp"><StudioSidebar active={active}/><div className="studioMain"><StudioTopbar/>{children}</div></div>;
}
