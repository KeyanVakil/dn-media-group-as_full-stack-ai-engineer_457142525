import { useRef, useEffect, useCallback } from "react";
import * as d3 from "d3";
import type { EntityConnections, EntityConnectionNode, EntityConnectionEdge, EntityType } from "../types";
import { getEntityColor } from "./EntityBadge";

interface EntityGraphProps {
  connections: EntityConnections;
  onNodeClick?: (id: string) => void;
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  type: EntityType;
  article_count: number;
  isCenter: boolean;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  strength: number;
  evidence_count: number;
}

export default function EntityGraph({ connections, onNodeClick }: EntityGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const buildGraph = useCallback(() => {
    const container = containerRef.current;
    const svg = svgRef.current;
    if (!container || !svg) return;

    // Clear previous graph
    d3.select(svg).selectAll("*").remove();
    d3.select(container).selectAll(".d3-tooltip").remove();

    const width = container.clientWidth;
    const height = container.clientHeight;

    // Build nodes
    const allNodes: EntityConnectionNode[] = [connections.center, ...connections.nodes];
    const nodeMap = new Map(allNodes.map((n) => [n.id, n]));

    const nodes: SimNode[] = allNodes.map((n) => ({
      id: n.id,
      name: n.name,
      type: n.type,
      article_count: n.article_count,
      isCenter: n.id === connections.center.id,
    }));

    const links: SimLink[] = connections.edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e: EntityConnectionEdge) => ({
        source: e.source,
        target: e.target,
        strength: e.strength,
        evidence_count: e.evidence_count,
      }));

    // Scales
    const maxArticles = Math.max(...nodes.map((n) => n.article_count), 1);
    const radiusScale = d3.scaleSqrt().domain([0, maxArticles]).range([6, 28]);
    const linkWidthScale = d3.scaleLinear()
      .domain([0, Math.max(...links.map((l) => l.strength), 1)])
      .range([1, 5]);

    // Tooltip
    const tooltip = d3
      .select(container)
      .append("div")
      .attr("class", "d3-tooltip")
      .style("opacity", 0);

    // SVG setup
    const svgSel = d3.select(svg).attr("width", width).attr("height", height);

    // Zoom container
    const g = svgSel.append("g");

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svgSel.call(zoom);

    // Simulation
    const simulation = d3
      .forceSimulation<SimNode>(nodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimLink>(links)
          .id((d) => d.id)
          .distance(100),
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide<SimNode>().radius((d) => radiusScale(d.article_count) + 4));

    // Links
    const link = g
      .append("g")
      .selectAll<SVGLineElement, SimLink>("line")
      .data(links)
      .join("line")
      .attr("stroke", "#c4cdd8")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d) => linkWidthScale(d.strength));

    // Node groups
    const node = g
      .append("g")
      .selectAll<SVGGElement, SimNode>("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      );

    // Node circles
    node
      .append("circle")
      .attr("r", (d) => radiusScale(d.article_count))
      .attr("fill", (d) => getEntityColor(d.type))
      .attr("fill-opacity", (d) => (d.isCenter ? 1 : 0.8))
      .attr("stroke", (d) => (d.isCenter ? "#1e222b" : "white"))
      .attr("stroke-width", (d) => (d.isCenter ? 3 : 1.5));

    // Center node ring
    node
      .filter((d) => d.isCenter)
      .append("circle")
      .attr("r", (d) => radiusScale(d.article_count) + 5)
      .attr("fill", "none")
      .attr("stroke", getEntityColor(connections.center.type))
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", "4 3")
      .attr("opacity", 0.5);

    // Node labels (visible for center and large nodes)
    node
      .filter((d) => d.isCenter || d.article_count > maxArticles * 0.3)
      .append("text")
      .text((d) => d.name)
      .attr("text-anchor", "middle")
      .attr("dy", (d) => radiusScale(d.article_count) + 14)
      .attr("font-size", (d) => (d.isCenter ? "13px" : "11px"))
      .attr("font-weight", (d) => (d.isCenter ? "600" : "400"))
      .attr("fill", "#343a47")
      .attr("font-family", "Inter, system-ui, sans-serif");

    // Hover + click handlers
    node
      .on("mouseover", (event, d) => {
        tooltip
          .style("opacity", 1)
          .html(
            `<strong>${d.name}</strong><br/>` +
            `<span style="opacity:0.7">${d.type} &middot; ${d.article_count} articles</span>`,
          )
          .style("left", `${event.offsetX + 12}px`)
          .style("top", `${event.offsetY - 10}px`);

        d3.select(event.currentTarget).select("circle").attr("fill-opacity", 1);
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", `${event.offsetX + 12}px`)
          .style("top", `${event.offsetY - 10}px`);
      })
      .on("mouseout", (event, d) => {
        tooltip.style("opacity", 0);
        d3.select(event.currentTarget)
          .select("circle")
          .attr("fill-opacity", d.isCenter ? 1 : 0.8);
      })
      .on("click", (_event, d) => {
        if (onNodeClick) onNodeClick(d.id);
      });

    // Tick update
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    // Cleanup
    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [connections, onNodeClick]);

  useEffect(() => {
    const cleanup = buildGraph();
    const handleResize = () => buildGraph();
    window.addEventListener("resize", handleResize);
    return () => {
      cleanup?.();
      window.removeEventListener("resize", handleResize);
    };
  }, [buildGraph]);

  return (
    <div ref={containerRef} className="relative w-full h-full min-h-[400px]">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
}
