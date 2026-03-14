import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { GroupBy } from "@/api/summary";

interface GroupByToggleProps {
  value: GroupBy;
  onChange: (value: GroupBy) => void;
}

export default function GroupByToggle({ value, onChange }: GroupByToggleProps) {
  return (
    <ToggleGroup
      type="single"
      value={value}
      onValueChange={(v) => {
        if (v === "category" || v === "payment_method") {
          onChange(v);
        }
      }}
      className="rounded-lg p-0.5 gap-0"
      style={{ backgroundColor: "var(--color-surface-raised)" }}
    >
      <ToggleGroupItem
        value="category"
        className="px-4 h-9 text-sm font-medium rounded-md data-[state=on]:text-[var(--color-accent-fg)] data-[state=off]:text-[var(--color-muted)] transition-all duration-[var(--duration-fast)]"
        style={{
          ...(value === "category"
            ? { backgroundColor: "var(--color-accent)", color: "var(--color-accent-fg)" }
            : {}),
        }}
        aria-label="Group by category"
      >
        Category
      </ToggleGroupItem>
      <ToggleGroupItem
        value="payment_method"
        className="px-4 h-9 text-sm font-medium rounded-md data-[state=on]:text-[var(--color-accent-fg)] data-[state=off]:text-[var(--color-muted)] transition-all duration-[var(--duration-fast)]"
        style={{
          ...(value === "payment_method"
            ? { backgroundColor: "var(--color-accent)", color: "var(--color-accent-fg)" }
            : {}),
        }}
        aria-label="Group by payment method"
      >
        Payment Method
      </ToggleGroupItem>
    </ToggleGroup>
  );
}
