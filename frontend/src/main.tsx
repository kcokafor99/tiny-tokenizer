import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import "./index.css"
import App from "./App.tsx"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { initPosthog, identify } from "@/lib/posthog"
import { getFingerprint } from "@/lib/fingerprint"
import { log } from "@/lib/logger"

initPosthog()

getFingerprint().then((fp) => identify(fp)).catch(() => {})

window.addEventListener("error", (e) => {
  log.error("window_error", { message: e.message, filename: e.filename, lineno: e.lineno })
})
window.addEventListener("unhandledrejection", (e) => {
  const reason = e.reason instanceof Error ? e.reason.message : String(e.reason)
  log.error("unhandled_rejection", { reason })
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
