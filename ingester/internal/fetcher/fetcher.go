// Package fetcher provides concurrent HTTP feed fetching with a semaphore pattern.
package fetcher

import (
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"newslens-ingester/internal/parser"
	"newslens-ingester/internal/store"
)

const httpTimeout = 10 * time.Second

// FeedResult holds the outcome of fetching and parsing a single feed.
type FeedResult struct {
	Source   store.Source
	Articles []parser.Article
	Err      error
}

// Fetcher fetches RSS/Atom feeds concurrently with a configurable concurrency limit.
type Fetcher struct {
	client      *http.Client
	concurrency int
}

// New creates a Fetcher with the given concurrency limit.
func New(concurrency int) *Fetcher {
	return &Fetcher{
		client: &http.Client{
			Timeout: httpTimeout,
		},
		concurrency: concurrency,
	}
}

// FetchAll fetches all given sources concurrently, respecting the concurrency limit.
// It returns a result for every source (with Err set on failure).
func (f *Fetcher) FetchAll(sources []store.Source) []FeedResult {
	results := make([]FeedResult, len(sources))
	sem := make(chan struct{}, f.concurrency)
	var wg sync.WaitGroup

	for i, src := range sources {
		wg.Add(1)
		go func(idx int, source store.Source) {
			defer wg.Done()

			sem <- struct{}{}        // acquire semaphore slot
			defer func() { <-sem }() // release

			articles, err := f.fetchOne(source)
			results[idx] = FeedResult{
				Source:   source,
				Articles: articles,
				Err:      err,
			}
		}(i, src)
	}

	wg.Wait()
	return results
}

// fetchOne fetches and parses a single feed.
func (f *Fetcher) fetchOne(source store.Source) ([]parser.Article, error) {
	req, err := http.NewRequest("GET", source.URL, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}
	req.Header.Set("User-Agent", "NewsLens-Ingester/1.0")
	req.Header.Set("Accept", "application/rss+xml, application/atom+xml, application/xml, text/xml")

	resp, err := f.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetching %s: %w", source.URL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status %d for %s", resp.StatusCode, source.URL)
	}

	articles, err := parser.Parse(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("parsing feed from %s: %w", source.URL, err)
	}

	log.Printf("  [%s] parsed %d articles", source.Name, len(articles))
	return articles, nil
}
