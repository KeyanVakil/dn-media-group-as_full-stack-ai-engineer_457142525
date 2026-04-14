// Package main is the entry point for the NewsLens RSS ingester service.
//
// It periodically fetches RSS/Atom feeds from sources configured in PostgreSQL,
// parses them, deduplicates articles by URL, and stores new articles in the database.
package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"newslens-ingester/internal/config"
	"newslens-ingester/internal/fetcher"
	"newslens-ingester/internal/store"
)

func main() {
	log.SetFlags(log.Ldate | log.Ltime | log.LUTC)
	log.Println("NewsLens Ingester starting...")

	// Load configuration from environment.
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("FATAL: failed to load config: %v", err)
	}
	log.Printf("Config: interval=%ds, concurrency=%d", cfg.Interval, cfg.Concurrency)

	// Connect to PostgreSQL.
	db, err := store.New(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("FATAL: failed to connect to database: %v", err)
	}
	defer db.Close()
	log.Println("Connected to PostgreSQL")

	// Create fetcher.
	f := fetcher.New(cfg.Concurrency)

	// Handle graceful shutdown.
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	// Run the first cycle immediately, then on interval.
	runCycle(db, f)

	ticker := time.NewTicker(time.Duration(cfg.Interval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			runCycle(db, f)
		case sig := <-quit:
			log.Printf("Received signal %v, shutting down...", sig)
			return
		}
	}
}

// runCycle performs a single ingestion cycle: fetch all active sources, parse
// their feeds, and insert new articles into the database.
func runCycle(db *store.Store, f *fetcher.Fetcher) {
	start := time.Now()
	log.Println("=== Starting ingestion cycle ===")

	// 1. Get active sources from the database.
	sources, err := db.GetActiveSources()
	if err != nil {
		log.Printf("ERROR: failed to get active sources: %v", err)
		return
	}
	if len(sources) == 0 {
		log.Println("No active sources found, skipping cycle")
		return
	}
	log.Printf("Found %d active source(s)", len(sources))

	// 2. Fetch all feeds concurrently.
	results := f.FetchAll(sources)

	// 3. Process results: insert articles and update last_fetched_at.
	var totalInserted, totalSkipped, totalErrors int

	for _, res := range results {
		if res.Err != nil {
			log.Printf("ERROR: [%s] %v", res.Source.Name, res.Err)
			totalErrors++
			continue
		}

		// Insert articles with dedup.
		insertResult, err := db.InsertArticles(res.Source.ID, res.Articles)
		if err != nil {
			log.Printf("ERROR: [%s] failed to insert articles: %v", res.Source.Name, err)
			totalErrors++
			continue
		}

		totalInserted += insertResult.Inserted
		totalSkipped += insertResult.Skipped

		if insertResult.Inserted > 0 {
			log.Printf("  [%s] +%d new, %d duplicate/skipped",
				res.Source.Name, insertResult.Inserted, insertResult.Skipped)
		}

		// Update last_fetched_at for this source.
		if err := db.UpdateLastFetched(res.Source.ID); err != nil {
			log.Printf("WARN: [%s] failed to update last_fetched_at: %v", res.Source.Name, err)
		}
	}

	elapsed := time.Since(start).Round(time.Millisecond)
	log.Printf("=== Cycle complete: %d new articles, %d duplicates, %d errors, took %s ===",
		totalInserted, totalSkipped, totalErrors, elapsed)
}
