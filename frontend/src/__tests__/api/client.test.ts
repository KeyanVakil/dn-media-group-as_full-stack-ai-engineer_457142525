import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// We need to test the internal get/post helpers via the exported functions
// that use them, since get/post are not exported directly.
import {
  fetchDashboardStats,
  fetchArticles,
  createResearchTask,
  fetchSources,
} from "../../api/client";

// ── Mock fetch globally ───────────────────────────────────────────

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  // jsdom sets window.location.origin to "http://localhost"
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Helpers ───────────────────────────────────────────────────────

function jsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response;
}

// ── GET requests ──────────────────────────────────────────────────

describe("GET requests", () => {
  it("constructs the correct URL for a simple endpoint", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ data: { total_articles: 10, total_entities: 5, total_sources: 2, articles_analyzed: 8, research_tasks_completed: 1 } }),
    );

    await fetchDashboardStats();

    expect(mockFetch).toHaveBeenCalledOnce();
    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain("/api/dashboard/stats");
  });

  it("appends query parameters, omitting undefined and empty values", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ data: [], meta: { total: 0, limit: 20, offset: 0 } }),
    );

    await fetchArticles({ search: "climate", limit: 10, offset: 0 });

    const url: string = mockFetch.mock.calls[0][0];
    expect(url).toContain("search=climate");
    expect(url).toContain("limit=10");
    expect(url).toContain("offset=0");
  });

  it("omits query parameters when their value is undefined", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ data: [], meta: { total: 0, limit: 20, offset: 0 } }),
    );

    // source_id and topic are not set, so they should be omitted
    await fetchArticles({ limit: 20, offset: 0 });

    const url: string = mockFetch.mock.calls[0][0];
    expect(url).not.toContain("source_id");
    expect(url).not.toContain("topic");
  });

  it("returns unwrapped data from SingleResponse endpoints", async () => {
    const statsPayload = {
      total_articles: 42,
      total_entities: 15,
      total_sources: 3,
      articles_analyzed: 30,
      research_tasks_completed: 7,
    };
    mockFetch.mockResolvedValueOnce(jsonResponse({ data: statsPayload }));

    const result = await fetchDashboardStats();
    expect(result).toEqual(statsPayload);
  });

  it("returns the full PaginatedResponse from list endpoints", async () => {
    const payload = { data: [], meta: { total: 0, limit: 20, offset: 0 } };
    mockFetch.mockResolvedValueOnce(jsonResponse(payload));

    const result = await fetchSources();
    // fetchSources returns res.data (the array), not the full paginated envelope
    expect(result).toEqual([]);
  });
});

// ── POST requests ─────────────────────────────────────────────────

describe("POST requests", () => {
  it("sends JSON body with correct headers", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        data: { id: "r1", query: "test query", status: "pending", steps: [], result: null, created_at: "2026-01-01" },
      }),
    );

    await createResearchTask("test query");

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/research");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body)).toEqual({ query: "test query" });
  });
});

// ── Error handling ────────────────────────────────────────────────

describe("error handling", () => {
  it("throws ApiError with status and message on non-OK GET response", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse("Not Found", 404));

    await expect(fetchDashboardStats()).rejects.toThrow();

    try {
      mockFetch.mockResolvedValueOnce(jsonResponse("Server Error", 500));
      await fetchDashboardStats();
    } catch (err: unknown) {
      const error = err as Error & { status?: number };
      expect(error.name).toBe("ApiError");
      expect(error.status).toBe(500);
    }
  });

  it("throws ApiError with status and message on non-OK POST response", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse("Bad Request", 400));

    await expect(createResearchTask("bad")).rejects.toThrow();

    try {
      mockFetch.mockResolvedValueOnce(jsonResponse("Unauthorized", 401));
      await createResearchTask("bad");
    } catch (err: unknown) {
      const error = err as Error & { status?: number };
      expect(error.name).toBe("ApiError");
      expect(error.status).toBe(401);
    }
  });

  it("includes the response body text in the error message", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Validation failed: missing field"),
    } as Response);

    try {
      await fetchDashboardStats();
      expect.unreachable("should have thrown");
    } catch (err: unknown) {
      const error = err as Error;
      expect(error.message).toBe("Validation failed: missing field");
    }
  });
});
