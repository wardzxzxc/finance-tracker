import { Skeleton } from "@/components/ui/skeleton";

export default function ChartSkeleton() {
  return (
    <div className="w-full flex flex-col items-center gap-4 py-4">
      {/* Pie chart placeholder */}
      <div className="relative">
        <Skeleton
          className="rounded-full"
          style={{
            width: 240,
            height: 240,
            background: `linear-gradient(
              135deg,
              var(--color-surface-raised) 0%,
              var(--color-border) 50%,
              var(--color-surface-raised) 100%
            )`,
            backgroundSize: "200% 200%",
            animation: "shimmer 2s ease-in-out infinite",
          }}
        />
        <div
          className="absolute inset-0 m-auto rounded-full"
          style={{
            width: 80,
            height: 80,
            backgroundColor: "var(--color-bg)",
          }}
        />
      </div>

      {/* Legend placeholder */}
      <div className="flex flex-col gap-2 w-full max-w-xs">
        {[80, 64, 72, 56].map((w, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton
              className="rounded-full"
              style={{
                width: 10,
                height: 10,
                flexShrink: 0,
                background: "var(--color-surface-raised)",
              }}
            />
            <Skeleton
              style={{
                height: 12,
                width: `${w}%`,
                borderRadius: 4,
                background: "var(--color-surface-raised)",
              }}
            />
          </div>
        ))}
      </div>

      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 200%; }
          100% { background-position: -200% -200%; }
        }
      `}</style>
    </div>
  );
}
