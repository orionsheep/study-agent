// English Workspace type definitions

export interface WordEntry {
  word: string;
  phonetic?: string;
  definition?: string;
  translation?: string;
  collinsLevel?: string;
  bnc?: number;
  frq?: number;
  tag?: string;
}

export interface WordDetail {
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
}

export interface FissionNode {
  id: string;
  label: string;
  group?: string;
  type?: "root" | "synonym" | "antonym" | "derivative" | "related";
  val?: number;
}

export interface FissionLink {
  source: string;
  target: string;
  relation?: string;
  type?: string;
}

export interface FissionGraphData {
  nodes: FissionNode[];
  links: FissionLink[];
}

export interface QuizQuestion {
  word: string;
  quizType: "multiple_choice" | "spelling" | "recall";
  question: string;
  options?: string[];
  correctAnswer: string;
  hint?: string;
}

export interface QuizResult {
  word: string;
  quizType: string;
  score: number;
  answers: Array<{ question: string; userAnswer: string; correct: boolean }>;
}

export interface WordLibrary {
  id: string;
  name: string;
  wordCount: number;
  description?: string;
}

export interface StudyPlan {
  dailyGoal: number;
  todayLearned: number;
  totalLearned: number;
  streak: number;
}

export type EnglishTab = "vocabulary" | "fission" | "quiz" | "chat";
