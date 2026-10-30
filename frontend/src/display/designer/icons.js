// The icons the schema names (one_display/blocks.py), written out because the
// build only bundles an icon it finds named in the source.
export const ICONS = [
  "lucide-align-left",
  "lucide-align-center",
  "lucide-align-right",
  "lucide-align-justify",
  "lucide-arrow-up-to-line",
  "lucide-fold-vertical",
  "lucide-arrow-down-to-line",
  "lucide-square",
  "lucide-circle",
  "lucide-triangle",
  "lucide-diamond",
  "lucide-star",
  "lucide-arrow-right",
  "lucide-minus",
];

export const glyph = (name) => (ICONS.includes(`lucide-${name}`) ? `lucide-${name}` : "lucide-circle-dot");
