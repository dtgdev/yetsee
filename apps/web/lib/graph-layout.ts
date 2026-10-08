type LayoutNode = { id: string; kind: string };

const evidenceKinds = new Set(["observation", "publication", "study", "clinical_trial", "source"]);
const contextKinds = new Set(["investigation", "hypothesis"]);
const outcomeKinds = new Set(["outcome", "assessment", "evidence_gap", "metric", "event"]);

export function graphLayout(nodes: LayoutNode[]) {
  const columns = [
    { label: "Question", x: 110, nodes: [] as LayoutNode[] },
    { label: "Evidence", x: 350, nodes: [] as LayoutNode[] },
    { label: "Related items", x: 590, nodes: [] as LayoutNode[] },
    { label: "Findings & gaps", x: 830, nodes: [] as LayoutNode[] },
  ];
  for (const node of nodes) {
    const index = contextKinds.has(node.kind) ? 0 : evidenceKinds.has(node.kind) ? 1 : outcomeKinds.has(node.kind) ? 3 : 2;
    columns[index].nodes.push(node);
  }
  const height = Math.max(460, Math.max(...columns.map(column => column.nodes.length)) * 110 + 100);
  const positions = new Map<string, { x: number; y: number }>();
  for (const column of columns) {
    column.nodes.forEach((node, index) => {
      positions.set(node.id, { x: column.x, y: 80 + (index + 0.5) * (height - 150) / column.nodes.length });
    });
  }
  return { width: 940, height, positions, columns: columns.filter(column => column.nodes.length) };
}

export function graphLabelLines(label: string): string[] {
  const words = label.replaceAll("_", " ").trim().split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    if (current && `${current} ${word}`.length > 24) {
      lines.push(current);
      current = word;
    } else current = current ? `${current} ${word}` : word;
  }
  if (current) lines.push(current);
  return lines.slice(0, 2).map((line, index) => {
    const truncated = line.length > 24 || (index === 1 && lines.length > 2);
    return truncated ? `${line.slice(0, 23)}…` : line;
  });
}
