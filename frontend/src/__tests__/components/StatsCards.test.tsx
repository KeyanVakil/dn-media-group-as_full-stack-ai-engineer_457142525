import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatsCards from "../../components/StatsCards";
import type { DashboardStats } from "../../types";

const sampleStats: DashboardStats = {
  total_articles: 1234,
  total_entities: 567,
  total_sources: 12,
  articles_analyzed: 890,
  research_tasks_completed: 45,
};

describe("StatsCards", () => {
  it("renders loading skeletons when loading=true", () => {
    const { container } = render(<StatsCards stats={null} loading={true} />);

    // Should render 5 skeleton placeholders (one per stat)
    const skeletons = container.querySelectorAll(".skeleton");
    expect(skeletons).toHaveLength(5);

    // Should still show labels even when loading
    expect(screen.getByText("Total Articles")).toBeInTheDocument();
    expect(screen.getByText("Analyzed")).toBeInTheDocument();
    expect(screen.getByText("Entities Tracked")).toBeInTheDocument();
    expect(screen.getByText("News Sources")).toBeInTheDocument();
    expect(screen.getByText("Research Tasks")).toBeInTheDocument();
  });

  it("renders all 5 stat values correctly when data is provided", () => {
    render(<StatsCards stats={sampleStats} loading={false} />);

    // toLocaleString() formats numbers, so check the formatted values
    expect(screen.getByText("1,234")).toBeInTheDocument();
    expect(screen.getByText("567")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("890")).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
  });

  it("renders all 5 labels", () => {
    render(<StatsCards stats={sampleStats} loading={false} />);

    expect(screen.getByText("Total Articles")).toBeInTheDocument();
    expect(screen.getByText("Analyzed")).toBeInTheDocument();
    expect(screen.getByText("Entities Tracked")).toBeInTheDocument();
    expect(screen.getByText("News Sources")).toBeInTheDocument();
    expect(screen.getByText("Research Tasks")).toBeInTheDocument();
  });

  it("handles zero values correctly", () => {
    const zeroStats: DashboardStats = {
      total_articles: 0,
      total_entities: 0,
      total_sources: 0,
      articles_analyzed: 0,
      research_tasks_completed: 0,
    };

    render(<StatsCards stats={zeroStats} loading={false} />);

    // All values should display "0"
    const zeroes = screen.getAllByText("0");
    expect(zeroes).toHaveLength(5);
  });

  it("renders '--' placeholders when stats is null and not loading", () => {
    render(<StatsCards stats={null} loading={false} />);

    const placeholders = screen.getAllByText("--");
    expect(placeholders).toHaveLength(5);
  });
});
