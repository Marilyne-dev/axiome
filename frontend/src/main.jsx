import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./styles.css";
import "./dashboard.css";
import "./forms.css";
import "./tabs.css";

createRoot(document.getElementById("root")).render(<BrowserRouter><App /></BrowserRouter>);
