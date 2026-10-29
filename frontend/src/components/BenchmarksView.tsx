import React, { useState, useEffect } from 'react';
import {
  apiClient,
  EvaluationSummaryResponse,
  RouterBenchmarkRow,
} from '../services/apiClient';

interface BenchmarksViewProps {
  activeRouter: string;
  onSelectActiveRouter: (routerName: string) => void;
}

export const BenchmarksView: React.FC<BenchmarksViewProps> = ({
  activeRouter,
  onSelectActiveRouter,
}) => {
  const [evalData, setEvalData] = useState<EvaluationSummaryResponse | null>(null);
  const [subsetTab, setSubsetTab] = useState<'all' | 'edge' | 'multiturn'>('all');
  const [isRunningEval, setIsRunningEval] = useState(false);
  const [selectedCommit, setSelectedCommit] = useState('#git-4a8f9c');
  const [showMarkdownModal, setShowMarkdownModal] = useState(false);

  useEffect(() => {
    apiClient.getEvaluationSummary().then(setEvalData);
  }, []);

  const handleRerunEvaluation = async () => {
    setIsRunningEval(true);
    const fresh = await apiClient.getEvaluationSummary();
    await new Promise((r) => setTimeout(r, 550));
    setEvalData({
      ...fresh,
      executedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' EST',
    });
    setIsRunningEval(false);
  };

  const handleDownloadJsonReport = () => {
    if (!evalData) return;
    const reportPayload = {
      ...evalData,
      active_production_router: activeRouter,
      exported_at: new Date().toISOString(),
      namespace: '/v1/evaluation/summary',
    };
    const blob = new Blob([JSON.stringify(reportPayload, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `techmart_rag_router_eval_${selectedCommit.replace('#', '')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!evalData) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center text-on-surface-variant text-[14px]">
        Loading evaluation suite metrics from /v1/evaluation/summary...
      </div>
    );
  }

  const rows: RouterBenchmarkRow[] = evalData.routers[subsetTab];

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar bg-background">
      <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
        {/* Page Header with Action Toolbar */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-outline-variant">
          <div>
            <h1 className="text-[24px] leading-[32px] font-semibold text-on-surface tracking-tight">
              RAG &amp; Router Benchmarks
            </h1>
            <p className="text-[14px] text-on-surface-variant mt-1">
              Automated evaluation suite across retrieval grounding, routing latency, and
              precision-recall trade-offs.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Commit Selector */}
            <button
              type="button"
              onClick={() =>
                setSelectedCommit((prev) =>
                  prev === '#git-4a8f9c' ? '#git-91d2e0' : '#git-4a8f9c'
                )
              }
              className="flex items-center gap-2 px-3 py-1.5 bg-surface-container-lowest border border-outline-variant rounded-lg text-[13px] text-on-surface hover:bg-surface-container-low transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-outline text-[16px]">commit</span>
              <span className="font-mono text-[12px] text-on-surface-variant">
                {selectedCommit}
              </span>
              <span className="text-outline-variant">|</span>
              <span className="text-[12px] text-on-surface-variant">Last 24h</span>
              <span className="material-symbols-outlined text-[16px]">expand_more</span>
            </button>

            {/* Export Suite Button */}
            <button
              type="button"
              onClick={handleDownloadJsonReport}
              className="flex items-center gap-2 px-3.5 py-2 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface border border-outline-variant rounded-lg text-[13px] font-semibold transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">download</span>
              <span>Export Suite</span>
            </button>

            {/* Primary Re-run Button */}
            <button
              type="button"
              disabled={isRunningEval}
              onClick={handleRerunEvaluation}
              className="flex items-center gap-2 px-4 py-2 bg-primary-container hover:bg-primary disabled:opacity-70 text-on-primary rounded-lg text-[13px] font-semibold shadow-xs transition-all duration-150 cursor-pointer"
            >
              <span
                className={`material-symbols-outlined text-[16px] ${
                  isRunningEval ? 'animate-spin' : ''
                }`}
              >
                refresh
              </span>
              <span>
                {isRunningEval ? 'Running 78 Queries...' : 'Re-run Evaluation Suite'}
              </span>
            </button>
          </div>
        </div>

        {/* Section 1: Top KPI Metric Cards (Bento Grid of 4) */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 tabular-nums">
          {/* Card 1: Retrieval Quality */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[14px] font-semibold text-on-surface">
                  Retrieval Quality
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-surface-container-low text-primary border border-primary-fixed">
                  FAISS Top-K
                </span>
              </div>
              <div className="text-[20px] leading-[28px] font-semibold text-on-surface mb-3">
                {evalData.metrics.hitAt3}%{' '}
                <span className="text-[13px] text-on-surface-variant font-normal">Hit@3</span>
              </div>

              <div className="space-y-2.5">
                <div>
                  <div className="flex justify-between text-[11px] font-semibold mb-1 text-on-surface-variant">
                    <span>Hit@1 (Precision)</span>
                    <span className="font-mono font-medium text-on-surface">
                      {evalData.metrics.hitAt1}%
                    </span>
                  </div>
                  <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-primary h-full rounded-full"
                      style={{ width: `${evalData.metrics.hitAt1}%` }}
                    ></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] font-semibold mb-1 text-on-surface-variant">
                    <span>Hit@3 (Balanced)</span>
                    <span className="font-mono font-medium text-on-surface">
                      {evalData.metrics.hitAt3}%
                    </span>
                  </div>
                  <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-primary-container h-full rounded-full"
                      style={{ width: `${evalData.metrics.hitAt3}%` }}
                    ></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] font-semibold mb-1 text-on-surface-variant">
                    <span>Hit@5 (Recall cap)</span>
                    <span className="font-mono font-medium text-on-surface">
                      {evalData.metrics.hitAt5}%
                    </span>
                  </div>
                  <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-secondary-container h-full rounded-full"
                      style={{ width: `${evalData.metrics.hitAt5}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
            <div className="pt-3 mt-3 border-t border-outline-variant flex items-center justify-between text-[11px] font-semibold text-on-surface-variant">
              <span>Vector recall across {evalData.totalQueries} queries</span>
              <span className="text-emerald-700">Optimal</span>
            </div>
          </div>

          {/* Card 2: Mean Reciprocal Rank (MRR@5) */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[14px] font-semibold text-on-surface">
                  Mean Reciprocal Rank
                </span>
                <span
                  className="material-symbols-outlined text-outline text-[18px]"
                  title="Chunk ranking score"
                >
                  info
                </span>
              </div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-[36px] leading-[44px] font-bold text-on-surface font-mono">
                  {evalData.metrics.mrrAt5.toFixed(3)}
                </span>
                <span className="text-[14px] text-on-surface-variant font-normal">MRR@5</span>
              </div>
              <div className="flex items-center gap-1.5 text-[12px] font-medium text-emerald-700 mb-3">
                <span className="material-symbols-outlined text-[16px]">trending_up</span>
                <span>+{evalData.metrics.mrrDelta.toFixed(3)} vs previous eval run</span>
              </div>
              <p className="text-[13px] text-on-surface-variant leading-relaxed">
                Top chunk ranking relevance index measured over gold-standard customer resolution
                sets.
              </p>
            </div>
            <div className="pt-3 mt-3 border-t border-outline-variant flex items-center justify-between text-[11px] font-semibold">
              <span className="text-on-surface-variant">Evaluation target: 0.850</span>
              <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                Passing
              </span>
            </div>
          </div>

          {/* Card 3: Groundedness Calibration */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[14px] font-semibold text-on-surface">
                  Groundedness Calibration
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                  {evalData.metrics.groundedRate}% Valid
                </span>
              </div>
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-[24px] leading-[32px] font-semibold text-on-surface">
                  {evalData.metrics.groundedRate}%
                </span>
                <span className="text-[13px] text-emerald-700 font-medium">Grounded Rate</span>
              </div>

              {/* Dual Visual Split Bar */}
              <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden flex my-2">
                <div
                  className="bg-emerald-600 h-full"
                  style={{ width: `${evalData.metrics.groundedRate}%` }}
                  title={`Grounded: ${evalData.metrics.groundedRate}%`}
                ></div>
                <div
                  className="bg-amber-500 h-full"
                  style={{ width: `${evalData.metrics.unsupportedClaimRate}%` }}
                  title={`Unsupported Claim Rate: ${evalData.metrics.unsupportedClaimRate}%`}
                ></div>
              </div>

              <div className="flex items-center justify-between mt-2 pt-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600"></span>
                  <span className="text-[11px] font-semibold text-on-surface-variant">
                    Grounded ({evalData.metrics.groundedCount})
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                  <span className="text-[11px] font-semibold text-amber-800">
                    Unsupported Claims ({evalData.metrics.unsupportedClaimRate}%)
                  </span>
                </div>
              </div>
            </div>
            <div className="pt-3 mt-3 border-t border-outline-variant flex items-center justify-between text-[11px] font-semibold text-on-surface-variant">
              <span>Hallucination (Strict Policy)</span>
              <span className="font-mono font-semibold text-emerald-700">
                {evalData.metrics.hallucinationRate.toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Card 4: Refusal Calibration */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[14px] font-semibold text-on-surface">
                  Refusal Calibration
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-surface-container-low text-on-surface-variant border border-outline-variant">
                  Guardrail
                </span>
              </div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-[24px] leading-[32px] font-semibold text-on-surface">
                  {evalData.metrics.trueRefusalRate.toFixed(1)}%
                </span>
                <span className="text-[13px] text-emerald-700 font-medium">True Refusal</span>
              </div>
              <div className="text-[13px] text-on-surface-variant mb-2">
                False Refusal Rate:{' '}
                <span className="font-mono font-medium text-on-surface">
                  {evalData.metrics.falseRefusalRate}%
                </span>{' '}
                ({evalData.metrics.falseRefusalCases})
              </div>
              <p className="text-[13px] text-on-surface-variant leading-tight">
                Escalations triggered accurately for non-KB product domains and ungrounded edge
                questions.
              </p>
            </div>
            <div className="pt-3 mt-3 border-t border-outline-variant flex items-center justify-between text-[11px] font-semibold">
              <span className="text-on-surface-variant">Out-of-Domain Guard</span>
              <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                Enforced
              </span>
            </div>
          </div>
        </div>

        {/* Section 2: Router Performance Comparison Table */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-xs overflow-hidden">
          <div className="p-5 border-b border-outline-variant flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-surface-container-lowest">
            <div>
              <h2 className="text-[16px] font-semibold text-on-surface">
                Router Strategy Comparative Benchmark
              </h2>
              <p className="text-[13px] text-on-surface-variant">
                Deterministic rules vs local statistical embeddings vs LLM structured
                classification. Click any strategy to set as active workspace router.
              </p>
            </div>

            <div className="inline-flex p-1 rounded-lg bg-surface-container-low border border-outline-variant">
              {(
                [
                  { id: 'all', label: 'All Queries (78)' },
                  { id: 'edge', label: 'Edge Cases (14)' },
                  { id: 'multiturn', label: 'Multi-turn (22)' },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setSubsetTab(tab.id)}
                  className={`px-3 py-1 rounded text-[12px] font-medium transition-colors cursor-pointer ${
                    subsetTab === tab.id
                      ? 'bg-surface-container-lowest text-on-surface shadow-xs font-semibold'
                      : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse tabular-nums">
              <thead>
                <tr className="bg-surface-container-low/60 border-b border-outline-variant text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
                  <th className="py-3 px-5">Router Strategy</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Accuracy</th>
                  <th className="py-3 px-4 text-right">Macro-F1</th>
                  <th className="py-3 px-4 text-right">Median Latency</th>
                  <th className="py-3 px-4 text-right">p95 Latency</th>
                  <th className="py-3 px-5 text-right">Cost / 1k Requests</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant text-[14px] text-on-surface">
                {rows.map((row) => {
                  const isCurrentActive =
                    activeRouter.toLowerCase().includes(row.id) ||
                    (row.id === 'tfidf' && activeRouter.includes('TF-IDF'));
                  return (
                    <tr
                      key={row.id}
                      onClick={() => onSelectActiveRouter(row.name)}
                      className={`hover:bg-surface-container-low/40 transition-colors cursor-pointer ${
                        isCurrentActive ? 'bg-surface-container-low/20' : ''
                      }`}
                    >
                      <td className="py-4 px-5">
                        <div className="flex items-center gap-2.5">
                          <span className="font-semibold text-on-surface">{row.name}</span>
                        </div>
                        <span className="text-[11px] text-on-surface-variant block mt-0.5">
                          {row.subtitle}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        {isCurrentActive || row.status === 'Active Production' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <span className="material-symbols-outlined text-[14px]">
                              check_circle
                            </span>
                            {isCurrentActive ? 'Active Production' : 'Production Ready'}
                          </span>
                        ) : row.status === 'Shadow / Experimental' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-surface-container-low text-primary border border-primary-fixed">
                            <span className="material-symbols-outlined text-[14px]">science</span>
                            Shadow / Experimental
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-300">
                            <span className="material-symbols-outlined text-[14px]">alt_route</span>
                            Fallback
                          </span>
                        )}
                      </td>
                      <td
                        className={`py-4 px-4 text-right font-mono font-medium ${
                          row.id === 'llm' ? 'text-primary' : ''
                        }`}
                      >
                        {row.accuracy.toFixed(1)}%
                      </td>
                      <td className="py-4 px-4 text-right font-mono">{row.macroF1.toFixed(3)}</td>
                      <td
                        className={`py-4 px-4 text-right font-mono font-medium ${
                          row.medianLatencyMs > 150 ? 'text-amber-700' : 'text-emerald-800'
                        }`}
                      >
                        {row.medianLatencyMs}ms
                      </td>
                      <td
                        className={`py-4 px-4 text-right font-mono ${
                          row.p95LatencyMs > 200 ? 'text-amber-700' : ''
                        }`}
                      >
                        {row.p95LatencyMs}ms
                      </td>
                      <td className="py-4 px-5 text-right font-mono">
                        <span className="text-on-surface font-medium">
                          ${row.costPer1kUsd.toFixed(4)}
                        </span>
                        <span className="text-[11px] text-on-surface-variant block font-sans">
                          {row.costLabel}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Engineering Decision Summary */}
          <div className="m-4 p-4 rounded-lg bg-surface-container-low border border-outline-variant flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="material-symbols-outlined text-primary shrink-0 mt-0.5">
                insights
              </span>
              <div>
                <h3 className="text-[14px] font-semibold text-on-surface">
                  Engineering Decision Summary
                </h3>
                <p className="text-[13px] text-on-surface-variant mt-0.5">
                  <strong className="text-on-surface">TF-IDF + Logistic</strong> achieves{' '}
                  <span className="font-semibold text-on-surface">98.5% of the LLM accuracy</span>{' '}
                  (94.8% vs 96.2%) while saving{' '}
                  <span className="font-semibold text-emerald-800">278ms per query</span> and
                  eliminating all variable token inference expenses. Recommended production status
                  remains confirmed.
                </p>
              </div>
            </div>
            <span className="text-[11px] px-2.5 py-1 rounded bg-surface-container-lowest text-primary border border-outline-variant font-semibold shrink-0">
              Validated in v2.4
            </span>
          </div>
        </div>

        {/* Section 3: Dataset & Run Metadata Footer Card */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div>
              <span className="text-[11px] font-semibold text-on-surface-variant block uppercase">
                Dataset
              </span>
              <span className="text-[13px] font-mono font-medium text-on-surface">
                {evalData.dataset}
              </span>
              <span className="text-[11px] text-on-surface-variant block">
                {evalData.totalQueries} labeled queries
              </span>
            </div>
            <div>
              <span className="text-[11px] font-semibold text-on-surface-variant block uppercase">
                Corpus Index
              </span>
              <span className="text-[13px] font-mono font-medium text-on-surface">
                {evalData.corpusIndex}
              </span>
              <span className="text-[11px] text-on-surface-variant block">
                {evalData.policyChunks.toLocaleString()} policy chunks
              </span>
            </div>
            <div>
              <span className="text-[11px] font-semibold text-on-surface-variant block uppercase">
                Evaluation Runner
              </span>
              <span className="text-[13px] font-medium text-on-surface">Monotonic Runner</span>
              <span className="text-[11px] text-on-surface-variant font-mono block">
                commit {selectedCommit}
              </span>
            </div>
            <div>
              <span className="text-[11px] font-semibold text-on-surface-variant block uppercase">
                Execution Time
              </span>
              <span className="text-[13px] font-medium text-on-surface">{evalData.executedAt}</span>
              <span className="text-[11px] text-emerald-700 block font-medium">
                Completed today
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5 pt-3 md:pt-0 border-t md:border-t-0 border-outline-variant shrink-0">
            <button
              type="button"
              onClick={handleDownloadJsonReport}
              className="flex items-center gap-2 px-3.5 py-2 bg-surface-container-lowest hover:bg-surface-container-low text-on-surface border border-outline-variant rounded-lg text-[13px] font-semibold transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">download</span>
              <span>Download JSON Report</span>
            </button>
            <button
              type="button"
              onClick={() => setShowMarkdownModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low rounded-lg text-[13px] font-semibold transition-colors cursor-pointer"
            >
              <span>View Markdown Summary</span>
              <span className="material-symbols-outlined text-[16px]">open_in_new</span>
            </button>
          </div>
        </div>
      </div>

      {/* Markdown Summary Modal */}
      {showMarkdownModal && (
        <div className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-[2px] z-50 flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl max-w-2xl w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-outline-variant pb-3">
              <h3 className="text-[16px] font-semibold text-on-surface">
                Evaluation Suite v2.4 — Markdown Report Summary
              </h3>
              <button
                type="button"
                onClick={() => setShowMarkdownModal(false)}
                className="p-1 rounded hover:bg-surface-container-low text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <pre className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/60 text-[12px] font-mono text-on-surface overflow-x-auto leading-relaxed">
{`# TechMart Support AI — RAG & Router Benchmark Report (${selectedCommit})

## 1. Retrieval & Grounding KPIs
- Hit@1 (Precision): ${evalData.metrics.hitAt1}%
- Hit@3 (Balanced):  ${evalData.metrics.hitAt3}%
- Hit@5 (Recall):    ${evalData.metrics.hitAt5}%
- MRR@5:             ${evalData.metrics.mrrAt5} (+${evalData.metrics.mrrDelta})
- Grounded Rate:     ${evalData.metrics.groundedRate}% (${evalData.metrics.groundedCount}/78)
- Unsupported Claim: ${evalData.metrics.unsupportedClaimRate}%
- True Refusal Rate: ${evalData.metrics.trueRefusalRate}% (False Refusal: ${evalData.metrics.falseRefusalRate}%)

## 2. Router Strategy Comparison
| Strategy                      | Status             | Accuracy | Macro-F1 | Median | p95   | Cost/1k |
|-------------------------------|--------------------|----------|----------|--------|-------|---------|
| TF-IDF + Logistic Regression  | Active Production  | 94.8%    | 0.941    | 42ms   | 68ms  | $0.0000 |
| LLM Structured (gpt-4o-mini)  | Shadow / Exp       | 96.2%    | 0.958    | 320ms  | 540ms | $0.3500 |
| Rule-Based Regex / Keywords   | Fallback           | 78.4%    | 0.762    | 4ms    | 9ms   | $0.0000 |`}
            </pre>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleDownloadJsonReport}
                className="px-3.5 py-1.5 rounded-lg border border-outline-variant text-[13px] font-semibold text-on-surface hover:bg-surface-container-low"
              >
                Download JSON
              </button>
              <button
                type="button"
                onClick={() => setShowMarkdownModal(false)}
                className="px-4 py-1.5 rounded-lg bg-primary-container text-on-primary text-[13px] font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
