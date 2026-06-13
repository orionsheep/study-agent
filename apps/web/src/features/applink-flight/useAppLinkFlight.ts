import { useCallback, useState } from "react";
import type { CanvasApp, ChatAppLink } from "@learnforge/app-protocol";
import { openAppLink, type SessionContext } from "../../lib/api/client";
import type { FlightState } from "./AppLinkFlightLayer";

export function useAppLinkFlight(onFocus: (appId: string, nextState?: CanvasApp["state"]) => void, sessionContext: SessionContext) {
  const [flight, setFlight] = useState<FlightState | null>(null);

  const open = useCallback(
    async (link: ChatAppLink, fromRect: DOMRect) => {
      const nextState: CanvasApp["state"] = link.action === "fullscreen" ? "fullscreen" : link.action === "split" ? "split_left" : "focused";
      onFocus(link.app_id, nextState);
      await new Promise((resolve) => window.requestAnimationFrame(resolve));
      await new Promise((resolve) => window.requestAnimationFrame(resolve));
      const target = document.querySelector(`[data-app-id="${link.app_id}"]`);
      const toRect = target?.getBoundingClientRect();
      const state: FlightState = {
        id: `${link.link_id}-${Date.now()}`,
        from: { x: fromRect.left + fromRect.width / 2, y: fromRect.top + fromRect.height / 2 },
        to: {
          x: (toRect?.left ?? window.innerWidth * 0.28) + (toRect?.width ?? 280) / 2,
          y: (toRect?.top ?? window.innerHeight * 0.48) + (toRect?.height ?? 220) / 2
        },
        label: link.label
      };
      setFlight(state);
      await openAppLink(link, sessionContext);
      window.setTimeout(() => setFlight(null), 900);
    },
    [onFocus, sessionContext]
  );

  return { flight, open };
}
