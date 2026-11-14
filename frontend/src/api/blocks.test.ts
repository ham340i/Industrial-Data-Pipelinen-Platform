import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { getBlocks } from "./blocks";
import { rowCountBlock, sampleBlock } from "../test/blocks";
import { server } from "../test/server";

const url = "http://127.0.0.1:8000/api/v1/blocks";

it("keeps hidden metadata available and accepts older catalogs without visibility", async () => {
  const legacy = { ...rowCountBlock };
  delete legacy.library_visible;
  server.use(
    http.get(url, () =>
      HttpResponse.json([sampleBlock, rowCountBlock, legacy]),
    ),
  );
  expect(await getBlocks()).toEqual([sampleBlock, rowCountBlock, legacy]);
});

it.each(["false", 0, null])(
  "rejects malformed library visibility %j",
  async (value) => {
    server.use(
      http.get(url, () =>
        HttpResponse.json([{ ...sampleBlock, library_visible: value }]),
      ),
    );
    await expect(getBlocks()).rejects.toMatchObject({
      kind: "invalid-response",
    });
  },
);
