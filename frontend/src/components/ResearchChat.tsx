import { useState, useEffect, useRef } from "react";
import type { ResearchTaskDetail, ResearchStep, ResearchStatus } from "../types";
import { fetchResearchTask, streamResearch } from "../api/client";

interface ResearchChatProps {
  taskId: string;
  initialTask: ResearchTaskDetail;
}

export default function ResearchChat({ taskId, initialTask }: ResearchChatProps) {
  const [task, setTask] = useState<ResearchTaskDetail>(initialTask);
  const [streamingSteps, setStreamingSteps] = useState<ResearchStep[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Stream steps when task is running
  useEffect(() => {
    if (task.status !== "running" && task.status !== "pending") return;

    const close = streamResearch(
      taskId,
      (data) => {
        const step = data as ResearchStep;
        setStreamingSteps((prev) => {
          const exists = prev.find((s) => s.step_number === step.step_number);
          if (exists) {
            return prev.map((s) => (s.step_number === step.step_number ? step : s));
          }
          return [...prev, step];
        });
      },
      () => {
        // Stream ended -- fetch final state
        fetchResearchTask(taskId)
          .then(setTask)
          .catch(() => {
            setTask((prev) => ({ ...prev, status: "failed" }));
          });
      },
    );

    return close;
  }, [taskId, task.status]);

  // Scroll to bottom when new steps arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [streamingSteps, task]);

  const allSteps = task.steps.length > 0 ? task.steps : streamingSteps;

  return (
    <div className="space-y-6">
      {/* Query header */}
      <div className="card p-5">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-accent-100 text-accent-600 flex items-center justify-center flex-shrink-0 mt-0.5">
            <QueryIcon className="w-4 h-4" />
          </div>
          <div>
            <p className="text-sm font-medium text-ink-500">Research Query</p>
            <p className="text-base font-serif text-ink-900 mt-1">{task.query}</p>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <StatusPill status={task.status} />
          <span className="text-xs text-ink-400">
            Started {new Date(task.created_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Steps */}
      {allSteps.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-ink-700 uppercase tracking-wider">
            Reasoning Steps
          </h3>
          <div className="relative pl-6 border-l-2 border-ink-200 space-y-4">
            {allSteps.map((step) => (
              <StepCard key={step.step_number} step={step} />
            ))}

            {(task.status === "running" || task.status === "pending") && (
              <div className="flex items-center gap-2 py-2">
                <div className="w-3 h-3 rounded-full bg-accent-500 -ml-[25px] animate-pulse" />
                <span className="text-sm text-ink-400">Thinking...</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Result */}
      {task.status === "completed" && task.result && (
        <div className="card border-sage-200 bg-sage-50/30">
          <div className="p-5">
            <h3 className="text-lg font-serif font-semibold text-ink-900 mb-3 flex items-center gap-2">
              <CheckCircleIcon className="w-5 h-5 text-sage-600" />
              Research Briefing
            </h3>
            <div className="prose prose-sm max-w-none text-ink-700 leading-relaxed whitespace-pre-wrap">
              {task.result.briefing}
            </div>
          </div>

          {task.result.key_findings.length > 0 && (
            <div className="px-5 pb-4">
              <h4 className="text-sm font-semibold text-ink-700 mb-2">Key Findings</h4>
              <ul className="space-y-1.5">
                {task.result.key_findings.map((finding, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-ink-600">
                    <span className="text-sage-500 mt-1 flex-shrink-0">&#9679;</span>
                    {finding}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {task.result.evidence.length > 0 && (
            <div className="px-5 pb-4">
              <h4 className="text-sm font-semibold text-ink-700 mb-2">Evidence</h4>
              <ul className="space-y-1.5">
                {task.result.evidence.map((ev, i) => (
                  <li key={i} className="text-sm text-ink-500">
                    <span className="font-medium text-ink-700 not-italic">{ev.title}</span>
                    {ev.relevance && (
                      <span className="italic ml-1">&mdash; {ev.relevance}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {task.result.follow_up_questions.length > 0 && (
            <div className="px-5 pb-5">
              <h4 className="text-sm font-semibold text-ink-700 mb-2">Follow-up Questions</h4>
              <div className="flex flex-wrap gap-2">
                {task.result.follow_up_questions.map((q, i) => (
                  <span key={i} className="badge bg-white border border-ink-200 text-ink-600">
                    {q}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error state */}
      {task.status === "failed" && (
        <div className="card border-red-200 bg-red-50/30 p-5">
          <div className="flex items-center gap-2">
            <ErrorIcon className="w-5 h-5 text-red-500" />
            <p className="text-sm font-medium text-red-700">
              Research task failed. Please try again.
            </p>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────

function StepCard({ step }: { step: ResearchStep }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="relative">
      <div className="w-2.5 h-2.5 rounded-full bg-accent-400 border-2 border-white absolute -left-[21.5px] top-2.5" />
      <div className="card p-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center justify-between w-full text-left"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-ink-400">#{step.step_number}</span>
            <span className="text-sm font-medium text-ink-800">{step.action}</span>
          </div>
          <ChevronIcon className={`w-4 h-4 text-ink-400 transition-transform ${expanded ? "rotate-180" : ""}`} />
        </button>
        {expanded && step.output_data && (
          <div className="mt-2 pt-2 border-t border-ink-100">
            <pre className="text-xs text-ink-600 font-mono whitespace-pre-wrap overflow-x-auto max-h-48 overflow-y-auto">
              {JSON.stringify(step.output_data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: ResearchStatus }) {
  const config: Record<ResearchStatus, { bg: string; text: string; label: string }> = {
    pending: { bg: "bg-ink-100", text: "text-ink-600", label: "Pending" },
    running: { bg: "bg-accent-100", text: "text-accent-700", label: "Running" },
    completed: { bg: "bg-sage-100", text: "text-sage-700", label: "Completed" },
    failed: { bg: "bg-red-100", text: "text-red-700", label: "Failed" },
  };
  const c = config[status];
  return (
    <span className={`badge ${c.bg} ${c.text}`}>
      {status === "running" && <span className="w-1.5 h-1.5 rounded-full bg-accent-500 animate-pulse mr-1" />}
      {c.label}
    </span>
  );
}

// ── Icons ──────────────────────────────────────────────────────────

function QueryIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function ErrorIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}
