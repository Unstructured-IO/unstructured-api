import { readFileSync } from "node:fs";

import { expect } from "@playwright/test";

import { Given, When, Then, downloadTestData } from "@utic/acceptance-core";

const LAYOUT_PARSER_PAPER_KEY = "unstructured-api/layout-parser-paper-fast.pdf";
const LAYOUT_PARSER_PAPER_SHA256 = "ee85a6a8f4cb095c625a1fdcb4718643acca70e34e3ff20430b5103c0437cf7a";

// hi_res runs can take minutes; "fast" on this two-page PDF returns in about a second.
const PARTITION_TIMEOUT_MS = 120_000;

type Element = { type: string; text: string };

// Read per step rather than at import time, so a hub run that never reaches these steps does
// not need the variables.
function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required env var ${name}`);
  return value;
}

// --- Given ---

Given("an API client with a valid Unstructured API key", async () => {
  requireEnv("TEST_API_KEY");
});

// --- When ---

When(
  "the API client partitions the LayoutParser paper PDF with the {string} strategy",
  async ({ request, ctx }, strategy: string) => {
    const path = await downloadTestData(LAYOUT_PARSER_PAPER_KEY, { sha256: LAYOUT_PARSER_PAPER_SHA256 });
    ctx.response = await request.post(`${requireEnv("TEST_API_URL")}/general/v0/general`, {
      headers: { "unstructured-api-key": requireEnv("TEST_API_KEY") },
      multipart: {
        files: { name: "layout-parser-paper-fast.pdf", mimeType: "application/pdf", buffer: readFileSync(path) },
        strategy,
      },
      timeout: PARTITION_TIMEOUT_MS,
    });
  },
);

// --- Then ---

Then("the partition API returns a list of document elements", async ({ ctx }) => {
  expect(ctx.response!.status(), await ctx.response!.text()).toBe(200);
  ctx.elements = await ctx.response!.json();
  expect(Array.isArray(ctx.elements)).toBe(true);
  expect(ctx.elements!.length).toBeGreaterThan(0);
});

Then("the first element is titled {string}", async ({ ctx }, title: string) => {
  const first = ctx.elements![0] as Element;
  expect(first.type).toBe("Title");
  // The PDF sets "fi" as a ligature, which partitioning keeps; NFKC folds it back to two letters.
  expect(first.text.normalize("NFKC")).toBe(title);
});
