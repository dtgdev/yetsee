import "./styles.css";
import "./mission-control.css";
import "./mission-provenance.css";
import "./scientific-decision.css";
import "./scientific-resolution.css";
import "./scientific-memory.css";
import "./mission-scientific-outcome.css";
import "./scientific-evidence.css";
import "./workspace-recovery.css";

export const metadata = {
  title: "YetSee — Scientific Investigation OS",
  description: "Evidence-backed living investigations, agent orchestration, knowledge graphs and replayable reasoning.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
