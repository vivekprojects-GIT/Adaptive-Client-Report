/**
 * Regression tests for progressive (streaming) markdown rendering.
 *
 * Run with:  npm test   (node --test, no extra dev deps)
 *
 * The invariant under test: at EVERY prefix of the stream, the visible output
 * must contain no raw markdown syntax — no `|---|` separators, no `**`, no
 * `#` heading markers, no ``` fences — and the final frame must contain the
 * same structure as the completed-message render.
 *
 * Frames are rendered through the REAL production parser (react-markdown +
 * remark-gfm, via react-dom/server), so these tests exercise exactly what the
 * browser shows, not a simulation.
 */

import test from "node:test";
import assert from "node:assert/strict";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  splitStreaming,
  withoutOpenCodeFence,
  withoutNascentTable,
  isTableSeparatorLine,
  cleanStreamTail,
} from "./streamRender.js";

// ---------- helpers ----------

/** Render markdown exactly like Message.jsx's <Markdown> does. */
function renderMd(md) {
  return renderToStaticMarkup(
    React.createElement(ReactMarkdown, { remarkPlugins: [remarkGfm] }, md),
  );
}

/** One streaming frame as HTML: committed markdown + sanitized tail. */
function renderFrame(buf) {
  const { thinking, committed, tail } = splitStreaming(buf);
  if (thinking) return "<thinking/>";
  return (
    (committed ? renderMd(committed) : "") +
    (tail ? `<div class="stream-tail">${tail}</div>` : "")
  );
}

/** Visible text of a rendered frame: strip all HTML tags. */
function visibleText(html) {
  return html.replace(/<[^>]+>/g, "");
}

/** Assert no raw markdown syntax is visible at ANY prefix of `answer`.
 *  Rendered code blocks are exempt: characters like ** or | inside
 *  <pre><code> are literal code content, not leaked markdown syntax.
 *  (The old regex renderer even bolded text inside code blocks — a bug
 *  react-markdown fixes, which is why the exemption is needed now.) */
function assertNoLeaksAtEveryPrefix(answer) {
  for (let i = 1; i <= answer.length; i++) {
    const frame = renderFrame(answer.slice(0, i))
      .replace(/<pre>[\s\S]*?<\/pre>/g, "");
    const v = visibleText(frame);
    assert.ok(!/\|\s*:?-{3,}/.test(v), `frame ${i}: leaked table separator:\n${v}`);
    assert.ok(!v.includes("**"), `frame ${i}: leaked ** stars:\n${v}`);
    assert.ok(!/(^|\n)\s*#{1,6}\s/.test(v), `frame ${i}: leaked # heading marker:\n${v}`);
    assert.ok(!v.includes("```"), `frame ${i}: leaked \`\`\` fence:\n${v}`);
  }
}

/** The completed-message render must contain the expected structural tags. */
function assertFinalHas(answer, tags) {
  const done = renderMd(answer);
  for (const t of tags) {
    assert.ok(done.includes(t), `completed render missing ${t}:\n${done}`);
  }
}

// ---------- tables ----------

const TABLE = [
  "Here is the comparison.",
  "",
  "| Aspect | Roth IRA | Traditional IRA |",
  "|--------|----------|-----------------|",
  "| **Tax now** | After-tax | Pre-tax |",
  "| Withdrawals | Tax-free | Taxed |",
].join("\n");

test("table: no raw pipes/stars at any prefix", () => {
  assertNoLeaksAtEveryPrefix(TABLE);
  for (let i = 1; i <= TABLE.length; i++) {
    const v = visibleText(renderFrame(TABLE.slice(0, i)));
    assert.ok(!v.includes("Aspect | Roth"), `frame ${i}: raw header row visible`);
  }
});

test("table: renders as <table> once separator lands, then grows row by row", () => {
  const sepEnd = TABLE.indexOf("\n", TABLE.indexOf("|----"));
  const after = renderFrame(TABLE.slice(0, sepEnd + 2));
  assert.ok(after.includes("<table>"), "table absent right after separator");
  const before = renderFrame(TABLE.slice(0, TABLE.indexOf("|----") - 1));
  assert.ok(!before.includes("<table>"));
  assert.ok(!visibleText(before).includes("|"));
});

test("table: completed render intact", () => {
  assertFinalHas(TABLE, ["<table>", "<thead>", "<strong>"]);
});

// ---------- code fences ----------

const CODE = [
  "Use this snippet:",
  "",
  "```python",
  "x = compute(1)   # comment with **stars** and |pipes|",
  "print(x)",
  "```",
  "",
  "Done.",
].join("\n");

test("code fence: fence and body hidden until the fence closes", () => {
  assertNoLeaksAtEveryPrefix(CODE);
  const openIdx = CODE.indexOf("print(x)") + 4; // mid-body
  const v = visibleText(renderFrame(CODE.slice(0, openIdx)));
  assert.ok(!v.includes("compute"), "code body visible while fence open");
  const closeIdx = CODE.indexOf("```", CODE.indexOf("python")) + 4;
  const html = renderFrame(CODE.slice(0, closeIdx));
  assert.ok(html.includes("<pre>"), "closed fence did not render");
});

test("code fence: completed render intact", () => {
  assertFinalHas(CODE, ["<pre>", "<code"]);
});

// ---------- lists ----------

const LISTS = [
  "Two options:",
  "",
  "- **Roth**: after-tax money",
  "- **Traditional**: pre-tax money",
  "",
  "Steps:",
  "",
  "1. Open the account",
  "2. Fund it with `cash`",
  "3. Invest",
].join("\n");

test("lists: no raw markers at any prefix; items appear as lines complete", () => {
  assertNoLeaksAtEveryPrefix(LISTS);
  const afterFirstItem = LISTS.indexOf("money") + 6;
  const html = renderFrame(LISTS.slice(0, afterFirstItem));
  assert.ok(html.includes("<ul>"), "first completed bullet did not render");
});

test("lists: completed render intact", () => {
  assertFinalHas(LISTS, ["<ul>", "<ol>", "<strong>", "<code>"]);
});

// ---------- headings ----------

const HEADINGS = [
  "# Title",
  "",
  "## Section **one**",
  "",
  "Body text here.",
].join("\n");

test("headings: marker never visible; renders as <h*> when line completes", () => {
  assertNoLeaksAtEveryPrefix(HEADINGS);
  const afterH1 = HEADINGS.indexOf("\n") + 2;
  assert.ok(renderFrame(HEADINGS.slice(0, afterH1)).includes("<h1>"));
});

test("headings: completed render intact", () => {
  assertFinalHas(HEADINGS, ["<h1>", "<h2>"]);
});

// ---------- previously-unsupported syntax, now real ----------

test("links render as real <a> anchors", () => {
  assertFinalHas("See [the docs](https://example.com) for more.", ['<a href="https://example.com"']);
});

test("blockquotes render as <blockquote>", () => {
  assertFinalHas("> Price is what you pay.\n\nWisdom.", ["<blockquote>"]);
});

test("horizontal rules render as <hr>", () => {
  assertFinalHas("Part one.\n\n---\n\nPart two.", ["<hr"]);
});

test("strikethrough renders as <del> (GFM)", () => {
  assertFinalHas("This is ~~wrong~~ right.", ["<del>"]);
});

test("task lists render as checkboxes (GFM)", () => {
  assertFinalHas("- [ ] Choose a broker\n- [x] Open account", ['type="checkbox"']);
});

test("inline code: backticks stripped mid-line, rendered when complete", () => {
  const mid = visibleText(renderFrame("Use `npm ru"));
  assert.ok(!mid.includes("`"));
  assertFinalHas("Use `npm run build` to compile.", ["<code>npm run build</code>"]);
});

test("single-star italic: no lone star flash on the in-progress line", () => {
  const v = visibleText(renderFrame("emphasis on *ke"));
  assert.ok(!v.includes("*"), `lone star visible: ${v}`);
  assertFinalHas("emphasis on *key terms* here", ["<em>"]);
});

// ---------- unit tests for the helpers ----------

test("withoutOpenCodeFence: hides only an unterminated fence", () => {
  assert.equal(withoutOpenCodeFence("a\n```js\ncode"), "a");
  assert.equal(withoutOpenCodeFence("a\n```js\ncode\n```"), "a\n```js\ncode\n```");
  assert.equal(withoutOpenCodeFence("no fences"), "no fences");
});

test("withoutNascentTable: hides header-only, keeps valid table", () => {
  assert.equal(withoutNascentTable("x\n| a | b |"), "x");
  const valid = "x\n| a | b |\n|---|---|";
  assert.equal(withoutNascentTable(valid), valid);
  assert.equal(withoutNascentTable("plain"), "plain");
});

test("isTableSeparatorLine", () => {
  assert.ok(isTableSeparatorLine("|---|---|"));
  assert.ok(isTableSeparatorLine("| :--- | ---: |"));
  assert.ok(!isTableSeparatorLine("| a | b |"));
  assert.ok(!isTableSeparatorLine("---"));
});

test("cleanStreamTail: hides table rows, strips inline markers", () => {
  assert.equal(cleanStreamTail("| a | b"), "");
  assert.equal(cleanStreamTail("## Head"), "Head");
  assert.equal(cleanStreamTail("some **bo"), "some bo");
  assert.equal(cleanStreamTail("a *wor"), "a wor");
  assert.equal(cleanStreamTail("> quo"), "quo");
  assert.equal(cleanStreamTail("run `np"), "run np");
});

// ---------- spinner ----------

test("empty buffer reports thinking state", () => {
  assert.equal(splitStreaming("").thinking, true);
  assert.equal(splitStreaming("   ").thinking, true);
  assert.equal(splitStreaming("hi").thinking, false);
});
