import { motion } from "motion/react";
import ExpenseBreakdownChart from "@/components/charts/ExpenseBreakdownChart";

export default function DashboardPage() {
  return (
    <main className="min-h-dvh px-4 py-6 md:px-8 md:py-10 max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 0.5,
          ease: [0.16, 1, 0.3, 1],
        }}
      >
        <h1
          className="text-2xl font-bold mb-6 tracking-tight"
          style={{ fontFamily: "var(--font-heading)", color: "var(--color-text)" }}
        >
          Dashboard
        </h1>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.5,
            ease: [0.16, 1, 0.3, 1],
            delay: 0.1,
          }}
        >
          <h2
            className="text-sm font-semibold uppercase tracking-widest mb-3"
            style={{ color: "var(--color-muted)" }}
          >
            Expense Breakdown
          </h2>
          <ExpenseBreakdownChart />
        </motion.div>
      </motion.div>
    </main>
  );
}
