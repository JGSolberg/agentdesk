import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import CommandPalette from "./CommandPalette";
import "./styles.css";
import "./board.css";
import "./ticket-detail.css";
import "./ticket-lifecycle.css";
import "./repositories.css";
import "./command-palette.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <CommandPalette />
    </BrowserRouter>
  </React.StrictMode>,
);
