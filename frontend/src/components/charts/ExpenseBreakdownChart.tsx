import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getExpenseSummary, type GroupBy } from "@/api/summary";
import MonthNavigator from "./MonthNavigator";
import GroupByToggle from "./GroupByToggle";
import PieChartDisplay from "./PieChartDisplay";
import ChartSkeleton from "./ChartSkeleton";

function parseMonth(raw: string | null): { year: number; month: number } | null {
  if (!raw) return null;
  const [y, m] = raw.split("-").map(Number);
  if (!y || !m || m < 1 || m > 12) return null;
  return { year: y, month: m };
}

function isValidGroupBy(v: string | null): v is GroupBy {
  return v === "category" || v === "payment_method";
}

export default function ExpenseBreakdownChart() {
  const [searchParams, setSearchParams] = useSearchParams();

  const now = new Date();
  const defaultYear = now.getFullYear();
  const defaultMonth = now.getMonth() + 1;

  const parsedMonth = parseMonth(searchParams.get("month"));
  const rawGroupBy = searchParams.get("groupBy");

  const [year, setYear] = useState(parsedMonth?.year ?? defaultYear);
  const [month, setMonth] = useState(parsedMonth?.month ?? defaultMonth);
  const [groupBy, setGroupBy] = useState<GroupBy>(
    isValidGroupBy(rawGroupBy) ? rawGroupBy : "category"
  );

  // Sync filter state → URL
  useEffect(() => {
    setSearchParams(
      {
        month: `${year}-${String(month).padStart(2, "0")}`,
        groupBy,
      },
      { replace: true }
    );
  }, [year, month, groupBy, setSearchParams]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["expense-summary", year, month, groupBy],
    queryFn: () => getExpenseSummary(month, year, groupBy),
  });

  const isNextDisabled =
    year === now.getFullYear() && month === now.getMonth() + 1;

  function handlePrev() {
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else {
      setMonth((m) => m - 1);
    }
  }

  function handleNext() {
    if (isNextDisabled) return;
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else {
      setMonth((m) => m + 1);
    }
  }

  return (
    <div
      className="rounded-xl p-5 md:p-6"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
      }}
    >
      {/* Controls */}
      <div className="flex flex-col gap-3 mb-5 md:flex-row md:items-center md:justify-between">
        <MonthNavigator
          year={year}
          month={month}
          onPrev={handlePrev}
          onNext={handleNext}
          isNextDisabled={isNextDisabled}
        />
        <GroupByToggle value={groupBy} onChange={setGroupBy} />
      </div>

      {/* Body */}
      {isLoading ? (
        <ChartSkeleton />
      ) : isError ? (
        <p
          className="text-sm py-8 text-center"
          style={{ color: "var(--color-danger)" }}
        >
          Failed to load expense summary. Please try again.
        </p>
      ) : !data || data.groups.length === 0 ? (
        <p
          className="text-sm py-8 text-center"
          style={{ color: "var(--color-muted)" }}
        >
          No expenses recorded for{" "}
          {new Date(year, month - 1).toLocaleString("default", {
            month: "long",
            year: "numeric",
          })}
          . Add a transaction to see your breakdown.
        </p>
      ) : (
        <PieChartDisplay groups={data.groups} total={data.total} />
      )}
    </div>
  );
}
