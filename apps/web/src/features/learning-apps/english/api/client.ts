// English Workspace API client — calls LearnForge /api/english/* endpoints

import { getAuthToken } from "../../../../lib/api/client";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8011";

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function englishFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}/api/english${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options?.headers,
    },
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new Error(`English API ${path}: ${resp.status} ${detail}`);
  }
  return resp.json();
}

export const englishClient = {
  // ── Fission Graph ──────────────────────────────────────
  getFissionGraph(word: string, depth = 2) {
    return englishFetch<{
      nodes: Array<{ id: string; label: string; group?: string; type?: string; val?: number }>;
      links: Array<{ source: string; target: string; relation?: string }>;
    }>(`/fission?word=${encodeURIComponent(word)}&depth=${depth}`);
  },

  // ── Word List ──────────────────────────────────────────
  getWordList(params?: { libraryId?: string; search?: string; limit?: number; offset?: number }) {
    const qs = new URLSearchParams();
    if (params?.libraryId) qs.set("libraryId", params.libraryId);
    if (params?.search) qs.set("search", params.search);
    qs.set("limit", String(params?.limit ?? 100));
    qs.set("offset", String(params?.offset ?? 0));
    return englishFetch<{
      words: Array<{
        word: string;
        phonetic?: string;
        definition?: string;
        translation?: string;
        collinsLevel?: string;
        bnc?: number;
        frq?: number;
      }>;
      total: number;
    }>(`/words?${qs}`);
  },

  // ── Word Detail ────────────────────────────────────────
  getWordDetail(word: string) {
    return englishFetch<{
      word: string;
      phonetic?: string;
      definition?: string;
      translation?: string;
      examples?: string[];
      synonyms?: string[];
      antonyms?: string[];
      collinsLevel?: string;
      bnc?: number;
      frq?: number;
      tags?: string[];
    }>(`/words/${encodeURIComponent(word)}`);
  },

  // ── Quiz ───────────────────────────────────────────────
  getQuizData(word: string, quizType = "multiple_choice") {
    return englishFetch<{
      questions: Array<{
        word: string;
        quizType: string;
        question: string;
        options?: string[];
        correctAnswer: string;
        hint?: string;
      }>;
    }>(`/quiz?word=${encodeURIComponent(word)}&quiz_type=${quizType}`);
  },

  submitQuizResult(data: { word: string; type: string; score: number; answers: Array<Record<string, unknown>> }) {
    return englishFetch<{ status: string }>("/quiz/submit", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // ── Libraries ──────────────────────────────────────────
  getLibraries() {
    return englishFetch<{
      libraries: Array<{ id: string; name: string; wordCount: number; description?: string }>;
    }>("/libraries");
  },

  createLibrary(name: string) {
    return englishFetch<{ id: string; name: string }>("/libraries", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  // ── Study Plan ─────────────────────────────────────────
  getStudyPlan() {
    return englishFetch<{
      dailyGoal: number;
      todayLearned: number;
      totalLearned: number;
      streak: number;
    }>("/study-plan");
  },

  updateStudyPlan(dailyGoal: number) {
    return englishFetch<{ status: string }>("/study-plan", {
      method: "PUT",
      body: JSON.stringify({ dailyGoal }),
    });
  },

  // ── Health ─────────────────────────────────────────────
  healthCheck() {
    return englishFetch<{ status: string; data?: unknown }>("/health");
  },
};
