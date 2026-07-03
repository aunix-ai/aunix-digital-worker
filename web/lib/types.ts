export interface ActionPermission {
  type: "email" | "hubspot" | "task" | "resolve" | "composio";
  to_field?: string | null;
  to?: string | null;
  ops?: Array<"add_note" | "set_property">;
  tool_slug?: string | null;
  argument_template?: Record<string, unknown> | string;
}

export interface ActionPolicy {
  email_auto?: boolean;
  email_to_domains?: string[];
  hubspot_auto?: boolean;
  hubspot_ops?: string[];
  composio_auto?: boolean;
  composio_tool_slugs?: string[];
  task_auto?: boolean;
  resolve_auto?: boolean;
  per_run?: number;
  per_day?: number;
}

export interface ComposioSource {
  type: "composio";
  toolkit: string;
  tool_slug: string;
  arguments?: Record<string, unknown>;
  record_key?: string;
  row_mapping?: Record<string, string>;
  key?: string | null;
}
export type DataSourceRef = string | ComposioSource;
export interface Condition { field: string; operator: string; value: number | string }
export interface AgentSpec {
  name: string;
  objective: string;
  task_type: "monitoring" | "analysis";
  data_sources: DataSourceRef[];
  record_key: string;
  conditions: { mode: "all" | "any"; conditions: Condition[] } | null;
  schedule: { mode: "interval" | "daily" | "on_demand"; interval_minutes?: number | null; daily_time?: string | null };
  notifications: { channels: string[]; email_to?: string | null };
  autonomy_level: number;
  actions?: ActionPermission[];
  policy?: ActionPolicy | null;
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
  trace: {
    rows_fetched?: number; breaches?: string[];
    findings?: { new: number; ongoing: number; resolved: number };
    actions?: { proposed: number; auto_executed: number; queued: number; failed: number };
  };
  error: string | null; started_at: string | null; finished_at: string | null;
  findings?: Finding[];
  actions?: ActionItem[];
}
export interface FeedItem {
  id: number; channel: string; status: string; created_at: string | null; finding: Finding;
}
export interface ClarifyingQuestion {
  text: string;
  choices: string[];
  kind: "text" | "email";
}
export type CompileSessionStatus =
  | "interpreting"
  | "validating"
  | "awaiting_probe_approval"
  | "probing"
  | "judging"
  | "awaiting_confirmation"
  | "failed";

export interface ValidationReport {
  passed: boolean;
  errors: string[];
  warnings: string[];
}

export interface JudgeVerdict {
  verdict: "pass" | "fail" | "revise";
  issues: string[];
}

export interface CompileResult {
  status?: CompileSessionStatus;
  spec: AgentSpec | null;
  questions: ClarifyingQuestion[];
  validation_report?: ValidationReport;
  judge?: JudgeVerdict;
  composio_context?: {
    connections?: Array<{ slug: string; name: string; is_connected: boolean; status: string }>;
    tool_search?: { results?: Array<{ primary_tool_slugs?: string[]; use_case?: string }> };
    probe_rows?: unknown[];
    tool_search_error?: string;
    error?: string;
  } | null;
}
export interface ActionItem {
  id: number; agent_id: number; run_id: number; finding_id: number;
  type: "email" | "hubspot" | "task" | "resolve" | "composio";
  params: Record<string, unknown>;
  status: "pending" | "approved" | "executed" | "rejected" | "expired" | "failed";
  origin: string; policy_decision: "auto" | "queued" | null; decided_by: string | null;
  result: Record<string, unknown>; error: string | null;
  created_at: string | null; expires_at: string | null;
  finding?: { id: number; summary: string; recommendation: string; source_ref: string; severity: string };
}
