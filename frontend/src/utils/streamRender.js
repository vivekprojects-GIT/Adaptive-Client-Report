/**
 * Progressive Markdown display for a reply that is still streaming.
 *
 * The UI commits COMPLETE LINES instead of waiting for complete
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
 * This module is TEXT-LEVEL and renderer-agnostic: it decides WHAT markdown is
 * safe to parse right now, not how to turn it into HTML. The actual rendering
 * is react-markdown (see Message.jsx), so the split survives any renderer
 * upgrade. Pure (no React) so it unit-tests directly — see
 * streamRender.test.mjs.
 */

/**
 * Split the stream buffer into what may render now vs. what must wait.
 *
 * Returns:
 *   { thinking: true }                      — buffer is still empty
 *   { thinking: false, committed, tail }    — `committed` is markdown that is
 *     safe to hand to the parser; `tail` is the sanitized plain-text remnant
 *     of the line still being typed ("" when there is nothing showable).
 */
export function splitStreaming(content) {
  const text = content || "";
  if (!text.trim()) {
    return { thinking: true, committed: "", tail: "", liveCode: null };
  }

  const cut = text.lastIndexOf("\n");
  const committedRaw = cut === -1 ? "" : text.slice(0, cut);
  const tailRaw      = cut === -1 ? text : text.slice(cut + 1);
  const liveCode = extractOpenCodeFence(committedRaw, tailRaw);
  const committedSource = liveCode ? liveCode.before : committedRaw;

  // Among the complete lines, hold back any structure that is not yet in a
  // renderable state, so the parser never receives half-open syntax.
  const committed = commitStableMarkdown(committedSource);

  // If the buffer ends inside an open code fence, the in-progress line is code,
  // not prose — hide it along with the fence instead of showing it as text.
  const startsFence = /^\s*```/.test(tailRaw);

  const tail = liveCode || startsFence ? "" : cleanStreamTail(tailRaw);
  return {
    thinking: false,
    committed,
    tail,
    liveCode: liveCode ? {
      language: liveCode.language,
      code: liveCode.code,
    } : null,
  };
}

/**
 * Trim the committed prefix down to the largest span that renders cleanly:
 * no open code fence, no header-only table. Order matters — remove an open
 * fence first, since fenced content can contain `|` lines that would
 * otherwise look like a nascent table.
 */
export function commitStableMarkdown(committed) {
  return withoutNascentTable(
    repairMarkdownTables(
      withoutOpenMathBlock(
        withoutOpenCodeFence(committed),
      ),
    ),
  );
}

export function extractOpenCodeFence(committed, tail = "") {
  if (!committed || committed.indexOf("```") === -1) return null;
  const lines = committed.split("\n");
  let open = false;
  let lastOpenIdx = -1;
  let language = "";

  for (let i = 0; i < lines.length; i++) {
    const fence = lines[i].match(/^\s*```(.*)$/);
    if (!fence) continue;
    if (!open) {
      open = true;
      lastOpenIdx = i;
      language = (fence[1] || "").trim().split(/\s+/)[0] || "";
    } else {
      open = false;
      lastOpenIdx = -1;
      language = "";
    }
  }

  if (!open || lastOpenIdx < 0) return null;
  const codeLines = lines.slice(lastOpenIdx + 1);
  const code = tail ? [...codeLines, tail].join("\n") : codeLines.join("\n");
  return {
    before: lines.slice(0, lastOpenIdx).join("\n"),
    language,
    code,
  };
}

/**
 * Hold back an unterminated ``` code fence.
 *
 * A fence renders as a code block only once BOTH its opening and closing ```
 * lines are present. While the fence is still open, the committed prefix ends
 * with `` ```lang `` and code lines that would render as loose text. Cut the
 * prefix at the last unmatched opening fence so the code block stays hidden
 * until it closes, then renders whole.
 */
export function withoutOpenCodeFence(committed) {
  const open = extractOpenCodeFence(committed);
  return open ? open.before : committed;
}

export function withoutOpenMathBlock(committed) {
  if (!committed || committed.indexOf("$$") === -1) return committed;
  const lines = committed.split("\n");
  let open = false;
  let lastOpenIdx = -1;

  for (let i = 0; i < lines.length; i++) {
    if (/^\s*\$\$\s*$/.test(lines[i])) {
      if (!open) { open = true; lastOpenIdx = i; }
      else { open = false; }
    }
  }

  return open ? lines.slice(0, lastOpenIdx).join("\n") : committed;
}

export function repairMarkdownTables(markdown) {
  if (!markdown || markdown.indexOf("|") === -1) return markdown;
  const lines = markdown.split("\n");
  const out = [];
  let i = 0;
  let inFence = false;

  while (i < lines.length) {
    if (/^\s*```/.test(lines[i])) {
      inFence = !inFence;
      out.push(lines[i++]);
      continue;
    }

    if (inFence || !isPipeTableLine(lines[i])) {
      out.push(lines[i++]);
      continue;
    }

    const start = i;
    while (i < lines.length && isPipeTableLine(lines[i])) i++;
    const block = lines.slice(start, i);
    const hasSeparator = block.some(isTableSeparatorLine);
    if (!hasSeparator && canRepairTableBlock(block)) {
      out.push(block[0], separatorForTableLine(block[0]), ...block.slice(1));
    } else {
      out.push(...block);
    }
  }

  return out.join("\n");
}

export function isPipeTableLine(line) {
  const s = (line || "").trim();
  return s.startsWith("|") && s.endsWith("|") && splitTableCells(s).length >= 2;
}

function canRepairTableBlock(block) {
  if (block.length < 2) return false;
  const count = splitTableCells(block[0]).length;
  return count >= 2 && block.every((line) => splitTableCells(line).length === count);
}

function separatorForTableLine(line) {
  const count = splitTableCells(line).length;
  return `|${Array.from({ length: count }, () => "---").join("|")}|`;
}

function splitTableCells(line) {
  const s = (line || "").trim().replace(/^\|/, "").replace(/\|$/, "");
  return s.split("|").map((cell) => cell.trim());
}

/**
 * Hold back a table that has its header row but not its `|---|` separator yet.
 *
 * A markdown table needs both a header row and a separator row to render.
 * While streaming, the header line completes one frame before the separator,
 * so for that window the committed text ends in table rows with no separator —
 * which would show as raw pipes. Find the trailing run of `|`-lines and, if
 * none of them is a separator, hide the whole run until the separator arrives.
 * Once it lands, the block renders as a real table.
 */
export function withoutNascentTable(committed) {
  if (!committed || committed.indexOf("|") === -1) return committed;
  const lines = committed.split("\n");
  let i = lines.length;
  while (i > 0 && isPipeTableLine(lines[i - 1])) i--;
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
 * typing through smoothly with only its (possibly unclosed) inline markers
 * dropped.
 */
export function cleanStreamTail(tail) {
  const t = tail || "";
  if (!t.trim()) return "";
  if (/^\s*\|/.test(t)) return "";            // table row / separator — hide
  return t
    .replace(/^\s*#{1,6}\s*/, "")             // heading marker being typed
    .replace(/^\s*>\s?/, "")                  // blockquote marker being typed
    .replace(/\$\$/g, "")                     // display math delimiter
    .replace(/(^|[^\\])\$(?=\S)(?!\d)/g, "$1") // inline math opener, not money
    .replace(/\*\*/g, "")                     // unclosed bold
    .replace(/(^|[^*])\*(?!\*)/g, "$1")       // unclosed single-star italic
    .replace(/~~/g, "")                       // unclosed strikethrough
    .replace(/`/g, "");                       // unclosed code span / fence
}
