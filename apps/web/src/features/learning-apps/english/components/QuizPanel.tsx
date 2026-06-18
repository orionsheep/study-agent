// QuizPanel — word quiz with multiple_choice / spelling / recall modes

import { useState, useCallback } from "react";
import { CheckCircle2, XCircle, RotateCcw, Loader2, Award } from "lucide-react";
import { useQuizData, useSubmitQuiz } from "../hooks/useEnglishAPI";

interface Props {
  word: string | null;
  onComplete?: (word: string, quizType: string, score: number, answers: Array<{ question: string; userAnswer: string; correct: boolean }>) => void;
}

type QuizMode = "multiple_choice" | "spelling" | "recall";

const MODE_LABELS: Record<QuizMode, string> = {
  multiple_choice: "选择题",
  spelling: "拼写",
  recall: "回忆",
};

export default function QuizPanel({ word, onComplete }: Props) {
  const [mode, setMode] = useState<QuizMode>("multiple_choice");
  const [currentIdx, setCurrentIdx] = useState(0);
  const [userAnswers, setUserAnswers] = useState<Array<{ question: string; userAnswer: string; correct: boolean }>>([]);
  const [showResult, setShowResult] = useState(false);
  const [spellingInput, setSpellingInput] = useState("");
  const [recallInput, setRecallInput] = useState("");

  const { questions, loading, error } = useQuizData(word, mode);
  const { submit, submitting } = useSubmitQuiz();

  const question = questions[currentIdx];

  const reset = useCallback(() => {
    setCurrentIdx(0);
    setUserAnswers([]);
    setShowResult(false);
    setSpellingInput("");
    setRecallInput("");
  }, []);

  const handleModeChange = (newMode: QuizMode) => {
    setMode(newMode);
    reset();
  };

  const checkAnswer = (userAnswer: string): boolean => {
    if (!question) return false;
    return userAnswer.trim().toLowerCase() === question.correctAnswer.trim().toLowerCase();
  };

  const handleNext = useCallback(
    (userAnswer: string) => {
      if (!question) return;
      const correct = checkAnswer(userAnswer);
      const newAnswers = [...userAnswers, { question: question.question, userAnswer, correct }];
      setUserAnswers(newAnswers);

      if (currentIdx + 1 < questions.length) {
        setCurrentIdx(currentIdx + 1);
        setSpellingInput("");
        setRecallInput("");
      } else {
        // Quiz complete
        const score = Math.round((newAnswers.filter((a) => a.correct).length / questions.length) * 100);
        setShowResult(true);
        if (word && onComplete) {
          onComplete(word, mode, score, newAnswers);
          // Submit to backend (auto-syncs to EduMem0)
          submit(word, mode, score, newAnswers).catch(() => {});
        }
      }
    },
    [question, userAnswers, currentIdx, questions.length, word, mode, onComplete, submit]
  );

  if (!word) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "var(--text-3)" }}>
        <CheckCircle2 size={36} style={{ opacity: 0.4 }} />
        <p style={{ margin: 0, fontSize: 13 }}>请先选择一个单词</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-3)", fontSize: 13, gap: 8 }}>
        <Loader2 size={16} className="animate-spin" />
        加载测验...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 8, color: "var(--text-3)", fontSize: 13, textAlign: "center", padding: 20 }}>
        <p style={{ margin: 0 }}>{error}</p>
      </div>
    );
  }

  // ── Results screen ──
  if (showResult) {
    const correctCount = userAnswers.filter((a) => a.correct).length;
    const score = Math.round((correctCount / userAnswers.length) * 100);
    return (
      <div style={{ padding: "20px 16px", height: "100%", overflow: "auto", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
        <Award size={48} style={{ color: score >= 60 ? "#10b981" : "#ef4444" }} />
        <h3 style={{ margin: 0, fontSize: 18, color: "var(--text-1)" }}>
          测验完成！
        </h3>
        <div style={{ fontSize: 32, fontWeight: 700, color: score >= 60 ? "#10b981" : "#ef4444" }}>
          {score}分
        </div>
        <p style={{ margin: 0, fontSize: 13, color: "var(--text-3)" }}>
          答对 {correctCount} / {userAnswers.length} 题
        </p>

        {/* Answer review */}
        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
          {userAnswers.map((a, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
                padding: "8px 12px",
                borderRadius: 8,
                background: a.correct ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)",
                border: `1px solid ${a.correct ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
                fontSize: 12,
              }}
            >
              {a.correct ? <CheckCircle2 size={14} style={{ color: "#10b981", flexShrink: 0, marginTop: 2 }} /> : <XCircle size={14} style={{ color: "#ef4444", flexShrink: 0, marginTop: 2 }} />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: "var(--text-2)", marginBottom: 2 }}>{a.question}</div>
                {!a.correct && (
                  <div style={{ color: "var(--text-3)", fontSize: 11 }}>
                    你的答案: {a.userAnswer || "(空)"} | 正确答案: {questions[i]?.correctAnswer ?? ""}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={reset}
          style={{
            padding: "8px 20px",
            borderRadius: 8,
            border: "1px solid var(--glass-border-hi)",
            background: "var(--glass-2)",
            color: "var(--text-1)",
            cursor: "pointer",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <RotateCcw size={14} />
          重新测验
        </button>
      </div>
    );
  }

  if (!question || questions.length === 0) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "var(--text-3)" }}>
        <CheckCircle2 size={36} style={{ opacity: 0.4 }} />
        <p style={{ margin: 0, fontSize: 13 }}>暂无测验数据</p>
      </div>
    );
  }

  // ── Quiz screen ──
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "12px 16px" }}>
      {/* Mode selector */}
      <div style={{ display: "flex", gap: 4, marginBottom: 12, flexShrink: 0 }}>
        {(Object.keys(MODE_LABELS) as QuizMode[]).map((m) => (
          <button
            key={m}
            onClick={() => handleModeChange(m)}
            style={{
              padding: "5px 12px",
              borderRadius: 6,
              border: "1px solid var(--border-1)",
              background: mode === m ? "var(--accent-grad)" : "var(--glass-1)",
              color: mode === m ? "#fff" : "var(--text-2)",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      {/* Progress */}
      <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 12, flexShrink: 0 }}>
        第 {currentIdx + 1} / {questions.length} 题
        <div style={{ marginTop: 4, height: 3, borderRadius: 2, background: "var(--glass-2)", overflow: "hidden" }}>
          <div style={{ width: `${((currentIdx) / questions.length) * 100}%`, height: "100%", background: "var(--accent-grad)", transition: "width 0.2s" }} />
        </div>
      </div>

      {/* Question */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ fontSize: 15, fontWeight: 500, color: "var(--text-1)", lineHeight: 1.5 }}>
          {question.question}
        </div>

        {question.hint && (
          <div style={{ fontSize: 12, color: "var(--text-3)", fontStyle: "italic" }}>
            提示: {question.hint}
          </div>
        )}

        {/* Multiple choice */}
        {mode === "multiple_choice" && question.options && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {question.options.map((opt, i) => (
              <button
                key={i}
                onClick={() => handleNext(opt)}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border-1)",
                  background: "var(--glass-1)",
                  color: "var(--text-1)",
                  fontSize: 13,
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.12s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--glass-2)";
                  e.currentTarget.style.borderColor = "var(--text-3)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "var(--glass-1)";
                  e.currentTarget.style.borderColor = "var(--border-1)";
                }}
              >
                <span style={{ display: "inline-block", width: 20, fontWeight: 600, color: "var(--text-3)" }}>
                  {String.fromCharCode(65 + i)}.
                </span>
                {opt}
              </button>
            ))}
          </div>
        )}

        {/* Spelling */}
        {mode === "spelling" && (
          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={spellingInput}
              onChange={(e) => setSpellingInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && spellingInput.trim()) handleNext(spellingInput);
              }}
              placeholder="输入单词拼写..."
              autoFocus
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 8,
                border: "1px solid var(--border-1)",
                background: "var(--glass-1)",
                color: "var(--text-1)",
                fontSize: 14,
                outline: "none",
              }}
            />
            <button
              onClick={() => spellingInput.trim() && handleNext(spellingInput)}
              disabled={!spellingInput.trim()}
              style={{
                padding: "10px 16px",
                borderRadius: 8,
                border: "none",
                background: "var(--accent-grad)",
                color: "#fff",
                cursor: "pointer",
                fontSize: 13,
                opacity: spellingInput.trim() ? 1 : 0.5,
              }}
            >
              确认
            </button>
          </div>
        )}

        {/* Recall */}
        {mode === "recall" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <textarea
              value={recallInput}
              onChange={(e) => setRecallInput(e.target.value)}
              placeholder="写下你记得的释义或用法..."
              rows={4}
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                border: "1px solid var(--border-1)",
                background: "var(--glass-1)",
                color: "var(--text-1)",
                fontSize: 13,
                outline: "none",
                resize: "none",
              }}
            />
            <button
              onClick={() => recallInput.trim() && handleNext(recallInput)}
              disabled={!recallInput.trim()}
              style={{
                alignSelf: "flex-end",
                padding: "8px 16px",
                borderRadius: 8,
                border: "none",
                background: "var(--accent-grad)",
                color: "#fff",
                cursor: "pointer",
                fontSize: 13,
                opacity: recallInput.trim() ? 1 : 0.5,
              }}
            >
              提交
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
