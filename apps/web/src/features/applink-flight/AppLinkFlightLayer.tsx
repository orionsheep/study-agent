import { AnimatePresence, motion } from "framer-motion";

export type FlightState = {
  id: string;
  from: { x: number; y: number };
  to: { x: number; y: number };
  label: string;
};

type Props = {
  flight: FlightState | null;
};

export function AppLinkFlightLayer({ flight }: Props) {
  const dx = flight ? flight.to.x - flight.from.x : 0;
  const dy = flight ? flight.to.y - flight.from.y : 0;
  const distance = Math.hypot(dx, dy);
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);
  return (
    <div className="flight-layer" aria-hidden="true">
      <AnimatePresence>
        {flight ? (
          <>
            <motion.div
              key={`${flight.id}-streak`}
              className="flight-streak"
              style={{
                left: flight.from.x,
                top: flight.from.y,
                width: distance,
                rotate: `${angle}deg`
              }}
              initial={{ opacity: 0, clipPath: "inset(0 100% 0 0)" }}
              animate={{
                opacity: [0.2, 1, 0],
                clipPath: ["inset(0 100% 0 0)", "inset(0 0% 0 0)", "inset(0 0 0 90%)"]
              }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.66, ease: [0.22, 1, 0.36, 1] }}
            />
            {[0, 1, 2].map((index) => (
              <motion.i
                key={`${flight.id}-particle-${index}`}
                className={`flight-particle p${index + 1}`}
                style={{ left: flight.from.x, top: flight.from.y }}
                initial={{ opacity: 0, x: 0, y: 0, scale: 0.55 }}
                animate={{
                  opacity: [0, 1, 0],
                  x: [0, dx * 0.52, dx],
                  y: [0, dy * 0.52 - 14 - index * 8, dy],
                  scale: [0.55, 1, 0.42]
                }}
                transition={{ duration: 0.72, delay: index * 0.055, ease: "easeInOut" }}
              />
            ))}
            <motion.div
              key={`${flight.id}-label`}
              className="applink-flight active"
              initial={{ opacity: 0, x: flight.from.x, y: flight.from.y, scale: 0.72 }}
              animate={{ opacity: [0, 1, 1, 0], x: flight.to.x, y: flight.to.y, scale: [0.72, 1.08, 0.92] }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.78, ease: "easeInOut" }}
            >
              <span>{flight.label}</span>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
