import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import ArticleCard from "../../components/ArticleCard";
import type { ArticleListItem } from "../../types";

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

const analyzedArticle: ArticleListItem = {
  id: "art-1",
  title: "Climate Report Shows Record Temperatures",
  source: { id: "src-1", name: "NRK" },
  published_at: new Date().toISOString(),
  analyzed: true,
  ingested_at: new Date().toISOString(),
};

const pendingArticle: ArticleListItem = {
  id: "art-2",
  title: "New Government Policy on Energy",
  source: { id: "src-2", name: "VG" },
  published_at: new Date().toISOString(),
  analyzed: false,
  ingested_at: new Date().toISOString(),
};

describe("ArticleCard", () => {
  it("renders the article title", () => {
    renderWithRouter(<ArticleCard article={analyzedArticle} />);
    expect(
      screen.getByText("Climate Report Shows Record Temperatures"),
    ).toBeInTheDocument();
  });

  it("renders the source name", () => {
    renderWithRouter(<ArticleCard article={analyzedArticle} />);
    expect(screen.getByText("NRK")).toBeInTheDocument();
  });

  it("shows 'Analyzed' badge when analyzed=true", () => {
    renderWithRouter(<ArticleCard article={analyzedArticle} />);
    expect(screen.getByText("Analyzed")).toBeInTheDocument();
    expect(screen.queryByText("Pending")).not.toBeInTheDocument();
  });

  it("shows 'Pending' badge when analyzed=false", () => {
    renderWithRouter(<ArticleCard article={pendingArticle} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.queryByText("Analyzed")).not.toBeInTheDocument();
  });

  it("links to the article detail page", () => {
    renderWithRouter(<ArticleCard article={analyzedArticle} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/articles/art-1");
  });

  it("renders different source names correctly", () => {
    renderWithRouter(<ArticleCard article={pendingArticle} />);
    expect(screen.getByText("VG")).toBeInTheDocument();
  });

  it("applies the correct CSS class on the Analyzed badge", () => {
    renderWithRouter(<ArticleCard article={analyzedArticle} />);
    const badge = screen.getByText("Analyzed");
    expect(badge.className).toContain("bg-sage-100");
    expect(badge.className).toContain("text-sage-700");
  });

  it("applies the correct CSS class on the Pending badge", () => {
    renderWithRouter(<ArticleCard article={pendingArticle} />);
    const badge = screen.getByText("Pending");
    expect(badge.className).toContain("bg-ink-100");
    expect(badge.className).toContain("text-ink-500");
  });
});
