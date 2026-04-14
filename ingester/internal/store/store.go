// Package store provides PostgreSQL operations for the ingester.
package store

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/lib/pq"

	"newslens-ingester/internal/parser"
)

// Source represents a row from the sources table.
type Source struct {
	ID       string
	Name     string
	URL      string
	Category string
}

// InsertResult tracks the outcome of inserting articles for a single source.
type InsertResult struct {
	Inserted int
	Skipped  int
}

// Store wraps the database connection and provides ingester-specific queries.
type Store struct {
	db *sql.DB
}

// New opens a PostgreSQL connection and verifies it with a ping.
func New(databaseURL string) (*Store, error) {
	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		return nil, fmt.Errorf("opening database: %w", err)
	}

	// Configure connection pool.
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("pinging database: %w", err)
	}

	return &Store{db: db}, nil
}

// Close closes the underlying database connection.
func (s *Store) Close() error {
	return s.db.Close()
}

// GetActiveSources returns all sources where active = true.
func (s *Store) GetActiveSources() ([]Source, error) {
	rows, err := s.db.Query(`
		SELECT id, name, url, category
		FROM sources
		WHERE active = true
		ORDER BY name
	`)
	if err != nil {
		return nil, fmt.Errorf("querying active sources: %w", err)
	}
	defer rows.Close()

	var sources []Source
	for rows.Next() {
		var src Source
		if err := rows.Scan(&src.ID, &src.Name, &src.URL, &src.Category); err != nil {
			return nil, fmt.Errorf("scanning source row: %w", err)
		}
		sources = append(sources, src)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterating source rows: %w", err)
	}
	return sources, nil
}

// InsertArticles inserts parsed articles for a given source, deduplicating by
// external_url using ON CONFLICT DO NOTHING. Returns count of inserted and skipped.
func (s *Store) InsertArticles(sourceID string, articles []parser.Article) (InsertResult, error) {
	if len(articles) == 0 {
		return InsertResult{}, nil
	}

	tx, err := s.db.Begin()
	if err != nil {
		return InsertResult{}, fmt.Errorf("beginning transaction: %w", err)
	}
	defer func() {
		if err != nil {
			if rbErr := tx.Rollback(); rbErr != nil {
				log.Printf("WARN: rollback failed: %v", rbErr)
			}
		}
	}()

	stmt, err := tx.Prepare(`
		INSERT INTO articles (source_id, external_url, title, content, author, published_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (external_url) DO NOTHING
	`)
	if err != nil {
		return InsertResult{}, fmt.Errorf("preparing insert statement: %w", err)
	}
	defer stmt.Close()

	var result InsertResult
	for _, a := range articles {
		if a.URL == "" {
			result.Skipped++
			continue
		}

		// Use content or a fallback if empty.
		content := a.Content
		if content == "" {
			content = a.Title
		}

		var publishedAt *time.Time
		if a.PublishedAt != nil {
			publishedAt = a.PublishedAt
		}

		var author *string
		if a.Author != "" {
			author = &a.Author
		}

		res, err := stmt.Exec(sourceID, a.URL, a.Title, content, author, publishedAt)
		if err != nil {
			log.Printf("WARN: failed to insert article %q: %v", a.URL, err)
			result.Skipped++
			continue
		}

		rowsAffected, _ := res.RowsAffected()
		if rowsAffected > 0 {
			result.Inserted++
		} else {
			result.Skipped++ // duplicate
		}
	}

	if err = tx.Commit(); err != nil {
		return InsertResult{}, fmt.Errorf("committing transaction: %w", err)
	}

	return result, nil
}

// UpdateLastFetched sets last_fetched_at = now() for the given source.
func (s *Store) UpdateLastFetched(sourceID string) error {
	_, err := s.db.Exec(`
		UPDATE sources SET last_fetched_at = now() WHERE id = $1
	`, sourceID)
	if err != nil {
		return fmt.Errorf("updating last_fetched_at for source %s: %w", sourceID, err)
	}
	return nil
}
