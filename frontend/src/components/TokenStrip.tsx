import { type TokenInfo } from "@/lib/api"
import { cn } from "@/lib/utils"

const PALETTE = [
  "bg-[var(--color-maroon-light)] text-[var(--color-maroon)] border-[var(--color-maroon-border)]",
  "bg-blue-50 text-blue-700 border-blue-100",
  "bg-amber-50 text-amber-700 border-amber-100",
  "bg-emerald-50 text-emerald-700 border-emerald-100",
  "bg-violet-50 text-violet-700 border-violet-100",
  "bg-orange-50 text-orange-700 border-orange-100",
] as const

function displayChar(t: TokenInfo) {
  if (!t.valid_utf8) return `\\x${t.bytes_hex}`
  if (t.display === " ") return "·"
  if (t.display === "\n") return "↵"
  if (t.display === "\t") return "→"
  return t.display
}

export function TokenStrip({ tokens }: { tokens: TokenInfo[] }) {
  if (tokens.length === 0) {
    return (
      <p className="font-mono text-sm text-[var(--color-text-muted)]">
        Nothing to tokenize yet.
      </p>
    )
  }
  return (
    <div className="flex flex-wrap gap-1">
      {tokens.map((t, i) => (
        <span
          key={i}
          title={`id ${t.id} · ${t.bytes_hex}`}
          className={cn(
            "rounded-md border px-1.5 py-0.5 font-mono text-sm leading-tight",
            PALETTE[i % PALETTE.length],
          )}
        >
          {displayChar(t)}
        </span>
      ))}
    </div>
  )
}
