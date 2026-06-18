/* CodePilot-inspired AI Elements — adapted for LearnForge */

export { Message, MessageContent, MessageActions, MessageAction, MessageResponse, AIMessage } from "./message";
export type { MessageProps, MessageContentProps, MessageActionsProps, MessageActionProps, MessageResponseProps, AIMessageProps } from "./message";

export { Shimmer } from "./shimmer";
export type { TextShimmerProps } from "./shimmer";

export { Tool, ToolHeader, ToolContent, ToolInput, ToolOutput } from "./tool";
export type { ToolProps, ToolHeaderProps, ToolContentProps, ToolInputProps, ToolOutputProps } from "./tool";

export { Reasoning, ReasoningTrigger, ReasoningContent } from "./reasoning";
export type { ReasoningProps, ReasoningTriggerProps, ReasoningContentProps } from "./reasoning";

export { ChainOfThought, ChainOfThoughtHeader, ChainOfThoughtContent, ChainOfThoughtStep } from "./chain-of-thought";
export type { ChainOfThoughtProps, ChainOfThoughtHeaderProps, ChainOfThoughtContentProps, ChainOfThoughtStepProps } from "./chain-of-thought";

export { PromptInput, PromptInputAttachments, PromptInputBody, PromptInputFooter, PromptInputComposed, usePromptInput } from "./prompt-input";
export type { PromptInputProps, PromptInputAttachmentsProps, PromptInputBodyProps, PromptInputFooterProps, PromptInputComposedProps, FileAttachment } from "./prompt-input";

export { MessageList } from "./message-list";
export type { MessageListProps } from "./message-list";

export { StreamingMessage } from "./streaming-message";
export type { StreamingMessageProps } from "./streaming-message";

export { Cockpit } from "./cockpit";
export type { CockpitProps, SkillStatus } from "./cockpit";
