import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("api client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("posts compile requests and returns the body", async () => {
    const body = { spec: null, questions: ["Which source?"] };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const result = await api.compile("watch my stuff");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/agents/compile",
      expect.objectContaining({ method: "POST" }),
    );
    expect(result.questions).toEqual(["Which source?"]);
  });

  it("throws a readable error on non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "agent not found" }), { status: 404 }),
    );
    await expect(api.runNow(999)).rejects.toThrow(/404/);
  });
});
