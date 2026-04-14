import { useState, useEffect, useCallback } from "react";
import type { ResearchTaskListItem, ResearchTaskDetail, ResearchStatus } from "../types";
import { fetchResearchTasks, fetchResearchTask, createResearchTask } from "../api/client";
import ResearchChat from "../components/ResearchChat";

export default function Research() {
  const [tasks, setTasks] = useState<ResearchTaskListItem[]>([]);
  const [selectedTask, setSelectedTask] = useState<ResearchTaskDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Load task list
  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const result = await fetchResearchTasks(50, 0);
      setTasks(result.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  // Submit new query
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || submitting) return;

    try {
      setSubmitting(true);
      setError(null);
      const task = await createResearchTask(trimmed);
      setQuery("");
      // Add to list and select it
      setTasks((prev) => [
        { id: task.id, query: task.query, status: task.status, created_at: task.created_at },
        ...prev,
      ]);
      setSelectedTask(task);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create research task");
    } finally {
      setSubmitting(false);
    }
  }

  // Select a task
  async function handleSelectTask(taskId: string) {
    try {
      setDetailLoading(true);
      const task = await fetchResearchTask(taskId);
      setSelectedTask(task);
    } catch {
      setError("Failed to load task details");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-serif font-bold text-ink-900">Research</h1>
        <p className="mt-1 text-sm text-ink-500">
          Ask questions and let the AI agent research across your news corpus
        </p>
      </div>

      {/* Query input */}
      <form onSubmit={handleSubmit} className="card p-4">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <ResearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a research question... e.g., 'What is the latest on renewable energy in Norway?'"
              className="input pl-9"
              disabled={submitting}
            />
          </div>
          <button type="submit" disabled={!query.trim() || submitting} className="btn-primary">
            {submitting ? (
              <>
                <Spinner /> Submitting...
              </>
            ) : (
              <>
                <SendIcon className="w-4 h-4" />
                Research
              </>
            )}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Main content: split layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Task list */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="px-4 py-3 border-b border-ink-100">
              <h2 className="text-sm font-semibold text-ink-700">Research History</h2>
            </div>
            <div className="max-h-[600px] overflow-y-auto divide-y divide-ink-100">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="p-3">
                    <div className="skeleton h-4 w-full mb-2" />
                    <div className="skeleton h-3 w-1/3" />
                  </div>
                ))
              ) : tasks.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-sm text-ink-400">No research tasks yet.</p>
                  <p className="text-xs text-ink-400 mt-1">
                    Submit a query to get started.
                  </p>
                </div>
              ) : (
                tasks.map((task) => (
                  <button
                    key={task.id}
                    onClick={() => handleSelectTask(task.id)}
                    className={`w-full text-left p-3 hover:bg-ink-50 transition-colors ${
                      selectedTask?.id === task.id ? "bg-accent-50 border-l-2 border-accent-500" : ""
                    }`}
                  >
                    <p className="text-sm text-ink-800 line-clamp-2 font-medium">
                      {task.query}
                    </p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <StatusDot status={task.status} />
                      <span className="text-xs text-ink-400">
                        {new Date(task.created_at).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Task detail */}
        <div className="lg:col-span-2">
          {detailLoading ? (
            <div className="card p-8">
              <div className="space-y-4">
                <div className="skeleton h-6 w-2/3" />
                <div className="skeleton h-4 w-1/3" />
                <div className="skeleton h-32 w-full mt-4" />
              </div>
            </div>
          ) : selectedTask ? (
            <ResearchChat
              key={selectedTask.id}
              taskId={selectedTask.id}
              initialTask={selectedTask}
            />
          ) : (
            <div className="card p-12 text-center">
              <ResearchBigIcon className="w-16 h-16 text-ink-200 mx-auto" />
              <h3 className="text-lg font-serif font-semibold text-ink-600 mt-4">
                Start a Research Task
              </h3>
              <p className="text-sm text-ink-400 mt-2 max-w-md mx-auto">
                Enter a question above, and the AI agent will search through articles,
                extract entities, and compile a research briefing.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Subcomponents ──────────────────────────────────────────────────

function StatusDot({ status }: { status: ResearchStatus }) {
  const colors: Record<ResearchStatus, string> = {
    pending: "bg-ink-400",
    running: "bg-accent-500 animate-pulse",
    completed: "bg-sage-500",
    failed: "bg-red-500",
  };

  return <span className={`w-2 h-2 rounded-full ${colors[status]}`} />;
}

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

// ── Icons ──────────────────────────────────────────────────────────

function ResearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function SendIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function ResearchBigIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.25} strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      <line x1="6" y1="8" x2="8" y2="8" />
      <line x1="6" y1="12" x2="8" y2="12" />
      <line x1="16" y1="8" x2="18" y2="8" />
      <line x1="16" y1="12" x2="18" y2="12" />
    </svg>
  );
}
