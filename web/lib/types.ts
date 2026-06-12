export interface Condition { field: string; operator: string; value: number | string }
export interface AgentSpec {
  name: string;
  objective: string;
  task_type: "monitoring" | "analysis";
  data_sources: string[];
  record_key: string;
  conditions: { mode: "all" | "any"; conditions: Condition[] } | null;
  schedule: { mode: "interval" | "daily" | "on_demand"; interval_minutes?: number | null; daily_time?: string | null };
  notifications: { channels: string[]; email_to?: string | null };
  autonomy_level: number;
  reasoning_instructions?: string | null;
  rank_by?: string | null;
  top_n: number;
}
export interface AgentOut { id: number; owner: string; status: "draft" | "active" | "paused"; spec: AgentSpec }
export interface Finding {
  id: number; agent_id: number; run_id: number; severity: string; state: string;
  summary: string; recommendation: string; source_ref: string;
  dedupe_key?: string; details?: Record<string, unknown>;
}
export interface RunOut {
  id: number; agent_id: number; trigger: string; status: string;
  trace: { rows_fetched?: number; breaches?: string[]; findings?: { new: number; ongoing: number; resolved: number } };
  error: string | null; started_at: string | null; finished_at: string | null;
  findings?: Finding[];
}
export interface FeedItem {
  id: number; channel: string; status: string; created_at: string | null; finding: Finding;
}
export interface ClarifyingQuestion {
  text: string;
  choices: string[];
  kind: "text" | "email";
}
export interface CompileResult { spec: AgentSpec | null; questions: ClarifyingQuestion[] }
