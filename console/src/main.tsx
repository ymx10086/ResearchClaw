import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AutoTranslate, I18nProvider } from "./i18n";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <BrowserRouter>
        <AutoTranslate>
          <App />
        </AutoTranslate>
      </BrowserRouter>
    </I18nProvider>
  </React.StrictMode>,
);
