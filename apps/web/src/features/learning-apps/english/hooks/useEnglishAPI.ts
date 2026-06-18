// useEnglishAPI — React hooks wrapping englishClient

import { useCallback, useEffect, useState } from "react";
import { englishClient } from "../api/client";
import type {
  FissionGraphData,
  QuizQuestion,
  StudyPlan,
  WordDetail,
  WordEntry,
  WordLibrary,
} from "../types/english";

// ── Fission Graph ─────────────────────────────────────────
export function useFissionGraph(word: string | null, depth = 2) {
  const [data, setData] = useState<FissionGraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!word) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    englishClient
      .getFissionGraph(word, depth)
      .then((res) => {
        if (cancelled) return;
        setData({
          nodes: (res.nodes ?? []).map((n) => ({
            id: n.id,
            label: n.label,
            group: n.group,
            type: n.type as FissionGraphData["nodes"][number]["type"],
            val: n.val,
          })),
          links: (res.links ?? []).map((l) => ({
            source: l.source,
            target: l.target,
            relation: l.relation,
          })),
        });
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load fission graph");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [word, depth]);

  return { data, loading, error };
}

// ── Word List ─────────────────────────────────────────────
export function useWordList(search: string, libraryId?: string, limit = 200) {
  const [words, setWords] = useState<WordEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    englishClient
      .getWordList({ search: search || undefined, libraryId, limit })
      .then((res) => {
        if (cancelled) return;
        setWords(
          (res.words ?? []).map((w) => ({
            word: w.word,
            phonetic: w.phonetic,
            definition: w.definition,
            translation: w.translation,
            collinsLevel: w.collinsLevel,
            bnc: w.bnc,
            frq: w.frq,
          }))
        );
        setTotal(res.total ?? 0);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load words");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [search, libraryId, limit]);

  return { words, total, loading, error };
}

// ── Word Detail ───────────────────────────────────────────
export function useWordDetail(word: string | null) {
  const [detail, setDetail] = useState<WordDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!word) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    englishClient
      .getWordDetail(word)
      .then((res) => {
        if (cancelled) return;
        setDetail({
          word: res.word,
          phonetic: res.phonetic,
          definition: res.definition,
          translation: res.translation,
          examples: res.examples,
          synonyms: res.synonyms,
          antonyms: res.antonyms,
          collinsLevel: res.collinsLevel,
          bnc: res.bnc,
          frq: res.frq,
          tags: res.tags,
        });
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load word detail");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [word]);

  return { detail, loading, error };
}

// ── Quiz ──────────────────────────────────────────────────
export function useQuizData(word: string | null, quizType: string = "multiple_choice") {
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!word) {
      setQuestions([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    englishClient
      .getQuizData(word, quizType)
      .then((res) => {
        if (cancelled) return;
        setQuestions(
          (res.questions ?? []).map((q) => ({
            word: q.word,
            quizType: q.quizType as QuizQuestion["quizType"],
            question: q.question,
            options: q.options,
            correctAnswer: q.correctAnswer,
            hint: q.hint,
          }))
        );
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load quiz");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [word, quizType]);

  return { questions, loading, error };
}

// ── Libraries ─────────────────────────────────────────────
export function useLibraries() {
  const [libraries, setLibraries] = useState<WordLibrary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    englishClient
      .getLibraries()
      .then((res) => {
        if (cancelled) return;
        setLibraries(
          (res.libraries ?? []).map((l) => ({
            id: l.id,
            name: l.name,
            wordCount: l.wordCount,
            description: l.description,
          }))
        );
      })
      .catch(() => {
        if (!cancelled) setLibraries([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { libraries, loading };
}

// ── Study Plan ────────────────────────────────────────────
export function useStudyPlan() {
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    englishClient
      .getStudyPlan()
      .then((res) => {
        if (cancelled) return;
        setPlan({
          dailyGoal: res.dailyGoal,
          todayLearned: res.todayLearned,
          totalLearned: res.totalLearned,
          streak: res.streak,
        });
      })
      .catch(() => {
        if (!cancelled) setPlan(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const update = useCallback(async (dailyGoal: number) => {
    await englishClient.updateStudyPlan(dailyGoal);
    setPlan((prev) => (prev ? { ...prev, dailyGoal } : prev));
  }, []);

  return { plan, loading, update };
}

// ── Quiz submit ───────────────────────────────────────────
export function useSubmitQuiz() {
  const [submitting, setSubmitting] = useState(false);

  const submit = useCallback(
    async (word: string, quizType: string, score: number, answers: Array<{ question: string; userAnswer: string; correct: boolean }>) => {
      setSubmitting(true);
      try {
        await englishClient.submitQuizResult({ word, type: quizType, score, answers });
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  return { submit, submitting };
}
