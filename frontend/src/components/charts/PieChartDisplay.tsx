import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { SummaryGroup } from "@/api/summary";

interface PieChartDisplayProps {
  groups: SummaryGroup[];
  total: number;
}

interface TooltipEntry {
  active?: boolean;
  payload?: Array<{ payload: SummaryGroup }>;
}

function CustomTooltip({ active, payload }: TooltipEntry) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      className="px-3 py-2 rounded-md text-sm shadow-lg"
      style={{
        backgroundColor: "var(--color-surface-raised)",
        border: "1px solid var(--color-border)",
        fontFamily: "var(--font-body)",
        color: "var(--color-text)",
      }}
    >
      <span className="font-semibold">{d.name}</span>
      {" — "}
      <span>${Number(d.amount).toFixed(2)}</span>
      {" — "}
      <span style={{ color: "var(--color-accent)" }}>{d.percentage}%</span>
    </div>
  );
}

function CustomLegend({ groups }: { groups: SummaryGroup[] }) {
  return (
    <ul className="flex flex-col gap-2 py-2">
      {groups.map((g) => (
        <li key={g.id} className="flex items-center gap-2 text-sm">
          <span
            className="inline-block rounded-full flex-shrink-0"
            style={{ width: 10, height: 10, backgroundColor: g.color }}
          />
          <span style={{ color: "var(--color-text)" }} className="font-medium truncate max-w-[140px]">
            {g.name}
          </span>
          <span style={{ color: "var(--color-muted)" }} className="ml-auto tabular-nums">
            ${Number(g.amount).toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function PieChartDisplay({ groups }: PieChartDisplayProps) {
  return (
    <div className="flex flex-col md:flex-row items-center gap-6 w-full">
      {/* Chart */}
      <div className="w-full md:flex-1" style={{ minHeight: 260 }}>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={groups}
              dataKey="amount"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius="38%"
              outerRadius="70%"
              paddingAngle={2}
              isAnimationActive
              animationBegin={0}
              animationDuration={600}
            >
              {groups.map((g) => (
                <Cell key={g.id} fill={g.color} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="w-full md:w-48 md:flex-shrink-0">
        <CustomLegend groups={groups} />
      </div>
    </div>
  );
}
