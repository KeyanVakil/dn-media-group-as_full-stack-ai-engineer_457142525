// Package config reads environment variables for the ingester service.
package config

import (
	"fmt"
	"os"
	"strconv"
)

// Config holds all ingester configuration values.
type Config struct {
	DatabaseURL string
	Interval    int // seconds between fetch cycles
	Concurrency int // max concurrent feed fetches
}

// Load reads configuration from environment variables with sensible defaults.
func Load() (*Config, error) {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		return nil, fmt.Errorf("DATABASE_URL environment variable is required")
	}

	interval := 900 // default: 15 minutes
	if v := os.Getenv("INGESTER_INTERVAL"); v != "" {
		n, err := strconv.Atoi(v)
		if err != nil {
			return nil, fmt.Errorf("invalid INGESTER_INTERVAL %q: %w", v, err)
		}
		if n < 1 {
			return nil, fmt.Errorf("INGESTER_INTERVAL must be positive, got %d", n)
		}
		interval = n
	}

	concurrency := 10
	if v := os.Getenv("INGESTER_CONCURRENCY"); v != "" {
		n, err := strconv.Atoi(v)
		if err != nil {
			return nil, fmt.Errorf("invalid INGESTER_CONCURRENCY %q: %w", v, err)
		}
		if n < 1 {
			return nil, fmt.Errorf("INGESTER_CONCURRENCY must be positive, got %d", n)
		}
		concurrency = n
	}

	return &Config{
		DatabaseURL: dbURL,
		Interval:    interval,
		Concurrency: concurrency,
	}, nil
}
