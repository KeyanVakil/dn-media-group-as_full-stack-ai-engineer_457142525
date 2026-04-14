// Package parser handles RSS 2.0 and Atom XML feed parsing.
package parser

import (
	"encoding/xml"
	"fmt"
	"io"
	"strings"
	"time"
)

// Article represents a single parsed feed item.
type Article struct {
	Title       string
	URL         string
	PublishedAt *time.Time
	Content     string
	Author      string
}

// --- RSS 2.0 structures ---

type rssRoot struct {
	XMLName xml.Name   `xml:"rss"`
	Channel rssChannel `xml:"channel"`
}

type rssChannel struct {
	Items []rssItem `xml:"item"`
}

type rssItem struct {
	Title       string `xml:"title"`
	Link        string `xml:"link"`
	Description string `xml:"description"`
	PubDate     string `xml:"pubDate"`
	Author      string `xml:"author"`
	Creator     string `xml:"creator"` // dc:creator
	Encoded     string `xml:"encoded"` // content:encoded
}

// --- Atom structures ---

type atomFeed struct {
	XMLName xml.Name   `xml:"feed"`
	Entries []atomEntry `xml:"entry"`
}

type atomEntry struct {
	Title     string     `xml:"title"`
	Links     []atomLink `xml:"link"`
	Published string     `xml:"published"`
	Updated   string     `xml:"updated"`
	Summary   string     `xml:"summary"`
	Content   atomContent `xml:"content"`
	Author    atomAuthor  `xml:"author"`
}

type atomLink struct {
	Href string `xml:"href,attr"`
	Rel  string `xml:"rel,attr"`
	Type string `xml:"type,attr"`
}

type atomContent struct {
	Body string `xml:",chardata"`
	Type string `xml:"type,attr"`
}

type atomAuthor struct {
	Name string `xml:"name"`
}

// Parse reads XML from r and returns parsed articles. It tries RSS 2.0 first,
// then falls back to Atom format.
func Parse(r io.Reader) ([]Article, error) {
	data, err := io.ReadAll(r)
	if err != nil {
		return nil, fmt.Errorf("reading feed body: %w", err)
	}

	// Try RSS 2.0 first.
	articles, err := parseRSS(data)
	if err == nil && len(articles) > 0 {
		return articles, nil
	}

	// Try Atom.
	articles, err = parseAtom(data)
	if err == nil && len(articles) > 0 {
		return articles, nil
	}

	// If both failed and we got items from neither, return what we have.
	if err != nil {
		return nil, fmt.Errorf("failed to parse feed as RSS or Atom: %w", err)
	}
	return articles, nil
}

func parseRSS(data []byte) ([]Article, error) {
	var feed rssRoot
	if err := xml.Unmarshal(data, &feed); err != nil {
		return nil, err
	}

	articles := make([]Article, 0, len(feed.Channel.Items))
	for _, item := range feed.Channel.Items {
		link := strings.TrimSpace(item.Link)
		if link == "" {
			continue // skip items without a URL
		}

		a := Article{
			Title:  strings.TrimSpace(item.Title),
			URL:    link,
			Author: firstNonEmpty(item.Author, item.Creator),
		}

		// Prefer content:encoded over description for richer content.
		a.Content = strings.TrimSpace(item.Encoded)
		if a.Content == "" {
			a.Content = strings.TrimSpace(item.Description)
		}

		if t := parseTime(item.PubDate); t != nil {
			a.PublishedAt = t
		}

		articles = append(articles, a)
	}
	return articles, nil
}

func parseAtom(data []byte) ([]Article, error) {
	var feed atomFeed
	if err := xml.Unmarshal(data, &feed); err != nil {
		return nil, err
	}

	articles := make([]Article, 0, len(feed.Entries))
	for _, entry := range feed.Entries {
		link := atomBestLink(entry.Links)
		if link == "" {
			continue
		}

		a := Article{
			Title:  strings.TrimSpace(entry.Title),
			URL:    link,
			Author: strings.TrimSpace(entry.Author.Name),
		}

		// Prefer content over summary.
		a.Content = strings.TrimSpace(entry.Content.Body)
		if a.Content == "" {
			a.Content = strings.TrimSpace(entry.Summary)
		}

		// Prefer published, fall back to updated.
		dateStr := entry.Published
		if dateStr == "" {
			dateStr = entry.Updated
		}
		if t := parseTime(dateStr); t != nil {
			a.PublishedAt = t
		}

		articles = append(articles, a)
	}
	return articles, nil
}

// atomBestLink picks the best link from an Atom entry's link list.
// It prefers rel="alternate" with type="text/html", then any rel="alternate",
// then the first link.
func atomBestLink(links []atomLink) string {
	var alternate, first string
	for _, l := range links {
		href := strings.TrimSpace(l.Href)
		if href == "" {
			continue
		}
		if first == "" {
			first = href
		}
		if l.Rel == "alternate" || l.Rel == "" {
			alternate = href
			if l.Type == "text/html" || l.Type == "" {
				return href // best match
			}
		}
	}
	if alternate != "" {
		return alternate
	}
	return first
}

// parseTime tries multiple common date formats used in RSS/Atom feeds.
func parseTime(s string) *time.Time {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}

	formats := []string{
		time.RFC1123Z,                  // RSS standard: Mon, 02 Jan 2006 15:04:05 -0700
		time.RFC1123,                   // Mon, 02 Jan 2006 15:04:05 MST
		time.RFC3339,                   // Atom standard: 2006-01-02T15:04:05Z07:00
		time.RFC3339Nano,               // 2006-01-02T15:04:05.999999999Z07:00
		"2006-01-02T15:04:05Z",         // ISO without offset
		"2006-01-02 15:04:05",          // Simple datetime
		"2006-01-02",                   // Date only
		"Mon, 2 Jan 2006 15:04:05 -0700", // RSS variant with single-digit day
		"Mon, 2 Jan 2006 15:04:05 MST",
		"02 Jan 2006 15:04:05 -0700",
	}

	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return &t
		}
	}
	return nil
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		v = strings.TrimSpace(v)
		if v != "" {
			return v
		}
	}
	return ""
}
