-- Postgres-first schema for LearnForge runtime.
-- IDs intentionally remain TEXT to preserve the existing App Protocol wire shape.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS students (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS courses (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS student_accounts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  student_id TEXT NOT NULL REFERENCES students(id),
  role TEXT NOT NULL DEFAULT 'owner',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  UNIQUE(user_id, student_id)
);

CREATE TABLE IF NOT EXISTS auth_sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT NOT NULL REFERENCES courses(id),
  expires_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS student_profiles (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  profile_json JSONB NOT NULL DEFAULT '{}',
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS onboarding_sessions (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT NOT NULL REFERENCES courses(id),
  status TEXT NOT NULL,
  current_step TEXT NOT NULL,
  missing_fields JSONB NOT NULL DEFAULT '[]',
  summary TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS profile_sources (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT NOT NULL REFERENCES courses(id),
  onboarding_session_id TEXT REFERENCES onboarding_sessions(id),
  source_type TEXT NOT NULL,
  title TEXT NOT NULL,
  raw_text TEXT NOT NULL DEFAULT '',
  extracted_text TEXT NOT NULL DEFAULT '',
  structured_payload JSONB NOT NULL DEFAULT '{}',
  parser_status TEXT NOT NULL,
  parser_reason TEXT,
  file_name TEXT,
  mime_type TEXT,
  url TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS edu_memories (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  knowledge_point_id TEXT,
  memory_type TEXT NOT NULL,
  content TEXT NOT NULL,
  structured_payload JSONB NOT NULL DEFAULT '{}',
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  importance DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  decay_rate DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  evidence_type TEXT NOT NULL,
  source_event_id TEXT,
  source_agent TEXT,
  valid_from TIMESTAMP NOT NULL DEFAULT now(),
  valid_until TIMESTAMP,
  embedding vector,
  tags TEXT[] NOT NULL DEFAULT '{}',
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_events (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mastery_records (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  knowledge_point_id TEXT NOT NULL,
  mastery_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  evidence_json JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS course_documents (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  title TEXT NOT NULL,
  file_url TEXT,
  parser TEXT,
  ingest_type TEXT NOT NULL DEFAULT 'course_seed',
  owner_scope TEXT NOT NULL DEFAULT 'course',
  owner_id TEXT,
  source_scope TEXT NOT NULL DEFAULT 'course_official',
  original_url TEXT,
  mime_type TEXT,
  upload_status TEXT NOT NULL DEFAULT 'ready',
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS ingest_type TEXT NOT NULL DEFAULT 'course_seed';
ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS owner_scope TEXT NOT NULL DEFAULT 'course';
ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS owner_id TEXT;
ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS source_scope TEXT NOT NULL DEFAULT 'course_official';
ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS original_url TEXT;
ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS mime_type TEXT;
ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS upload_status TEXT NOT NULL DEFAULT 'ready';
ALTER TABLE course_documents ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES course_documents(id),
  course_id TEXT NOT NULL REFERENCES courses(id),
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  source_ref JSONB NOT NULL DEFAULT '{}',
  embedding vector,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notebooks (
  id TEXT PRIMARY KEY,
  owner_scope TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  course_id TEXT REFERENCES courses(id),
  title TEXT NOT NULL,
  purpose TEXT NOT NULL,
  description TEXT,
  tags JSONB NOT NULL DEFAULT '[]',
  open_notebook_id TEXT,
  sync_status TEXT NOT NULL DEFAULT 'not_synced',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notebook_sources (
  id TEXT PRIMARY KEY,
  notebook_id TEXT NOT NULL REFERENCES notebooks(id),
  source_id TEXT NOT NULL,
  source_kind TEXT NOT NULL DEFAULT 'course_document',
  source_role TEXT NOT NULL DEFAULT 'primary',
  sync_status TEXT NOT NULL DEFAULT 'not_synced',
  open_notebook_source_id TEXT,
  synced_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  UNIQUE(notebook_id, source_id)
);

CREATE TABLE IF NOT EXISTS notebook_assignments (
  id TEXT PRIMARY KEY,
  notebook_id TEXT NOT NULL REFERENCES notebooks(id),
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  status TEXT NOT NULL DEFAULT 'active',
  rank INT NOT NULL DEFAULT 100,
  assigned_reason TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  UNIQUE(notebook_id, student_id, course_id)
);

CREATE TABLE IF NOT EXISTS notebook_memory_events (
  id TEXT PRIMARY KEY,
  notebook_id TEXT REFERENCES notebooks(id),
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  event_type TEXT NOT NULL,
  source_refs JSONB NOT NULL DEFAULT '[]',
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_points (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  title TEXT NOT NULL,
  description TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS knowledge_edges (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5
);

CREATE TABLE IF NOT EXISTS learning_paths (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  title TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_path_nodes (
  id TEXT PRIMARY KEY,
  path_id TEXT NOT NULL REFERENCES learning_paths(id),
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  mastery_required DOUBLE PRECISION,
  current_mastery DOUBLE PRECISION,
  payload JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS resources (
  id TEXT PRIMARY KEY,
  student_id TEXT REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  knowledge_point_id TEXT,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  difficulty TEXT,
  content_json JSONB NOT NULL DEFAULT '{}',
  file_url TEXT,
  source_refs JSONB NOT NULL DEFAULT '[]',
  personalized_reason TEXT,
  quality_score DOUBLE PRECISION,
  verifier_result JSONB,
  created_by_skill TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS resource_versions (
  id TEXT PRIMARY KEY,
  resource_id TEXT NOT NULL REFERENCES resources(id),
  version INT NOT NULL,
  content_json JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS canvas_apps (
  id TEXT PRIMARY KEY,
  student_id TEXT REFERENCES students(id),
  conversation_id TEXT,
  resource_id TEXT REFERENCES resources(id),
  app_type TEXT NOT NULL,
  title TEXT NOT NULL,
  icon TEXT,
  status TEXT NOT NULL,
  render_mode TEXT NOT NULL,
  state TEXT NOT NULL,
  layout JSONB NOT NULL DEFAULT '{}',
  payload JSONB NOT NULL DEFAULT '{}',
  source_refs JSONB NOT NULL DEFAULT '[]',
  personalized_reason TEXT,
  created_by_agent TEXT,
  created_by_skill TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_app_links (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL,
  app_id TEXT NOT NULL REFERENCES canvas_apps(id),
  label TEXT NOT NULL,
  action TEXT NOT NULL,
  anchor_text TEXT,
  source_run_id TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_resource_links (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL,
  resource_id TEXT NOT NULL REFERENCES resources(id),
  source_run_id TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL,
  text TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  object_key TEXT NOT NULL,
  content_type TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  title TEXT,
  source_run_id TEXT,
  student_id TEXT REFERENCES students(id),
  course_id TEXT REFERENCES courses(id),
  conversation_id TEXT,
  metadata_json JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_events (
  id TEXT PRIMARY KEY,
  app_id TEXT NOT NULL REFERENCES canvas_apps(id),
  student_id TEXT REFERENCES students(id),
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quiz_questions (
  id TEXT PRIMARY KEY,
  resource_id TEXT REFERENCES resources(id),
  question_type TEXT NOT NULL,
  prompt TEXT NOT NULL,
  options JSONB,
  answer JSONB NOT NULL,
  explanation TEXT,
  knowledge_point_id TEXT,
  difficulty TEXT,
  misconception_tags TEXT[] NOT NULL DEFAULT '{}',
  source_refs JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS quiz_submissions (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  question_id TEXT NOT NULL REFERENCES quiz_questions(id),
  answer JSONB NOT NULL,
  is_correct BOOLEAN NOT NULL,
  evaluation JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  student_id TEXT REFERENCES students(id),
  task_type TEXT NOT NULL,
  input_json JSONB NOT NULL DEFAULT '{}',
  output_json JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL,
  model_name TEXT,
  latency_ms INT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_steps (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES agent_runs(id),
  step_order INT NOT NULL,
  agent_or_skill TEXT NOT NULL,
  input_json JSONB,
  output_json JSONB,
  status TEXT NOT NULL,
  latency_ms INT,
  error_message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS verifier_results (
  id TEXT PRIMARY KEY,
  resource_id TEXT REFERENCES resources(id),
  passed BOOLEAN NOT NULL,
  score DOUBLE PRECISION NOT NULL,
  issues JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS image_assets (
  id TEXT PRIMARY KEY,
  resource_id TEXT REFERENCES resources(id),
  provider TEXT NOT NULL,
  prompt TEXT NOT NULL,
  file_url TEXT,
  overlay_labels JSONB NOT NULL DEFAULT '[]',
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedbacks (
  id TEXT PRIMARY KEY,
  student_id TEXT REFERENCES students(id),
  resource_id TEXT REFERENCES resources(id),
  app_id TEXT REFERENCES canvas_apps(id),
  rating INT,
  comment TEXT,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_student_accounts_user ON student_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_student_profiles_student_course ON student_profiles(student_id, course_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_student_course ON onboarding_sessions(student_id, course_id);
CREATE INDEX IF NOT EXISTS idx_profile_sources_student_course ON profile_sources(student_id, course_id);
CREATE INDEX IF NOT EXISTS idx_edu_memories_student_course_type ON edu_memories(student_id, course_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_edu_memories_student_course_updated ON edu_memories(student_id, course_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_edu_memories_source_event ON edu_memories(student_id, source_event_id);
CREATE INDEX IF NOT EXISTS idx_resources_student_course ON resources(student_id, course_id);
CREATE INDEX IF NOT EXISTS idx_chat_resource_links_message ON chat_resource_links(message_id);
CREATE INDEX IF NOT EXISTS idx_chat_resource_links_run ON chat_resource_links(source_run_id);
CREATE INDEX IF NOT EXISTS idx_canvas_apps_student_updated ON canvas_apps(student_id, updated_at);
