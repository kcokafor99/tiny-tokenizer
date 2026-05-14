import { Link, Route, Routes } from "react-router-dom"
import { Playground } from "@/pages/Playground"
import { Learn } from "@/pages/Learn"

export default function App() {
  return (
    <div className="min-h-full">
      <nav className="border-b border-[var(--color-border)] bg-[var(--color-bg-warm)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <Link
            to="/"
            className="font-display text-lg text-[var(--color-maroon)] hover:text-[var(--color-maroon-hover)]"
          >
            TinyTokenizer
          </Link>
          <div className="flex gap-5 text-sm">
            <Link
              to="/"
              className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
            >
              Playground
            </Link>
            <Link
              to="/learn"
              className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
            >
              Learn
            </Link>
            <a
              href="https://github.com/kcokafor99/tiny-tokenizer"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
            >
              GitHub
            </a>
          </div>
        </div>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<Playground />} />
          <Route path="/learn" element={<Learn />} />
        </Routes>
      </main>
    </div>
  )
}
