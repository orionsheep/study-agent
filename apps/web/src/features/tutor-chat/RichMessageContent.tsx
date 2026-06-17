import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { CustomHtmlAppRenderer } from "../custom-html-app/CustomHtmlAppRenderer";
import { parseShowWidget } from "../custom-html-app/widgetParser";

type Props = {
  text: string;
  onGenerate?: (prompt: string, attachments?: Array<{ name: string; preview?: string }>, skillLabel?: { key?: string; label: string; color: string; bgColor: string; borderColor: string }) => void | Promise<void>;
};

type Segment =
  | { kind: "markdown"; text: string }
  | { kind: "widget"; code: string; closed: boolean };

type GenerateAction = {
  capability: string;
  topic: string;
  skillKey: string;
  label: string;
  prompt: string;
};

function promptForGenerate(capability: string, topic: string) {
  if (capability === "interactive_demo") return `请基于${topic}生成一个可以在左侧画布打开的互动演示 App`;
  if (capability === "custom_infographic") return `请基于${topic}生成一张教学信息图`;
  if (capability === "mindmap") return `请基于${topic}生成一张思维导图`;
  if (capability === "quiz") return `请基于${topic}生成一组练习题`;
  if (capability === "code_lab") return `请基于${topic}生成一个代码实验 App`;
  return `请基于${topic}生成一张教学图片`;
}

function skillKeyForCapability(capability: string) {
  if (capability === "interactive_demo") return "demo";
  if (capability === "ppt") return "ppt";
  if (capability === "image_explanation" || capability === "custom_infographic") return "image";
  if (capability === "video_search") return "video";
  return capability;
}

function extractGenerateActions(text: string): { cleanText: string; actions: GenerateAction[] } {
  const actions: GenerateAction[] = [];
  const cleanText = text.replace(/\[\[generate:([^:\]]+):([^:\]]+)(?::([^\]]+))?\]\]([\s\S]*?)\[\[\/generate\]\]/g, (_all, capability, topic, skillKey, label) => {
    const safeCapability = String(capability || "image_explanation").trim();
    const safeTopic = String(topic || "当前主题").trim();
    const safeSkillKey = String(skillKey || skillKeyForCapability(safeCapability)).trim();
    actions.push({
      capability: safeCapability,
      topic: safeTopic,
      skillKey: safeSkillKey,
      label: String(label || `生成 ${safeTopic}`).trim(),
      prompt: promptForGenerate(safeCapability, safeTopic)
    });
    return "";
  }).replace(/\[\[generate:[\s\S]*$/g, "");
  return { cleanText, actions };
}

function splitRichSegments(input: string): Segment[] {
  const segments: Segment[] = [];
  let remaining = input;
  while (remaining.includes("```show-widget")) {
    const parsed = parseShowWidget(remaining);
    if (parsed.textBefore) {
      segments.push({ kind: "markdown", text: parsed.textBefore });
    }
    if (parsed.widgetCode) {
      segments.push({ kind: "widget", code: parsed.widgetCode, closed: parsed.isClosed });
    }
    const start = remaining.indexOf("```show-widget");
    const afterStart = remaining.slice(start + "```show-widget".length);
    const close = afterStart.indexOf("```");
    if (close === -1) {
      remaining = "";
    } else {
      remaining = afterStart.slice(close + 3);
    }
  }
  if (remaining) {
    segments.push({ kind: "markdown", text: remaining });
  }
  return segments.length ? segments : [{ kind: "markdown", text: input }];
}

export function RichMessageContent({ text, onGenerate }: Props) {
  const { cleanText, actions } = extractGenerateActions(text);
  const segments = splitRichSegments(cleanText);
  return (
    <div className="rich-message">
      {segments.map((segment, index) => {
        if (segment.kind === "widget") {
          return (
            <section className={`rich-widget ${segment.closed ? "is-final" : "is-streaming"}`} key={`widget-${index}`}>
              <div className="rich-widget-head">
                <span className="pdot" />
                <strong>{segment.closed ? "交互式学习组件" : "正在生成交互式学习组件"}</strong>
              </div>
              <CustomHtmlAppRenderer code={segment.code} theme="dark" />
            </section>
          );
        }
        return (
          <div className="markdown-response" key={`markdown-${index}`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noreferrer">
                    {children}
                  </a>
                ),
                code: ({ children, className }) => {
                  const inline = !className;
                  if (inline) return <code>{children}</code>;
                  return <code className={className}>{children}</code>;
                }
              }}
            >
              {segment.text}
            </ReactMarkdown>
          </div>
        );
      })}
      {actions.length ? (
        <div className="generate-suggestions" data-testid="generate-suggestions">
          {actions.map((action) => (
            <button
              key={`${action.capability}-${action.topic}`}
              type="button"
              onClick={() => onGenerate?.(action.prompt, undefined, {
                key: action.skillKey,
                label: action.label,
                color: "#64d8ff",
                bgColor: "rgba(100, 216, 255, 0.12)",
                borderColor: "rgba(100, 216, 255, 0.35)",
              })}
            >
              <span>生成到左侧画布</span>
              <strong>{action.label}</strong>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
