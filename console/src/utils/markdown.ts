/**
 * Strip YAML frontmatter from the beginning of markdown text.
 */
export const stripFrontmatter = (s: string): string =>
  s.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, "");

function transformOutsideCode(
  input: string,
  transform: (segment: string) => string,
): string {
  const protectedPattern = /(```[\s\S]*?```|~~~[\s\S]*?~~~|(`+)([\s\S]*?)\2)/g;
  let output = "";
  let lastIndex = 0;

  for (const match of input.matchAll(protectedPattern)) {
    const index = match.index ?? 0;
    output += transform(input.slice(lastIndex, index));
    output += match[0];
    lastIndex = index + match[0].length;
  }

  output += transform(input.slice(lastIndex));
  return output;
}

/**
 * Convert LaTeX delimiters commonly emitted by models into remark-math syntax.
 *
 * `react-markdown` treats `\[...\]` as escaped brackets before math parsing,
 * so normalize those forms up front.
 */
export function normalizeMathDelimiters(input: string): string {
  if (!input) return "";

  return transformOutsideCode(input, (segment) =>
    segment
      .replace(/\\\[\s*([\s\S]*?)\s*\\\]/g, (_, expr: string) => {
        const body = expr.trim();
        return body ? `\n\n$$\n${body}\n$$\n\n` : "";
      })
      .replace(/\\\(([\s\S]*?)\\\)/g, (_, expr: string) => {
        const body = expr.trim();
        return body ? `$${body}$` : "";
      }),
  );
}

/**
 * Normalize common malformed table outputs from LLMs so remark-gfm can render.
 *
 * Typical malformed shape:
 * | h1 | h2 | |----|----| | a | b |
 */
export function normalizeMarkdownTables(input: string): string {
  if (!input) return "";

  let text = input.replace(/\r\n/g, "\n").replace(/｜/g, "|");

  // Split collapsed table rows that are accidentally emitted on one line.
  // Example: "| a | b | |---|---| | 1 | 2 |" -> multi-line rows.
  for (let i = 0; i < 10; i += 1) {
    const next = text.replace(/(\|[^\n]*?\|)\s+(?=\|)/g, "$1\n");
    if (next === text) break;
    text = next;
  }

  // Ensure a blank line before table blocks to help markdown parsers.
  text = text.replace(/([^\n])\n(\|[^\n]*\|\n\|[-:|\s]+\|)/g, "$1\n\n$2");

  return text;
}

/**
 * End-to-end markdown cleanup before rendering.
 */
export function preprocessMarkdown(input: string): string {
  return normalizeMarkdownTables(
    normalizeMathDelimiters(stripFrontmatter(input || "")),
  );
}
