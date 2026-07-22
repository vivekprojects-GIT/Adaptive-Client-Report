/**
 * Progressive Markdown rendering for a reply that is still streaming.
 *
 * The renderer commits COMPLETE LINES instead of waiting for complete
 * blank-line-delimited blocks, while buffering or sanitizing incomplete
 * Markdown structures so raw syntax is never exposed to the reader.
 *
 * Two ideas do the work together — the line-level split is not sufficient on
 * its own:
 *
 *   1. Split at the last newline, so every finished line can render and only
 *      the partially-typed final line waits. (Splitting at the last blank line
 *      instead would freeze a whole table — which has no blank lines — as raw
 *      text for the entire stream.)
 *
 *   2. Buffer the multi-line structures that a prefix of complete lines can
 *      still leave half-open:
 *        - an unterminated ``` code fence (`withoutOpenCodeFence`)
 *        - a table with its header row but no `|---|` separator yet
 *          (`withoutNascentTable`)
 *      and sanitize the single in-progress line (`cleanStreamTail`).
 *
 * This module is pure (no React) so it can be unit-tested directly — see
 * streamRender.test.mjs.
 */

import { escapeHtml, renderMarkdown } from "./markdown.js";

export function renderStreaming(content) {
  const text = content || "";
  if (!text.trim()) {
    return `<div class="placeholder-text"><span class="spinner"></span>Thinking…</div>`;
  }

  const cut = text.lastIndexOf("\n");
  const committedRaw = cut === -1 ? "" : text.slice(0, cut);
  const tail         = cut === -1 ? text : text.slice(cut + 1);

  // Among the complete lines, hold back any structure that is not yet in a
  // renderable state, so the markdown renderer never spills its raw syntax.
  const committed = commitStableMarkdown(committedRaw);

  // If the buffer ends inside an open code fence, the in-progress line is code,
  // not prose — hide it along with the fence instead of showing it as text.
  const insideFence =
    withoutOpenCodeFence(committedRaw) !== committedRaw || /^\s*```/.test(tail);

  const committedHtml = committed ? renderMarkdown(committed) : "";
  const visibleTail = insideFence ? "" : cleanStreamTail(tail);
  const tailHtml = visibleTail
    ? `<div class="stream-tail">${escapeHtml(visibleTail)}</div>`
    : "";
  return committedHtml + tailHtml;
}

/**
 * Trim the committed prefix down to the largest span that renders cleanly:
 * no open code fence, no header-only table. Order matters — remove an open
 * fence first, since fenced content can contain `|` lines that would
 * otherwise look like a nascent table.
 */
export function commitStableMarkdown(committed) {
  return withoutNascentTable(withoutOpenCodeFence(committed));
}

/**
 * Hold back an unterminated ``` code fence.
 *
 * The renderer only turns a fence into <pre><code> once BOTH its opening and
 * closing ``` lines are present. While the fence is still open, the committed
 * prefix ends with `` ```lang `` and code lines that would render as loose
 * escaped text. Cut the prefix at the last unmatched opening fence so the code
 * block stays hidden until it closes, then renders whole.
 */
export function withoutOpenCodeFence(committed) {
  if (!committed || committed.indexOf("```") === -1) return committed;
  const lines = committed.split("\n");
  let open = false;
  let lastOpenIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*```/.test(lines[i])) {
      if (!open) { open = true; lastOpenIdx = i; }
      else { open = false; }
    }
  }
  if (!open) return committed;                 // every fence is closed
  return lines.slice(0, lastOpenIdx).join("\n"); // hide the open fence
}

/**
 * Hold back a table that has its header row but not its `|---|` separator yet.
 *
 * A markdown table needs both a header row and a separator row to render.
 * While streaming, the header line completes one frame before the separator,
 * so for that window the committed text ends in table rows with no separator —
 * which the renderer would spill as raw pipes. Find the trailing run of
 * `|`-lines and, if none of them is a separator, hide the whole run until the
 * separator arrives. Once it lands, the block renders as a real table.
 */
export function withoutNascentTable(committed) {
  if (!committed || committed.indexOf("|") === -1) return committed;
  const lines = committed.split("\n");
  let i = lines.length;
  while (i > 0 && /^\s*\|/.test(lines[i - 1])) i--;
  const trailing = lines.slice(i);
  if (trailing.length === 0) return committed;               // no trailing table
  if (trailing.some(isTableSeparatorLine)) return committed; // already a table
  return lines.slice(0, i).join("\n");                       // header-only → hide
}

export function isTableSeparatorLine(line) {
  const s = (line || "").trim();
  if (!(s.startsWith("|") && s.endsWith("|"))) return false;
  return /-/.test(s) && /^\|[\s:|-]+\|$/.test(s);
}

/**
 * Sanitize the single in-progress line before showing it.
 *
 * That line is raw markdown, so printing it verbatim leaks syntax: a half-typed
 * separator shows as `|---|`, an unclosed bold shows its `**`. A table row
 * mid-build is pure scaffolding, so it is hidden outright; ordinary prose keeps
 * typing through smoothly with only its inline markers dropped.
 */
export function cleanStreamTail(tail) {
  const t = tail || "";
  if (!t.trim()) return "";
  if (/^\s*\|/.test(t)) return "";            // table row / separator — hide
  return t
    .replace(/^\s*#{1,6}\s*/, "")             // heading marker being typed
    .replace(/\*\*/g, "")                     // unclosed bold
    .replace(/`/g, "");                       // unclosed code span / fence
}
