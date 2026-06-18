from __future__ import annotations

REQUIRED_TABLES = [
    "users",
    "auth_sessions",
    "student_accounts",
    "students",
    "student_profiles",
    "onboarding_sessions",
    "profile_sources",
    "edu_memories",
    "learning_events",
    "mastery_records",
    "courses",
    "course_documents",
    "document_chunks",
    "notebooks",
    "notebook_sources",
    "notebook_assignments",
    "notebook_memory_events",
    "knowledge_points",
    "knowledge_edges",
    "learning_paths",
    "learning_path_nodes",
    "resources",
    "resource_versions",
    "canvas_apps",
    "chat_app_links",
    "chat_resource_links",
    "chat_messages",
    "artifacts",
    "app_events",
    "quiz_questions",
    "quiz_submissions",
    "agent_runs",
    "agent_steps",
    "verifier_results",
    "image_assets",
    "feedbacks",
]

SQLITE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      display_name TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
      token TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      student_id TEXT NOT NULL,
      course_id TEXT NOT NULL,
      expires_at TEXT,
      created_at TEXT NOT NULL,
      last_seen_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS student_accounts (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      student_id TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'owner',
      created_at TEXT NOT NULL,
      UNIQUE(user_id, student_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS students (
      id TEXT PRIMARY KEY,
      display_name TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS courses (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS student_profiles (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      course_id TEXT,
      profile_json TEXT NOT NULL,
      version INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS onboarding_sessions (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      course_id TEXT NOT NULL,
      status TEXT NOT NULL,
      current_step TEXT NOT NULL,
      missing_fields TEXT NOT NULL,
      summary TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS profile_sources (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      course_id TEXT NOT NULL,
      onboarding_session_id TEXT,
      source_type TEXT NOT NULL,
      title TEXT NOT NULL,
      raw_text TEXT NOT NULL,
      extracted_text TEXT NOT NULL,
      structured_payload TEXT NOT NULL,
      parser_status TEXT NOT NULL,
      parser_reason TEXT,
      file_name TEXT,
      mime_type TEXT,
      url TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS edu_memories (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      course_id TEXT,
      knowledge_point_id TEXT,
      memory_type TEXT NOT NULL,
      content TEXT NOT NULL,
      structured_payload TEXT NOT NULL,
      confidence REAL NOT NULL,
      importance REAL NOT NULL,
      decay_rate REAL NOT NULL,
      evidence_type TEXT NOT NULL,
      source_event_id TEXT,
      source_agent TEXT,
      valid_from TEXT NOT NULL,
      valid_until TEXT,
      embedding TEXT,
      tags TEXT NOT NULL,
      version INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_events (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mastery_records (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      course_id TEXT,
      knowledge_point_id TEXT NOT NULL,
      mastery_score REAL NOT NULL,
      confidence REAL NOT NULL,
      evidence_json TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS course_documents (
      id TEXT PRIMARY KEY,
      course_id TEXT NOT NULL,
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
      metadata TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
      id TEXT PRIMARY KEY,
      document_id TEXT NOT NULL,
      course_id TEXT NOT NULL,
      chunk_index INTEGER NOT NULL,
      content TEXT NOT NULL,
      source_ref TEXT NOT NULL,
      embedding TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notebooks (
      id TEXT PRIMARY KEY,
      owner_scope TEXT NOT NULL,
      owner_id TEXT NOT NULL,
      course_id TEXT,
      title TEXT NOT NULL,
      purpose TEXT NOT NULL,
      description TEXT,
      tags TEXT NOT NULL,
      open_notebook_id TEXT,
      sync_status TEXT NOT NULL DEFAULT 'not_synced',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notebook_sources (
      id TEXT PRIMARY KEY,
      notebook_id TEXT NOT NULL,
      source_id TEXT NOT NULL,
      source_kind TEXT NOT NULL DEFAULT 'course_document',
      source_role TEXT NOT NULL DEFAULT 'primary',
      sync_status TEXT NOT NULL DEFAULT 'not_synced',
      open_notebook_source_id TEXT,
      synced_at TEXT,
      created_at TEXT NOT NULL,
      UNIQUE(notebook_id, source_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notebook_assignments (
      id TEXT PRIMARY KEY,
      notebook_id TEXT NOT NULL,
      student_id TEXT NOT NULL,
      course_id TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      rank INTEGER NOT NULL DEFAULT 100,
      assigned_reason TEXT,
      created_at TEXT NOT NULL,
      UNIQUE(notebook_id, student_id, course_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notebook_memory_events (
      id TEXT PRIMARY KEY,
      notebook_id TEXT,
      student_id TEXT NOT NULL,
      course_id TEXT,
      event_type TEXT NOT NULL,
      source_refs TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_points (
      id TEXT PRIMARY KEY,
      course_id TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      metadata TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_edges (
      id TEXT PRIMARY KEY,
      course_id TEXT NOT NULL,
      source_id TEXT NOT NULL,
      target_id TEXT NOT NULL,
      relation TEXT NOT NULL,
      confidence REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_paths (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      course_id TEXT,
      title TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_path_nodes (
      id TEXT PRIMARY KEY,
      path_id TEXT NOT NULL,
      title TEXT NOT NULL,
      status TEXT NOT NULL,
      mastery_required REAL,
      current_mastery REAL,
      payload TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resources (
      id TEXT PRIMARY KEY,
      student_id TEXT,
      course_id TEXT,
      knowledge_point_id TEXT,
      type TEXT NOT NULL,
      title TEXT NOT NULL,
      difficulty TEXT,
      content_json TEXT NOT NULL,
      file_url TEXT,
      source_refs TEXT NOT NULL,
      personalized_reason TEXT,
      quality_score REAL,
      verifier_result TEXT,
      created_by_skill TEXT,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resource_versions (
      id TEXT PRIMARY KEY,
      resource_id TEXT NOT NULL,
      version INTEGER NOT NULL,
      content_json TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS canvas_apps (
      id TEXT PRIMARY KEY,
      student_id TEXT,
      conversation_id TEXT,
      resource_id TEXT,
      app_type TEXT NOT NULL,
      title TEXT NOT NULL,
      icon TEXT,
      status TEXT NOT NULL,
      render_mode TEXT NOT NULL,
      state TEXT NOT NULL,
      layout TEXT NOT NULL,
      payload TEXT NOT NULL,
      source_refs TEXT NOT NULL,
      personalized_reason TEXT,
      created_by_agent TEXT,
      created_by_skill TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_app_links (
      id TEXT PRIMARY KEY,
      message_id TEXT NOT NULL,
      app_id TEXT NOT NULL,
      label TEXT NOT NULL,
      action TEXT NOT NULL,
      anchor_text TEXT,
      source_run_id TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_resource_links (
      id TEXT PRIMARY KEY,
      message_id TEXT NOT NULL,
      resource_id TEXT NOT NULL,
      source_run_id TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      course_id TEXT,
      conversation_id TEXT NOT NULL,
      role TEXT NOT NULL,
      text TEXT NOT NULL,
      metadata TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
      id TEXT PRIMARY KEY,
      kind TEXT NOT NULL,
      object_key TEXT NOT NULL,
      content_type TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      size_bytes INTEGER NOT NULL,
      title TEXT,
      source_run_id TEXT,
      student_id TEXT,
      course_id TEXT,
      conversation_id TEXT,
      metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_events (
      id TEXT PRIMARY KEY,
      app_id TEXT NOT NULL,
      student_id TEXT,
      event_type TEXT NOT NULL,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quiz_questions (
      id TEXT PRIMARY KEY,
      resource_id TEXT,
      question_type TEXT NOT NULL,
      prompt TEXT NOT NULL,
      options TEXT,
      answer TEXT NOT NULL,
      explanation TEXT,
      knowledge_point_id TEXT,
      difficulty TEXT,
      misconception_tags TEXT NOT NULL,
      source_refs TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quiz_submissions (
      id TEXT PRIMARY KEY,
      student_id TEXT NOT NULL,
      question_id TEXT NOT NULL,
      answer TEXT NOT NULL,
      is_correct INTEGER NOT NULL,
      evaluation TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_runs (
      id TEXT PRIMARY KEY,
      student_id TEXT,
      task_type TEXT NOT NULL,
      input_json TEXT NOT NULL,
      output_json TEXT NOT NULL,
      status TEXT NOT NULL,
      model_name TEXT,
      latency_ms INTEGER,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_steps (
      id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      step_order INTEGER NOT NULL,
      agent_or_skill TEXT NOT NULL,
      input_json TEXT,
      output_json TEXT,
      status TEXT NOT NULL,
      latency_ms INTEGER,
      error_message TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS verifier_results (
      id TEXT PRIMARY KEY,
      resource_id TEXT,
      passed INTEGER NOT NULL,
      score REAL NOT NULL,
      issues TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS image_assets (
      id TEXT PRIMARY KEY,
      resource_id TEXT,
      provider TEXT NOT NULL,
      prompt TEXT NOT NULL,
      file_url TEXT,
      overlay_labels TEXT NOT NULL,
      metadata TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedbacks (
      id TEXT PRIMARY KEY,
      student_id TEXT,
      resource_id TEXT,
      app_id TEXT,
      rating INTEGER,
      comment TEXT,
      payload TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_edu_memories_student_course ON edu_memories(student_id, course_id)",
    "CREATE INDEX IF NOT EXISTS idx_edu_memories_student_course_type ON edu_memories(student_id, course_id, memory_type)",
    "CREATE INDEX IF NOT EXISTS idx_edu_memories_student_course_kp ON edu_memories(student_id, course_id, knowledge_point_id)",
    "CREATE INDEX IF NOT EXISTS idx_edu_memories_student_course_updated ON edu_memories(student_id, course_id, updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_edu_memories_source_event ON edu_memories(student_id, source_event_id)",
    "CREATE INDEX IF NOT EXISTS idx_mastery_student_course_kp ON mastery_records(student_id, course_id, knowledge_point_id)",
    "CREATE INDEX IF NOT EXISTS idx_resources_student_course ON resources(student_id, course_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_resource_links_message ON chat_resource_links(message_id)",
    "CREATE INDEX IF NOT EXISTS idx_chat_resource_links_run ON chat_resource_links(source_run_id)",
    "CREATE INDEX IF NOT EXISTS idx_canvas_apps_student_updated ON canvas_apps(student_id, updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_student_accounts_user ON student_accounts(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_onboarding_student_course ON onboarding_sessions(student_id, course_id)",
    "CREATE INDEX IF NOT EXISTS idx_profile_sources_student_course ON profile_sources(student_id, course_id)",
    "CREATE INDEX IF NOT EXISTS idx_student_profiles_student_course ON student_profiles(student_id, course_id)",
]
