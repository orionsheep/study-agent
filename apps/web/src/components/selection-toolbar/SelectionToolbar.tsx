import { useEffect, useState, useCallback, useRef } from "react";
import { BookOpen } from "lucide-react";

interface Props {
  onLookup: (word: string) => void;
}

export function SelectionToolbar({ onLookup }: Props) {
  const [selection, setSelection] = useState<{ text: string; x: number; y: number } | null>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearSelection = useCallback(() => {
    setSelection(null);
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const handleSelectionChange = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
        clearSelection();
        return;
      }

      const text = sel.toString().trim();
      // Only match pure English words (1-30 letters)
      if (!/^[a-zA-Z]{1,30}$/.test(text)) {
        clearSelection();
        return;
      }

      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();

      // Position above the selection, centered
      const x = rect.left + rect.width / 2;
      const y = rect.top - 8;

      setSelection({ text: text.toLowerCase(), x, y });

      // Auto-hide after 5 seconds
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      hideTimerRef.current = setTimeout(() => setSelection(null), 5000);
    };

    document.addEventListener("selectionchange", handleSelectionChange);
    return () => {
      document.removeEventListener("selectionchange", handleSelectionChange);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, [clearSelection]);

  if (!selection) return null;

  return (
    <div
      className="selection-toolbar"
      style={{
        position: "fixed",
        left: selection.x,
        top: selection.y,
        transform: "translate(-50%, -100%)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 12px",
        borderRadius: 10,
        background: "linear-gradient(180deg, var(--glass-2), var(--glass-1))",
        border: "1px solid var(--glass-border-hi)",
        boxShadow: "var(--shadow-lg)",
        backdropFilter: "blur(22px) saturate(1.2)",
        fontSize: 13,
        color: "var(--text-1)",
        whiteSpace: "nowrap",
        pointerEvents: "auto",
      }}
      onMouseDown={(e) => e.preventDefault()}
    >
      <span style={{ color: "var(--text-3)", fontWeight: 500 }}>{selection.text}</span>
      <div style={{ width: 1, height: 16, background: "var(--border-1)" }} />
      <button
        onClick={() => {
          onLookup(selection.text);
          clearSelection();
        }}
        style={{
          display: "flex", alignItems: "center", gap: 4,
          padding: "4px 10px", borderRadius: 6, border: "none",
          background: "var(--accent-grad)", color: "#fff",
          cursor: "pointer", fontSize: 13, fontWeight: 500,
        }}
      >
        <BookOpen size={13} /> 查单词
      </button>
    </div>
  );
}
