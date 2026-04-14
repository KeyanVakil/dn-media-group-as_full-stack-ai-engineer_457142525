package fetcher

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"newslens-ingester/internal/store"
)

// validRSSFeed returns an RSS feed with N items for testing.
func validRSSFeed(n int) string {
	var b strings.Builder
	b.WriteString(`<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>`)
	for i := 1; i <= n; i++ {
		fmt.Fprintf(&b, `
    <item>
      <title>Article %d</title>
      <link>https://example.com/article/%d</link>
      <description>Content of article %d.</description>
      <pubDate>Mon, 14 Apr 2025 10:%02d:00 +0000</pubDate>
    </item>`, i, i, i, i)
	}
	b.WriteString(`
  </channel>
</rss>`)
	return b.String()
}

func newTestServer(handler http.HandlerFunc) *httptest.Server {
	return httptest.NewServer(handler)
}

func TestFetchSingleValidFeed(t *testing.T) {
	ts := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/rss+xml")
		fmt.Fprint(w, validRSSFeed(3))
	})
	defer ts.Close()

	f := New(5)
	sources := []store.Source{
		{ID: "src-1", Name: "Test Source", URL: ts.URL, Category: "tech"},
	}

	results := f.FetchAll(sources)

	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	r := results[0]
	if r.Err != nil {
		t.Fatalf("unexpected error: %v", r.Err)
	}
	if r.Source.ID != "src-1" {
		t.Errorf("Source.ID = %q, want %q", r.Source.ID, "src-1")
	}
	if len(r.Articles) != 3 {
		t.Errorf("expected 3 articles, got %d", len(r.Articles))
	}

	// Spot-check first article fields.
	if r.Articles[0].Title != "Article 1" {
		t.Errorf("first article title = %q, want %q", r.Articles[0].Title, "Article 1")
	}
	if r.Articles[0].URL != "https://example.com/article/1" {
		t.Errorf("first article URL = %q, want %q", r.Articles[0].URL, "https://example.com/article/1")
	}
}

func TestFetchMultipleFeedsConcurrently(t *testing.T) {
	feedCount := 5
	servers := make([]*httptest.Server, feedCount)
	sources := make([]store.Source, feedCount)

	for i := 0; i < feedCount; i++ {
		itemCount := i + 1 // different number of items per feed
		ts := newTestServer(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/rss+xml")
			fmt.Fprint(w, validRSSFeed(itemCount))
		})
		servers[i] = ts
		sources[i] = store.Source{
			ID:       fmt.Sprintf("src-%d", i),
			Name:     fmt.Sprintf("Feed %d", i),
			URL:      ts.URL,
			Category: "tech",
		}
	}
	defer func() {
		for _, s := range servers {
			s.Close()
		}
	}()

	f := New(3) // concurrency = 3 for 5 feeds
	results := f.FetchAll(sources)

	if len(results) != feedCount {
		t.Fatalf("expected %d results, got %d", feedCount, len(results))
	}

	for i, r := range results {
		if r.Err != nil {
			t.Errorf("result[%d] unexpected error: %v", i, r.Err)
			continue
		}
		wantCount := i + 1
		if len(r.Articles) != wantCount {
			t.Errorf("result[%d] expected %d articles, got %d", i, wantCount, len(r.Articles))
		}
	}
}

func TestFetchHandlesServerError(t *testing.T) {
	// One server returns 500, the other is healthy.
	failServer := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprint(w, "internal server error")
	})
	defer failServer.Close()

	goodServer := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/rss+xml")
		fmt.Fprint(w, validRSSFeed(2))
	})
	defer goodServer.Close()

	sources := []store.Source{
		{ID: "fail", Name: "Failing Feed", URL: failServer.URL, Category: "tech"},
		{ID: "good", Name: "Good Feed", URL: goodServer.URL, Category: "tech"},
	}

	f := New(5)
	results := f.FetchAll(sources)

	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}

	// The failing feed should have an error.
	failResult := results[0]
	if failResult.Err == nil {
		t.Error("expected error for 500-status feed, got nil")
	}
	if failResult.Source.ID != "fail" {
		t.Errorf("expected source ID 'fail', got %q", failResult.Source.ID)
	}
	if !strings.Contains(failResult.Err.Error(), "500") {
		t.Errorf("error should mention status 500, got: %v", failResult.Err)
	}

	// The good feed should succeed despite the other failing.
	goodResult := results[1]
	if goodResult.Err != nil {
		t.Errorf("unexpected error for good feed: %v", goodResult.Err)
	}
	if len(goodResult.Articles) != 2 {
		t.Errorf("expected 2 articles from good feed, got %d", len(goodResult.Articles))
	}
}

func TestFetchHandlesTimeout(t *testing.T) {
	// Create a server that delays longer than the client timeout.
	slowServer := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(3 * time.Second) // longer than our custom short timeout
		w.Header().Set("Content-Type", "application/rss+xml")
		fmt.Fprint(w, validRSSFeed(1))
	})
	defer slowServer.Close()

	// Use a fetcher with a short custom timeout to keep the test fast.
	f := &Fetcher{
		client: &http.Client{
			Timeout: 500 * time.Millisecond,
		},
		concurrency: 5,
	}

	sources := []store.Source{
		{ID: "slow", Name: "Slow Feed", URL: slowServer.URL, Category: "tech"},
	}

	results := f.FetchAll(sources)

	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].Err == nil {
		t.Fatal("expected timeout error, got nil")
	}
	// The error message should indicate a timeout or context deadline.
	errStr := results[0].Err.Error()
	if !strings.Contains(errStr, "Client.Timeout") &&
		!strings.Contains(errStr, "deadline exceeded") &&
		!strings.Contains(errStr, "context") &&
		!strings.Contains(errStr, "timeout") {
		t.Errorf("expected timeout-related error, got: %v", results[0].Err)
	}
}

func TestFetchConcurrencyLimitRespected(t *testing.T) {
	const totalFeeds = 10
	const maxConcurrency = 3

	// Track the peak number of in-flight requests.
	var inflight int64
	var peak int64

	ts := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		current := atomic.AddInt64(&inflight, 1)
		defer atomic.AddInt64(&inflight, -1)

		// Atomically update peak.
		for {
			old := atomic.LoadInt64(&peak)
			if current <= old {
				break
			}
			if atomic.CompareAndSwapInt64(&peak, old, current) {
				break
			}
		}

		// Small delay so requests actually overlap.
		time.Sleep(50 * time.Millisecond)

		w.Header().Set("Content-Type", "application/rss+xml")
		fmt.Fprint(w, validRSSFeed(1))
	})
	defer ts.Close()

	sources := make([]store.Source, totalFeeds)
	for i := 0; i < totalFeeds; i++ {
		sources[i] = store.Source{
			ID:       fmt.Sprintf("src-%d", i),
			Name:     fmt.Sprintf("Feed %d", i),
			URL:      ts.URL,
			Category: "tech",
		}
	}

	f := New(maxConcurrency)
	results := f.FetchAll(sources)

	// All results should come back.
	if len(results) != totalFeeds {
		t.Fatalf("expected %d results, got %d", totalFeeds, len(results))
	}
	for i, r := range results {
		if r.Err != nil {
			t.Errorf("result[%d] unexpected error: %v", i, r.Err)
		}
	}

	// Peak concurrency should not exceed the limit.
	observedPeak := atomic.LoadInt64(&peak)
	if observedPeak > int64(maxConcurrency) {
		t.Errorf("peak concurrency = %d, exceeds limit %d", observedPeak, maxConcurrency)
	}

	// Sanity: should have seen some concurrency (at least 2 if the test machine allows).
	if observedPeak < 1 {
		t.Error("peak concurrency was 0, something went wrong")
	}
}

func TestFetchUserAgentHeader(t *testing.T) {
	var receivedUA string
	ts := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		receivedUA = r.Header.Get("User-Agent")
		w.Header().Set("Content-Type", "application/rss+xml")
		fmt.Fprint(w, validRSSFeed(1))
	})
	defer ts.Close()

	f := New(1)
	sources := []store.Source{
		{ID: "ua-test", Name: "UA Test", URL: ts.URL, Category: "tech"},
	}
	results := f.FetchAll(sources)

	if results[0].Err != nil {
		t.Fatalf("unexpected error: %v", results[0].Err)
	}
	if receivedUA != "NewsLens-Ingester/1.0" {
		t.Errorf("User-Agent = %q, want %q", receivedUA, "NewsLens-Ingester/1.0")
	}
}

func TestFetchInvalidURL(t *testing.T) {
	f := New(1)
	sources := []store.Source{
		{ID: "bad", Name: "Bad URL", URL: "http://localhost:0/does-not-exist", Category: "tech"},
	}
	results := f.FetchAll(sources)

	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].Err == nil {
		t.Error("expected error for unreachable URL, got nil")
	}
}

func TestFetchEmptySourceList(t *testing.T) {
	f := New(5)
	results := f.FetchAll(nil)
	if len(results) != 0 {
		t.Errorf("expected 0 results for nil sources, got %d", len(results))
	}

	results = f.FetchAll([]store.Source{})
	if len(results) != 0 {
		t.Errorf("expected 0 results for empty sources, got %d", len(results))
	}
}
