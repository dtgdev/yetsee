import "./styles.css";

export const metadata = {
  title: "YetSee — Scientific Investigation OS",
  description: "Evidence-backed living investigations, agent orchestration, knowledge graphs and replayable reasoning.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
