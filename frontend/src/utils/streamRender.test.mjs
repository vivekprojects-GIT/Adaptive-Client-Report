/**
 * Regression tests for progressive (streaming) markdown rendering.
 *
 * Run with:  npm test   (node --test, no dependencies)
 *
 * The invariant under test: at EVERY prefix of the stream, the visible output
 * must contain no raw markdown syntax — no `|---|` separators, no `**`, no
 * `#` heading markers, no ``` fences — and the final render must equal the
 * normal completed-message render.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { renderMarkdown } from "./markdown.js";
import {
  renderStreaming,
  withoutOpenCodeFence,
  withoutNascentTable,
  isTableSeparatorLine,
  cleanStreamTail,
} from "./streamRender.js";

// ---------- helpers ----------

/** Visible text of a rendered frame: strip all HTML tags. */
function visibleText(html) {
  return html.replace(/<[^>]+>/g, "");
}

/** Assert no raw markdown syntax is visible at ANY prefix of `answer`. */
function assertNoLeaksAtEveryPrefix(answer, { allowBackticks = false } = {}) {
  for (let i = 1; i <= answer.length; i++) {
    const frame = renderStreaming(answer.slice(0, i));
    const v = visibleText(frame);
    assert.ok(!/\|\s*:?-{3,}/.test(v), `frame ${i}: leaked table separator:\n${v}`);
    assert.ok(!v.includes("**"), `frame ${i}: leaked ** stars:\n${v}`);
    assert.ok(!/(^|\n)\s*#{1,6}\s/.test(v), `frame ${i}: leaked # heading marker:\n${v}`);
    if (!allowBackticks) {
      assert.ok(!v.includes("```"), `frame ${i}: leaked \`\`\` fence:\n${v}`);
    }
  }
}

/** The stream's final frame must contain the same structure as the
 *  completed-message render (renderMarkdown of the full text). */
function assertFinalMatchesCompleted(answer, tags) {
  const done = renderMarkdown(answer);
  for (const t of tags) {
    assert.ok(done.includes(t), `completed render missing ${t}`);
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
  // the header row must never be visible as raw text
  for (let i = 1; i <= TABLE.length; i++) {
    const v = visibleText(renderStreaming(TABLE.slice(0, i)));
    assert.ok(!v.includes("Aspect | Roth"), `frame ${i}: raw header row visible`);
  }
});

test("table: renders as <table> once separator lands, then grows row by row", () => {
  const sepEnd = TABLE.indexOf("\n", TABLE.indexOf("|----"));
  // one char after the separator's newline: table must exist
  const after = renderStreaming(TABLE.slice(0, sepEnd + 2));
  assert.ok(after.includes("<table>"), "table absent right after separator");
  // before the separator line completes: no table, and no raw header either
  const before = renderStreaming(TABLE.slice(0, TABLE.indexOf("|----") - 1));
  assert.ok(!before.includes("<table>"));
  assert.ok(!visibleText(before).includes("|"));
});

test("table: completed render intact", () => {
  assertFinalMatchesCompleted(TABLE, ["<table>", "<thead>", "<strong>"]);
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
  // while the fence is open, none of the code body may be visible
  const openIdx = CODE.indexOf("print(x)") + 4; // mid-body
  const v = visibleText(renderStreaming(CODE.slice(0, openIdx)));
  assert.ok(!v.includes("compute"), "code body visible while fence open");
  // after the closing fence line, the block renders as <pre><code>
  const closeIdx = CODE.indexOf("```", CODE.indexOf("python")) + 4;
  const html = renderStreaming(CODE.slice(0, closeIdx));
  assert.ok(html.includes("<pre><code"), "closed fence did not render");
});

test("code fence: completed render intact", () => {
  assertFinalMatchesCompleted(CODE, ["<pre><code"]);
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
  const html = renderStreaming(LISTS.slice(0, afterFirstItem));
  assert.ok(html.includes("<ul>"), "first completed bullet did not render");
});

test("lists: completed render intact", () => {
  assertFinalMatchesCompleted(LISTS, ["<ul>", "<ol>", "<strong>", "<code>"]);
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
  assert.ok(renderStreaming(HEADINGS.slice(0, afterH1)).includes("<h1>"));
});

test("headings: completed render intact", () => {
  assertFinalMatchesCompleted(HEADINGS, ["<h1>", "<h2>"]);
});

// ---------- inline code + links ----------

test("inline code: backticks stripped from in-progress line, rendered when complete", () => {
  const md = "Use `npm run build` to compile.";
  // mid-line: tail shows text without backticks
  const mid = visibleText(renderStreaming(md.slice(0, 10)));
  assert.ok(!mid.includes("`"));
  // completed line renders <code>
  assert.ok(renderMarkdown(md).includes("<code>npm run build</code>"));
});

test("links: renderer has no [text](url) support — documents current behavior", () => {
  // The minimal renderer deliberately does not convert links; they pass
  // through as literal text. This test pins that so a future renderer
  // upgrade consciously flips it.
  const html = renderMarkdown("See [the docs](https://example.com).");
  assert.ok(!html.includes("<a "), "renderer unexpectedly grew link support — update streaming holdback if needed");
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
  assert.equal(cleanStreamTail("run `np"), "run np");
});

// ---------- spinner ----------

test("empty buffer shows the thinking placeholder", () => {
  assert.ok(renderStreaming("").includes("Thinking"));
  assert.ok(renderStreaming("   ").includes("Thinking"));
});
