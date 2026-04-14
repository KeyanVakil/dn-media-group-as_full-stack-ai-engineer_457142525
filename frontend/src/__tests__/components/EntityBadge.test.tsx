import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EntityBadge from "../../components/EntityBadge";
import type { EntityType } from "../../types";

describe("EntityBadge", () => {
  it("renders the entity name when provided", () => {
    render(<EntityBadge type="person" name="Elon Musk" />);
    expect(screen.getByText("Elon Musk")).toBeInTheDocument();
  });

  it("renders the type label when no name is provided", () => {
    render(<EntityBadge type="company" />);
    expect(screen.getByText("Company")).toBeInTheDocument();
  });

  it("applies correct color classes for person type", () => {
    const { container } = render(<EntityBadge type="person" name="Test" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("bg-accent-50");
    expect(badge.className).toContain("text-accent-700");
  });

  it("applies correct color classes for company type", () => {
    const { container } = render(<EntityBadge type="company" name="Test" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("bg-rust-50");
    expect(badge.className).toContain("text-rust-700");
  });

  it("applies correct color classes for location type", () => {
    const { container } = render(<EntityBadge type="location" name="Test" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("bg-sage-50");
    expect(badge.className).toContain("text-sage-700");
  });

  it("applies correct color classes for topic type", () => {
    const { container } = render(<EntityBadge type="topic" name="Test" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("bg-purple-50");
    expect(badge.className).toContain("text-purple-700");
  });

  it("applies correct color classes for event type", () => {
    const { container } = render(<EntityBadge type="event" name="Test" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("bg-amber-50");
    expect(badge.className).toContain("text-amber-700");
  });

  it("renders the correct dot color for each entity type", () => {
    const typeToColor: Record<EntityType, string> = {
      person: "bg-accent-500",
      company: "bg-rust-500",
      location: "bg-sage-500",
      topic: "bg-purple-500",
      event: "bg-amber-500",
    };

    for (const [type, dotClass] of Object.entries(typeToColor)) {
      const { container, unmount } = render(
        <EntityBadge type={type as EntityType} name="Test" />,
      );
      // The dot is the first child span inside the badge
      const dot = container.querySelector(`.${dotClass.replace(/\s/g, ".")}`);
      expect(dot).not.toBeNull();
      unmount();
    }
  });

  it("renders as a span by default (not clickable)", () => {
    const { container } = render(<EntityBadge type="person" name="Test" />);
    expect(container.firstElementChild!.tagName).toBe("SPAN");
  });

  it("renders as a button when clickable=true", () => {
    const { container } = render(
      <EntityBadge type="person" name="Test" clickable />,
    );
    expect(container.firstElementChild!.tagName).toBe("BUTTON");
  });

  it("applies small size classes by default", () => {
    const { container } = render(<EntityBadge type="person" name="Test" />);
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("px-2");
    expect(badge.className).toContain("text-xs");
  });

  it("applies medium size classes when size='md'", () => {
    const { container } = render(
      <EntityBadge type="person" name="Test" size="md" />,
    );
    const badge = container.firstElementChild!;
    expect(badge.className).toContain("px-3");
    expect(badge.className).toContain("text-sm");
  });
});
