import type { ChatAppLink } from "@learnforge/app-protocol";
import { ExternalLink } from "lucide-react";

type Props = {
  link: ChatAppLink;
  onOpen: (link: ChatAppLink, rect: DOMRect) => void;
};

export function AppLinkChip({ link, onOpen }: Props) {
  return (
    <button
      className="app-link-chip applink"
      data-testid={`applink-${link.app_id}`}
      onClick={(event) => onOpen(link, event.currentTarget.getBoundingClientRect())}
      title={`打开并聚焦 ${link.label}`}
    >
      <span className="lk-ico"><ExternalLink size={12} /></span>
      <span>{link.label}</span>
    </button>
  );
}
