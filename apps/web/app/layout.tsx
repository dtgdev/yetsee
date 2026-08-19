import "./styles.css";
import "./mission-control.css";
import "./mission-provenance.css";
import "./scientific-decision.css";

export const metadata = {
  title: "YetSee — Scientific Investigation OS",
  description: "Evidence-backed living investigations, agent orchestration, knowledge graphs and replayable reasoning.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
