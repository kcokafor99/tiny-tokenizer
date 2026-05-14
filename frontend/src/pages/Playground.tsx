import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { TokenStrip } from "@/components/TokenStrip"
import { api, ApiError, type TokenizeResponse, type TokenizerInfo } from "@/lib/api"
import { log } from "@/lib/logger"
import { track } from "@/lib/posthog"

const DEFAULT_PROMPT = "onyé iberibe imaka nnó"

export function Playground() {
  const [text, setText] = useState(DEFAULT_PROMPT)
  const [tokenizer, setTokenizer] = useState("tiny")
  const [available, setAvailable] = useState<TokenizerInfo[]>([])
  const [result, setResult] = useState<TokenizeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.tokenizers()
      .then((r) => setAvailable(r.tokenizers))
      .catch((e) => log.warn("tokenizers_fetch_failed", { error: String(e) }))
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const r = await api.tokenize(text, tokenizer)
      setResult(r)
      track("prompt_tokenized", {
        tokenizer,
        text_len: text.length,
        token_count: r.token_count,
      })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err)
      setError(msg)
      log.warn("tokenize_failed_in_ui", { error: msg })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-10">
        <h1 className="font-display text-4xl tracking-tight">TinyTokenizer</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Visualize and compare how LLMs tokenize your text.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-3 font-mono text-sm focus:border-[var(--color-maroon)] focus:outline-none focus:ring-1 focus:ring-[var(--color-maroon)]"
          placeholder="Type or paste text…"
        />

        <div className="flex items-center gap-3">
          <label className="text-sm text-[var(--color-text-secondary)]">
            Tokenizer
          </label>
          <select
            value={tokenizer}
            onChange={(e) => setTokenizer(e.target.value)}
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5 text-sm"
          >
            {available.length === 0 ? (
              <option value="tiny">tiny</option>
            ) : (
              available.map((t) => (
                <option key={t.slug} value={t.slug}>
                  {t.label}
                </option>
              ))
            )}
          </select>

          <Button type="submit" variant="maroon" disabled={loading}>
            {loading ? "Tokenizing…" : "Tokenize"}
          </Button>
        </div>
      </form>

      {error && (
        <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {result && (
        <section className="mt-10 space-y-4">
          <div className="flex items-baseline gap-4 text-sm text-[var(--color-text-secondary)]">
            <span>
              <span className="font-display text-2xl text-[var(--color-text)]">
                {result.token_count}
              </span>{" "}
              tokens
            </span>
            <span>·</span>
            <span>{result.duration_ms} ms</span>
          </div>
          <TokenStrip tokens={result.tokens} />
        </section>
      )}
    </div>
  )
}
