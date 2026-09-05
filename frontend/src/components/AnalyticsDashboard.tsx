import { useEffect, useState } from "react";
import {
  ShieldAlert,
  TrendingUp,
  RefreshCw,
  Scale,
  FileSpreadsheet,
  AlertTriangle,
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import { getAnalyticsSummary } from "../api";
import type { AnalyticsSummary } from "../api";

const STATUS_COLORS: Record<string, string> = {
  COMPLIANT: "#10b981",
  NON_COMPLIANT: "#ef4444",
  NEEDS_MANUAL_REVIEW: "#f59e0b",
};

export default function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await getAnalyticsSummary();
      setData(summary);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading && !data) {
    return (
      <div className="analytics-loading card">
        <RefreshCw className="animate-spin text-accent" size={32} />
        <p className="mt-3 text-muted">Aggregating Legal Metrology enforcement data...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="analytics-error card">
        <AlertTriangle className="text-red" size={32} />
        <p className="mt-2 font-semibold">Unable to load Enforcement Intelligence</p>
        <p className="text-sm text-muted">{error}</p>
        <button onClick={fetchStats} className="btn-secondary mt-3">
          Retry
        </button>
      </div>
    );
  }

  const pieData = [
    { name: "Compliant", value: data?.compliant_count || 0, color: STATUS_COLORS.COMPLIANT },
    { name: "Non-Compliant", value: data?.non_compliant_count || 0, color: STATUS_COLORS.NON_COMPLIANT },
    { name: "Sec 15 Review", value: data?.manual_review_count || 0, color: STATUS_COLORS.NEEDS_MANUAL_REVIEW },
  ].filter((item) => item.value > 0);

  const fieldData = (data?.top_violated_fields || []).map((f) => ({
    name: f.field.replace(/_/g, " "),
    Violations: f.count,
  }));

  const contraventionData = (data?.top_contraventions || []).map((c) => ({
    name: c.contravention.length > 25 ? c.contravention.slice(0, 25) + "..." : c.contravention,
    Count: c.count,
  }));

  const brandData = (data?.top_offending_brands || []).map((b) => ({
    name: b.brand.length > 18 ? b.brand.slice(0, 18) + "..." : b.brand,
    Infractions: b.violations_count,
  }));

  const formattedFines = (data?.estimated_fines_inr || 0).toLocaleString("en-IN");

  return (
    <div className="analytics-dashboard">
      {/* Top Header */}
      <div className="analytics-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="badge badge-accent">OFFICER INTELLIGENCE PORTAL</span>
            <span className="text-xs text-muted">Legal Metrology Act, 2009 Enforcement</span>
          </div>
          <h2 className="text-2xl font-bold mt-1">Regulatory Enforcement & Violation Analytics</h2>
          <p className="text-sm text-muted">
            Population-level compliance monitoring, repetitive contravention patterns & fine liabilities.
          </p>
        </div>
        <button onClick={fetchStats} className="btn-secondary flex items-center gap-2" disabled={loading}>
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
          Refresh Stats
        </button>
      </div>

      {/* KPI Stats Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon-wrap bg-blue-500/10 text-blue-400">
            <FileSpreadsheet size={22} />
          </div>
          <div className="kpi-info">
            <div className="kpi-label">Total Commodities Audited</div>
            <div className="kpi-value">{data?.total_audits || 0}</div>
            <div className="kpi-subtext text-muted">Field raids & marketplace sweeps</div>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap bg-emerald-500/10 text-emerald-400">
            <TrendingUp size={22} />
          </div>
          <div className="kpi-info">
            <div className="kpi-label">Overall Compliance Rate</div>
            <div className="kpi-value text-green">{data?.compliance_rate || 0}%</div>
            <div className="kpi-subtext text-muted">Avg Score: {data?.average_compliance_score || 0}%</div>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap bg-rose-500/10 text-rose-400">
            <ShieldAlert size={22} />
          </div>
          <div className="kpi-info">
            <div className="kpi-label">Contravening Packages Flagged</div>
            <div className="kpi-value text-red">
              {(data?.non_compliant_count || 0) + (data?.manual_review_count || 0)}
            </div>
            <div className="kpi-subtext text-muted">
              {data?.violations_by_severity.critical || 0} Critical • {data?.violations_by_severity.major || 0} Major
            </div>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap bg-amber-500/10 text-amber-400">
            <Scale size={22} />
          </div>
          <div className="kpi-info">
            <div className="kpi-label">Estimated Fine Liabilities</div>
            <div className="kpi-value text-amber">₹{formattedFines}</div>
            <div className="kpi-subtext text-muted">Under Sections 36(1), 36(2) & 29</div>
          </div>
        </div>
      </div>

      {/* Primary Visualizations */}
      <div className="charts-grid mt-6">
        {/* Compliance Status Donut */}
        <div className="chart-card card">
          <h3 className="chart-title">Compliance Verdict Breakdown</h3>
          <p className="chart-subtitle">Distribution of inspected commodities by statutory status</p>
          {pieData.length > 0 ? (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={pieData}
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }: { name?: string; percent?: number }) =>
                      `${name || ""} ${(((percent ?? 0) * 100)).toFixed(0)}%`
                    }
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-chart text-muted">No audit data recorded yet.</div>
          )}
        </div>

        {/* Top Violated Declarations */}
        <div className="chart-card card">
          <h3 className="chart-title">Most Frequent Declaration Failures</h3>
          <p className="chart-subtitle">Rule 6 mandatory declarations omitted or misdeclared</p>
          {fieldData.length > 0 ? (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={fieldData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} angle={-15} textAnchor="end" />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8 }}
                  />
                  <Bar dataKey="Violations" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-chart text-muted">No violations logged yet.</div>
          )}
        </div>
      </div>

      {/* Secondary Visualizations */}
      <div className="charts-grid mt-6">
        {/* Act Contraventions */}
        <div className="chart-card card">
          <h3 className="chart-title">Statutory Contraventions by Legal Clause</h3>
          <p className="chart-subtitle">Legal Metrology Act, 2009 sections invoked</p>
          {contraventionData.length > 0 ? (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={contraventionData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} angle={-15} textAnchor="end" />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8 }}
                  />
                  <Bar dataKey="Count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-chart text-muted">No statutory citations logged yet.</div>
          )}
        </div>

        {/* Top Offending Brands */}
        <div className="chart-card card">
          <h3 className="chart-title">Repeat Offender Manufacturers / Packers</h3>
          <p className="chart-subtitle">Brands with multiple non-compliant packages</p>
          {brandData.length > 0 ? (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={brandData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} angle={-15} textAnchor="end" />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: 8 }}
                  />
                  <Bar dataKey="Infractions" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-chart text-muted">No manufacturer infractions recorded yet.</div>
          )}
        </div>
      </div>

      {/* Recent Inspection Activity Table */}
      <div className="card mt-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="chart-title">Recent Field Inspection Logs</h3>
            <p className="chart-subtitle">Latest regulatory checks conducted across trade points</p>
          </div>
          <span className="badge badge-outline">Live Sync Active</span>
        </div>

        {data?.recent_audits && data.recent_audits.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table-auto w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-muted uppercase">
                  <th className="py-2.5 px-3">Date & Time</th>
                  <th className="py-2.5 px-3">Commodity / Item</th>
                  <th className="py-2.5 px-3">Manufacturer / Packer</th>
                  <th className="py-2.5 px-3 text-center">Score</th>
                  <th className="py-2.5 px-3 text-center">Statutory Status</th>
                  <th className="py-2.5 px-3 text-center">Violations</th>
                  <th className="py-2.5 px-3 text-right">Notice</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_audits.map((a) => {
                  const statusClass =
                    a.overall_status === "COMPLIANT"
                      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                      : a.overall_status === "NEEDS_MANUAL_REVIEW"
                      ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                      : "text-rose-400 bg-rose-500/10 border-rose-500/20";

                  return (
                    <tr key={a.id} className="border-b border-border/50 hover:bg-surface/60 transition-colors">
                      <td className="py-2.5 px-3 text-xs font-mono text-muted">
                        {a.created_at ? new Date(a.created_at).toLocaleString("en-IN") : "—"}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-text">{a.product_name}</td>
                      <td className="py-2.5 px-3 text-muted text-xs">{a.manufacturer}</td>
                      <td className="py-2.5 px-3 text-center font-bold font-mono">
                        {a.compliance_score.toFixed(0)}%
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded border ${statusClass}`}>
                          {a.overall_status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono">
                        {a.violations_count > 0 ? (
                          <span className="text-red font-semibold">{a.violations_count}</span>
                        ) : (
                          <span className="text-green font-semibold">0</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <a
                          href={`/api/report/html/${a.id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-accent hover:underline font-mono"
                        >
                          View Notice ↗
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-6 text-muted text-sm">
            No audits recorded yet. Conduct an inspection via the Package Scanner or URL Auditor.
          </div>
        )}
      </div>
    </div>
  );
}
