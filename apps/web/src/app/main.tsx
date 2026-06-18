import React from "react";
import { createRoot } from "react-dom/client";
import { LearnForgeApp } from "./LearnForgeApp";
import "katex/dist/katex.min.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LearnForgeApp />
  </React.StrictMode>
);
