import React from "react";
import { createRoot } from "react-dom/client";
import { LearnForgeApp } from "./LearnForgeApp";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LearnForgeApp />
  </React.StrictMode>
);
