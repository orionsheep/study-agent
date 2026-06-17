export type CanvasAppState = 'icon' | 'card' | 'window' | 'fullscreen' | 'split_left' | 'split_right' | 'minimized' | 'focused';
export type RenderMode = 'native_react' | 'sandbox_iframe' | 'svg' | 'react_flow' | 'pptx_preview';
export type CanvasAppType =
  | 'profile.dashboard'
  | 'learning.path'
  | 'knowledge.graph'
  | 'mindmap.concept'
  | 'quiz.practice'
  | 'physics.work_energy_demo'
  | 'math.gradient_descent_demo'
  | 'code.lab'
  | 'notes.session'
  | 'dashboard.learning'
  | 'ppt.preview'
  | 'image.explanation'
  | 'video.script'
  | 'video.player'
  | 'resource.center'
  | 'resource.folder'
  | 'custom.html'
  | 'english.workspace'
  | 'humanities.notebook';

export interface CanvasViewport { x: number; y: number; scale: number; }
export interface CanvasPosition { x: number; y: number; }
export interface CanvasSize { width: number; height: number; }
export interface CanvasFrame { frame_id: string; title: string; app_ids: string[]; position: CanvasPosition; size: CanvasSize; }
export interface CanvasConnector { connector_id: string; source_app_id: string; target_app_id: string; label: string; relation: string; }

export interface CanvasApp {
  app_id: string;
  app_type: CanvasAppType;
  title: string;
  icon?: string;
  status: 'creating' | 'ready' | 'error' | 'blocked';
  render_mode: RenderMode;
  state: CanvasAppState;
  position: CanvasPosition;
  size: CanvasSize;
  z_index: number;
  group_id?: string;
  payload: Record<string, unknown>;
  source: { message_id?: string; run_id?: string; resource_id?: string; skill_name?: string };
  source_refs: Array<Record<string, unknown>>;
  personalized_reason?: string;
  actions: Array<{ label: string; action: string; payload?: Record<string, unknown> }>;
  created_at: string;
  updated_at: string;
}

export interface ChatAppLink {
  link_id: string;
  message_id: string;
  app_id: string;
  label: string;
  action: 'focus' | 'open' | 'split' | 'fullscreen' | 'explain' | 'generate_related';
  anchor_text?: string;
  created_at: string;
  source_run_id?: string;
}

export interface AppEvent {
  event_id: string;
  app_id: string;
  student_id: string;
  course_id?: string;
  event_type: string;
  conversation_id?: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export type AgentStreamEvent =
  | { type: 'assistant.delta'; message_id: string; text: string }
  | { type: 'assistant.done'; message_id: string }
  | { type: 'run.started'; run_id: string; task_type: string }
  | { type: 'run.step'; run_id: string; step_name: string; status: string; detail?: string }
  | { type: 'run.done'; run_id: string; status: string }
  | { type: 'app.create'; app: CanvasApp; link?: ChatAppLink }
  | { type: 'app.update'; app_id: string; patch: Partial<CanvasApp> }
  | { type: 'app.focus'; app_id: string; intent?: string }
  | { type: 'app.link.create'; link: ChatAppLink }
  | { type: 'app.event.received'; event: AppEvent }
  | { type: 'resource.create'; resource: LearningResource; message_id?: string }
  | { type: 'resource.update'; resource_id: string; patch: Partial<LearningResource> }
  | { type: 'memory.update'; memory: EduMemoryItem; summary: string }
  | { type: 'path.update'; path: LearningPath }
  | { type: 'dashboard.update'; dashboard: DashboardSnapshot }
  | { type: 'verifier.result'; resource_id: string; result: VerifierResult }
  | { type: 'context.update'; topic: string; capability: string; course_label?: string; learning_objective?: string }
  | { type: 'error'; message: string; code?: string }
  | { type: 'consent_required'; run_id: string; capability: string; topic: string; original_message: string }
  | { type: 'background.task_started'; run_id: string; label: string; task_type: string }
  | { type: 'background.task_progress'; run_id: string; progress: number; detail: string }
  | { type: 'background.task_completed'; run_id: string; detail: string }
  // Hermes SDK callback 透传的实时状态
  | { type: 'hermes.reasoning'; text: string; run_id: string }
  | { type: 'hermes.thinking'; text: string; run_id: string }
  | { type: 'hermes.status'; text: string; run_id: string }
  | { type: 'hermes.tool_call'; iteration: number; tools: string[]; run_id: string };

export type ResourceType = 'document' | 'mindmap' | 'quiz' | 'ppt' | 'code_practice' | 'image' | 'video_script' | 'reading' | 'notes' | 'dashboard' | 'app_bundle' | 'video';
export interface LearningResource {
  resource_id: string;
  type: ResourceType;
  title: string;
  target_topic: string;
  difficulty: string;
  content: Record<string, unknown>;
  source_refs: Array<Record<string, unknown>>;
  personalized_reason: string;
  estimated_minutes?: number;
  tags: string[];
  quality_check?: VerifierResult;
}

export interface EduMemoryItem {
  id: string;
  student_id: string;
  course_id?: string;
  knowledge_point_id?: string;
  memory_type: string;
  content: string;
  structured_payload: Record<string, unknown>;
  confidence: number;
  effective_confidence?: number;
  decayed?: boolean;
  evidence_type: string;
  source_event_id?: string;
  source_agent?: string;
  valid_from?: string;
  valid_until?: string;
  importance: number;
  decay_rate: number;
  tags: string[];
  version?: number;
  created_at: string;
  updated_at: string;
}

export interface StudentProfile { student_id: string; display_name: string; dimensions: Record<string, unknown>; evidence: EduMemoryItem[]; }

export interface LearningPathStage {
  stage_id: string;
  title: string;
  status: 'locked' | 'recommended' | 'in_progress' | 'completed' | 'needs_review';
  mastery_required: number;
  current_mastery: number;
  recommended_resource_ids: string[];
  app_ids: string[];
  reason: string;
}
export interface LearningPath { path_id: string; title: string; current_stage_id?: string; overall_progress: number; stages: LearningPathStage[]; next_actions: string[]; }
export interface VerifierResult { passed: boolean; score: number; issues: string[]; source_coverage: number; profile_fit: number; safety: 'pass' | 'warn' | 'fail'; }
export interface DashboardSnapshot { student_id: string; profile: Record<string, unknown>; mastery: Record<string, number>; weak_points: string[]; recommendations: Array<Record<string, unknown>>; memory_evidence: EduMemoryItem[]; recent_runs: Array<Record<string, unknown>>; path_progress?: number; canvas_activity?: Array<Record<string, unknown>>; }
export interface AgentStep { step_id: string; run_id: string; step_order: number; agent_or_skill: string; input_json: Record<string, unknown>; output_json: Record<string, unknown>; status: string; latency_ms: number; error_message?: string; created_at: string; }
export interface AgentRun { run_id: string; student_id?: string; task_type: string; input_json: Record<string, unknown>; output_json: Record<string, unknown>; status: string; model_name?: string; latency_ms: number; created_at: string; updated_at: string; steps: AgentStep[]; }
export interface QuizQuestion { question_id: string; question_type: string; prompt: string; options: string[]; answer: unknown; explanation: string; knowledge_point_id?: string; difficulty: string; misconception_tags: string[]; source_refs: Array<Record<string, unknown>>; }
export interface QuizSubmission { submission_id: string; student_id: string; question_id: string; answer: unknown; is_correct: boolean; evaluation: Record<string, unknown>; created_at: string; }
