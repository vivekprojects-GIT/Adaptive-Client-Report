/**
 * Minimal markdown renderer — escapes HTML, then converts the formats
 * Anthropic typically returns: headings, bold/italic, code, lists, tables.
 *
 * NOT a full markdown parser. Use a real library (react-markdown) if you
 * need full CommonMark compliance.
 */

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

export function renderMarkdown(md) {
  if (!md) return "";
  let html = escapeHtml(md);

  // Code fences
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="lang-${lang || ""}">${code}</code></pre>`);

  // Inline code
  html = html.replace(/`([^`\n]+?)`/g, "<code>$1</code>");

  // Headings
  html = html.replace(/^###\s+(.+)$/gm, "<h3>$1</h3>")
             .replace(/^##\s+(.+)$/gm,  "<h2>$1</h2>")
             .replace(/^#\s+(.+)$/gm,   "<h1>$1</h1>");

  // Bold + italic (bold first to avoid conflict)
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
             .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");

  // Tables
  html = html.replace(/((?:^\|.*\|\s*$\n?)+)/gm, (block) => {
    const rows = block.trim().split("\n");
    if (rows.length < 2) return block;
    const [head, sep, ...body] = rows;
    if (!/^\|[\s|:-]+\|$/.test(sep)) return block;
    const ths = head.split("|").slice(1, -1).map((c) => `<th>${c.trim()}</th>`).join("");
    const trs = body.map((r) => "<tr>" + r.split("|").slice(1, -1)
      .map((c) => `<td>${c.trim()}</td>`).join("") + "</tr>").join("");
    return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
  });

  // Unordered lists
  html = html.replace(/((?:^\s*[-*]\s+.+\n?)+)/gm, (block) => {
    const items = block.trim().split("\n").map((line) =>
      `<li>${line.replace(/^\s*[-*]\s+/, "")}</li>`).join("");
    return `<ul>${items}</ul>`;
  });

  // Ordered lists
  html = html.replace(/((?:^\s*\d+\.\s+.+\n?)+)/gm, (block) => {
    const items = block.trim().split("\n").map((line) =>
      `<li>${line.replace(/^\s*\d+\.\s+/, "")}</li>`).join("");
    return `<ol>${items}</ol>`;
  });

  // Paragraphs — wrap blocks of plain text
  html = html.split(/\n\n+/).map((block) => {
    if (/^<(h\d|ul|ol|pre|table)/i.test(block.trim())) return block;
    return `<p>${block.trim().replace(/\n/g, "<br>")}</p>`;
  }).join("\n");

  return html;
}
