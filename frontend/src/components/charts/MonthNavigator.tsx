import { format } from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface MonthNavigatorProps {
  year: number;
  month: number;
  onPrev: () => void;
  onNext: () => void;
  isNextDisabled: boolean;
}

export default function MonthNavigator({
  year,
  month,
  onPrev,
  onNext,
  isNextDisabled,
}: MonthNavigatorProps) {
  const label = format(new Date(year, month - 1), "MMMM yyyy");

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onPrev}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-md transition-colors duration-[var(--duration-fast)] hover:bg-[var(--color-accent-dim)] text-[var(--color-accent)] active:scale-95"
        aria-label="Previous month"
      >
        <ChevronLeft size={20} strokeWidth={2.5} />
      </button>

      <span
        className="min-w-[9rem] text-center text-lg font-semibold tracking-tight transition-opacity duration-[var(--duration-fast)]"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        {label}
      </span>

      <button
        onClick={onNext}
        disabled={isNextDisabled}
        aria-disabled={isNextDisabled}
        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-md transition-colors duration-[var(--duration-fast)] hover:bg-[var(--color-accent-dim)] text-[var(--color-accent)] active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:active:scale-100"
        aria-label="Next month"
      >
        <ChevronRight size={20} strokeWidth={2.5} />
      </button>
    </div>
  );
}
