package parser

import (
	"strings"
	"testing"
	"time"
)

// --- Sample XML feeds used across tests ---

const validRSS = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Test RSS Feed</title>
    <link>https://example.com</link>
    <item>
      <title>First Article</title>
      <link>https://example.com/article/1</link>
      <description>Short summary of first article.</description>
      <pubDate>Mon, 14 Apr 2025 10:30:00 +0200</pubDate>
      <author>alice@example.com</author>
    </item>
    <item>
      <title>Second Article</title>
      <link>https://example.com/article/2</link>
      <description>Short summary of second article.</description>
      <content:encoded><![CDATA[<p>Full HTML body of the second article.</p>]]></content:encoded>
      <pubDate>Tue, 15 Apr 2025 08:00:00 +0000</pubDate>
      <dc:creator>Bob Writer</dc:creator>
    </item>
    <item>
      <title>Third Article</title>
      <link>https://example.com/article/3</link>
      <description>Third article description.</description>
      <pubDate>Wed, 16 Apr 2025 14:45:00 -0500</pubDate>
    </item>
  </channel>
</rss>`

const validAtom = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Atom Feed</title>
  <link href="https://example.com" rel="alternate" type="text/html"/>
  <entry>
    <title>Atom Entry One</title>
    <link href="https://example.com/entry/1" rel="alternate" type="text/html"/>
    <published>2025-04-14T10:30:00Z</published>
    <updated>2025-04-14T11:00:00Z</updated>
    <content type="html">Full content of Atom entry one.</content>
    <author><name>Alice Author</name></author>
  </entry>
  <entry>
    <title>Atom Entry Two</title>
    <link href="https://example.com/entry/2" rel="alternate" type="text/html"/>
    <link href="https://example.com/entry/2.json" rel="alternate" type="application/json"/>
    <updated>2025-04-15T12:00:00+02:00</updated>
    <summary>Summary of entry two.</summary>
    <author><name>Bob Blogger</name></author>
  </entry>
</feed>`

const emptyRSS = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
  </channel>
</rss>`

const emptyAtom = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Empty Atom Feed</title>
</feed>`

const invalidXML = `<this is not valid xml at all!!! <<>>`

const rssMissingOptionalFields = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>No Author No Date</title>
      <link>https://example.com/sparse</link>
      <description>Bare-bones item.</description>
    </item>
    <item>
      <title>Also Sparse</title>
      <link>https://example.com/sparse2</link>
    </item>
  </channel>
</rss>`

const atomMissingOptionalFields = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>No Author No Date</title>
    <link href="https://example.com/atom-sparse" rel="alternate"/>
    <summary>Sparse atom entry.</summary>
  </entry>
</feed>`

// rssNoLink ensures items without links are skipped.
const rssNoLink = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Linkless Item</title>
      <description>This item has no link.</description>
    </item>
    <item>
      <title>Has Link</title>
      <link>https://example.com/has-link</link>
    </item>
  </channel>
</rss>`

func TestParseRSS(t *testing.T) {
	articles, err := Parse(strings.NewReader(validRSS))
	if err != nil {
		t.Fatalf("unexpected error parsing valid RSS: %v", err)
	}

	if got := len(articles); got != 3 {
		t.Fatalf("expected 3 articles, got %d", got)
	}

	tests := []struct {
		name            string
		article         Article
		wantTitle       string
		wantURL         string
		wantContent     string
		wantAuthor      string
		wantHasDate     bool
		wantYear        int
		wantMonth       time.Month
		wantDay         int
	}{
		{
			name:        "first item",
			article:     articles[0],
			wantTitle:   "First Article",
			wantURL:     "https://example.com/article/1",
			wantContent: "Short summary of first article.",
			wantAuthor:  "alice@example.com",
			wantHasDate: true,
			wantYear:    2025,
			wantMonth:   time.April,
			wantDay:     14,
		},
		{
			name:        "second item prefers content:encoded over description",
			article:     articles[1],
			wantTitle:   "Second Article",
			wantURL:     "https://example.com/article/2",
			wantContent: "<p>Full HTML body of the second article.</p>",
			wantAuthor:  "Bob Writer", // dc:creator fallback
			wantHasDate: true,
			wantYear:    2025,
			wantMonth:   time.April,
			wantDay:     15,
		},
		{
			name:        "third item with no author",
			article:     articles[2],
			wantTitle:   "Third Article",
			wantURL:     "https://example.com/article/3",
			wantContent: "Third article description.",
			wantAuthor:  "",
			wantHasDate: true,
			wantYear:    2025,
			wantMonth:   time.April,
			wantDay:     16,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			assertArticle(t, tc.article, tc.wantTitle, tc.wantURL, tc.wantContent, tc.wantAuthor)
			if tc.wantHasDate {
				assertDate(t, tc.article.PublishedAt, tc.wantYear, tc.wantMonth, tc.wantDay)
			}
		})
	}
}

func TestParseAtom(t *testing.T) {
	articles, err := Parse(strings.NewReader(validAtom))
	if err != nil {
		t.Fatalf("unexpected error parsing valid Atom: %v", err)
	}

	if got := len(articles); got != 2 {
		t.Fatalf("expected 2 articles, got %d", got)
	}

	tests := []struct {
		name        string
		article     Article
		wantTitle   string
		wantURL     string
		wantContent string
		wantAuthor  string
		wantHasDate bool
		wantYear    int
		wantMonth   time.Month
		wantDay     int
	}{
		{
			name:        "first entry with content and published date",
			article:     articles[0],
			wantTitle:   "Atom Entry One",
			wantURL:     "https://example.com/entry/1",
			wantContent: "Full content of Atom entry one.",
			wantAuthor:  "Alice Author",
			wantHasDate: true,
			wantYear:    2025,
			wantMonth:   time.April,
			wantDay:     14,
		},
		{
			name:        "second entry with summary fallback and updated date",
			article:     articles[1],
			wantTitle:   "Atom Entry Two",
			wantURL:     "https://example.com/entry/2",
			wantContent: "Summary of entry two.",
			wantAuthor:  "Bob Blogger",
			wantHasDate: true,
			wantYear:    2025,
			wantMonth:   time.April,
			wantDay:     15,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			assertArticle(t, tc.article, tc.wantTitle, tc.wantURL, tc.wantContent, tc.wantAuthor)
			if tc.wantHasDate {
				assertDate(t, tc.article.PublishedAt, tc.wantYear, tc.wantMonth, tc.wantDay)
			}
		})
	}
}

func TestParseEmptyFeed(t *testing.T) {
	t.Run("empty Atom feed returns empty slice, no error", func(t *testing.T) {
		articles, err := Parse(strings.NewReader(emptyAtom))
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if len(articles) != 0 {
			t.Errorf("expected 0 articles, got %d", len(articles))
		}
	})

	// An empty RSS feed (valid RSS XML, zero items) causes the parser to
	// fall through to Atom parsing, which fails because the root element
	// is <rss> not <feed>. This is expected behavior: the parser treats
	// an empty RSS channel as unparseable since it produced no articles
	// from either format.
	t.Run("empty RSS feed returns error (falls through to Atom which fails)", func(t *testing.T) {
		_, err := Parse(strings.NewReader(emptyRSS))
		if err == nil {
			t.Fatal("expected error for empty RSS feed, got nil")
		}
	})
}

func TestParseInvalidXML(t *testing.T) {
	_, err := Parse(strings.NewReader(invalidXML))
	if err == nil {
		t.Fatal("expected error for invalid XML, got nil")
	}
}

func TestParseMissingOptionalFields(t *testing.T) {
	tests := []struct {
		name       string
		xml        string
		wantCount  int
		wantURL    string
		wantAuthor string
	}{
		{
			name:       "RSS missing author and date",
			xml:        rssMissingOptionalFields,
			wantCount:  2,
			wantURL:    "https://example.com/sparse",
			wantAuthor: "",
		},
		{
			name:       "Atom missing author and date",
			xml:        atomMissingOptionalFields,
			wantCount:  1,
			wantURL:    "https://example.com/atom-sparse",
			wantAuthor: "",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			articles, err := Parse(strings.NewReader(tc.xml))
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got := len(articles); got != tc.wantCount {
				t.Fatalf("expected %d articles, got %d", tc.wantCount, got)
			}
			if articles[0].URL != tc.wantURL {
				t.Errorf("URL = %q, want %q", articles[0].URL, tc.wantURL)
			}
			if articles[0].Author != tc.wantAuthor {
				t.Errorf("Author = %q, want %q", articles[0].Author, tc.wantAuthor)
			}
			if articles[0].PublishedAt != nil {
				t.Errorf("PublishedAt should be nil for missing date, got %v", articles[0].PublishedAt)
			}
		})
	}
}

func TestParseSkipsItemsWithoutLink(t *testing.T) {
	articles, err := Parse(strings.NewReader(rssNoLink))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got := len(articles); got != 1 {
		t.Fatalf("expected 1 article (linkless skipped), got %d", got)
	}
	if articles[0].URL != "https://example.com/has-link" {
		t.Errorf("expected has-link article, got URL %q", articles[0].URL)
	}
}

func TestDateParsing(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantNil   bool
		wantYear  int
		wantMonth time.Month
		wantDay   int
	}{
		{
			name:      "RFC1123Z",
			input:     "Mon, 14 Apr 2025 10:30:00 +0200",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "RFC1123",
			input:     "Mon, 14 Apr 2025 10:30:00 UTC",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "RFC3339",
			input:     "2025-04-14T10:30:00Z",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "RFC3339 with offset",
			input:     "2025-04-14T10:30:00+02:00",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "RFC3339Nano",
			input:     "2025-04-14T10:30:00.123456789Z",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "ISO without offset",
			input:     "2025-04-14T10:30:00Z",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "simple datetime",
			input:     "2025-04-14 10:30:00",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "date only",
			input:     "2025-04-14",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:      "RSS variant single-digit day",
			input:     "Mon, 7 Apr 2025 08:00:00 +0000",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   7,
		},
		{
			name:      "RSS variant single-digit day MST",
			input:     "Mon, 7 Apr 2025 08:00:00 UTC",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   7,
		},
		{
			name:      "day month year with offset",
			input:     "14 Apr 2025 10:30:00 +0200",
			wantYear:  2025,
			wantMonth: time.April,
			wantDay:   14,
		},
		{
			name:    "empty string",
			input:   "",
			wantNil: true,
		},
		{
			name:    "whitespace only",
			input:   "   ",
			wantNil: true,
		},
		{
			name:    "unrecognized format",
			input:   "April fourteenth, twenty twenty-five",
			wantNil: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			result := parseTime(tc.input)
			if tc.wantNil {
				if result != nil {
					t.Errorf("expected nil for %q, got %v", tc.input, result)
				}
				return
			}
			if result == nil {
				t.Fatalf("expected non-nil time for %q, got nil", tc.input)
			}
			if result.Year() != tc.wantYear {
				t.Errorf("year = %d, want %d", result.Year(), tc.wantYear)
			}
			if result.Month() != tc.wantMonth {
				t.Errorf("month = %v, want %v", result.Month(), tc.wantMonth)
			}
			if result.Day() != tc.wantDay {
				t.Errorf("day = %d, want %d", result.Day(), tc.wantDay)
			}
		})
	}
}

func TestAtomBestLink(t *testing.T) {
	tests := []struct {
		name     string
		links    []atomLink
		wantHref string
	}{
		{
			name:     "empty links",
			links:    nil,
			wantHref: "",
		},
		{
			name: "prefers alternate+html",
			links: []atomLink{
				{Href: "https://example.com/json", Rel: "alternate", Type: "application/json"},
				{Href: "https://example.com/html", Rel: "alternate", Type: "text/html"},
			},
			wantHref: "https://example.com/html",
		},
		{
			name: "falls back to alternate without type",
			links: []atomLink{
				{Href: "https://example.com/self", Rel: "self"},
				{Href: "https://example.com/alt", Rel: "alternate"},
			},
			wantHref: "https://example.com/alt",
		},
		{
			name: "falls back to first link",
			links: []atomLink{
				{Href: "https://example.com/only", Rel: "self"},
			},
			wantHref: "https://example.com/only",
		},
		{
			name: "skips empty hrefs",
			links: []atomLink{
				{Href: "", Rel: "alternate"},
				{Href: "https://example.com/real", Rel: "alternate"},
			},
			wantHref: "https://example.com/real",
		},
		{
			name: "empty rel treated as alternate",
			links: []atomLink{
				{Href: "https://example.com/default", Rel: ""},
			},
			wantHref: "https://example.com/default",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := atomBestLink(tc.links)
			if got != tc.wantHref {
				t.Errorf("atomBestLink() = %q, want %q", got, tc.wantHref)
			}
		})
	}
}

func TestFirstNonEmpty(t *testing.T) {
	tests := []struct {
		name   string
		values []string
		want   string
	}{
		{"all empty", []string{"", "  ", ""}, ""},
		{"first wins", []string{"a", "b"}, "a"},
		{"second wins after empty", []string{"", "b"}, "b"},
		{"trims whitespace", []string{"  ", " hello "}, "hello"},
		{"no args", nil, ""},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got := firstNonEmpty(tc.values...)
			if got != tc.want {
				t.Errorf("firstNonEmpty() = %q, want %q", got, tc.want)
			}
		})
	}
}

// --- Test helpers ---

func assertArticle(t *testing.T, a Article, wantTitle, wantURL, wantContent, wantAuthor string) {
	t.Helper()
	if a.Title != wantTitle {
		t.Errorf("Title = %q, want %q", a.Title, wantTitle)
	}
	if a.URL != wantURL {
		t.Errorf("URL = %q, want %q", a.URL, wantURL)
	}
	if a.Content != wantContent {
		t.Errorf("Content = %q, want %q", a.Content, wantContent)
	}
	if a.Author != wantAuthor {
		t.Errorf("Author = %q, want %q", a.Author, wantAuthor)
	}
}

func assertDate(t *testing.T, pubAt *time.Time, wantYear int, wantMonth time.Month, wantDay int) {
	t.Helper()
	if pubAt == nil {
		t.Fatal("PublishedAt is nil, expected a date")
	}
	if pubAt.Year() != wantYear {
		t.Errorf("year = %d, want %d", pubAt.Year(), wantYear)
	}
	if pubAt.Month() != wantMonth {
		t.Errorf("month = %v, want %v", pubAt.Month(), wantMonth)
	}
	if pubAt.Day() != wantDay {
		t.Errorf("day = %d, want %d", pubAt.Day(), wantDay)
	}
}
