const PAGE = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project 08 — Performance &amp; Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/exceljs@4.4.0/dist/exceljs.min.js"></script>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #eef1f6; color: #1a1a1a; }
  .wrap { max-width: 1400px; margin: 0 auto; padding: 0 24px 40px; }

  .hero { background: linear-gradient(120deg, #4338ca 0%, #6d28d9 45%, #7c3aed 100%); color: #fff; padding: 28px 24px; margin-bottom: 24px; }
  .hero .wrap { padding: 0 24px; }
  .hero h1 { font-size: 24px; margin: 0 0 6px; font-weight: 700; letter-spacing: -0.01em; }
  .hero .updated { display: inline-flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.14); padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; }
  .hero .agent-scope-badge { display: inline-flex; align-items: center; gap: 8px; background: #fbbf24; color: #1a1a1a; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; margin-left: 10px; }
  .hero .updated .dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 0 3px rgba(74,222,128,0.3); }

  .date-bar { display: flex; align-items: center; gap: 14px; margin-bottom: 22px; flex-wrap: wrap; }
  .day-label { font-size: 11px; color: #9ca3af; font-weight: 700; letter-spacing: 0.06em; }
  .day-status { font-size: 15px; color: #ea580c; font-weight: 800; letter-spacing: 0.02em; }
  .day-status.past { color: #6b7280; }
  .date-bar input[type=date] { padding: 8px 12px; border-radius: 8px; border: 1px solid #d8dce5; font-size: 13px; background: #fff; }
  .date-bar button { padding: 8px 16px; border-radius: 8px; border: 1px solid #d8dce5; background: #fff; font-size: 13px; cursor: pointer; font-weight: 600; color: #444; }
  .date-bar button.active { background: #4338ca; color: #fff; border-color: #4338ca; }
  .date-bar .spacer { flex: 1; }
  .date-bar .stat { font-size: 13px; color: #555; }
  .date-bar .stat b { color: #1a1a1a; font-weight: 700; }

  .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 18px; }
  @media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 560px) { .kpi-grid { grid-template-columns: 1fr; } }
  .kpi-grid.row2 { grid-template-columns: repeat(3, 1fr); margin-top: 18px; margin-bottom: 28px; }
  @media (max-width: 900px) { .kpi-grid.row2 { grid-template-columns: repeat(2, 1fr); } }
  .kpi { background: #fff; border-radius: 12px; padding: 22px 18px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border-left: 4px solid #ccc; }
  .kpi .dash { width: 28px; height: 3px; border-radius: 2px; margin: 0 auto 12px; }
  .kpi .value { font-size: 22px; font-weight: 800; color: #111; letter-spacing: -0.01em; }
  .kpi .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 700; margin-top: 8px; }
  .kpi .desc { font-size: 11px; color: #9ca3af; margin-top: 4px; }
  .kpi.c-green { border-left-color: #10b981; } .kpi.c-green .dash { background: #10b981; } .kpi.c-green .value { color: #059669; }
  .kpi.c-red { border-left-color: #e11d48; } .kpi.c-red .dash { background: #e11d48; } .kpi.c-red .value { color: #be123c; }
  .kpi.c-amber { border-left-color: #f59e0b; } .kpi.c-amber .dash { background: #f59e0b; } .kpi.c-amber .value { color: #b45309; }
  .kpi.c-pink { border-left-color: #ec4899; } .kpi.c-pink .dash { background: #ec4899; } .kpi.c-pink .value { color: #be185d; }
  .kpi.c-sky { border-left-color: #0ea5e9; } .kpi.c-sky .dash { background: #0ea5e9; } .kpi.c-sky .value { color: #0369a1; }
  .kpi.c-orange { border-left-color: #f97316; } .kpi.c-orange .dash { background: #f97316; } .kpi.c-orange .value { color: #c2410c; }
  .kpi.c-purple { border-left-color: #7c3aed; } .kpi.c-purple .dash { background: #7c3aed; } .kpi.c-purple .value { color: #6d28d9; }
  .kpi.c-emerald2 { border-left-color: #10b981; } .kpi.c-emerald2 .dash { background: #10b981; } .kpi.c-emerald2 .value { color: #047857; }

  .su-searchbar { display: flex; align-items: center; gap: 10px; background: #fff; border: 1px solid #d8dce5; border-radius: 12px; padding: 6px 6px 6px 16px; margin: 4px 0 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); max-width: 560px; }
  .su-searchbar-icon { font-size: 16px; color: #9ca3af; }
  .su-searchbar input { flex: 1; border: none; outline: none; font-size: 15px; padding: 10px 0; background: transparent; }
  .su-searchbar button { padding: 12px 26px; border: none; border-radius: 9px; background: #4338ca; color: #fff; font-weight: 700; font-size: 14px; cursor: pointer; }
  .su-searchbar button:disabled { background: #a5a6f0; cursor: default; }
  .su-searchbar button:hover:not(:disabled) { background: #3730a3; }

  .su-reassign-card { background: #f8f9fc; border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px 16px; margin: 0 0 22px; max-width: 560px; }
  .su-reassign-title { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; color: #374151; margin-bottom: 10px; }
  .su-reassign-title .badge { width: 24px; height: 24px; border-radius: 6px; background: #dbeafe; display: flex; align-items: center; justify-content: center; font-size: 12px; }
  .su-reassign-row { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; }
  .su-reassign-row input, .su-reassign-row select { border: 1px solid #d8dce5; border-radius: 8px; padding: 9px 10px; font-size: 13px; background: #fff; }
  .su-reassign-row input { width: 110px; flex: none; }
  .su-reassign-row select { width: 150px; flex: none; }
  .su-reassign-row button { padding: 9px 16px; border: none; border-radius: 8px; background: #2563eb; color: #fff; font-weight: 700; font-size: 13px; cursor: pointer; white-space: nowrap; }
  .su-reassign-row button:disabled { background: #93b4e8; cursor: default; }
  .su-reassign-row button:hover:not(:disabled) { background: #1d4ed8; }
  .su-reassign-msg { margin-top: 10px; font-size: 13px; }
  .su-reassign-msg.ok { color: #059669; }
  .su-reassign-msg.err { color: #991b1b; }

  .su-bulk-card { max-width: 640px; }
  .su-bulk-note { font-size: 12px; color: #6b7280; margin-bottom: 10px; max-width: 640px; }
  .su-bulk-textarea { width: 100%; min-height: 110px; border: 1px solid #d8dce5; border-radius: 8px; padding: 10px 12px; font-size: 13px; font-family: ui-monospace, monospace; resize: vertical; box-sizing: border-box; }
  .su-bulk-count { font-size: 12px; color: #6b7280; }

  .su-ban-card { border-color: #fecdd3; background: #fff5f5; }
  .su-ban-card .su-reassign-title .badge { background: #fecdd3; }
  .su-ban-note { font-size: 12px; color: #9f1239; margin-bottom: 10px; max-width: 480px; }
  .su-ban-btn { background: #be123c !important; }
  .su-ban-btn:hover:not(:disabled) { background: #9f1239 !important; }
  .su-ban-btn:disabled { background: #fca5a5 !important; }
  .su-unban-btn { background: #059669 !important; }
  .su-unban-btn:hover:not(:disabled) { background: #047857 !important; }
  .su-unban-btn:disabled { background: #6ee7b7 !important; }

  .su-state { padding: 30px; text-align: center; color: #6b7280; font-size: 14px; }
  .su-state-error { color: #991b1b; background: #fef2f2; border-radius: 10px; font-weight: 600; }

  .su-profile-card { background: #fff; border-radius: 14px; padding: 24px 28px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-left: 5px solid #4338ca; }
  .su-profile-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; }
  .su-profile-id { font-size: 22px; font-weight: 800; color: #111; letter-spacing: -0.01em; }
  .su-profile-meta { font-size: 13px; color: #6b7280; margin-top: 6px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .su-profile-balance { text-align: right; }
  .su-profile-balance .lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; }
  .su-profile-balance .amt { font-size: 26px; font-weight: 800; color: #0369a1; letter-spacing: -0.01em; }

  .su-fin-panel { background: #fff; border-radius: 14px; padding: 18px 24px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .su-fin-section + .su-fin-section { margin-top: 16px; padding-top: 16px; border-top: 1px solid #eef0f4; }
  .su-fin-section-title { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; margin-bottom: 12px; }
  .su-fin-section-title .su-fin-note { font-weight: 500; text-transform: none; letter-spacing: 0; color: #9ca3af; margin-left: 4px; }
  .su-fin-stats { display: flex; flex-wrap: wrap; gap: 28px; }
  .su-fin-stat { min-width: 130px; }
  .su-fin-label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
  .su-fin-value { font-size: 19px; font-weight: 800; letter-spacing: -0.01em; }
  .su-fin-value.c-green { color: #059669; }
  .su-fin-value.c-red { color: #be123c; }
  .su-fin-value.c-blue { color: #0369a1; }
  @media (max-width: 640px) { .su-fin-stats { gap: 18px; } .su-profile-balance { text-align: left; } }

  .su-vip-badge { padding: 8px 18px; border-radius: 20px; font-weight: 800; font-size: 13px; white-space: nowrap; }
  .su-vip-standard { background: #e5e7eb; color: #374151; }
  .su-vip-gold { background: #dbeafe; color: #1e40af; }
  .su-vip-elite { background: #ede9fe; color: #6d28d9; }

  .su-pill { padding: 3px 10px; border-radius: 20px; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.02em; white-space: nowrap; }
  .su-pill-green { background: #d1fae5; color: #065f46; }
  .su-pill-blue { background: #dbeafe; color: #1e40af; }
  .su-pill-amber { background: #fef3c7; color: #92400e; }
  .su-pill-red { background: #fee2e2; color: #991b1b; }
  .su-pill-grey { background: #e5e7eb; color: #374151; }

  .stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  @media (max-width: 760px) { .stat-row { grid-template-columns: repeat(2, 1fr); } }
  .stat-tile { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px 16px; }
  .stat-tile .st-label { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; }
  .stat-tile .st-value { font-size: 22px; font-weight: 800; color: #1f2937; margin: 4px 0 2px; letter-spacing: -0.01em; }
  .stat-tile .st-delta { font-size: 12px; font-weight: 700; }
  .stat-tile .st-delta.up { color: #16a34a; }
  .stat-tile .st-delta.down { color: #dc2626; }
  .stat-tile .st-delta.flat { color: #9ca3af; }

  .reactivation-highlight { display: flex; align-items: baseline; gap: 18px; background: #ecfeff; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; flex-wrap: wrap; }
  .reactivation-highlight .rh-count { font-size: 28px; font-weight: 800; color: #0e7490; letter-spacing: -0.01em; }
  .reactivation-highlight .rh-count small { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #0e7490; margin-left: 6px; }
  .reactivation-highlight .rh-pct { font-size: 20px; font-weight: 800; color: #0891b2; }
  .reactivation-highlight .rh-pct small { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #0891b2; margin-left: 4px; }

  .net-flow { display: flex; align-items: center; justify-content: space-between; background: #f3f4f6; border-radius: 10px; padding: 12px 18px; margin-bottom: 18px; flex-wrap: wrap; gap: 10px; }
  .net-flow .nf-label { font-size: 11px; font-weight: 700; letter-spacing: 0.06em; color: #6b7280; }
  .net-flow .nf-stats { display: flex; gap: 24px; font-size: 13px; color: #444; }
  .net-flow .nf-stats b { color: #1a1a1a; }
  .net-flow .nf-stats b.pos { color: #059669; }
  .net-flow .nf-stats b.neg { color: #be123c; }

  .analysis-heading { display: flex; align-items: center; gap: 10px; margin: 30px 0 14px; }
  .analysis-heading h2 { font-size: 15px; margin: 0; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; color: #374151; }
  .analysis-heading .line { flex: 1; height: 1px; background: #dfe3ea; }
  .analysis-heading .tag { font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 700; }
  .analysis-heading.deposit .tag { background: #d1fae5; color: #065f46; }
  .analysis-heading.withdrawal .tag { background: #fee2e2; color: #991b1b; }
  .today-tag { font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 700; background: #e0e7ff; color: #3730a3; }

  .row2col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; align-items: start; }
  @media (max-width: 1000px) { .row2col { grid-template-columns: 1fr; } }

  section { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px 18px; margin-bottom: 18px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); border-left: 4px solid #6366f1; }
  section.acc-blue { border-left-color: #3b82f6; }
  section.acc-purple { border-left-color: #8b5cf6; }
  section.acc-orange { border-left-color: #f59e0b; }
  section.acc-rose { border-left-color: #f43f5e; }
  section.acc-cyan { border-left-color: #06b6d4; }
  section.ac-compact { padding: 12px 16px; }
  section.ac-compact .table-wrap { max-height: none; }
  section.ac-compact table { max-width: 420px; }
  @media (max-width: 600px) { section.ac-compact table { max-width: 100%; } }
  section.acc-emerald { border-left-color: #10b981; }
  .sec-title { display: flex; align-items: center; gap: 8px; margin: 0 0 12px; }
  .sec-title .badge { width: 26px; height: 26px; border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }
  .sec-title h2 { font-size: 14px; margin: 0; font-weight: 700; }
  .badge.b-blue { background: #dbeafe; }
  .badge.b-purple { background: #ede9fe; }
  .badge.b-orange { background: #fef3c7; }
  .badge.b-indigo { background: #e0e7ff; }
  .badge.b-rose { background: #ffe4e6; }
  .badge.b-cyan { background: #cffafe; }
  .badge.b-emerald { background: #d1fae5; }

  .section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .download-btn { padding: 7px 14px; border-radius: 20px; border: none; background: linear-gradient(135deg, #10b981, #059669); color: #fff; font-size: 12px; cursor: pointer; font-weight: 600; box-shadow: 0 2px 8px rgba(16,185,129,0.3); }
  .download-btn:hover { filter: brightness(1.05); }
  .download-btn-sm { padding: 5px 11px; border-radius: 16px; border: none; background: linear-gradient(135deg, #10b981, #059669); color: #fff; font-size: 11px; cursor: pointer; font-weight: 600; white-space: nowrap; }
  .download-btn-sm:hover { filter: brightness(1.05); }

  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { text-align: left; padding: 7px 9px; border: 1px solid #edeff3; }
  th { color: #6b7280; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; position: sticky; top: 0; background: #f9fafb; cursor: pointer; }
  tbody tr:hover { background: #f8f9fc; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .bar-cell { position: relative; }
  .bar { position: absolute; left: 0; top: 0; bottom: 0; background: #ddeaff; z-index: 0; border-radius: 4px; }
  .bar-cell span { position: relative; z-index: 1; }
  .table-wrap { max-height: 420px; overflow: auto; }
  canvas { max-height: 280px; }
  .loading { padding: 60px; text-align: center; color: #888; }
  .no-data { color: #999; font-style: italic; padding: 12px 0; }

  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
  .sub-table h3 { font-size: 12px; color: #444; margin: 0 0 8px; font-weight: 700; }
  .pct-good { color: #15803d; font-weight: 700; }
  .pct-mid { color: #a16207; font-weight: 700; }
  .pct-bad { color: #b91c1c; font-weight: 700; }

  .heat-legend { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #666; margin-bottom: 12px; flex-wrap: wrap; }
  .chip { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .chip.good { background: #bbf7d0; color: #166534; }
  .chip.mid { background: #fef08a; color: #854d0e; }
  .chip.bad { background: #fecaca; color: #991b1b; }
  .chip.none { background: #eee; color: #999; }
  .heat-table { border-collapse: collapse; font-size: 12px; }
  .heat-table th, .heat-table td { padding: 6px 9px; text-align: center; border: 1px solid #edeff3; white-space: nowrap; border-radius: 4px; }
  .heat-table th.row-label, .heat-table td.row-label { text-align: left; position: sticky; left: 0; background: #fff; z-index: 2; font-weight: 500; }
  .heat-table th { position: sticky; top: 0; background: #f9fafb; z-index: 1; }
  .heat-table th.row-label { z-index: 3; }
  .heat-table th.row-total, .heat-table td.row-total { font-weight: 700; background: #f9fafb; }

  .layout { display: flex; align-items: flex-start; max-width: 1560px; margin: 0 auto; }
  .sidebar { width: 190px; flex-shrink: 0; padding: 20px 12px; position: sticky; top: 0; }
  .sidebar .nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 8px; color: #444; text-decoration: none; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
  .sidebar .nav-item:hover { background: #e5e7eb; }
  .sidebar .nav-item.active { background: #4338ca; color: #fff; }
  .main { flex: 1; min-width: 0; }

  .ac-note { font-size: 11px; color: #9ca3af; margin: -6px 0 10px; font-style: italic; }
  .ac-pagination { display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-top: 10px; font-size: 12px; color: #666; }
  .ac-pagination button { padding: 5px 12px; border-radius: 16px; border: 1px solid #d8dce5; background: #fff; font-size: 12px; cursor: pointer; font-weight: 600; color: #444; }
  .ac-pagination button:disabled { opacity: 0.4; cursor: default; }
  .badge.b-indigo2 { background: #e0e7ff; }

  .date-switch { display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; }
  .date-switch button { padding: 8px 16px; border-radius: 20px; border: 1px solid #d8dce5; background: #fff; font-size: 13px; cursor: pointer; font-weight: 600; color: #444; }
  .date-switch button.active { background: #4338ca; color: #fff; border-color: #4338ca; }
  .range-date-select { padding: 8px 12px; border-radius: 20px; border: 1px solid #d8dce5; background: #fff; font-size: 13px; font-weight: 600; color: #444; cursor: pointer; }

  /* ---- Performance page: shared tokens ---- */
  :root {
    --perf-ink: #111827;
    --perf-sub: #6b7280;
    --perf-line: #e5e7eb;
    --perf-green: #059669;
    --perf-amber: #d97706;
    --perf-red: #dc2626;
  }

  .perf-controls { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; background: #fff; border: 1px solid var(--perf-line); border-radius: 12px; padding: 12px 16px; margin-bottom: 22px; }
  .perf-controls input[type=date] { border: 1px solid #d8dce5; border-radius: 8px; padding: 8px 10px; font-size: 13px; }
  .perf-controls .perf-to { color: #9ca3af; font-size: 12px; font-weight: 700; }
  .perf-preset { padding: 7px 14px; border-radius: 18px; border: 1px solid #d8dce5; background: #f9fafb; font-size: 12px; cursor: pointer; font-weight: 700; color: #444; }
  .perf-preset.active { background: #4338ca; color: #fff; border-color: #4338ca; }
  .perf-daterange { position: relative; }
  .perf-daterange-btn { padding: 8px 14px; border-radius: 8px; border: 1px solid #d8dce5; background: #fff; font-size: 13px; cursor: pointer; font-weight: 600; color: #333; }
  .perf-daterange-btn:hover { border-color: #4338ca; }
  .perf-daterange-popover { position: absolute; top: calc(100% + 6px); left: 0; z-index: 20; background: #fff; border: 1px solid var(--perf-line); border-radius: 10px; box-shadow: 0 6px 20px rgba(0,0,0,0.12); padding: 14px; display: flex; align-items: flex-end; gap: 10px; }
  .perf-daterange-popover label { display: flex; flex-direction: column; gap: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; color: #6b7280; }
  .perf-daterange-popover input[type=date] { border: 1px solid #d8dce5; border-radius: 8px; padding: 8px 10px; font-size: 13px; }
  .perf-daterange-popover button { padding: 8px 16px; border: none; border-radius: 8px; background: #4338ca; color: #fff; font-weight: 700; font-size: 13px; cursor: pointer; }
  .perf-daterange-popover button:hover { background: #3730a3; }

  /* Explainer card replacing the old cramped one-line legend */
  .perf-explainer { display: grid; grid-template-columns: 1.1fr 1fr; gap: 22px; background: #fff; border: 1px solid var(--perf-line); border-radius: 14px; padding: 18px 22px; margin-bottom: 24px; }
  @media (max-width: 900px) { .perf-explainer { grid-template-columns: 1fr; } }
  .perf-explainer h5 { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: var(--perf-sub); margin: 0 0 10px; }
  .perf-tier-key { display: flex; flex-direction: column; gap: 7px; }
  .perf-tier-key .tk-row { display: flex; align-items: center; gap: 9px; font-size: 12.5px; color: #374151; }
  .perf-tier-key .tk-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
  .perf-incentive-table { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .perf-incentive-cell { border-radius: 10px; padding: 10px 12px; text-align: center; }
  .perf-incentive-cell.tier1 { background: #eff6ff; }
  .perf-incentive-cell.tier2 { background: #f5f3ff; }
  .perf-incentive-cell.tier3 { background: #fffbeb; }
  .perf-incentive-cell .ic-thresh { font-size: 11px; font-weight: 800; color: var(--perf-sub); }
  .perf-incentive-cell .ic-amts { font-size: 12px; font-weight: 700; color: var(--perf-ink); margin-top: 3px; }

  .perf-section-lead { font-size: 13px; color: var(--perf-sub); margin: -8px 0 18px; }

  /* Monthly Leaderboard: departments (left) + Overall Ranking (right) */
  .perf-leaderboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; margin-bottom: 30px; align-items: start; }
  @media (max-width: 900px) { .perf-leaderboard-grid { grid-template-columns: 1fr; } }
  .perf-dept-panel { background: #fff; border: 1px solid var(--perf-line); border-radius: 14px; padding: 16px 18px 18px; margin-bottom: 16px; }
  .perf-dept-panel:last-child { margin-bottom: 0; }
  .perf-dept-panel-head { display: flex; align-items: center; gap: 9px; margin-bottom: 12px; }
  .perf-dept-panel-head .dp-icon { font-size: 16px; }
  .perf-dept-panel-head h4 { font-size: 12.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.03em; color: var(--perf-ink); margin: 0; }
  .perf-rank-row { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid #f1f2f5; }
  .perf-rank-row:first-of-type { border-top: none; }
  .perf-rank-row .pr-medal { width: 22px; font-size: 15px; text-align: center; flex-shrink: 0; }
  .perf-rank-row .pr-main { flex: 1; min-width: 0; }
  .perf-rank-row .pr-name-line { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 4px; }
  .perf-rank-row .pr-name { font-weight: 700; font-size: 12.5px; color: var(--perf-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .perf-rank-row .pr-score { font-weight: 800; font-size: 12.5px; flex-shrink: 0; }
  .perf-rank-row .pr-bar { height: 5px; border-radius: 3px; background: #eef0f4; overflow: hidden; }
  .perf-rank-row .pr-bar-fill { height: 100%; border-radius: 3px; }
  .perf-rank-row .pr-incentive { font-size: 10.5px; font-weight: 700; color: var(--perf-green); flex-shrink: 0; white-space: nowrap; }
  .perf-rank-row .pr-incentive.na { color: #b0b6c0; font-weight: 500; }
  .perf-dept-empty { font-size: 12px; color: #9ca3af; font-style: italic; padding: 6px 0; }

  .perf-overall-podium { display: flex; flex-direction: column; gap: 16px; height: 100%; }
  .perf-overall-podium .poc { flex: 1; border-radius: 16px; padding: 22px 26px; color: #fff; display: flex; align-items: center; gap: 18px; box-shadow: 0 8px 22px rgba(0,0,0,0.14); }
  .perf-overall-podium .poc.gold { background: linear-gradient(145deg, #f5c542, #d4941f); }
  .perf-overall-podium .poc.silver { background: linear-gradient(145deg, #b8c2cc, #8a97a3); }
  .perf-overall-podium .poc.bronze { background: linear-gradient(145deg, #d0925a, #a86a37); }
  .perf-overall-podium .poc-medal { font-size: 36px; flex-shrink: 0; }
  .perf-overall-podium .poc-body { flex: 1; min-width: 0; }
  .perf-overall-podium .poc-rank-label { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.85; }
  .perf-overall-podium .poc-name { font-size: 22px; font-weight: 800; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .perf-overall-podium .poc-incentive { margin-top: 6px; font-size: 13px; font-weight: 700; }
  .perf-overall-podium .poc-score { text-align: right; flex-shrink: 0; }
  .perf-overall-podium .poc-score .val { font-size: 32px; font-weight: 900; letter-spacing: -0.02em; }
  .perf-overall-podium .poc-score small { display: block; font-size: 11px; font-weight: 700; opacity: 0.85; }
  .perf-overall-empty { background: #fff; border: 1px dashed var(--perf-line); border-radius: 14px; padding: 30px; text-align: center; color: #9ca3af; font-size: 13px; height: 100%; display: flex; align-items: center; justify-content: center; }
  .perf-extra-rank { display: flex; flex-direction: column; gap: 8px; margin-top: 2px; }
  .perf-extra-rank-row { display: flex; align-items: center; gap: 12px; background: #fff; border: 1px solid var(--perf-line); border-left-width: 3px; border-radius: 10px; padding: 10px 14px; }
  .perf-extra-rank-row.fourth { border-left-color: #9ca3af; }
  .perf-extra-rank-row.last { border-left-color: #dc2626; }
  .perf-extra-rank-row .er-label { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; color: var(--perf-sub); width: 90px; flex-shrink: 0; white-space: nowrap; }
  .perf-extra-rank-row .er-name { font-weight: 700; font-size: 13px; color: var(--perf-ink); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .perf-extra-rank-row .er-score { font-weight: 800; font-size: 14px; flex-shrink: 0; }

  /* Daily / Range Performance */
  .perf-range-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 26px; align-items: start; }
  @media (max-width: 900px) { .perf-range-grid { grid-template-columns: 1fr; } }
  .perf-range-col > .perf-dept-block { margin-bottom: 22px; }
  .perf-range-col > .perf-dept-block:last-child { margin-bottom: 0; }
  .perf-dept-block-head { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; }
  .perf-dept-block-head .db-icon { font-size: 17px; }
  .perf-dept-block-head h3 { font-size: 14px; font-weight: 800; color: var(--perf-ink); margin: 0; }
  .perf-dept-block-head .db-count { font-size: 11px; font-weight: 700; color: var(--perf-sub); background: #f3f4f6; padding: 2px 9px; border-radius: 10px; margin-left: 2px; }
  .perf-dept-scroll { max-height: 460px; overflow-y: auto; border: 1px solid var(--perf-line); border-radius: 12px; background: #fff; }
  .perf-card { padding: 13px 16px; display: flex; align-items: center; gap: 14px; border-bottom: 1px solid #f1f2f5; }
  .perf-card:last-child { border-bottom: none; }
  .perf-card:nth-child(even) { background: #fafbfc; }
  .perf-card .perf-rank { width: 28px; height: 28px; border-radius: 50%; background: #f3f4f6; color: #444; font-weight: 800; font-size: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .perf-card .perf-rank.top3 { background: linear-gradient(145deg, #4338ca, #6366f1); color: #fff; }
  .perf-card .perf-agent-name { font-weight: 800; font-size: 13px; color: var(--perf-ink); width: 128px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .perf-card .perf-score-big { font-size: 17px; font-weight: 900; min-width: 62px; text-align: right; flex-shrink: 0; }
  .perf-criteria-grid { display: grid; gap: 10px; flex: 1; min-width: 0; }
  .perf-crit { font-size: 11px; color: var(--perf-sub); min-width: 0; }
  .perf-crit .pc-label { font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em; font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .perf-crit .pc-target { display: block; font-weight: 600; font-size: 9.5px; color: #9ca3af; margin-top: 1px; }
  .perf-crit .pc-value { font-weight: 800; font-size: 12.5px; color: var(--perf-ink); margin: 3px 0; }
  .perf-bar { height: 6px; border-radius: 4px; background: #eef0f4; overflow: hidden; }
  .perf-bar-fill { height: 100%; border-radius: 4px; }
  .perf-bar-fill.pb-green { background: var(--perf-green); }
  .perf-bar-fill.pb-amber { background: var(--perf-amber); }
  .perf-bar-fill.pb-red { background: var(--perf-red); }
  .perf-bar-fill.pb-na { background: #d1d5db; }
  .perf-crit-na .pc-value { color: #9ca3af; font-style: italic; font-size: 11px; }
</style>
</head>
<body>
<div class="hero">
  <div class="wrap">
    <h1>Project 08 &mdash; Performance &amp; Analysis</h1>
    <div class="updated" id="updated-badge"><span class="dot"></span> Loading&hellip;</div>
    <div class="agent-scope-badge" id="agent-scope-badge" style="display:none"></div>
  </div>
</div>
<div class="layout">
  <nav class="sidebar">
    <a href="/" class="nav-item" id="nav-home">&#127968; Home</a>
    <a href="/action-center" class="nav-item" id="nav-action-center">&#9889; Action Center</a>
    <a href="/performance" class="nav-item" id="nav-performance">&#127942; Performance</a>
    <a href="/analytics" class="nav-item" id="nav-analytics">&#128202; Analytics</a>
    <a href="/platform-analysis" class="nav-item" id="nav-platform-analysis">&#127918; Platform Analysis</a>
    <a href="/search-user" class="nav-item" id="nav-search-user">&#128269; Search User</a>
  </nav>
  <div class="main">
    <div class="wrap" id="home-wrap">
      <div class="date-bar" id="date-bar" style="display:none">
        <div class="day-label">DAY</div>
        <div class="day-status" id="day-status">TODAY</div>
        <input type="date" id="date-picker">
        <button id="btn-today">Reset to Today</button>
        <div class="spacer"></div>
        <div class="stat">Total Users: <b id="stat-total-users">&mdash;</b></div>
        <div class="stat">Registered Active: <b id="stat-registered-active">&mdash;</b></div>
      </div>
      <div id="app" class="loading">Loading report data&hellip;</div>
    </div>
    <div class="wrap" id="action-center-wrap" style="display:none">
      <div id="action-center-app" class="loading">Loading report data&hellip;</div>
    </div>
    <div class="wrap" id="performance-wrap" style="display:none">
      <div id="performance-app" class="loading">Loading report data&hellip;</div>
    </div>
    <div class="wrap" id="analytics-wrap" style="display:none">
      <div id="analytics-app" class="loading">Loading report data&hellip;</div>
    </div>
    <div class="wrap" id="platform-analysis-wrap" style="display:none">
      <div id="platform-analysis-app" class="loading">Loading report data&hellip;</div>
    </div>
    <div class="wrap" id="search-user-wrap" style="display:none">
      <div id="search-user-app"></div>
    </div>
  </div>
</div>

<script>
function fmt(n) { return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
function money(n) { return '₹' + fmt(n); }

function sortableTable(container, headers, rows, rowRenderer, numericCols) {
  let sortCol = null, sortDir = -1;
  function render() {
    let data = rows.slice();
    if (sortCol !== null) {
      data.sort((a, b) => {
        const av = a[sortCol], bv = b[sortCol];
        if (typeof av === 'number') return (av - bv) * sortDir;
        return String(av).localeCompare(String(bv)) * sortDir;
      });
    }
    const thead = '<thead><tr>' + headers.map((h, i) =>
      '<th data-i="' + i + '"' + (numericCols && numericCols.includes(i) ? ' class="num"' : '') + '>' +
      h + (sortCol === i ? (sortDir === 1 ? ' ▲' : ' ▼') : '') + '</th>'
    ).join('') + '</tr></thead>';
    const tbody = '<tbody>' + data.map(rowRenderer).join('') + '</tbody>';
    container.innerHTML = '<div class="table-wrap"><table>' + thead + tbody + '</table></div>';
    container.querySelectorAll('th').forEach(th => {
      th.addEventListener('click', () => {
        const i = Number(th.dataset.i);
        if (sortCol === i) sortDir *= -1; else { sortCol = i; sortDir = -1; }
        render();
      });
    });
  }
  render();
}

const EMPTY_SCOPE = {
  totals: { count: 0, total_amount: 0 }, by_channel: [], by_amount_range: [], by_channel_and_range: [], hourly: [],
  success_by_range: [], success_by_channel: [], hourly_success_by_channel: [], hourly_success_by_range: [],
  withdrawal_review_by_channel: [], withdrawal_completion_by_channel: [], withdrawal_orders: [], top_depositors: [],
  summary: {
    total_deposit: 0, total_withdraw: 0, deposit_orders: 0, withdraw_orders: 0,
    deposit_users: 0, withdraw_users: 0, active_users: 0, difference: 0, withdraw_deposit_pct: null,
  },
};

function pctClass(pct) {
  if (pct >= 41) return 'pct-good';
  if (pct >= 30) return 'pct-mid';
  return 'pct-bad';
}
function heatColor(total, pct) {
  if (!total) return { bg: '#f3f4f6', color: '#bbb' };
  if (pct >= 41) return { bg: '#bbf7d0', color: '#166534' };
  if (pct >= 30) return { bg: '#fef08a', color: '#854d0e' };
  return { bg: '#fecaca', color: '#991b1b' };
}

function todayLocalISO() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

// Per-agent dashboards live under /agent/<encoded-name>(/<page>)? -- the
// name is URL-decoded directly from the path (no lookup table/file needed)
// and must match an agent_assignments value exactly, since that's the key
// build_deposit_report.py slugified when uploading reports/agent/*.json.
const AGENT_URL_MATCH = location.pathname.match(/^\\/agent\\/([^/]+)(\\/(action-center|analytics|search-user))?\\/?$/);
const AGENT_NAME = AGENT_URL_MATCH ? decodeURIComponent(AGENT_URL_MATCH[1]) : null;
const IS_AGENT_SCOPED = !!AGENT_NAME;
const AGENT_SUBPAGE = AGENT_URL_MATCH ? (AGENT_URL_MATCH[3] || '') : '';
function agentUrl(page) {
  return '/agent/' + encodeURIComponent(AGENT_NAME) + (page ? '/' + page : '');
}

const IS_ACTION_CENTER = IS_AGENT_SCOPED ? AGENT_SUBPAGE === 'action-center' : location.pathname.indexOf('/action-center') === 0;
const IS_PERFORMANCE = !IS_AGENT_SCOPED && location.pathname.indexOf('/performance') === 0;
const IS_ANALYTICS = IS_AGENT_SCOPED ? AGENT_SUBPAGE === 'analytics' : location.pathname.indexOf('/analytics') === 0;
const IS_PLATFORM_ANALYSIS = !IS_AGENT_SCOPED && location.pathname.indexOf('/platform-analysis') === 0;
const IS_SEARCH_USER = IS_AGENT_SCOPED ? AGENT_SUBPAGE === 'search-user' : location.pathname.indexOf('/search-user') === 0;
document.getElementById(IS_SEARCH_USER ? 'nav-search-user' : (IS_PLATFORM_ANALYSIS ? 'nav-platform-analysis' : (IS_ANALYTICS ? 'nav-analytics' : (IS_PERFORMANCE ? 'nav-performance' : (IS_ACTION_CENTER ? 'nav-action-center' : 'nav-home'))))).classList.add('active');
document.getElementById('home-wrap').style.display = (IS_ACTION_CENTER || IS_PERFORMANCE || IS_ANALYTICS || IS_PLATFORM_ANALYSIS || IS_SEARCH_USER) ? 'none' : '';
document.getElementById('action-center-wrap').style.display = IS_ACTION_CENTER ? '' : 'none';
document.getElementById('performance-wrap').style.display = IS_PERFORMANCE ? '' : 'none';
document.getElementById('analytics-wrap').style.display = IS_ANALYTICS ? '' : 'none';
document.getElementById('platform-analysis-wrap').style.display = IS_PLATFORM_ANALYSIS ? '' : 'none';
document.getElementById('search-user-wrap').style.display = IS_SEARCH_USER ? '' : 'none';

// Client-side deterrent only (this is a static page, no real auth backend) --
// gates the Ban User/Reassign Agent actions and the whole Platform Analysis
// page behind a shared PIN.
const ACTION_PASSWORD = '3177';
function checkActionPassword(msgEl, actionLabel) {
  const entered = prompt('Enter password to ' + actionLabel + ':');
  if (entered === null) return false; // cancelled
  if (entered !== ACTION_PASSWORD) {
    msgEl.textContent = 'Access Denied';
    msgEl.className = 'su-reassign-msg err';
    return false;
  }
  return true;
}

// Ban/Reassign/Unban actually hit the upload worker's API, which now
// verifies the password itself (see ACTION_PASSWORD in worker/src/index.js)
// -- so this just prompts and passes the raw value through; the server's
// 403 "Access Denied" is the real check, not a client-side comparison.
function promptActionPassword(actionLabel) {
  const entered = prompt('Enter password to ' + actionLabel + ':');
  return entered === null ? null : entered;
}

if (IS_AGENT_SCOPED) {
  document.getElementById('nav-home').href = agentUrl('');
  document.getElementById('nav-action-center').href = agentUrl('action-center');
  document.getElementById('nav-analytics').href = agentUrl('analytics');
  document.getElementById('nav-search-user').href = agentUrl('search-user');
  // Performance stays a global, unscoped link (full cross-agent leaderboard,
  // by design) -- Platform Analysis is hidden entirely for agent dashboards.
  document.getElementById('nav-platform-analysis').style.display = 'none';
  const badge = document.getElementById('agent-scope-badge');
  badge.textContent = 'Agent: ' + AGENT_NAME;
  badge.style.display = '';
}

// Filters every per-row "agent"-tagged section of the (already-fetched,
// global) report down to one agent's own users -- reused across Action
// Center, Analytics, and Weekly Cashback Shield, all of which already ship
// an "agent" field per row and need no separate per-agent backend file.
// cohort_size/pct_converted/pct_reactivated/pct_upgraded are intentionally
// left as the GLOBAL platform-wide rate: the true agent-specific cohort
// (including non-converted members) isn't shipped to the browser at all,
// so recomputing them here would either be wrong or require guessing.
function scopeReportToAgent(data, agentName) {
  if (!agentName) return data;
  const filterRows = rows => (rows || []).filter(r => r.agent === agentName);
  const scoped = { ...data };

  if (scoped.action_center) {
    const ac = scoped.action_center;
    const acOut = {};
    for (const key of ['near_upgrade_low', 'near_upgrade_high', 'inactive_high', 'inactive_low', 'active_low', 'active_high']) {
      if (!ac[key]) continue;
      const rows = filterRows(ac[key].rows);
      acOut[key] = { ...ac[key], rows, total_matching: rows.length };
    }
    scoped.action_center = acOut;
  }

  if (scoped.action_center_extra) {
    scoped.action_center_extra = {
      ...scoped.action_center_extra,
      yesterday_first_deposit_users: filterRows(scoped.action_center_extra.yesterday_first_deposit_users),
      no_return_fd_users: filterRows(scoped.action_center_extra.no_return_fd_users),
    };
  }

  if (scoped.weekly_cashback_shield) {
    const rows = filterRows(scoped.weekly_cashback_shield.rows);
    scoped.weekly_cashback_shield = {
      ...scoped.weekly_cashback_shield,
      rows,
      eligible_count: rows.length,
      total_bonus: Math.round(rows.reduce((s, r) => s + r.bonus_amount, 0) * 100) / 100,
    };
  }

  for (const key of ['reactivation', 'vip_upgrade']) {
    if (!scoped[key]) continue;
    const out = { ...scoped[key] };
    for (const tier of ['low', 'high']) {
      if (!scoped[key][tier]) continue;
      const rows = filterRows(scoped[key][tier].rows);
      out[tier] = { ...scoped[key][tier], rows };
      if (key === 'reactivation') out[tier].reactivated_count = rows.length;
      if (key === 'vip_upgrade') out[tier].upgraded_count = rows.length;
    }
    scoped[key] = out;
  }

  if (scoped.retention) {
    const out = { ...scoped.retention };
    for (const sub of ['first_deposit', 'no_return_fd_conversion']) {
      if (!scoped.retention[sub]) continue;
      const rows = filterRows(scoped.retention[sub].rows);
      out[sub] = { ...scoped.retention[sub], rows, converted_count: rows.length };
    }
    scoped.retention = out;
  }

  if (scoped.premium_active) {
    const out = { ...scoped.premium_active };
    for (const tier of ['low', 'high']) {
      if (!scoped.premium_active[tier]) continue;
      const rows = filterRows(scoped.premium_active[tier].rows);
      out[tier] = { ...scoped.premium_active[tier], rows, converted_count: rows.length };
    }
    scoped.premium_active = out;
  }

  if (scoped.withdrawal_orders_full) {
    scoped.withdrawal_orders_full = filterRows(scoped.withdrawal_orders_full);
  }

  if (scoped.by_date) {
    const byDateOut = {};
    for (const [date, dayData] of Object.entries(scoped.by_date)) {
      byDateOut[date] = { ...dayData, withdrawal_orders: filterRows(dayData.withdrawal_orders) };
    }
    scoped.by_date = byDateOut;
  }

  return scoped;
}

// columns: {label, render, raw, num} -- raw (already used for Excel exports)
// doubles as the sort key when present, since it's the plain underlying
// value rather than rendered HTML (badges/pills). Falls back to the
// rendered string for columns with no raw().
function paginatedTable(containerId, paginationId, rows, columns, pageSize, opts) {
  const jumpDropdown = opts && opts.jumpDropdown;
  let page = 0;
  let sortCol = null, sortDir = 1;
  function sortedRows() {
    if (sortCol === null) return rows;
    const col = columns[sortCol];
    const keyOf = r => col.raw ? col.raw(r) : col.render(r);
    return rows.slice().sort((a, b) => {
      const av = keyOf(a), bv = keyOf(b);
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sortDir;
      return String(av).localeCompare(String(bv)) * sortDir;
    });
  }
  function render() {
    const data = sortedRows();
    const totalPages = Math.max(1, Math.ceil(data.length / pageSize));
    if (page >= totalPages) page = totalPages - 1;
    const container = document.getElementById(containerId);
    const pageRows = data.slice(page * pageSize, page * pageSize + pageSize);
    if (!pageRows.length) {
      container.innerHTML = '<div class="no-data">No matching users.</div>';
    } else {
      const thead = '<thead><tr>' + columns.map((c, i) => '<th class="th-sortable' + (c.num ? ' num' : '') + '" data-i="' + i + '">' +
        c.label + (sortCol === i ? (sortDir === 1 ? ' &#9650;' : ' &#9660;') : '') + '</th>').join('') + '</tr></thead>';
      const tbody = '<tbody>' + pageRows.map(r => '<tr>' + columns.map(c =>
        '<td class="' + (c.num ? 'num' : '') + '">' + c.render(r) + '</td>'
      ).join('') + '</tr>').join('') + '</tbody>';
      container.innerHTML = '<div class="table-wrap"><table>' + thead + tbody + '</table></div>';
      container.querySelectorAll('th').forEach(th => {
        th.addEventListener('click', () => {
          const i = Number(th.dataset.i);
          if (sortCol === i) sortDir *= -1; else { sortCol = i; sortDir = 1; }
          page = 0;
          render();
        });
      });
    }
    const pag = document.getElementById(paginationId);
    const jumpHtml = jumpDropdown
      ? ' <select id="' + paginationId + '-jump" class="range-date-select" style="padding:4px 8px">' +
        Array.from({ length: totalPages }, (_, i) => '<option value="' + i + '"' + (i === page ? ' selected' : '') + '>Page ' + (i + 1) + '</option>').join('') +
        '</select>'
      : '';
    pag.innerHTML = 'Page ' + (page + 1) + ' of ' + totalPages +
      ' <button id="' + paginationId + '-prev"' + (page === 0 ? ' disabled' : '') + '>&larr; Prev</button>' +
      ' <button id="' + paginationId + '-next"' + (page >= totalPages - 1 ? ' disabled' : '') + '>Next &rarr;</button>' + jumpHtml;
    const prevBtn = document.getElementById(paginationId + '-prev');
    const nextBtn = document.getElementById(paginationId + '-next');
    if (prevBtn) prevBtn.addEventListener('click', () => { page = Math.max(0, page - 1); render(); });
    if (nextBtn) nextBtn.addEventListener('click', () => { page = Math.min(totalPages - 1, page + 1); render(); });
    const jumpSelect = document.getElementById(paginationId + '-jump');
    if (jumpSelect) jumpSelect.addEventListener('change', () => { page = Number(jumpSelect.value); render(); });
  }
  render();
}

function shortDate(isoDateStr) {
  if (!isoDateStr) return '&mdash;';
  const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const parts = isoDateStr.split('-');
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return d.getDate() + '-' + MONTHS[d.getMonth()];
}

const HEADER_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFDBEAFE' } };
// Same green/red/amber used on-screen for up/down deltas and MET/MISSED
// pills (.st-delta.up/.down, .su-pill-green/.su-pill-amber) -- reused here
// so an exported Excel report reads the same way the dashboard does.
const XL_GREEN_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFD1FAE5' } };
const XL_GREEN_FONT = { color: { argb: 'FF065F46' }, bold: true };
const XL_RED_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFEE2E2' } };
const XL_RED_FONT = { color: { argb: 'FF991B1B' }, bold: true };
const XL_AMBER_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFEF3C7' } };
const XL_AMBER_FONT = { color: { argb: 'FF92400E' }, bold: true };

function styleHeaderRow(ws) {
  const row = ws.getRow(1);
  row.font = { bold: true };
  row.eachCell(c => { c.fill = HEADER_FILL; });
}

// Colors a single cell green (positive) or red (negative) -- used for
// Change/% Change columns so a reader can spot up/down at a glance without
// reading every number.
function styleDeltaCell(cell, value) {
  if (value > 0) { cell.fill = XL_GREEN_FILL; cell.font = XL_GREEN_FONT; }
  else if (value < 0) { cell.fill = XL_RED_FILL; cell.font = XL_RED_FONT; }
}

async function saveWorkbook(wb, filename) {
  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// rowObjects: array of plain objects, keys become the header row (same shape
// XLSX.utils.json_to_sheet expected) -- bold + light-blue header on every export.
async function downloadStyledExcel(rowObjects, sheetName, filename) {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet(sheetName);
  if (rowObjects.length) {
    ws.columns = Object.keys(rowObjects[0]).map(k => ({ header: k, key: k, width: Math.max(12, k.length + 2) }));
    ws.addRows(rowObjects);
  }
  styleHeaderRow(ws);
  await saveWorkbook(wb, filename);
}

function downloadExcel(rows, columns, sheetName, filename) {
  const data = rows.map(r => {
    const obj = {};
    columns.forEach(c => { obj[c.label] = c.raw ? c.raw(r) : c.render(r); });
    return obj;
  });
  downloadStyledExcel(data, sheetName, filename);
}

if (IS_ACTION_CENTER) {
  (async () => {
    const res = await fetch('/data.json');
    if (!res.ok) {
      document.getElementById('action-center-app').textContent = 'Failed to load report data (' + res.status + ')';
      return;
    }
    const data = scopeReportToAgent(await res.json(), AGENT_NAME);
    const ac = data.action_center;
    const acx = data.action_center_extra;
    document.getElementById('updated-badge').innerHTML =
      '<span class="dot"></span> Records updated through ' +
      (data.latest_record_time ? new Date(data.latest_record_time).toLocaleString() : 'n/a');
    document.getElementById('action-center-app').className = '';

    if (!ac) {
      document.getElementById('action-center-app').innerHTML = '<div class="no-data">Action Center data not available in this report yet.</div>';
      return;
    }

    const newUserCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP', render: r => (r.vip_level == null ? '&mdash;' : r.vip_level), num: true },
      { label: 'Deposit Count', render: r => fmt(r.deposit_count), raw: r => r.deposit_count, num: true },
      { label: 'Total Deposit Amount', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Total Withdraw', render: r => money(r.total_withdraw), raw: r => r.total_withdraw, num: true },
      { label: 'Profit/Loss', render: r => money(r.profit_loss), raw: r => r.profit_loss, num: true },
      { label: 'Region', render: r => r.region || '&mdash;' },
    ];
    const bonusCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'FD Date', render: r => shortDate(r.fd_date), raw: r => r.fd_date },
      { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Withdraw', render: r => money(r.total_withdraw), raw: r => r.total_withdraw, num: true },
    ];

    const nearCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'Current VIP Level', render: r => r.current_vip, num: true },
      { label: 'Next VIP Level', render: r => r.next_vip, num: true },
      { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Amount to Reach Next Level', render: r => money(r.amount_to_next), raw: r => r.amount_to_next, num: true },
      { label: 'Inactive Days', render: r => (r.inactive_days == null ? '&mdash;' : fmt(r.inactive_days)), raw: r => r.inactive_days, num: true },
    ];
    const inactiveCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP Level', render: r => r.vip_level, num: true },
      { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Wallet Balance', render: r => money(r.wallet_balance), raw: r => r.wallet_balance, num: true },
      { label: 'Inactive Days', render: r => fmt(r.inactive_days), raw: r => r.inactive_days, num: true },
      { label: 'Last Active Date', render: r => r.last_active_date || '&mdash;', raw: r => r.last_active_date },
    ];
    const activeCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP Level', render: r => r.vip_level, num: true },
      { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Wallet Balance', render: r => money(r.wallet_balance), raw: r => r.wallet_balance, num: true },
      { label: 'Inactive Days', render: r => fmt(r.inactive_days), raw: r => r.inactive_days, num: true },
    ];
    // Older cached reports (before loss_pct was added to the backend row)
    // won't have this field yet -- fall back to deriving it client-side
    // until the next pipeline run backfills it.
    function cashbackLossPct(r) {
      if (r.loss_pct != null) return Number(r.loss_pct);
      return r.total_deposit ? (r.verified_loss / r.total_deposit * 100) : 0;
    }
    const cashbackCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP', render: r => (r.vip == null ? '&mdash;' : r.vip), raw: r => r.vip, num: true },
      { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Total Withdraw', render: r => money(r.total_withdraw), raw: r => r.total_withdraw, num: true },
      { label: 'User Balance', render: r => money(r.user_balance), raw: r => r.user_balance, num: true },
      { label: 'Verified Loss', render: r => money(r.verified_loss), raw: r => r.verified_loss, num: true },
      { label: 'Loss %', render: r => cashbackLossPct(r).toFixed(2) + '%', raw: r => cashbackLossPct(r), num: true },
      { label: 'Eligible %', render: r => Number(r.eligible_pct).toFixed(2) + '%', raw: r => r.eligible_pct, num: true },
      { label: 'Bonus Amount', render: r => money(r.bonus_amount), raw: r => r.bonus_amount, num: true },
    ];
    const wcs = data.weekly_cashback_shield;

    document.getElementById('action-center-app').innerHTML = \`
      \${acx ? \`
      <div class="analysis-heading deposit"><h2>FTD</h2><div class="line"></div><span class="tag">ACTION CENTER</span></div>
      <div class="row2col">
        <section class="acc-blue">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-blue">&#127881;</div><h2>Yesterday First Deposit Users</h2><span class="today-tag">\${acx.yesterday_first_deposit_users.length.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-new-users">&#128190; Excel</button>
          </div>
          <div class="ac-note">Flagged by the source system's own first-deposit marker &middot; \${acx.yesterday_first_deposit_users.length.toLocaleString('en-IN')} users</div>
          <div id="new-users-table"></div>
          <div class="ac-pagination" id="new-users-pagination"></div>
        </section>
        <section class="acc-cyan">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-cyan">&#127942;</div><h2>No-Return First Deposit Users</h2><span class="today-tag">\${acx.no_return_fd_users.length.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-bonus">&#128190; Excel</button>
          </div>
          <div class="ac-note">First deposit 2-5 days ago, no deposit since &middot; \${acx.no_return_fd_users.length.toLocaleString('en-IN')} users</div>
          <div id="bonus-table"></div>
          <div class="ac-pagination" id="bonus-pagination"></div>
        </section>
      </div>
      \` : ''}

      <div class="analysis-heading withdrawal"><h2>Inactive Users</h2><div class="line"></div><span class="tag">ACTION CENTER</span></div>
      <div class="row2col">
        <section class="acc-rose">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-rose">&#128564;</div><h2>Inactive Users - High</h2><span class="today-tag">\${ac.inactive_high.total_matching.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-inactive-high">&#128190; Excel</button>
          </div>
          <div class="ac-note">\${ac.inactive_high.note} &middot; showing top \${ac.inactive_high.total_matching.toLocaleString('en-IN')} matching, most-inactive-first</div>
          <div id="inactive-high-table"></div>
          <div class="ac-pagination" id="inactive-high-pagination"></div>
        </section>
        <section class="acc-rose">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-rose">&#128564;</div><h2>Inactive Users - Low</h2><span class="today-tag">\${ac.inactive_low.total_matching.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-inactive-low">&#128190; Excel</button>
          </div>
          <div class="ac-note">\${ac.inactive_low.note} &middot; showing top \${ac.inactive_low.total_matching.toLocaleString('en-IN')} matching, most-inactive-first</div>
          <div id="inactive-low-table"></div>
          <div class="ac-pagination" id="inactive-low-pagination"></div>
        </section>
      </div>

      <div class="analysis-heading withdrawal"><h2>Active Users</h2><div class="line"></div><span class="tag">ACTION CENTER</span></div>
      <div class="row2col">
        <section class="acc-cyan">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-cyan">&#9989;</div><h2>Low - Active Users (V2-V4)</h2><span class="today-tag">\${ac.active_low.total_matching.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-active-low">&#128190; Excel</button>
          </div>
          <div class="ac-note">\${ac.active_low.note} &middot; showing top \${ac.active_low.total_matching.toLocaleString('en-IN')} matching, most-inactive-first</div>
          <div id="active-low-table"></div>
          <div class="ac-pagination" id="active-low-pagination"></div>
        </section>
        <section class="acc-cyan">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-cyan">&#9989;</div><h2>High - Active Users (V5-V15)</h2><span class="today-tag">\${ac.active_high.total_matching.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-active-high">&#128190; Excel</button>
          </div>
          <div class="ac-note">\${ac.active_high.note} &middot; showing top \${ac.active_high.total_matching.toLocaleString('en-IN')} matching, most-inactive-first</div>
          <div id="active-high-table"></div>
          <div class="ac-pagination" id="active-high-pagination"></div>
        </section>
      </div>

      <div class="analysis-heading deposit"><h2>VIP Near Upgrade</h2><div class="line"></div><span class="tag">ACTION CENTER</span></div>
      <div class="row2col">
        <section class="acc-purple">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-purple">&#11014;&#65039;</div><h2>Low - VIP Near Upgrade</h2><span class="today-tag">\${ac.near_upgrade_low.total_matching.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-near-low">&#128190; Excel</button>
          </div>
          <div class="ac-note">\${ac.near_upgrade_low.note} &middot; showing top \${ac.near_upgrade_low.total_matching.toLocaleString('en-IN')} matching, sorted closest-first</div>
          <div id="near-low-table"></div>
          <div class="ac-pagination" id="near-low-pagination"></div>
        </section>
        <section class="acc-purple">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-purple">&#11014;&#65039;</div><h2>High - VIP Near Upgrade</h2><span class="today-tag">\${ac.near_upgrade_high.total_matching.toLocaleString('en-IN')}</span></div>
            <button class="download-btn-sm" id="btn-dl-near-high">&#128190; Excel</button>
          </div>
          <div class="ac-note">\${ac.near_upgrade_high.note} &middot; showing top \${ac.near_upgrade_high.total_matching.toLocaleString('en-IN')} matching, sorted closest-first</div>
          <div id="near-high-table"></div>
          <div class="ac-pagination" id="near-high-pagination"></div>
        </section>
      </div>

      \${wcs ? \`
      <div class="analysis-heading withdrawal"><h2>Weekly Cashback Shield</h2><div class="line"></div><span class="today-tag">\${shortDate(wcs.week_start)} - \${shortDate(wcs.week_end)}</span><span class="tag">ACTION CENTER</span></div>
      <section class="acc-orange">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-orange">&#128737;&#65039;</div><h2>Eligible Users This Week</h2><span class="today-tag">\${fmt(wcs.eligible_count)}</span></div>
          <button class="download-btn-sm" id="btn-dl-cashback">&#128190; Excel</button>
        </div>
        <div class="reactivation-highlight">
          <div class="rh-count">\${fmt(wcs.eligible_count)}<small>Eligible Users</small></div>
          <div class="rh-pct">\${money(wcs.total_bonus)}<small>Total Bonus Payable</small></div>
        </div>
        <div class="ac-note">VIP 2+ only &middot; Loss Rs 500-4,999 (80%+ of week's deposit lost): flat 1.5% &middot; Loss Rs 5,000-2,500,000: 50%-100%+ loss scales cashback -- VIP 2-4: 2.00%-4.00%, VIP 5-15: 1.51%-5.00% &middot; credited Sunday morning, no wagering requirement</div>
        <div id="cashback-table"></div>
        <div class="ac-pagination" id="cashback-pagination"></div>
      </section>
      \` : ''}
    \`;

    if (wcs) {
      paginatedTable('cashback-table', 'cashback-pagination', wcs.rows, cashbackCols, 6, { jumpDropdown: true });
      document.getElementById('btn-dl-cashback').addEventListener('click', () =>
        downloadExcel(wcs.rows, cashbackCols, 'Weekly Cashback Shield', 'weekly-cashback-shield-' + wcs.week_start + '.xlsx'));
    }

    paginatedTable('near-low-table', 'near-low-pagination', ac.near_upgrade_low.rows, nearCols, 6, { jumpDropdown: true });
    paginatedTable('near-high-table', 'near-high-pagination', ac.near_upgrade_high.rows, nearCols, 6, { jumpDropdown: true });
    paginatedTable('inactive-high-table', 'inactive-high-pagination', ac.inactive_high.rows, inactiveCols, 6, { jumpDropdown: true });
    paginatedTable('inactive-low-table', 'inactive-low-pagination', ac.inactive_low.rows, inactiveCols, 6, { jumpDropdown: true });

    document.getElementById('btn-dl-near-low').addEventListener('click', () =>
      downloadExcel(ac.near_upgrade_low.rows, nearCols, 'Low VIP Near Upgrade', 'low-vip-near-upgrade.xlsx'));
    document.getElementById('btn-dl-near-high').addEventListener('click', () =>
      downloadExcel(ac.near_upgrade_high.rows, nearCols, 'High VIP Near Upgrade', 'high-vip-near-upgrade.xlsx'));
    document.getElementById('btn-dl-inactive-high').addEventListener('click', () =>
      downloadExcel(ac.inactive_high.rows, inactiveCols, 'Inactive Users High', 'inactive-users-high.xlsx'));
    document.getElementById('btn-dl-inactive-low').addEventListener('click', () =>
      downloadExcel(ac.inactive_low.rows, inactiveCols, 'Inactive Users Low', 'inactive-users-low.xlsx'));

    paginatedTable('active-low-table', 'active-low-pagination', ac.active_low.rows, activeCols, 6, { jumpDropdown: true });
    paginatedTable('active-high-table', 'active-high-pagination', ac.active_high.rows, activeCols, 6, { jumpDropdown: true });
    document.getElementById('btn-dl-active-low').addEventListener('click', () =>
      downloadExcel(ac.active_low.rows, activeCols, 'Active Users Low', 'active-users-low.xlsx'));
    document.getElementById('btn-dl-active-high').addEventListener('click', () =>
      downloadExcel(ac.active_high.rows, activeCols, 'Active Users High', 'active-users-high.xlsx'));

    if (acx) {
      paginatedTable('new-users-table', 'new-users-pagination', acx.yesterday_first_deposit_users, newUserCols, 6, { jumpDropdown: true });
      paginatedTable('bonus-table', 'bonus-pagination', acx.no_return_fd_users, bonusCols, 6, { jumpDropdown: true });
      document.getElementById('btn-dl-new-users').addEventListener('click', () =>
        downloadExcel(acx.yesterday_first_deposit_users, newUserCols, 'Yesterday First Deposit Users', 'yesterday-first-deposit-users.xlsx'));
      document.getElementById('btn-dl-bonus').addEventListener('click', () =>
        downloadExcel(acx.no_return_fd_users, bonusCols, 'No-Return First Deposit Users', 'no-return-fd-users.xlsx'));
    }
  })();
}

if (IS_PERFORMANCE) {
  (async () => {
    const res = await fetch('/data.json');
    if (!res.ok) {
      document.getElementById('performance-app').textContent = 'Failed to load report data (' + res.status + ')';
      return;
    }
    const data = await res.json();
    const perfRows = data.agent_performance || [];
    const targets = data.agent_performance_targets || {};
    const reactivationData = data.reactivation || {};
    const REACTIVATION_COHORT_CATEGORIES = { 'Reactivation Low': 'low', 'Reactivation High': 'high' };
    // Departments: each is its own scorecard, scored only on its own
    // categories -- every agent is scored in every department (see
    // agent_performance_departments), earning a separate score in each.
    const departments = data.agent_performance_departments || {};
    const deptNames = Object.keys(departments);
    const allDates = Array.from(new Set(perfRows.map(r => r.date))).sort();
    const todayStr = data.report_today || allDates[allDates.length - 1];
    // Incentives are always judged on the CURRENT CALENDAR MONTH's cumulative
    // performance, independent of whatever range is picked below for
    // browsing day-to-day numbers -- so the podium never moves just because
    // someone clicked "Yesterday" to look something up.
    const monthFrom = todayStr.slice(0, 7) + '-01';
    const monthTo = todayStr;

    const el = document.getElementById('performance-app');
    el.className = '';
    if (!deptNames.length) {
      el.innerHTML = '<div class="no-data">Performance data not available in this report yet.</div>';
      return;
    }
    el.innerHTML = \`
      <div class="analysis-heading deposit"><h2>Monthly Leaderboard &amp; Incentives</h2><div class="line"></div><span class="tag">\${shortDate(monthFrom)} - \${shortDate(monthTo)}</span></div>
      <div class="perf-explainer">
        <div>
          <h5>How scoring works</h5>
          <div class="perf-tier-key">
            <div class="tk-row"><span class="tk-dot" style="background:#059669"></span>100%+ of target -- fully on track</div>
            <div class="tk-row"><span class="tk-dot" style="background:#d97706"></span>60-99% of target -- getting there</div>
            <div class="tk-row"><span class="tk-dot" style="background:#dc2626"></span>Below 60% of target</div>
            <div class="tk-row"><span class="tk-dot" style="background:#d1d5db"></span>No users assigned this criterion -- excluded, not counted against the agent</div>
          </div>
        </div>
        <div>
          <h5>Incentive brackets (rank 1 / 2 / 3)</h5>
          <div class="perf-incentive-table">
            <div class="perf-incentive-cell tier1"><div class="ic-thresh">50%+</div><div class="ic-amts">Rs1500 / 800 / 500</div></div>
            <div class="perf-incentive-cell tier2"><div class="ic-thresh">75%+</div><div class="ic-amts">Rs4000 / 2000 / 1400</div></div>
            <div class="perf-incentive-cell tier3"><div class="ic-thresh">90%+</div><div class="ic-amts">Rs10000 / 5000 / 2000</div></div>
          </div>
        </div>
      </div>
      <div class="perf-leaderboard-grid">
        <div>
          \${deptNames.map(dept => \`
            <div class="perf-dept-panel">
              <div class="perf-dept-panel-head"><span class="dp-icon">\${deptIcon(dept)}</span><h4>\${dept}</h4></div>
              <div id="perf-mini-\${slugifyDept(dept)}"></div>
            </div>
          \`).join('')}
        </div>
        <div>
          <div class="perf-dept-panel-head" style="margin-bottom:12px"><span class="dp-icon">&#127942;</span><h4>Overall Ranking -- average across all departments</h4></div>
          <div class="perf-controls" id="perf-overall-range-controls" style="margin-bottom:14px">
            <button class="perf-preset" data-overall-preset="today">Today</button>
            <button class="perf-preset active" data-overall-preset="month">This Month</button>
            <button class="perf-preset" data-overall-preset="yesterday">Till Yesterday</button>
            <button class="perf-preset" data-overall-preset="lastmonth">Last Month</button>
          </div>
          <div id="perf-podium-overall" class="perf-overall-podium"></div>
        </div>
      </div>

      <div class="analysis-heading withdrawal"><h2>Daily / Range Performance</h2><div class="line"></div><span class="tag">Scored per department</span></div>
      <div class="perf-section-lead">Pick a date or range below -- every department's list recalculates against that window (separate from the Monthly Leaderboard's own date-range control above).</div>
      <div class="perf-controls">
        <button class="perf-preset active" data-preset="today">Today</button>
        <button class="perf-preset" data-preset="yesterday">Yesterday</button>
        <button class="perf-preset" data-preset="7d">Last 7 Days</button>
        <button class="perf-preset" data-preset="30d">Last 30 Days</button>
        <button class="perf-preset" data-preset="35d">Last 35 Days</button>
        <span class="perf-to">|</span>
        <div class="perf-daterange">
          <button type="button" id="perf-daterange-btn" class="perf-daterange-btn">&#128197; <span id="perf-daterange-label">Today</span></button>
          <div id="perf-daterange-popover" class="perf-daterange-popover" style="display:none">
            <label>From<input type="date" id="perf-from"></label>
            <label>To<input type="date" id="perf-to"></label>
            <button type="button" id="perf-daterange-apply">Apply</button>
          </div>
        </div>
      </div>
      <div class="perf-range-grid">
        <div class="perf-range-col">
          \${deptNames.slice(0, 2).map(dept => \`
            <div class="perf-dept-block">
              <div class="perf-dept-block-head"><span class="db-icon">\${deptIcon(dept)}</span><h3>\${dept}</h3><span class="db-count" id="perf-count-\${slugifyDept(dept)}"></span></div>
              <div class="perf-dept-scroll"><div id="perf-list-\${slugifyDept(dept)}"></div></div>
            </div>
          \`).join('')}
        </div>
        <div class="perf-range-col">
          \${deptNames.slice(2).map(dept => \`
            <div class="perf-dept-block">
              <div class="perf-dept-block-head"><span class="db-icon">\${deptIcon(dept)}</span><h3>\${dept}</h3><span class="db-count" id="perf-count-\${slugifyDept(dept)}"></span></div>
              <div class="perf-dept-scroll"><div id="perf-list-\${slugifyDept(dept)}"></div></div>
            </div>
          \`).join('')}
        </div>
      </div>
    \`;

    function deptIcon(name) {
      const n = name.toLowerCase();
      if (n.includes('ftd')) return '&#127881;';
      if (n.includes('reactivation')) return '&#128260;';
      if (n.includes('vip')) return '&#128142;';
      return '&#128202;';
    }

    function slugifyDept(name) { return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''); }
    function fmtMoney(v) { return 'Rs' + Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
    function tierForPct(pct) {
      if (pct >= 90) return 3;
      if (pct >= 75) return 2;
      if (pct >= 50) return 1;
      return 0;
    }
    const INCENTIVE_TABLE = {
      1: [1500, 800, 500],
      2: [4000, 2000, 1400],
      3: [10000, 5000, 2000],
    };
    function barClass(pct) {
      if (pct >= 100) return 'pb-green';
      if (pct >= 60) return 'pb-amber';
      return 'pb-red';
    }

    function computeLeaderboard(fromDate, toDate, agents, categories) {
      const inRange = perfRows.filter(r => r.date >= fromDate && r.date <= toDate);
      const byAgentCat = {};
      for (const r of inRange) {
        if (r.agent === 'Un-Assigned') continue;
        byAgentCat[r.agent] = byAgentCat[r.agent] || {};
        const cur = byAgentCat[r.agent][r.category] || { num: 0, den: 0 };
        cur.num += r.numerator || 0;
        cur.den += r.denominator || 0;
        byAgentCat[r.agent][r.category] = cur;
      }
      const results = agents.map(agent => {
        const catData = byAgentCat[agent] || {};
        // Every APPLICABLE KPI shares an equal weight in the composite below
        // -- a KPI is "not applicable" when the agent had zero assigned/
        // eligible users for it (e.g. nobody who made a first deposit
        // yesterday, so Retention has nothing to measure). Rather than
        // scoring that as an unearnable 0%, it's excluded entirely and its
        // share redistributed across whichever KPIs DO apply, so an agent
        // is only ever judged on what was actually possible for them.
        const criteria = categories.map(cat => {
          const meta = targets[cat] || { type: 'count', target: 0 };
          const agg = catData[cat] || { num: 0, den: 0 };
          const applicable = agg.den > 0;
          let actualDisplay, pctOfTarget;
          if (meta.type === 'rate') {
            const rawRate = agg.den > 0 ? (agg.num / agg.den) * 100 : 0;
            pctOfTarget = meta.target > 0 ? (rawRate / meta.target) * 100 : 0;
            // Show the raw assigned/retained counts alongside the rate --
            // a bare percentage on a tiny cohort (e.g. 1 of 1 = "100%") reads
            // as misleading without the counts backing it up.
            actualDisplay = applicable
              ? Math.round(agg.num) + ' / ' + Math.round(agg.den) + ' (' + rawRate.toFixed(1) + '%)'
              : 'No users assigned';
          } else {
            pctOfTarget = agg.den > 0 ? (agg.num / agg.den) * 100 : 0;
            actualDisplay = Math.round(agg.num) + ' / ' + Math.round(agg.den);
          }
          return { category: cat, pctOfTarget, actualDisplay, applicable, type: meta.type, cohortSize: Math.round(agg.den) };
        });
        const applicableCriteria = criteria.filter(c => c.applicable);
        // Each KPI's contribution to the composite is capped at 100% -- a
        // single small-sample rate (e.g. 1 of 2 retained = 50%, which is
        // 167% of a 30% target) would otherwise swing the whole average on
        // its own, letting one lucky data point outrank agents who are
        // genuinely stronger across every other KPI. The uncapped
        // pctOfTarget is still shown per-KPI, so real overshoots stay
        // visible -- they just can't outweigh the rest of the scorecard.
        const composite = applicableCriteria.length
          ? applicableCriteria.reduce((s, c) => s + Math.min(c.pctOfTarget, 100), 0) / applicableCriteria.length
          : 0;
        return { agent, criteria, composite };
      });
      results.sort((a, b) => b.composite - a.composite);
      return results;
    }

    function renderOverallPodiumInto(elId, ranked) {
      const el = document.getElementById(elId);
      if (!el) return;
      if (!ranked.length) {
        el.innerHTML = '<div class="perf-overall-empty">No agents to rank yet</div>';
        return;
      }
      const medals = ['&#129351;', '&#129352;', '&#129353;'];
      const tiers = ['gold', 'silver', 'bronze'];
      const labels = ['Gold', 'Silver', 'Bronze'];
      let html = ranked.slice(0, 3).map((r, i) => {
        const tier = tierForPct(r.composite);
        const incentive = tier > 0 ? INCENTIVE_TABLE[tier][i] : null;
        return '<div class="poc ' + tiers[i] + '">' +
          '<div class="poc-medal">' + medals[i] + '</div>' +
          '<div class="poc-body">' +
          '<div class="poc-rank-label">' + labels[i] + '</div>' +
          '<div class="poc-name">' + r.agent + '</div>' +
          (incentive
            ? '<div class="poc-incentive">Incentive earned: ' + fmtMoney(incentive) + '</div>'
            : '<div class="poc-incentive" style="opacity:0.8">Below 50% of target -- no incentive yet</div>') +
          '</div>' +
          '<div class="poc-score"><span class="val">' + r.composite.toFixed(1) + '%</span><small>of target</small></div>' +
          '</div>';
      }).join('');

      // Every rank from 4th down to last, shown as slim rows below the
      // podium -- the full spread, not just a sampled few.
      if (ranked.length > 3) {
        const rest = ranked.slice(3);
        html += '<div class="perf-extra-rank">' + rest.map((r, idx) => {
          const rankNum = idx + 4;
          const isLast = rankNum === ranked.length;
          const color = r.composite >= 100 ? '#059669' : r.composite >= 60 ? '#d97706' : '#dc2626';
          return '<div class="perf-extra-rank-row' + (isLast ? ' last' : '') + '">' +
            '<span class="er-label">' + ordinal(rankNum) + (isLast ? ' (Last)' : '') + '</span>' +
            '<span class="er-name">' + r.agent + '</span>' +
            '<span class="er-score" style="color:' + color + '">' + r.composite.toFixed(1) + '%</span>' +
            '</div>';
        }).join('') + '</div>';
      }
      el.innerHTML = html;
    }

    function ordinal(n) {
      const v = n % 100;
      if (v >= 11 && v <= 13) return n + 'th';
      switch (n % 10) {
        case 1: return n + 'st';
        case 2: return n + 'nd';
        case 3: return n + 'rd';
        default: return n + 'th';
      }
    }

    function renderRankListInto(elId, ranked, opts) {
      const listEl = document.getElementById(elId);
      if (!listEl) return;
      const showIncentive = !opts || opts.showIncentive !== false;
      if (!ranked.length) {
        listEl.innerHTML = '<div class="perf-dept-empty">No agents to rank yet</div>';
        return;
      }
      const medals = ['&#129351;', '&#129352;', '&#129353;'];
      listEl.innerHTML = ranked.slice(0, 3).map((r, i) => {
        const tier = tierForPct(r.composite);
        const incentive = tier > 0 ? INCENTIVE_TABLE[tier][i] : null;
        const barPct = Math.max(0, Math.min(r.composite, 100));
        return '<div class="perf-rank-row">' +
          '<span class="pr-medal">' + medals[i] + '</span>' +
          '<div class="pr-main">' +
          '<div class="pr-name-line"><span class="pr-name">' + r.agent + '</span>' +
          '<span class="pr-score" style="color:' + (r.composite >= 100 ? '#059669' : r.composite >= 60 ? '#d97706' : '#dc2626') + '">' + r.composite.toFixed(1) + '%</span></div>' +
          '<div class="pr-bar"><div class="pr-bar-fill" style="width:' + barPct + '%;background:' + (r.composite >= 100 ? '#059669' : r.composite >= 60 ? '#d97706' : '#dc2626') + '"></div></div>' +
          '</div>' +
          (showIncentive
            ? (incentive
              ? '<span class="pr-incentive">' + fmtMoney(incentive) + '</span>'
              : '<span class="pr-incentive na">No incentive</span>')
            : '') +
          '</div>';
      }).join('');
    }

    // Overall Ranking: a WEIGHTED average of an agent's composite across
    // every department -- Reactivation Team counts for 20%, General for
    // 15%, and the remaining departments (FTD Team, VIP Team) split the
    // other 65% equally between them (32.5% each with 2 of them). Falls
    // back to a plain equal split across whatever departments exist if
    // neither named department is present, so this doesn't silently lose
    // weight. Each department's composite is already normalized to "% of
    // that department's own target," so a weighted sum is apples-to-apples
    // regardless of which/how-many categories each one covers.
    const NAMED_WEIGHTS = { 'Reactivation Team': 0.20, 'General': 0.15 };
    function departmentWeights() {
      const weights = {};
      const namedPresent = Object.keys(NAMED_WEIGHTS).filter(d => deptNames.includes(d));
      const otherDepts = deptNames.filter(d => !namedPresent.includes(d));
      if (namedPresent.length && otherDepts.length) {
        const namedTotal = namedPresent.reduce((s, d) => s + NAMED_WEIGHTS[d], 0);
        const otherWeight = (1 - namedTotal) / otherDepts.length;
        deptNames.forEach(d => { weights[d] = namedPresent.includes(d) ? NAMED_WEIGHTS[d] : otherWeight; });
      } else {
        deptNames.forEach(d => { weights[d] = 1 / deptNames.length; });
      }
      return weights;
    }
    function computeOverallLeaderboard(fromDate, toDate) {
      const allAgents = new Set();
      deptNames.forEach(dept => departments[dept].agents.forEach(a => allAgents.add(a)));
      const weights = departmentWeights();
      const scoreByAgent = {};
      for (const dept of deptNames) {
        const { agents: deptAgents, categories: deptCategories } = departments[dept];
        const ranked = computeLeaderboard(fromDate, toDate, deptAgents, deptCategories);
        for (const r of ranked) {
          scoreByAgent[r.agent] = (scoreByAgent[r.agent] || 0) + r.composite * weights[dept];
        }
      }
      const results = Array.from(allAgents).map(agent => ({ agent, composite: scoreByAgent[agent] || 0 }));
      results.sort((a, b) => b.composite - a.composite);
      return results;
    }

    // The Monthly Leaderboard's date-range control (This Month / Till
    // Yesterday / custom From-To) drives BOTH the Overall Ranking podium
    // (right) and the department top-3 mini-lists (left) together --
    // independent of the separate Daily/Range Performance controls
    // further down the page. Defaults to the current calendar month,
    // which is also what the incentive brackets are judged against.
    function renderOverallPodium(fromDate, toDate) {
      renderOverallPodiumInto('perf-podium-overall', computeOverallLeaderboard(fromDate, toDate));
    }

    function renderDeptMiniLists(fromDate, toDate) {
      for (const dept of deptNames) {
        const { agents: deptAgents, categories: deptCategories } = departments[dept];
        const ranked = computeLeaderboard(fromDate, toDate, deptAgents, deptCategories);
        renderRankListInto('perf-mini-' + slugifyDept(dept), ranked, { showIncentive: false });
      }
    }

    function renderLeaderboardSection(fromDate, toDate) {
      renderOverallPodium(fromDate, toDate);
      renderDeptMiniLists(fromDate, toDate);
    }

    function renderPodium() {
      renderLeaderboardSection(monthFrom, monthTo);
    }

    function render(fromDate, toDate) {
      for (const dept of deptNames) {
        const { agents: deptAgents, categories: deptCategories } = departments[dept];
        const ranked = computeLeaderboard(fromDate, toDate, deptAgents, deptCategories);
        const listEl = document.getElementById('perf-list-' + slugifyDept(dept));
        if (!listEl) continue;
        const countEl = document.getElementById('perf-count-' + slugifyDept(dept));
        if (countEl) countEl.textContent = ranked.length + (ranked.length === 1 ? ' agent' : ' agents');

        listEl.innerHTML = ranked.map((r, i) => {
          const rankNum = i + 1;
          const critHtml = r.criteria.map(c => {
            const meta = targets[c.category] || { type: 'count', target: 0 };
            const targetLabel = meta.type === 'rate' ? meta.target + '%' : fmt(meta.target);
            // Total users: for rate-type metrics, the cohort size behind
            // the %. For Reactivation Low/High specifically, the flat
            // daily target isn't a cohort size, so pull the agent's actual
            // "inactive + reactivated today" pool from data.reactivation
            // instead. VIP Upgrade (General) has no equivalent pool concept
            // -- skipped there.
            const reactTier = REACTIVATION_COHORT_CATEGORIES[c.category];
            let totalUsersLabel = '';
            if (meta.type === 'rate') {
              totalUsersLabel = ' &middot; ' + fmt(c.cohortSize) + (c.cohortSize === 1 ? ' user' : ' users');
            } else if (reactTier) {
              const cohort = ((reactivationData[reactTier] || {}).cohort_by_agent || {})[r.agent] || 0;
              totalUsersLabel = ' &middot; ' + fmt(cohort) + (cohort === 1 ? ' user' : ' users');
            }
            if (!c.applicable) {
              return '<div class="perf-crit perf-crit-na">' +
                '<div class="pc-label">' + c.category + '</div>' +
                '<div class="pc-target">Target: ' + targetLabel + '</div>' +
                '<div class="pc-value">' + c.actualDisplay + '</div>' +
                '<div class="perf-bar"><div class="perf-bar-fill pb-na" style="width:100%"></div></div>' +
                '</div>';
            }
            const pct = Math.max(0, Math.min(c.pctOfTarget, 999));
            const barPct = Math.min(pct, 100);
            return '<div class="perf-crit">' +
              '<div class="pc-label">' + c.category + '</div>' +
              '<div class="pc-target">Target: ' + targetLabel + totalUsersLabel + '</div>' +
              '<div class="pc-value">' + c.actualDisplay + '</div>' +
              '<div class="perf-bar"><div class="perf-bar-fill ' + barClass(pct) + '" style="width:' + barPct + '%"></div></div>' +
              '</div>';
          }).join('');
          return '<div class="perf-card">' +
            '<div class="perf-rank' + (rankNum <= 3 ? ' top3' : '') + '">' + rankNum + '</div>' +
            '<div class="perf-agent-name">' + r.agent + '</div>' +
            '<div class="perf-criteria-grid" style="grid-template-columns:repeat(' + Math.max(1, r.criteria.length) + ',1fr)">' + critHtml + '</div>' +
            '<div class="perf-score-big" style="color:' + (r.composite >= 100 ? '#059669' : r.composite >= 60 ? '#d97706' : '#dc2626') + '">' + r.composite.toFixed(2) + '%</div>' +
            '</div>';
        }).join('');
      }
    }

    const fromInput = document.getElementById('perf-from');
    const toInput = document.getElementById('perf-to');
    const presetBtns = Array.from(document.querySelectorAll('.perf-preset'));
    const dateRangeBtn = document.getElementById('perf-daterange-btn');
    const dateRangeLabel = document.getElementById('perf-daterange-label');
    const dateRangePopover = document.getElementById('perf-daterange-popover');
    const dateRangeApply = document.getElementById('perf-daterange-apply');

    function updateDateRangeLabel(from, to) {
      dateRangeLabel.textContent = from === to ? shortDate(from) : shortDate(from) + ' \\u2013 ' + shortDate(to);
    }

    dateRangeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dateRangePopover.style.display = dateRangePopover.style.display === 'none' ? 'flex' : 'none';
    });
    dateRangePopover.addEventListener('click', (e) => e.stopPropagation());
    document.addEventListener('click', () => { dateRangePopover.style.display = 'none'; });

    function applyPreset(preset) {
      let from = todayStr, to = todayStr;
      const idx = allDates.indexOf(todayStr);
      function dateNDaysBack(n) {
        const anchorIdx = idx >= 0 ? idx : allDates.length - 1;
        const backIdx = Math.max(0, anchorIdx - (n - 1));
        return allDates[backIdx] || allDates[0];
      }
      if (preset === 'today') { from = todayStr; to = todayStr; }
      else if (preset === 'yesterday') {
        const anchorIdx = idx >= 0 ? idx : allDates.length - 1;
        const yIdx = Math.max(0, anchorIdx - 1);
        from = allDates[yIdx] || todayStr; to = from;
      }
      else if (preset === '7d') { from = dateNDaysBack(7); to = todayStr; }
      else if (preset === '30d') { from = dateNDaysBack(30); to = todayStr; }
      else if (preset === '35d') { from = allDates[0] || todayStr; to = todayStr; }
      fromInput.value = from;
      toInput.value = to;
      presetBtns.forEach(b => b.classList.toggle('active', b.dataset.preset === preset));
      updateDateRangeLabel(from, to);
      dateRangePopover.style.display = 'none';
      render(from, to);
    }

    presetBtns.forEach(btn => btn.addEventListener('click', () => applyPreset(btn.dataset.preset)));
    dateRangeApply.addEventListener('click', () => {
      const from = fromInput.value || toInput.value;
      const to = toInput.value || fromInput.value;
      if (!from || !to) return;
      presetBtns.forEach(b => b.classList.remove('active'));
      updateDateRangeLabel(from, to);
      dateRangePopover.style.display = 'none';
      render(from, to);
    });

    // Overall Ranking's own date-range control (Today / This Month / Till
    // Yesterday / Last Month) -- independent of the Daily/Range Performance
    // controls above and of the department mini-lists, which both stay
    // pinned to the current calendar month.
    const overallPresetBtns = Array.from(document.querySelectorAll('#perf-overall-range-controls .perf-preset'));

    function yesterdayStr() {
      const idx = allDates.indexOf(todayStr);
      const anchorIdx = idx >= 0 ? idx : allDates.length - 1;
      const yIdx = Math.max(0, anchorIdx - 1);
      return allDates[yIdx] || todayStr;
    }

    function lastMonthRange() {
      const [ty, tm] = todayStr.split('-').map(Number);
      const lastDayPrevMonth = new Date(Date.UTC(ty, tm - 1, 0));
      const to = lastDayPrevMonth.toISOString().slice(0, 10);
      const from = to.slice(0, 7) + '-01';
      return { from, to };
    }

    overallPresetBtns.forEach(btn => btn.addEventListener('click', () => {
      overallPresetBtns.forEach(b => b.classList.toggle('active', b === btn));
      if (btn.dataset.overallPreset === 'month') {
        renderLeaderboardSection(monthFrom, monthTo);
      } else if (btn.dataset.overallPreset === 'today') {
        renderLeaderboardSection(todayStr, todayStr);
      } else if (btn.dataset.overallPreset === 'lastmonth') {
        const { from, to } = lastMonthRange();
        renderLeaderboardSection(from, to);
      } else {
        // If today is the 1st of the month, "yesterday" falls in the
        // previous month -- clamp to a same-day range at month start
        // rather than reaching into last month's data.
        const y = yesterdayStr();
        const to = y >= monthFrom ? y : monthFrom;
        renderLeaderboardSection(monthFrom, to);
      }
    }));

    renderPodium();
    applyPreset('today');
  })();
}

if (IS_ANALYTICS) {
  (async () => {
    const res = await fetch('/data.json');
    if (!res.ok) {
      document.getElementById('analytics-app').textContent = 'Failed to load report data (' + res.status + ')';
      return;
    }
    const globalData = await res.json();
    let data = scopeReportToAgent(globalData, AGENT_NAME);
    if (IS_AGENT_SCOPED) {
      // region_vip_analytics can't be scoped client-side (derived from raw
      // per-transaction records never shipped to the browser) -- pull it
      // from the small per-agent file instead, same pattern the Home page uses.
      const agentRes = await fetch('/data.json?agent=' + encodeURIComponent(AGENT_NAME));
      if (!agentRes.ok) {
        document.getElementById('analytics-app').textContent = 'Failed to load this agent\\'s report (' + agentRes.status + ')';
        return;
      }
      const agentData = await agentRes.json();
      data = { ...data, region_vip_analytics: agentData.region_vip_analytics };
    }
    document.getElementById('updated-badge').innerHTML =
      '<span class="dot"></span> Records updated through ' +
      (data.latest_record_time ? new Date(data.latest_record_time).toLocaleString() : 'n/a');
    document.getElementById('analytics-app').className = '';

    const rv = data.region_vip_analytics || {};
    const dates = Object.keys(rv).sort();
    if (!dates.length) {
      document.getElementById('analytics-app').innerHTML = '<div class="no-data">Analytics data not available in this report yet.</div>';
      return;
    }
    let selectedDate = dates[dates.length - 1];

    // Reactivation/VIP Upgrade/Retention/Premium Active are single "as of
    // that day" computations, overwritten every pipeline run -- so browsing
    // to a past date needs that day's own snapshot (a separate small R2
    // object per day, fetched on demand via /api/analytics-history), not
    // something derivable from the main report. Today's snapshot is already
    // sitting in the already-fetched data itself, so it's seeded here to skip a redundant fetch.
    const snapshotCache = {
      [data.report_today]: {
        reactivation: data.reactivation,
        vip_upgrade: data.vip_upgrade,
        retention: data.retention,
        premium_active: data.premium_active,
      },
    };
    function dateTag(d) {
      return '<span class="today-tag">' + (d === data.report_today ? 'TODAY: ' : 'DATE: ') + shortDate(d) + '</span>';
    }

    const reactivationCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP Level', render: r => r.vip_level, num: true },
      { label: 'Inactive Days', render: r => fmt(r.inactive_days), raw: r => r.inactive_days, num: true },
      { label: 'Total Deposit Today', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
    ];

    const vipUpgradeCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP Before', render: r => r.vip_before, num: true },
      { label: 'VIP After', render: r => r.vip_after, num: true },
      { label: 'Total Deposit Today', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Amount Over Minimum', render: r => money(r.amount_over_minimum), raw: r => r.amount_over_minimum, num: true },
    ];

    const retentionCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'Total Deposit Today', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Deposit Count', render: r => fmt(r.deposit_count), raw: r => r.deposit_count, num: true },
      { label: 'Region', render: r => r.region, raw: r => r.region },
    ];

    const premiumActiveCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP', render: r => r.vip, raw: r => r.vip, num: true },
      { label: 'Deposit Amount', render: r => money(r.deposit_amount), raw: r => r.deposit_amount, num: true },
      { label: 'Deposit Count', render: r => fmt(r.deposit_count), raw: r => r.deposit_count, num: true },
    ];

    function funnelLine(funnel, tier) {
      if (!funnel) return '';
      const parts = ['3', '7'].map(w => {
        const f = funnel[w] && funnel[w][tier];
        return f
          ? w + '-day: <b>' + f.pct + '%</b> (' + fmt(f.converted) + ' of ' + fmt(f.cohort_size) + ')'
          : w + '-day: not enough history yet';
      });
      return '<div class="ac-note">Conversion funnel &middot; ' + parts.join(' &middot; ') + '</div>';
    }

    document.getElementById('analytics-app').innerHTML = \`
      <div class="analysis-heading deposit"><h2>Analytics</h2><div class="line"></div><span class="tag">ALL SECTIONS BELOW</span></div>
      <div class="date-switch" id="analytics-date-switch"></div>

      <div class="analysis-heading deposit"><h2>Region &amp; VIP Deposit Analytics</h2><div class="line"></div><span class="tag">ANALYTICS</span></div>
      <div class="row2col">
        <section class="acc-blue">
          <div class="sec-title"><div class="badge b-blue">&#127758;</div><h2>Top 10 Regions by Deposit</h2></div>
          <canvas id="region-chart"></canvas>
        </section>
        <section class="acc-purple">
          <div class="sec-title"><div class="badge b-purple">&#128142;</div><h2>Deposit by VIP Level</h2></div>
          <canvas id="vip-chart"></canvas>
        </section>
      </div>
      <div id="analytics-sections">\${sectionsTemplate(selectedDate, snapshotCache[selectedDate])}</div>
    \`;

    function sectionsTemplate(dateForTag, snap) {
      if (!snap) {
        return '<div class="no-data">No historical snapshot captured for this date yet -- snapshots started the day this feature shipped, so earlier dates will fill in as they occur.</div>';
      }
      const reactivation = snap.reactivation;
      const vipUpgrade = snap.vip_upgrade;
      const retention = snap.retention;
      const premiumActive = snap.premium_active;
      const todayTag = dateTag(dateForTag);
      return \`
      \${reactivation ? \`
      <div class="analysis-heading withdrawal"><h2>Reactivation</h2><div class="line"></div>\${todayTag}<span class="tag">ANALYTICS</span></div>
      <div class="row2col">
        <section class="acc-cyan">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-cyan">&#128260;</div><h2>Low V - Reactivation (V2-V4)</h2></div>
            <button class="download-btn-sm" id="btn-dl-reactivation-low">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(reactivation.low.reactivated_count)}<small>Reactivated Today</small></div>
            <div class="rh-pct">\${reactivation.low.pct_reactivated}%<small>of Inactive-Low Cohort</small></div>
          </div>
          <div class="ac-note">\${reactivation.low.note}</div>
          \${funnelLine(reactivation.funnel, 'low')}
          <div id="reactivation-low-table"></div>
          <div class="ac-pagination" id="reactivation-low-pagination"></div>
        </section>
        <section class="acc-cyan">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-cyan">&#128260;</div><h2>High V - Reactivation (V5-V15)</h2></div>
            <button class="download-btn-sm" id="btn-dl-reactivation-high">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(reactivation.high.reactivated_count)}<small>Reactivated Today</small></div>
            <div class="rh-pct">\${reactivation.high.pct_reactivated}%<small>of Inactive-High Cohort</small></div>
          </div>
          <div class="ac-note">\${reactivation.high.note}</div>
          \${funnelLine(reactivation.funnel, 'high')}
          <div id="reactivation-high-table"></div>
          <div class="ac-pagination" id="reactivation-high-pagination"></div>
        </section>
      </div>
      \` : ''}

      \${vipUpgrade ? \`
      <div class="analysis-heading deposit"><h2>VIP Level Upgrade</h2><div class="line"></div>\${todayTag}<span class="tag">ANALYTICS</span></div>
      <div class="row2col">
        <section class="acc-purple">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-purple">&#127942;</div><h2>Low - VIP Upgrade (V2-V4)</h2></div>
            <button class="download-btn-sm" id="btn-dl-vip-upgrade-low">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(vipUpgrade.low.upgraded_count)}<small>Upgraded Today</small></div>
            <div class="rh-pct">\${vipUpgrade.low.pct_upgraded}%<small>of Near-Upgrade Cohort</small></div>
          </div>
          <div class="ac-note">\${vipUpgrade.low.note}</div>
          \${funnelLine(vipUpgrade.funnel, 'low')}
          <div id="vip-upgrade-low-table"></div>
          <div class="ac-pagination" id="vip-upgrade-low-pagination"></div>
        </section>
        <section class="acc-purple">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-purple">&#127942;</div><h2>High - VIP Upgrade (V5-V15)</h2></div>
            <button class="download-btn-sm" id="btn-dl-vip-upgrade-high">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(vipUpgrade.high.upgraded_count)}<small>Upgraded Today</small></div>
            <div class="rh-pct">\${vipUpgrade.high.pct_upgraded}%<small>of Near-Upgrade Cohort</small></div>
          </div>
          <div class="ac-note">\${vipUpgrade.high.note}</div>
          \${funnelLine(vipUpgrade.funnel, 'high')}
          <div id="vip-upgrade-high-table"></div>
          <div class="ac-pagination" id="vip-upgrade-high-pagination"></div>
        </section>
      </div>
      \` : ''}

      \${retention ? \`
      <div class="analysis-heading withdrawal"><h2>Retention</h2><div class="line"></div>\${todayTag}<span class="tag">ANALYTICS</span></div>
      <div class="row2col">
        <section class="acc-emerald">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-emerald">&#127793;</div><h2>First-Deposit Day-1 Retention</h2></div>
            <button class="download-btn-sm" id="btn-dl-retention-fd">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(retention.first_deposit.converted_count)}<small>of \${fmt(retention.first_deposit.cohort_size)} Deposited Again</small></div>
            <div class="rh-pct">\${retention.first_deposit.pct_converted}%<small>Conversion</small></div>
            <div class="rh-pct">\${money(retention.first_deposit.avg_deposit_amount)}<small>Avg Deposit</small></div>
          </div>
          <div class="ac-note">\${retention.first_deposit.note}</div>
          <div id="retention-fd-table"></div>
          <div class="ac-pagination" id="retention-fd-pagination"></div>
        </section>
        <section class="acc-emerald">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-emerald">&#127793;</div><h2>No-Return FD Conversion</h2></div>
            <button class="download-btn-sm" id="btn-dl-retention-bonus">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(retention.no_return_fd_conversion.converted_count)}<small>of \${fmt(retention.no_return_fd_conversion.cohort_size)} Deposited Again</small></div>
            <div class="rh-pct">\${retention.no_return_fd_conversion.pct_converted}%<small>Conversion</small></div>
            <div class="rh-pct">\${money(retention.no_return_fd_conversion.avg_deposit_amount)}<small>Avg Deposit</small></div>
          </div>
          <div class="ac-note">\${retention.no_return_fd_conversion.note}</div>
          <div id="retention-bonus-table"></div>
          <div class="ac-pagination" id="retention-bonus-pagination"></div>
        </section>
      </div>
      \` : ''}

      \${premiumActive ? \`
      <div class="row2col">
        <section class="acc-emerald">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-emerald">&#128142;</div><h2>Low Premium Active</h2></div>
            <button class="download-btn-sm" id="btn-dl-premium-active-low">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(premiumActive.low.converted_count)}<small>of \${fmt(premiumActive.low.cohort_size)} Deposited Today</small></div>
            <div class="rh-pct">\${premiumActive.low.pct_converted}%<small>Conversion</small></div>
            <div class="rh-pct">\${money(premiumActive.low.avg_deposit_amount)}<small>Avg Deposit</small></div>
          </div>
          <div class="ac-note">\${premiumActive.low.note}</div>
          <div id="premium-active-low-table"></div>
          <div class="ac-pagination" id="premium-active-low-pagination"></div>
        </section>
        <section class="acc-emerald">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-emerald">&#128142;</div><h2>High Premium Active</h2></div>
            <button class="download-btn-sm" id="btn-dl-premium-active-high">&#128190; Excel</button>
          </div>
          <div class="reactivation-highlight">
            <div class="rh-count">\${fmt(premiumActive.high.converted_count)}<small>of \${fmt(premiumActive.high.cohort_size)} Deposited Today</small></div>
            <div class="rh-pct">\${premiumActive.high.pct_converted}%<small>Conversion</small></div>
            <div class="rh-pct">\${money(premiumActive.high.avg_deposit_amount)}<small>Avg Deposit</small></div>
          </div>
          <div class="ac-note">\${premiumActive.high.note}</div>
          <div id="premium-active-high-table"></div>
          <div class="ac-pagination" id="premium-active-high-pagination"></div>
        </section>
      </div>
      \` : ''}
      \`;
    }

    function wireSections(snap) {
      if (!snap) return;
      const reactivation = snap.reactivation;
      const vipUpgrade = snap.vip_upgrade;
      const retention = snap.retention;
      const premiumActive = snap.premium_active;

      if (reactivation) {
        paginatedTable('reactivation-low-table', 'reactivation-low-pagination', reactivation.low.rows, reactivationCols, 5);
        paginatedTable('reactivation-high-table', 'reactivation-high-pagination', reactivation.high.rows, reactivationCols, 5);
        document.getElementById('btn-dl-reactivation-low').addEventListener('click', () =>
          downloadExcel(reactivation.low.rows, reactivationCols, 'Reactivation Low', 'reactivation-low.xlsx'));
        document.getElementById('btn-dl-reactivation-high').addEventListener('click', () =>
          downloadExcel(reactivation.high.rows, reactivationCols, 'Reactivation High', 'reactivation-high.xlsx'));
      }

      if (vipUpgrade) {
        paginatedTable('vip-upgrade-low-table', 'vip-upgrade-low-pagination', vipUpgrade.low.rows, vipUpgradeCols, 5);
        paginatedTable('vip-upgrade-high-table', 'vip-upgrade-high-pagination', vipUpgrade.high.rows, vipUpgradeCols, 5);
        document.getElementById('btn-dl-vip-upgrade-low').addEventListener('click', () =>
          downloadExcel(vipUpgrade.low.rows, vipUpgradeCols, 'VIP Upgrade Low', 'vip-upgrade-low.xlsx'));
        document.getElementById('btn-dl-vip-upgrade-high').addEventListener('click', () =>
          downloadExcel(vipUpgrade.high.rows, vipUpgradeCols, 'VIP Upgrade High', 'vip-upgrade-high.xlsx'));
      }

      if (retention) {
        paginatedTable('retention-fd-table', 'retention-fd-pagination', retention.first_deposit.rows, retentionCols, 5);
        paginatedTable('retention-bonus-table', 'retention-bonus-pagination', retention.no_return_fd_conversion.rows, retentionCols, 5);
        document.getElementById('btn-dl-retention-fd').addEventListener('click', () =>
          downloadExcel(retention.first_deposit.rows, retentionCols, 'First Deposit Retention', 'retention-first-deposit.xlsx'));
        document.getElementById('btn-dl-retention-bonus').addEventListener('click', () =>
          downloadExcel(retention.no_return_fd_conversion.rows, retentionCols, 'No-Return FD Conversion', 'no-return-fd-conversion.xlsx'));
      }

      if (premiumActive) {
        paginatedTable('premium-active-low-table', 'premium-active-low-pagination', premiumActive.low.rows, premiumActiveCols, 5);
        paginatedTable('premium-active-high-table', 'premium-active-high-pagination', premiumActive.high.rows, premiumActiveCols, 5);
        document.getElementById('btn-dl-premium-active-low').addEventListener('click', () =>
          downloadExcel(premiumActive.low.rows, premiumActiveCols, 'Low Premium Active', 'low-premium-active.xlsx'));
        document.getElementById('btn-dl-premium-active-high').addEventListener('click', () =>
          downloadExcel(premiumActive.high.rows, premiumActiveCols, 'High Premium Active', 'high-premium-active.xlsx'));
      }
    }

    let sectionsLoadToken = 0;
    async function renderSections(date) {
      const token = ++sectionsLoadToken;
      const container = document.getElementById('analytics-sections');
      if (!(date in snapshotCache)) {
        container.innerHTML = '<div class="no-data">Loading ' + shortDate(date) + '&hellip;</div>';
        try {
          const r = await fetch('/api/analytics-history?date=' + date);
          snapshotCache[date] = r.ok ? scopeReportToAgent(await r.json(), AGENT_NAME) : null;
        } catch (e) {
          snapshotCache[date] = null;
        }
        if (token !== sectionsLoadToken) return; // a newer date was clicked meanwhile
      }
      const snap = snapshotCache[date];
      container.innerHTML = sectionsTemplate(date, snap);
      wireSections(snap);
    }

    function renderDateSwitch() {
      const el = document.getElementById('analytics-date-switch');
      el.innerHTML = dates.map(d =>
        '<button data-date="' + d + '" class="' + (d === selectedDate ? 'active' : '') + '">' + shortDate(d) + '</button>'
      ).join('');
      el.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          selectedDate = btn.dataset.date;
          renderDateSwitch();
          renderCharts();
          renderSections(selectedDate);
        });
      });
    }

    let regionChart = null, vipChart = null;
    function renderCharts() {
      const scope = rv[selectedDate] || { top_regions: [], vip_breakdown: [] };

      if (regionChart) regionChart.destroy();
      regionChart = new Chart(document.getElementById('region-chart'), {
        type: 'bar',
        data: {
          labels: scope.top_regions.map(r => r.region + ' (' + fmt(r.user_count) + ' users)'),
          datasets: [{ label: 'Total Deposit', data: scope.top_regions.map(r => r.total_deposit), backgroundColor: '#3b82f6', borderRadius: 6 }],
        },
        options: {
          indexAxis: 'y',
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => {
              const r = scope.top_regions[ctx.dataIndex];
              return money(ctx.parsed.x) + ' · ' + fmt(r.user_count) + ' users · ' + fmt(r.count) + ' orders';
            } } },
          },
          scales: { x: { beginAtZero: true, ticks: { callback: v => money(v) } } },
        },
      });

      if (vipChart) vipChart.destroy();
      vipChart = new Chart(document.getElementById('vip-chart'), {
        type: 'bar',
        data: {
          labels: scope.vip_breakdown.map(r => 'VIP ' + r.vip_level + ' (' + fmt(r.user_count) + ' users)'),
          datasets: [{ label: 'Total Deposit', data: scope.vip_breakdown.map(r => r.total_deposit), backgroundColor: '#8b5cf6', borderRadius: 6 }],
        },
        options: {
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => {
              const r = scope.vip_breakdown[ctx.dataIndex];
              return money(ctx.parsed.y) + ' · ' + fmt(r.user_count) + ' users · ' + fmt(r.count) + ' orders';
            } } },
          },
          scales: { y: { beginAtZero: true, ticks: { callback: v => money(v) } } },
        },
      });
    }

    renderDateSwitch();
    renderCharts();
    wireSections(snapshotCache[selectedDate]);

    // Every date besides "today" (seeded above from the main report) is a
    // separate on-demand R2 fetch -- previously that happened lazily on
    // first click, so switching to an older date always paid a fresh
    // network round-trip and felt slow. Warm the cache for the rest of the
    // visible date range in the background so by the time the user clicks,
    // it's already there.
    dates.filter(d => d !== selectedDate).forEach(d => {
      if (d in snapshotCache) return;
      fetch('/api/analytics-history?date=' + d)
        .then(r => r.ok ? r.json() : null)
        .then(json => { snapshotCache[d] = json ? scopeReportToAgent(json, AGENT_NAME) : null; })
        .catch(() => { snapshotCache[d] = null; });
    });
  })();
}

if (IS_PLATFORM_ANALYSIS) {
  (async () => {
    // No extra password prompt here -- the server already gates this page
    // to admin sessions only (session auth + /platform-analysis is never
    // reachable from an agent session, which always gets redirected to its
    // own /agent/<name> page regardless of URL). This client-side prompt
    // was a redundant second gate on top of that.
    // Fetched in parallel: /data.json (shared fields also used by other
    // pages) and /api/platform-analysis.json (the heavier fields exclusive
    // to this page -- games/bonus/roller/region-vip/weekly-performance --
    // split into their own file so every OTHER page doesn't have to
    // download them too; see build_deposit_report.py's
    // platform_analysis_extra). Merged into one "data" object so every
    // reference below is unchanged either way.
    const [res, paRes] = await Promise.all([fetch('/data.json'), fetch('/api/platform-analysis.json')]);
    if (!res.ok) {
      document.getElementById('platform-analysis-app').textContent = 'Failed to load report data (' + res.status + ')';
      return;
    }
    const data = await res.json();
    if (paRes.ok) {
      Object.assign(data, await paRes.json());
    }
    document.getElementById('updated-badge').innerHTML =
      '<span class="dot"></span> Records updated through ' +
      (data.latest_record_time ? new Date(data.latest_record_time).toLocaleString() : 'n/a');
    document.getElementById('platform-analysis-app').className = '';

    const profitUsers = data.profit_users;
    const netRevRegionVip = data.region_vip_analytics || {};
    const netRevDates = Object.keys(netRevRegionVip).sort();
    const netRevLatest = netRevDates.length ? netRevRegionVip[netRevDates[netRevDates.length - 1]] : null;
    const acqChannel = data.channel_performance;
    const suspiciousWithdraw = data.suspicious_withdraw_users;
    const bonusClaimsRangeSources = {
      day: data.bonus_claims_by_date || {},
      week: data.bonus_claims_by_week || {},
      month: data.bonus_claims_by_month || {},
    };
    // Day pills only show the most recent 10 -- Week/Month cover further
    // back automatically via their own rolling window, without needing to
    // pick an older day first.
    const bonusDatesAll = Object.keys(bonusClaimsRangeSources.day).sort();
    const bonusDates = bonusDatesAll.slice(-10);
    let bonusRange = 'day';
    let selectedBonusDate = data.report_today && bonusClaimsRangeSources.day[data.report_today] ? data.report_today : bonusDatesAll[bonusDatesAll.length - 1];
    let bonusClaims = bonusClaimsRangeSources[bonusRange][selectedBonusDate] || data.bonus_claims;
    const newOldAnalysis = data.new_old_user_analysis || { daily: [], retention: [] };

    document.getElementById('platform-analysis-app').innerHTML = \`
      <div class="analysis-heading deposit"><h2>Weekly Performance</h2><div class="line"></div><span class="today-tag" id="weekly-perf-range-tag">&mdash;</span><span class="tag">PLATFORM</span></div>
      <section class="acc-blue" id="weekly-perf-section">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-blue">&#128200;</div><h2>This Week vs Last Week</h2></div>
          <button class="download-btn-sm" id="btn-dl-weekly-perf">&#128190; Excel</button>
        </div>
        <div class="ac-note">Current calendar week (Monday-Sunday, however many days have elapsed) vs the most recent FULLY COMPLETE prior week -- same daily data as New vs Old User Analysis below, just compared week-on-week. Read the current week as "pace so far," not a final result until Sunday.</div>
        <div class="stat-row" id="weekly-perf-stats"></div>
        <div class="date-switch" id="weekly-perf-view-switch" style="margin-top:18px">
          <button data-view="wow" class="active">Week-on-Week</button>
          <button data-view="daywise">Day-wise</button>
        </div>
        <div id="weekly-perf-table"></div>
        <div id="weekly-perf-daywise" style="display:none"></div>
        <div id="weekly-perf-retention" style="margin-top:22px"></div>
        <div id="weekly-perf-target" style="margin-top:22px"></div>
      </section>

      <div class="analysis-heading withdrawal"><h2>Bonus Claim Report</h2><div class="line"></div><span class="tag">PLATFORM</span></div>
      <section class="acc-purple">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-purple">&#127942;</div><h2>Bonus Claim Report</h2></div>
          <button class="download-btn-sm" id="btn-dl-bonus-claims">&#128190; Excel</button>
        </div>
        <div class="ac-note">All bonuses claimed in the selected date range, and % who deposited afterward. Cost Ratio % = this bonus's total cost &divide; the deposit amount its own converters brought back -- lower is more efficient; &mdash; means nobody converted, not "free."</div>
        <div class="date-switch" id="bonus-claims-range-switch">
          <button data-range="day" class="active">Single Day</button>
          <button data-range="week">7-Day Range</button>
          <button data-range="month">30-Day Range</button>
        </div>
        <div class="ac-note" id="bonus-range-readout" style="margin:-6px 0 10px"></div>
        <div class="date-switch" id="bonus-claims-date-switch"></div>
        <div class="date-switch" id="bonus-claims-switch">
          <button data-view="wallet" class="active">Wallet Bonuses</button>
          <button data-view="dcb">Deposit Challenge Bonus</button>
        </div>
        <div id="bonus-claims-table"></div>
      </section>

      <div class="analysis-heading withdrawal"><h2>Acquisition &amp; Bonus Economics</h2><div class="line"></div><span class="tag">PLATFORM</span></div>
      <div class="row2col">
        <section class="acc-blue">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-blue">&#128202;</div><h2>Channel performance &mdash; 4-day combined</h2></div>
            <button class="download-btn-sm" id="btn-dl-acq-channel">&#128190; Excel</button>
          </div>
          <div id="acq-channel-table"></div>
          <div class="ac-pagination" id="acq-channel-pagination"></div>
        </section>
        <section class="acc-emerald">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-emerald">&#128176;</div><h2>Net Revenue by Region &amp; VIP</h2></div>
            <button class="download-btn-sm" id="btn-dl-net-revenue">&#128190; Excel</button>
          </div>
          <div class="ac-note">Deposit minus withdrawal, not just gross deposit volume -- a region/tier can look like a top performer by deposit total while actually net-negative once withdrawals are subtracted. Most recent date in the report.</div>
          <div class="date-switch" id="net-rev-switch">
            <button data-view="region" class="active">By Region</button>
            <button data-view="vip">By VIP Level</button>
          </div>
          <div id="net-rev-table"></div>
        </section>
      </div>

      <div class="analysis-heading withdrawal"><h2>Game Activity</h2><div class="line"></div><span class="tag">PLATFORM</span></div>
      <div class="date-switch" id="new-games-range-switch">
        <button data-range="overall" class="active">Last 15 Days</button>
        <button data-range="day">Day</button>
        <button data-range="week">Week</button>
        <button data-range="month">Month</button>
      </div>
      <select class="range-date-select" id="new-games-date-select" style="display:none;margin-bottom:18px"></select>
      <div class="row2col">
        <section class="acc-blue">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-blue">&#127918;</div><h2>Top Games - New Users</h2><span class="today-tag" id="top-games-new-count">&mdash;</span></div>
            <button class="download-btn-sm" id="btn-dl-top-games-new">&#128190; Excel</button>
          </div>
          <div class="ac-note">New = users whose first-ever deposit landed within the last 33 days. Bet-only (excludes win payouts), total wagered per user per game, highest first.</div>
          <div id="top-games-new-table"></div>
          <div class="ac-pagination" id="top-games-new-pagination"></div>
        </section>
        <section class="acc-orange">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-orange">&#128176;</div><h2>Highest Single Bet - New Users</h2><span class="today-tag" id="highest-bet-new-count">&mdash;</span></div>
            <button class="download-btn-sm" id="btn-dl-highest-bet-new">&#128190; Excel</button>
          </div>
          <div class="ac-note">New = users whose first-ever deposit landed within the last 33 days. Each user's single largest bet transaction and which game it was on.</div>
          <div id="highest-bet-new-table"></div>
          <div class="ac-pagination" id="highest-bet-new-pagination"></div>
        </section>
      </div>

      <div class="row2col">
        <section class="acc-emerald">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-emerald">&#128142;</div><h2>High Roller Active</h2><span class="today-tag" id="high-roller-count">&mdash;</span></div>
            <button class="download-btn-sm" id="btn-dl-high-roller">&#128190; Excel</button>
          </div>
          <div class="ac-note">VIP 7+, avg lifetime deposit &#8377;5,000+, 500+ lifetime deposits, &#8377;5,00,000+ lifetime total deposit, avg bet size (last 15 days) over &#8377;500, active within 15 days.</div>
          <div id="high-roller-table"></div>
          <div class="ac-pagination" id="high-roller-pagination"></div>
        </section>
        <section class="acc-rose">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-rose">&#127183;</div><h2>Low Roller Active</h2><span class="today-tag" id="low-roller-count">&mdash;</span></div>
            <button class="download-btn-sm" id="btn-dl-low-roller">&#128190; Excel</button>
          </div>
          <div class="ac-note">VIP 2-6, avg lifetime deposit under &#8377;5,000, under 500 lifetime deposits, under &#8377;5,00,000 lifetime total deposit, avg bet size (last 15 days) under &#8377;500, active within 10 days.</div>
          <div id="low-roller-table"></div>
          <div class="ac-pagination" id="low-roller-pagination"></div>
        </section>
      </div>

      <div class="analysis-heading deposit"><h2>Game &amp; Revenue Economics</h2><div class="line"></div><span class="tag">PLATFORM</span></div>
      <div class="row2col">
        <section class="acc-orange">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-orange">&#128181;</div><h2>Profit Users of the Day</h2></div>
            <div style="display:flex;gap:8px">
              <button class="download-btn-sm" id="btn-profit-new-users" style="background:#f59e0b">&#127881; 3 Days New User</button>
              <button class="download-btn-sm" id="btn-dl-profit-users">&#128190; Excel</button>
            </div>
          </div>
          <div class="ac-note">Top users by CURRENT wallet balance -- who's sitting on the most money right now. Last Dep/WD show "Today" or how many days ago, tracked permanently so it stays accurate even beyond the 33-day window.</div>
          <div id="profit-users-table"></div>
          <div class="ac-pagination" id="profit-users-pagination"></div>
        </section>
        <section class="acc-rose">
          <div class="section-head">
            <div class="sec-title"><div class="badge b-rose">&#128680;</div><h2>Suspicious Withdraw Users</h2></div>
            <button class="download-btn-sm" id="btn-dl-suspicious-withdraw">&#128190; Excel</button>
          </div>
          <div class="ac-note">Deposited &#8377;1,000+ AND requested a withdrawal (In-Review/Processing/Complete) within the last 3 days, while playing fewer than 50 games in that same window -- deposit-and-cash-out without genuine play.</div>
          <div id="suspicious-withdraw-table"></div>
          <div class="ac-pagination" id="suspicious-withdraw-pagination"></div>
        </section>
      </div>

      <div class="analysis-heading deposit"><h2>New vs Old User Analysis &mdash; Last 33 Days</h2><div class="line"></div><span class="tag">PLATFORM</span></div>
      <section class="acc-blue">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-blue">&#128200;</div><h2>New vs Old User Analysis &mdash; Last 33 Days</h2></div>
          <button class="download-btn-sm" id="btn-dl-new-old">&#128190; Excel</button>
        </div>
        <div class="ac-note">Old = repeat depositors that day. New = users whose first-ever deposit landed that day. Covers every day daily_records.db has (rolling 33-day retention), so it starts wherever data first became available.</div>
        <div class="date-switch" id="new-old-switch">
          <button data-view="daily" class="active">Daily Breakdown</button>
          <button data-view="retention">New User 3-Day Retention</button>
        </div>
        <div id="new-old-table"></div>
        <div class="ac-pagination" id="new-old-pagination"></div>
      </section>

      <div class="analysis-heading deposit"><h2>Region vs VIP Depositor Matrix</h2><div class="line"></div><span class="tag">PLATFORM</span></div>
      <section class="acc-emerald">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-emerald">&#128506;&#65039;</div><h2>Region vs VIP Depositor Matrix</h2></div>
          <button class="download-btn-sm" id="btn-dl-region-vip-matrix">&#128190; Excel</button>
        </div>
        <div class="ac-note">Rows = Region, columns = VIP level, each cell = how many DISTINCT users in that Region+VIP combination made at least one COMPLETE deposit within the selected range. A user active on multiple selected days is counted once, not once per day.</div>
        <div class="date-switch" id="region-vip-range-switch">
          <button data-range="day" class="active">Day</button>
          <button data-range="multi">Multi-select Dates</button>
          <button data-range="week">Week (Mon-Sun)</button>
          <button data-range="month">Month</button>
        </div>
        <select class="range-date-select" id="region-vip-date-select"></select>
        <select class="range-date-select" id="region-vip-date-multiselect" multiple size="6" style="display:none"></select>
        <select class="range-date-select" id="region-vip-week-select" style="display:none"></select>
        <select class="range-date-select" id="region-vip-month-select" style="display:none"></select>
        <div id="region-vip-matrix-table" style="overflow-x:auto;margin-top:16px"></div>
      </section>
    \`;

    // --- Profit Users of the Day ---
    function coloredMoney(v, positiveColor, zeroColor) {
      const color = v > 0 ? positiveColor : (v < 0 ? '#dc2626' : zeroColor);
      return '<span style="color:' + color + ';font-weight:' + (v !== 0 ? '700' : '400') + '">' + money(v) + '</span>';
    }
    function lastActivityPill(label) {
      if (!label) return '<span style="color:#9ca3af">&mdash;</span>';
      if (label === 'Today') return '<span style="background:#d1fae5;color:#065f46;padding:2px 9px;border-radius:20px;font-weight:700;font-size:12px">Today</span>';
      return '<span style="color:#6b7280">' + label + '</span>';
    }
    const profitUsersCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP', render: r => r.vip, raw: r => r.vip, num: true },
      { label: 'Dep Today', render: r => coloredMoney(r.dep_today, '#16a34a', '#9ca3af'), raw: r => r.dep_today, num: true },
      { label: 'Wallet Bal', render: r => money(r.wallet_bal), raw: r => r.wallet_bal, num: true },
      { label: 'WD Today', render: r => coloredMoney(r.wd_today, '#dc2626', '#9ca3af'), raw: r => r.wd_today, num: true },
      { label: 'Net Dep', render: r => coloredMoney(r.net_dep, '#16a34a', '#9ca3af'), raw: r => r.net_dep, num: true },
      { label: 'Last Dep', render: r => lastActivityPill(r.last_dep), raw: r => r.last_dep },
      { label: 'Last WD', render: r => lastActivityPill(r.last_wd), raw: r => r.last_wd },
    ];
    let profitUsersNewOnly = false;
    function currentProfitUsers() {
      return profitUsersNewOnly ? (profitUsers || []).filter(r => r.is_new_user_3d) : (profitUsers || []);
    }
    function renderProfitUsersTable() {
      const rows = currentProfitUsers();
      if (rows.length) {
        paginatedTable('profit-users-table', 'profit-users-pagination', rows, profitUsersCols, 10);
      } else {
        document.getElementById('profit-users-table').innerHTML = '<div class="no-data">' +
          (profitUsersNewOnly ? 'No new users (first deposit in the last 3 days) currently hold a wallet balance.' : 'No wallet balance data available.') +
          '</div>';
        document.getElementById('profit-users-pagination').innerHTML = '';
      }
    }
    if (profitUsers && profitUsers.length) {
      renderProfitUsersTable();
      document.getElementById('btn-dl-profit-users').addEventListener('click', () =>
        downloadExcel(currentProfitUsers(), profitUsersCols, 'Profit Users of the Day', 'profit-users-of-the-day.xlsx'));
      const newUserBtn = document.getElementById('btn-profit-new-users');
      newUserBtn.addEventListener('click', () => {
        profitUsersNewOnly = !profitUsersNewOnly;
        newUserBtn.style.background = profitUsersNewOnly ? '#b45309' : '#f59e0b';
        newUserBtn.innerHTML = profitUsersNewOnly ? '&#127881; Showing New Users (click to reset)' : '&#127881; 3 Days New User';
        renderProfitUsersTable();
      });
    } else {
      document.getElementById('profit-users-table').innerHTML = '<div class="no-data">No wallet balance data available.</div>';
    }

    // --- Net Revenue by Region & VIP ---
    let netRevView = 'region';
    function netRevRows() {
      if (!netRevLatest) return [];
      if (netRevView === 'region') return netRevLatest.top_regions.slice().sort((a, b) => b.net_revenue - a.net_revenue);
      return netRevLatest.vip_breakdown.slice().sort((a, b) => b.net_revenue - a.net_revenue);
    }
    function netRevCols() {
      return [
        { label: netRevView === 'region' ? 'Region' : 'VIP Level', render: r => (netRevView === 'region' ? r.region : 'VIP ' + r.vip_level), raw: r => (netRevView === 'region' ? r.region : r.vip_level) },
        { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
        { label: 'Total Withdrawal', render: r => money(r.total_withdrawal), raw: r => r.total_withdrawal, num: true },
        { label: 'Net Revenue', render: r => money(r.net_revenue), raw: r => r.net_revenue, num: true },
        { label: 'Users', render: r => fmt(r.user_count), raw: r => r.user_count, num: true },
      ];
    }
    function renderNetRev() {
      const rows = netRevRows();
      const cols = netRevCols();
      const container = document.getElementById('net-rev-table');
      if (!rows.length) {
        container.innerHTML = '<div class="no-data">No data available.</div>';
        return;
      }
      const thead = '<thead><tr>' + cols.map(c => '<th' + (c.num ? ' class="num"' : '') + '>' + c.label + '</th>').join('') + '</tr></thead>';
      const tbody = '<tbody>' + rows.map(r => '<tr>' + cols.map(c => '<td class="' + (c.num ? 'num' : '') + '">' + c.render(r) + '</td>').join('') + '</tr>').join('') + '</tbody>';
      container.innerHTML = '<div class="table-wrap"><table>' + thead + tbody + '</table></div>';
    }
    document.querySelectorAll('#net-rev-switch button').forEach(btn => {
      btn.addEventListener('click', () => {
        netRevView = btn.dataset.view;
        document.querySelectorAll('#net-rev-switch button').forEach(b => b.classList.toggle('active', b === btn));
        renderNetRev();
      });
    });
    renderNetRev();
    document.getElementById('btn-dl-net-revenue').addEventListener('click', () => {
      const userDetailCols = [
        { label: 'User ID', raw: r => r.user_id },
        { label: 'Agent', raw: r => r.agent || 'Un-Assigned' },
        { label: 'Deposit Today', raw: r => r.dep_today },
        { label: 'Wallet Balance', raw: r => r.wallet_bal },
        { label: 'Withdraw Today', raw: r => r.wd_today },
        { label: 'Net Deposit', raw: r => r.net_dep },
      ];
      (async () => {
        const wb = new ExcelJS.Workbook();
        const summaryCols = netRevCols();
        const ws1 = wb.addWorksheet('Net Revenue');
        ws1.columns = summaryCols.map(c => ({ header: c.label, key: c.label, width: 18 }));
        ws1.addRows(netRevRows().map(r => summaryCols.reduce((o, c) => { o[c.label] = c.raw(r); return o; }, {})));
        styleHeaderRow(ws1);

        const ws2 = wb.addWorksheet('User Detail');
        const userRows = profitUsers || [];
        ws2.columns = userDetailCols.map(c => ({ header: c.label, key: c.label, width: 16 }));
        ws2.addRows(userRows.map(r => userDetailCols.reduce((o, c) => { o[c.label] = c.raw(r); return o; }, {})));
        styleHeaderRow(ws2);

        await saveWorkbook(wb, 'net-revenue-' + netRevView + '.xlsx');
      })();
    });

    // --- Channel performance -- 4-day combined ---
    function pctPill(pct) {
      const bg = pct >= 25 ? '#d1fae5' : (pct >= 15 ? '#fef3c7' : '#fee2e2');
      const fg = pct >= 25 ? '#065f46' : (pct >= 15 ? '#92400e' : '#991b1b');
      return '<span style="background:' + bg + ';color:' + fg + ';padding:3px 10px;border-radius:20px;font-weight:700;font-size:12px">' + pct + '%</span>';
    }
    function qualityPill(q) {
      const styles = {
        'High value': ['#d1fae5', '#065f46'], 'Good': ['#d1fae5', '#065f46'],
        'Average': ['#fef3c7', '#92400e'], 'Weak': ['#fee2e2', '#991b1b'],
      };
      const [bg, fg] = styles[q] || ['#e5e7eb', '#374151'];
      return '<span style="background:' + bg + ';color:' + fg + ';padding:3px 10px;border-radius:20px;font-weight:700;font-size:12px">' + q + '</span>';
    }
    const acqChannelCols = [
      { label: 'Channel', render: r => r.channel, raw: r => r.channel },
      { label: 'FD Users', render: r => fmt(r.fd_users), raw: r => r.fd_users, num: true },
      { label: 'FD Amount', render: r => money(r.fd_amount), raw: r => r.fd_amount, num: true },
      { label: 'Avg FD', render: r => money(r.avg_fd), raw: r => r.avg_fd, num: true },
      { label: 'D2 Users', render: r => fmt(r.d2_users), raw: r => r.d2_users, num: true },
      { label: 'D2 %', render: r => pctPill(r.d2_pct), raw: r => r.d2_pct, num: true },
      { label: 'D3 Users', render: r => fmt(r.d3_users), raw: r => r.d3_users, num: true },
      { label: 'D3 %', render: r => pctPill(r.d3_pct), raw: r => r.d3_pct, num: true },
      { label: 'Quality', render: r => qualityPill(r.quality), raw: r => r.quality },
    ];
    if (acqChannel && acqChannel.length) {
      paginatedTable('acq-channel-table', 'acq-channel-pagination', acqChannel, acqChannelCols, 10);
      document.getElementById('btn-dl-acq-channel').addEventListener('click', () =>
        downloadExcel(acqChannel, acqChannelCols, 'Channel Performance', 'channel-performance-4day.xlsx'));
    } else {
      document.getElementById('acq-channel-table').innerHTML = '<div class="no-data">No channel data available for the last 4 days.</div>';
    }

    const suspiciousWithdrawCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'VIP', render: r => r.vip == null ? '—' : r.vip, raw: r => r.vip, num: true },
      { label: 'Deposit (3d)', render: r => money(r.deposit_amount), raw: r => r.deposit_amount, num: true },
      { label: 'Withdraw (3d)', render: r => money(r.withdraw_amount), raw: r => r.withdraw_amount, num: true },
      { label: 'Games Played (3d)', render: r => fmt(r.game_count), raw: r => r.game_count, num: true },
      { label: 'In Review?', render: r => r.in_review ? 'Yes' : 'No', raw: r => r.in_review ? 1 : 0 },
    ];
    if (suspiciousWithdraw && suspiciousWithdraw.length) {
      paginatedTable('suspicious-withdraw-table', 'suspicious-withdraw-pagination', suspiciousWithdraw, suspiciousWithdrawCols, 10);
      document.getElementById('btn-dl-suspicious-withdraw').addEventListener('click', () =>
        downloadExcel(suspiciousWithdraw, suspiciousWithdrawCols, 'Suspicious Withdraw Users', 'suspicious-withdraw-users.xlsx'));
    } else {
      document.getElementById('suspicious-withdraw-table').innerHTML = '<div class="no-data">No users matched this pattern in the last 3 days.</div>';
    }

    // --- Bonus Claim Report -- today only, both views share the same shape ---
    let bonusView = 'wallet';
    function bonusRows() {
      if (!bonusClaims) return [];
      return bonusView === 'wallet' ? bonusClaims.wallet_bonuses : bonusClaims.deposit_challenge_bonuses;
    }
    function bonusCols() {
      return [
        { label: bonusView === 'wallet' ? 'Bonus Category' : 'Rule', render: r => r.bonus_category, raw: r => r.bonus_category },
        { label: 'Claimed Users', render: r => fmt(r.claimed_users), raw: r => r.claimed_users, num: true },
        { label: 'Total Bonus', render: r => money(r.total_value), raw: r => r.total_value, num: true },
        { label: 'Deposited After', render: r => fmt(r.deposited_after), raw: r => r.deposited_after, num: true },
        { label: 'Deposit Amount', render: r => money(r.deposit_amount), raw: r => r.deposit_amount, num: true },
        { label: '%', render: r => r.pct_deposited + '%', raw: r => r.pct_deposited, num: true },
        { label: 'Cost Ratio %', render: r => r.bonus_cost_ratio_pct == null ? '&mdash;' : r.bonus_cost_ratio_pct + '%', raw: r => r.bonus_cost_ratio_pct, num: true },
      ];
    }
    function renderBonusClaims() {
      const rows = bonusRows();
      const cols = bonusCols();
      const container = document.getElementById('bonus-claims-table');
      if (!rows.length) {
        container.innerHTML = '<div class="no-data">No bonus claims recorded yet.</div>';
        return;
      }
      const thead = '<thead><tr>' + cols.map(c => '<th' + (c.num ? ' class="num"' : '') + '>' + c.label + '</th>').join('') + '</tr></thead>';
      const tbody = '<tbody>' + rows.map(r => '<tr>' + cols.map(c => '<td class="' + (c.num ? 'num' : '') + '">' + c.render(r) + '</td>').join('') + '</tr>').join('') + '</tbody>';
      container.innerHTML = '<div class="table-wrap"><table>' + thead + tbody + '</table></div>';
    }
    // Shows the ACTUAL date range covered by the current selection -- e.g.
    // "12 Jul - 18 Jul (7 days)" -- instead of leaving "7-Day Range" as an
    // abstract label the admin has to mentally translate. Computed from
    // bonusDatesAll (the real available data dates), walking back by index
    // rather than raw calendar subtraction, so it stays correct even if a
    // day is ever missing from the retention window.
    function updateBonusRangeReadout() {
      const readoutEl = document.getElementById('bonus-range-readout');
      if (!readoutEl) return;
      const windowSize = bonusRange === 'day' ? 1 : bonusRange === 'week' ? 7 : 30;
      const endIdx = bonusDatesAll.indexOf(selectedBonusDate);
      const startIdx = endIdx >= 0 ? Math.max(0, endIdx - (windowSize - 1)) : 0;
      const fromDate = bonusDatesAll[startIdx] || selectedBonusDate;
      const dayCount = endIdx >= 0 ? (endIdx - startIdx + 1) : 1;
      readoutEl.textContent = fromDate === selectedBonusDate
        ? 'Showing: ' + shortDate(selectedBonusDate)
        : 'Showing: ' + shortDate(fromDate) + ' \\u2013 ' + shortDate(selectedBonusDate) + ' (' + dayCount + ' days)';
    }
    function renderBonusDateSwitch() {
      const el = document.getElementById('bonus-claims-date-switch');
      el.innerHTML = bonusDates.map(d =>
        '<button data-date="' + d + '" class="' + (d === selectedBonusDate ? 'active' : '') + '">' + shortDate(d) + '</button>'
      ).join('');
      el.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          selectedBonusDate = btn.dataset.date;
          bonusClaims = bonusClaimsRangeSources[bonusRange][selectedBonusDate] || { wallet_bonuses: [], deposit_challenge_bonuses: [] };
          renderBonusDateSwitch();
          updateBonusRangeReadout();
          renderBonusClaims();
        });
      });
    }
    if (bonusDates.length) {
      renderBonusDateSwitch();
      updateBonusRangeReadout();
      document.querySelectorAll('#bonus-claims-switch button').forEach(btn => {
        btn.addEventListener('click', () => {
          bonusView = btn.dataset.view;
          document.querySelectorAll('#bonus-claims-switch button').forEach(b => b.classList.toggle('active', b === btn));
          renderBonusClaims();
        });
      });
      document.querySelectorAll('#bonus-claims-range-switch button').forEach(btn => {
        btn.addEventListener('click', () => {
          bonusRange = btn.dataset.range;
          document.querySelectorAll('#bonus-claims-range-switch button').forEach(b => b.classList.toggle('active', b === btn));
          bonusClaims = bonusClaimsRangeSources[bonusRange][selectedBonusDate] || { wallet_bonuses: [], deposit_challenge_bonuses: [] };
          updateBonusRangeReadout();
          renderBonusClaims();
        });
      });
      renderBonusClaims();
      document.getElementById('btn-dl-bonus-claims').addEventListener('click', async () => {
        const cols = bonusCols();
        const summaryRows = bonusRows().map(r => {
          const obj = {};
          cols.forEach(c => { obj[c.label] = c.raw ? c.raw(r) : c.render(r); });
          return obj;
        });
        const detailRaw = bonusView === 'wallet'
          ? (bonusClaims.wallet_claim_details || [])
          : (bonusClaims.deposit_challenge_bonus_claim_details || []);
        const detailRows = bonusView === 'wallet'
          ? detailRaw.map(d => ({
              'User ID': d.user_id, Agent: d.agent || 'Un-Assigned', 'Bonus Category': d.bonus_category,
              'Bonus Amount': d.bonus_amount, 'Claimed Time': d.claimed_time,
              'Deposited After': d.deposited_after, 'Deposit Amount': d.deposit_amount,
            }))
          : detailRaw.map(d => ({
              'User ID': d.user_id, Agent: d.agent || 'Un-Assigned', Rule: d.rule,
              'Bonus Amount': d.bonus_amount, 'FD Date': d.fd_date,
            }));

        const wb = new ExcelJS.Workbook();
        const wsSummary = wb.addWorksheet('Summary');
        if (summaryRows.length) {
          wsSummary.columns = Object.keys(summaryRows[0]).map(k => ({ header: k, key: k, width: Math.max(12, k.length + 2) }));
          wsSummary.addRows(summaryRows);
        }
        styleHeaderRow(wsSummary);
        const wsUsers = wb.addWorksheet('User Data');
        if (detailRows.length) {
          wsUsers.columns = Object.keys(detailRows[0]).map(k => ({ header: k, key: k, width: Math.max(12, k.length + 2) }));
          wsUsers.addRows(detailRows);
        } else if (bonusRange !== 'day') {
          wsUsers.columns = [{ header: 'Note', key: 'note', width: 90 }];
          wsUsers.addRow({ note: 'Per-user detail is only available for the Day view -- switch to Day to export individual claim rows. Week/Month only ship the category summary (see the Summary sheet) to keep the report file a manageable size.' });
        }
        styleHeaderRow(wsUsers);
        await saveWorkbook(wb, 'bonus-claims-' + bonusView + '-' + bonusRange + '-' + selectedBonusDate + '.xlsx');
      });
    } else {
      document.getElementById('bonus-claims-table').innerHTML = '<div class="no-data">No bonus claims recorded yet.</div>';
    }

    // --- New vs Old User Analysis -- rolling window, whatever daily_records.db retains (up to 33 days) ---
    let newOldView = 'daily';
    function pctOrDash(v) { return v === null || v === undefined ? '&mdash;' : v + '%'; }
    const newOldDailyCols = [
      { label: 'Date', render: r => shortDate(r.date), raw: r => r.date },
      { label: 'Old Users', render: r => fmt(r.old_users_count), raw: r => r.old_users_count, num: true },
      { label: 'Avg Dep (Old)', render: r => money(r.old_users_avg_deposit), raw: r => r.old_users_avg_deposit, num: true },
      { label: 'New Users', render: r => fmt(r.new_users_count), raw: r => r.new_users_count, num: true },
      { label: 'Avg Dep (New)', render: r => money(r.new_users_avg_deposit), raw: r => r.new_users_avg_deposit, num: true },
      { label: 'Old WD Users', render: r => fmt(r.old_users_withdraw_count), raw: r => r.old_users_withdraw_count, num: true },
      { label: 'Avg WD (Old)', render: r => money(r.old_users_avg_withdraw), raw: r => r.old_users_avg_withdraw, num: true },
      { label: 'New WD Users', render: r => fmt(r.new_users_withdraw_count), raw: r => r.new_users_withdraw_count, num: true },
      { label: 'Avg WD (New)', render: r => money(r.new_users_avg_withdraw), raw: r => r.new_users_avg_withdraw, num: true },
      { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Total Depositors', render: r => fmt(r.total_depositor_count), raw: r => r.total_depositor_count, num: true },
    ];
    const newOldRetentionCols = [
      { label: 'Date', render: r => shortDate(r.date), raw: r => r.date },
      { label: 'New Users', render: r => fmt(r.new_users), raw: r => r.new_users, num: true },
      { label: 'Withdrew - Count', render: r => fmt(r.withdrew_group_count), raw: r => r.withdrew_group_count, num: true },
      { label: 'Withdrew - Returned', render: r => fmt(r.withdrew_group_returned), raw: r => r.withdrew_group_returned, num: true },
      { label: 'Withdrew - Retention %', render: r => pctOrDash(r.withdrew_group_retention_pct), raw: r => r.withdrew_group_retention_pct, num: true },
      { label: 'Never Withdrew - Count', render: r => fmt(r.never_withdrew_group_count), raw: r => r.never_withdrew_group_count, num: true },
      { label: 'Never Withdrew - Returned', render: r => fmt(r.never_withdrew_group_returned), raw: r => r.never_withdrew_group_returned, num: true },
      { label: 'Never Withdrew - Retention %', render: r => pctOrDash(r.never_withdrew_group_retention_pct), raw: r => r.never_withdrew_group_retention_pct, num: true },
    ];
    function newOldRows() { return newOldView === 'daily' ? newOldAnalysis.daily : newOldAnalysis.retention; }
    function newOldCols() { return newOldView === 'daily' ? newOldDailyCols : newOldRetentionCols; }
    function renderNewOld() {
      const rows = newOldRows().slice().sort((a, b) => b.date.localeCompare(a.date));
      const cols = newOldCols();
      if (!rows.length) {
        document.getElementById('new-old-table').innerHTML = '<div class="no-data">No data available yet.</div>';
        document.getElementById('new-old-pagination').innerHTML = '';
        return;
      }
      paginatedTable('new-old-table', 'new-old-pagination', rows, cols, 10);
    }
    if ((newOldAnalysis.daily && newOldAnalysis.daily.length) || (newOldAnalysis.retention && newOldAnalysis.retention.length)) {
      renderNewOld();
      document.querySelectorAll('#new-old-switch button').forEach(btn => {
        btn.addEventListener('click', () => {
          newOldView = btn.dataset.view;
          document.querySelectorAll('#new-old-switch button').forEach(b => b.classList.toggle('active', b === btn));
          renderNewOld();
        });
      });
      document.getElementById('btn-dl-new-old').addEventListener('click', () =>
        downloadExcel(newOldRows(), newOldCols(), newOldView === 'daily' ? 'New vs Old Daily' : 'New User Retention', 'new-old-user-analysis-' + newOldView + '.xlsx'));
    } else {
      document.getElementById('new-old-table').innerHTML = '<div class="no-data">No data available yet.</div>';
    }

    // --- Weekly Performance: this week (so far) vs last complete week ---
    const weeklyPerf = data.weekly_performance;
    function pctDeltaHtml(pct) {
      if (pct == null) return '<span class="st-delta flat">&mdash;</span>';
      const cls = pct > 0 ? 'up' : (pct < 0 ? 'down' : 'flat');
      const arrow = pct > 0 ? '&#9650;' : (pct < 0 ? '&#9660;' : '');
      return '<span class="st-delta ' + cls + '">' + arrow + ' ' + Math.abs(pct).toFixed(2) + '%</span>';
    }
    const WEEKLY_PERF_MONEY_KEYS = new Set([
      'old_users_avg_deposit', 'new_users_avg_deposit', 'old_users_avg_withdraw', 'new_users_avg_withdraw', 'total_deposit',
    ]);
    function weeklyPerfMetricValue(v, key) {
      return WEEKLY_PERF_MONEY_KEYS.has(key) ? money(v) : fmt(Math.round(v * 100) / 100);
    }
    if (weeklyPerf) {
      document.getElementById('weekly-perf-range-tag').textContent =
        shortDate(weeklyPerf.prior_week_start) + '-' + shortDate(weeklyPerf.prior_week_end) + ' vs ' +
        shortDate(weeklyPerf.current_week_start) + '-' + shortDate(weeklyPerf.current_week_end) + ' (' + weeklyPerf.current_week_days + 'd so far)';

      const headline = ['old_users_count', 'new_users_count', 'total_deposit', 'total_depositor_count'];
      const byKey = {};
      weeklyPerf.comparison.forEach(r => { byKey[r.key] = r; });
      document.getElementById('weekly-perf-stats').innerHTML = headline.map(k => {
        const r = byKey[k];
        return '<div class="stat-tile"><div class="st-label">' + r.metric + '</div>' +
          '<div class="st-value">' + weeklyPerfMetricValue(r.current, k) + '</div>' +
          pctDeltaHtml(r.pct_change) + '</div>';
      }).join('');

      let tableHtml = '<div class="table-wrap"><table><thead><tr><th>Metric</th><th class="num">Last Week (7d avg)</th>' +
        '<th class="num">This Week (' + weeklyPerf.current_week_days + 'd avg)</th><th class="num">Change</th><th class="num">% Change</th></tr></thead><tbody>';
      weeklyPerf.comparison.forEach(r => {
        const deltaCls = r.pct_change > 0 ? 'up' : (r.pct_change < 0 ? 'down' : 'flat');
        tableHtml += '<tr><td>' + r.metric + '</td>' +
          '<td class="num">' + weeklyPerfMetricValue(r.prior, r.key) + '</td>' +
          '<td class="num">' + weeklyPerfMetricValue(r.current, r.key) + '</td>' +
          '<td class="num"><span class="st-delta ' + deltaCls + '">' + (r.change > 0 ? '+' : '') + weeklyPerfMetricValue(r.change, r.key) + '</span></td>' +
          '<td class="num">' + pctDeltaHtml(r.pct_change) + '</td></tr>';
      });
      tableHtml += '</tbody></table></div>';
      document.getElementById('weekly-perf-table').innerHTML = tableHtml;

      // Day-wise tab: every individual day from both weeks (prior week's
      // full 7 + however many of the current week have completed), same
      // rows New vs Old User Analysis already has -- just filtered to
      // these two week ranges and labeled which week each belongs to.
      const dwInRange = (dateStr, start, end) => dateStr >= start && dateStr <= end;
      const dayWiseRows = (newOldAnalysis.daily || [])
        .filter(r => dwInRange(r.date, weeklyPerf.prior_week_start, weeklyPerf.prior_week_end) || dwInRange(r.date, weeklyPerf.current_week_start, weeklyPerf.current_week_end))
        .map(r => Object.assign({ week: dwInRange(r.date, weeklyPerf.prior_week_start, weeklyPerf.prior_week_end) ? 'Last Week' : 'This Week' }, r))
        .sort((a, b) => a.date.localeCompare(b.date));
      const dayWiseCols = [
        { label: 'Week', render: r => r.week, raw: r => r.week },
        { label: 'Date', render: r => shortDate(r.date), raw: r => r.date },
        { label: 'Old Users Count', render: r => fmt(r.old_users_count), raw: r => r.old_users_count, num: true },
        { label: 'Avg Deposit of Old Users', render: r => money(r.old_users_avg_deposit), raw: r => r.old_users_avg_deposit, num: true },
        { label: 'New Users Count', render: r => fmt(r.new_users_count), raw: r => r.new_users_count, num: true },
        { label: 'Avg Deposit of New Users', render: r => money(r.new_users_avg_deposit), raw: r => r.new_users_avg_deposit, num: true },
        { label: 'Old Users (Withdrew)', render: r => fmt(r.old_users_withdraw_count), raw: r => r.old_users_withdraw_count, num: true },
        { label: 'Avg Withdraw - Old Users', render: r => money(r.old_users_avg_withdraw), raw: r => r.old_users_avg_withdraw, num: true },
        { label: 'New Users (Withdrew)', render: r => fmt(r.new_users_withdraw_count), raw: r => r.new_users_withdraw_count, num: true },
        { label: 'Avg Withdraw - New Users', render: r => money(r.new_users_avg_withdraw), raw: r => r.new_users_avg_withdraw, num: true },
        { label: 'Total Deposit (Day)', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
        { label: 'Total Depositor Count (Day)', render: r => fmt(r.total_depositor_count), raw: r => r.total_depositor_count, num: true },
      ];
      let dwHtml = '<div class="ac-note" style="margin-bottom:12px">Every retained day from both weeks -- Last Week is always the full 7 days, This Week is however many have fully completed so far.</div>';
      dwHtml += '<div class="table-wrap"><table><thead><tr>' + dayWiseCols.map(c => '<th' + (c.num ? ' class="num"' : '') + '>' + c.label + '</th>').join('') + '</tr></thead><tbody>';
      dayWiseRows.forEach(r => {
        dwHtml += '<tr>' + dayWiseCols.map(c => '<td' + (c.num ? ' class="num"' : '') + '>' + c.render(r) + '</td>').join('') + '</tr>';
      });
      dwHtml += '</tbody></table></div>';
      document.getElementById('weekly-perf-daywise').innerHTML = dwHtml;

      document.querySelectorAll('#weekly-perf-view-switch button').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('#weekly-perf-view-switch button').forEach(b => b.classList.toggle('active', b === btn));
          const showDaywise = btn.dataset.view === 'daywise';
          document.getElementById('weekly-perf-table').style.display = showDaywise ? 'none' : '';
          document.getElementById('weekly-perf-daywise').style.display = showDaywise ? '' : 'none';
        });
      });

      document.getElementById('btn-dl-weekly-perf').onclick = async () => {
        const wowCols = [
          { label: 'Metric', raw: r => r.metric },
          { label: 'Last Week (7d avg)', raw: r => r.prior },
          { label: 'This Week (' + weeklyPerf.current_week_days + 'd avg)', raw: r => r.current },
          { label: 'Change', raw: r => r.change },
          { label: '% Change', raw: r => r.pct_change },
        ];
        const wb = new ExcelJS.Workbook();
        const ws1 = wb.addWorksheet('Week-on-Week');
        ws1.columns = wowCols.map(c => ({ header: c.label, key: c.label, width: 24 }));
        ws1.addRows(weeklyPerf.comparison.map(r => wowCols.reduce((o, c) => { o[c.label] = c.raw(r); return o; }, {})));
        styleHeaderRow(ws1);
        weeklyPerf.comparison.forEach((r, i) => {
          const row = ws1.getRow(i + 2);
          styleDeltaCell(row.getCell('Change'), r.change);
          styleDeltaCell(row.getCell('% Change'), r.pct_change);
        });

        const ws2 = wb.addWorksheet('Day-wise');
        ws2.columns = dayWiseCols.map(c => ({ header: c.label, key: c.label, width: c.label === 'Date' ? 14 : 20 }));
        ws2.addRows(dayWiseRows.map(r => dayWiseCols.reduce((o, c) => { o[c.label] = c.raw(r); return o; }, {})));
        styleHeaderRow(ws2);

        const rcExport = weeklyPerf.retention_comparison;
        if (rcExport && (rcExport.prior || rcExport.current)) {
          const p = rcExport.prior || {}, c = rcExport.current || {};
          const retCols = [
            { label: 'Metric', key: 'metric' },
            { label: 'Last Week', key: 'prior' },
            { label: 'This Week', key: 'current' },
          ];
          const ws3 = wb.addWorksheet('Retention');
          ws3.columns = retCols.map(col => ({ header: col.label, key: col.key, width: 30 }));
          ws3.addRows([
            { metric: 'Cohorts Included', prior: p.cohorts_included ?? '', current: c.cohorts_included ?? '' },
            { metric: 'Avg New Users / Cohort', prior: p.new_users_avg ?? '', current: c.new_users_avg ?? '' },
            { metric: 'Withdrew, then Redeposited %', prior: p.withdrew_retention_pct ?? '', current: c.withdrew_retention_pct ?? '' },
            { metric: 'Never Withdrew, then Redeposited %', prior: p.never_withdrew_retention_pct ?? '', current: c.never_withdrew_retention_pct ?? '' },
          ]);
          styleHeaderRow(ws3);
        }

        if (weeklyPerf.target && weeklyPerf.target.length) {
          const targetCols = [
            { label: 'Metric', key: 'metric' },
            { label: 'Target', key: 'target' },
            { label: 'Actual', key: 'actual' },
            { label: 'Variance', key: 'variance' },
            { label: '% of Target', key: 'pct_of_target' },
            { label: 'Status', key: 'status' },
          ];
          const ws4 = wb.addWorksheet('Target vs Actual');
          ws4.columns = targetCols.map(c => ({ header: c.label, key: c.key, width: c.label === 'Metric' ? 30 : 16 }));
          ws4.addRows(weeklyPerf.target.map(t => ({
            metric: t.metric, target: t.target, actual: t.actual, variance: t.variance,
            pct_of_target: t.pct_of_target, status: t.status,
          })));
          styleHeaderRow(ws4);
          weeklyPerf.target.forEach((t, i) => {
            const row = ws4.getRow(i + 2);
            styleDeltaCell(row.getCell('variance'), t.variance);
            const statusCell = row.getCell('status');
            if (t.status === 'MET') { statusCell.fill = XL_GREEN_FILL; statusCell.font = XL_GREEN_FONT; }
            else { statusCell.fill = XL_AMBER_FILL; statusCell.font = XL_AMBER_FONT; }
          });
        }

        await saveWorkbook(wb, 'weekly-performance-' + weeklyPerf.current_week_start + '.xlsx');
      };

      const rc = weeklyPerf.retention_comparison;
      if (rc.prior || rc.current) {
        let retHtml = '<h3 style="font-size:14px;margin:0 0 10px">New User 3-Day Retention</h3>' +
          '<div class="ac-note" style="margin-bottom:12px">Only cohorts with a fully-elapsed 3-day window are included -- the current week may show fewer cohorts than days elapsed.</div>' +
          '<div class="table-wrap"><table><thead><tr><th>Metric</th><th class="num">Last Week</th><th class="num">This Week</th></tr></thead><tbody>';
        const p = rc.prior || {}, c = rc.current || {};
        retHtml += '<tr><td>Cohorts Included</td><td class="num">' + (p.cohorts_included ?? '&mdash;') + '</td><td class="num">' + (c.cohorts_included ?? '&mdash;') + '</td></tr>';
        retHtml += '<tr><td>Avg New Users / Cohort</td><td class="num">' + (p.new_users_avg ?? '&mdash;') + '</td><td class="num">' + (c.new_users_avg ?? '&mdash;') + '</td></tr>';
        retHtml += '<tr><td>Withdrew, then Redeposited %</td><td class="num">' + (p.withdrew_retention_pct != null ? p.withdrew_retention_pct + '%' : '&mdash;') + '</td><td class="num">' + (c.withdrew_retention_pct != null ? c.withdrew_retention_pct + '%' : '&mdash;') + '</td></tr>';
        retHtml += '<tr><td>Never Withdrew, then Redeposited %</td><td class="num">' + (p.never_withdrew_retention_pct != null ? p.never_withdrew_retention_pct + '%' : '&mdash;') + '</td><td class="num">' + (c.never_withdrew_retention_pct != null ? c.never_withdrew_retention_pct + '%' : '&mdash;') + '</td></tr>';
        retHtml += '</tbody></table></div>';
        document.getElementById('weekly-perf-retention').innerHTML = retHtml;
      }

      if (weeklyPerf.target && weeklyPerf.target.length) {
        let targetHtml = '<h3 style="font-size:14px;margin:0 0 10px">Target vs Actual -- Week of ' + shortDate(weeklyPerf.current_week_start) + '-' + shortDate(weeklyPerf.current_week_end) + '</h3>' +
          '<div class="ac-note" style="margin-bottom:12px">Actual is the ' + weeklyPerf.current_week_days + '-day average so far -- a pace read, not a final score until the week ends.</div>' +
          '<div class="table-wrap"><table><thead><tr><th>Metric</th><th class="num">Target</th><th class="num">Actual</th><th class="num">Variance</th><th class="num">% of Target</th><th>Status</th></tr></thead><tbody>';
        weeklyPerf.target.forEach(t => {
          const isMoney = WEEKLY_PERF_MONEY_KEYS.has(t.key);
          const pillCls = t.status === 'MET' ? 'su-pill-green' : 'su-pill-amber';
          targetHtml += '<tr><td>' + t.metric + '</td>' +
            '<td class="num">' + (isMoney ? money(t.target) : fmt(t.target)) + '</td>' +
            '<td class="num">' + (isMoney ? money(t.actual) : fmt(t.actual)) + '</td>' +
            '<td class="num">' + (t.variance > 0 ? '+' : '') + (isMoney ? money(t.variance) : fmt(t.variance)) + '</td>' +
            '<td class="num">' + t.pct_of_target + '%</td>' +
            '<td><span class="su-pill ' + pillCls + '">' + t.status + '</span></td></tr>';
        });
        targetHtml += '</tbody></table></div>';
        document.getElementById('weekly-perf-target').innerHTML = targetHtml;
      } else {
        document.getElementById('weekly-perf-target').innerHTML = '';
      }
    } else {
      document.getElementById('weekly-perf-section').innerHTML = '<div class="no-data">Not enough data yet -- need at least one fully complete prior week to compare against.</div>';
      document.getElementById('weekly-perf-range-tag').textContent = 'No data';
    }

    // --- Top Games / Highest Single Bet -- New Users (same "new" population as above) ---
    const newUsersGames = data.new_users_games || { overall: { top_games: [], highest_single_bet: [] }, by_date: {}, by_week: {}, by_month: {}, dates: [] };
    const gamesEmpty = { top_games: [], highest_single_bet: [] };
    const gamesDates = (newUsersGames.dates || []).slice().sort();
    let gamesRange = 'overall';
    let selectedGamesDate = gamesDates.length ? gamesDates[gamesDates.length - 1] : null;

    const topGamesCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'VIP', render: r => r.vip_level == null ? '&mdash;' : r.vip_level, raw: r => r.vip_level, num: true },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'Game Name', render: r => r.game_name, raw: r => r.game_name },
      { label: 'Total Bet Amount', render: r => money(r.total_bet_amount), raw: r => r.total_bet_amount, num: true },
      { label: 'Last Active', render: r => lastActivityPill(r.last_active), raw: r => r.last_active },
    ];
    const highestBetCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'VIP', render: r => r.vip_level == null ? '&mdash;' : r.vip_level, raw: r => r.vip_level, num: true },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'Highest Bet', render: r => money(r.highest_bet), raw: r => r.highest_bet, num: true },
      { label: 'Game Name', render: r => r.game_name, raw: r => r.game_name },
      { label: 'Last Active', render: r => lastActivityPill(r.last_active), raw: r => r.last_active },
    ];

    function currentGamesData() {
      if (gamesRange === 'overall') return newUsersGames.overall || gamesEmpty;
      if (!selectedGamesDate) return gamesEmpty;
      const source = gamesRange === 'day' ? newUsersGames.by_date : gamesRange === 'week' ? newUsersGames.by_week : newUsersGames.by_month;
      return (source && source[selectedGamesDate]) || gamesEmpty;
    }

    function renderGamesTables() {
      const gd = currentGamesData();
      const rangeLabel = gamesRange === 'overall' ? 'overall' : gamesRange + '-' + selectedGamesDate;
      document.getElementById('top-games-new-count').textContent = fmt((gd.top_games || []).length);
      document.getElementById('highest-bet-new-count').textContent = fmt((gd.highest_single_bet || []).length);
      if (gd.top_games && gd.top_games.length) {
        paginatedTable('top-games-new-table', 'top-games-new-pagination', gd.top_games, topGamesCols, 10);
        document.getElementById('btn-dl-top-games-new').onclick = () =>
          downloadExcel(gd.top_games, topGamesCols, 'Top Games - New Users', 'top-games-new-users-' + rangeLabel + '.xlsx');
      } else {
        document.getElementById('top-games-new-table').innerHTML = '<div class="no-data">No data available yet.</div>';
        document.getElementById('top-games-new-pagination').innerHTML = '';
      }
      if (gd.highest_single_bet && gd.highest_single_bet.length) {
        paginatedTable('highest-bet-new-table', 'highest-bet-new-pagination', gd.highest_single_bet, highestBetCols, 10);
        document.getElementById('btn-dl-highest-bet-new').onclick = () =>
          downloadExcel(gd.highest_single_bet, highestBetCols, 'Highest Single Bet - New Users', 'highest-single-bet-new-users-' + rangeLabel + '.xlsx');
      } else {
        document.getElementById('highest-bet-new-table').innerHTML = '<div class="no-data">No data available yet.</div>';
        document.getElementById('highest-bet-new-pagination').innerHTML = '';
      }
    }

    const gamesDateSelect = document.getElementById('new-games-date-select');
    gamesDateSelect.innerHTML = gamesDates.slice().reverse().map(d => '<option value="' + d + '">' + shortDate(d) + '</option>').join('');
    if (selectedGamesDate) gamesDateSelect.value = selectedGamesDate;
    gamesDateSelect.addEventListener('change', () => {
      selectedGamesDate = gamesDateSelect.value;
      renderGamesTables();
    });

    document.querySelectorAll('#new-games-range-switch button').forEach(btn => {
      btn.addEventListener('click', () => {
        gamesRange = btn.dataset.range;
        document.querySelectorAll('#new-games-range-switch button').forEach(b => b.classList.toggle('active', b === btn));
        gamesDateSelect.style.display = gamesRange === 'overall' ? 'none' : '';
        renderGamesTables();
      });
    });

    renderGamesTables();

    // --- High Roller Active / Low Roller Active ---
    const rollerReports = data.roller_reports || { high_roller: [], low_roller: [] };
    const rollerCols = [
      { label: 'User ID', render: r => r.user_id, raw: r => r.user_id },
      { label: 'VIP', render: r => r.vip_level == null ? '&mdash;' : r.vip_level, raw: r => r.vip_level, num: true },
      { label: 'Agent', render: r => r.agent || 'Un-Assigned', raw: r => r.agent || 'Un-Assigned' },
      { label: 'Total Deposit', render: r => money(r.total_deposit), raw: r => r.total_deposit, num: true },
      { label: 'Wallet Balance', render: r => money(r.wallet_balance), raw: r => r.wallet_balance, num: true },
      { label: 'Top Game Played', render: r => r.top_game_played || '&mdash;', raw: r => r.top_game_played || '' },
    ];
    document.getElementById('high-roller-count').textContent = fmt((rollerReports.high_roller || []).length);
    document.getElementById('low-roller-count').textContent = fmt((rollerReports.low_roller || []).length);
    if (rollerReports.high_roller && rollerReports.high_roller.length) {
      paginatedTable('high-roller-table', 'high-roller-pagination', rollerReports.high_roller, rollerCols, 10);
      document.getElementById('btn-dl-high-roller').addEventListener('click', () =>
        downloadExcel(rollerReports.high_roller, rollerCols, 'High Roller Active', 'high-roller-active.xlsx'));
    } else {
      document.getElementById('high-roller-table').innerHTML = '<div class="no-data">No users match this criteria yet.</div>';
    }
    if (rollerReports.low_roller && rollerReports.low_roller.length) {
      paginatedTable('low-roller-table', 'low-roller-pagination', rollerReports.low_roller, rollerCols, 10);
      document.getElementById('btn-dl-low-roller').addEventListener('click', () =>
        downloadExcel(rollerReports.low_roller, rollerCols, 'Low Roller Active', 'low-roller-active.xlsx'));
    } else {
      document.getElementById('low-roller-table').innerHTML = '<div class="no-data">No users match this criteria yet.</div>';
    }

    // --- Region vs VIP Depositor Matrix ---
    const rvMatrixData = data.region_vip_depositor_matrix || { dates: [], matrix_by_date: {} };
    const rvDates = (rvMatrixData.dates || []).slice().sort();

    function isoMonday(dateStr) {
      const d = new Date(dateStr + 'T00:00:00Z');
      const day = d.getUTCDay(); // 0=Sun..6=Sat
      const diffToMonday = day === 0 ? -6 : 1 - day;
      const monday = new Date(d);
      monday.setUTCDate(d.getUTCDate() + diffToMonday);
      const sunday = new Date(monday);
      sunday.setUTCDate(monday.getUTCDate() + 6);
      return { key: monday.toISOString().slice(0, 10), monday: monday.toISOString().slice(0, 10), sunday: sunday.toISOString().slice(0, 10) };
    }

    const rvWeeksMap = {};
    rvDates.forEach(d => {
      const { key, monday, sunday } = isoMonday(d);
      if (!rvWeeksMap[key]) rvWeeksMap[key] = { monday, sunday, dates: [] };
      rvWeeksMap[key].dates.push(d);
    });
    const rvWeekKeys = Object.keys(rvWeeksMap).sort();

    const rvMonthsMap = {};
    rvDates.forEach(d => {
      const key = d.slice(0, 7);
      if (!rvMonthsMap[key]) rvMonthsMap[key] = [];
      rvMonthsMap[key].push(d);
    });
    const rvMonthKeys = Object.keys(rvMonthsMap).sort();
    function monthLabel(key) {
      const [y, m] = key.split('-');
      return new Date(Date.UTC(Number(y), Number(m) - 1, 1)).toLocaleString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });
    }

    let rvRange = 'day';
    let rvSelectedDate = rvDates.length ? rvDates[rvDates.length - 1] : null;
    let rvSelectedMultiDates = [];
    let rvSelectedWeekKey = rvWeekKeys.length ? rvWeekKeys[rvWeekKeys.length - 1] : null;
    let rvSelectedMonthKey = rvMonthKeys.length ? rvMonthKeys[rvMonthKeys.length - 1] : null;

    const rvDateSelect = document.getElementById('region-vip-date-select');
    rvDateSelect.innerHTML = rvDates.slice().reverse().map(d => '<option value="' + d + '">' + shortDate(d) + '</option>').join('');
    if (rvSelectedDate) rvDateSelect.value = rvSelectedDate;

    const rvMultiSelect = document.getElementById('region-vip-date-multiselect');
    rvMultiSelect.innerHTML = rvDates.slice().reverse().map(d => '<option value="' + d + '">' + shortDate(d) + '</option>').join('');

    const rvWeekSelect = document.getElementById('region-vip-week-select');
    rvWeekSelect.innerHTML = rvWeekKeys.slice().reverse().map(k =>
      '<option value="' + k + '">' + shortDate(rvWeeksMap[k].monday) + ' - ' + shortDate(rvWeeksMap[k].sunday) + '</option>').join('');
    if (rvSelectedWeekKey) rvWeekSelect.value = rvSelectedWeekKey;

    const rvMonthSelect = document.getElementById('region-vip-month-select');
    rvMonthSelect.innerHTML = rvMonthKeys.slice().reverse().map(k => '<option value="' + k + '">' + monthLabel(k) + '</option>').join('');
    if (rvSelectedMonthKey) rvMonthSelect.value = rvSelectedMonthKey;

    function rvCurrentDates() {
      if (rvRange === 'day') return rvSelectedDate ? [rvSelectedDate] : [];
      if (rvRange === 'multi') return rvSelectedMultiDates;
      if (rvRange === 'week') return rvSelectedWeekKey ? rvWeeksMap[rvSelectedWeekKey].dates : [];
      if (rvRange === 'month') return rvSelectedMonthKey ? rvMonthsMap[rvSelectedMonthKey] : [];
      return [];
    }

    function rvCombine(dateList) {
      const combined = {}; // region -> vip -> Set(user_id)
      dateList.forEach(d => {
        const dayMatrix = rvMatrixData.matrix_by_date[d];
        if (!dayMatrix) return;
        Object.keys(dayMatrix).forEach(region => {
          if (!combined[region]) combined[region] = {};
          Object.keys(dayMatrix[region]).forEach(vip => {
            if (!combined[region][vip]) combined[region][vip] = new Set();
            dayMatrix[region][vip].forEach(uid => combined[region][vip].add(uid));
          });
        });
      });
      return combined;
    }

    function renderRegionVipMatrix() {
      const combined = rvCombine(rvCurrentDates());
      const regions = Object.keys(combined);
      const vipSet = new Set();
      regions.forEach(r => Object.keys(combined[r]).forEach(v => vipSet.add(v)));
      const vips = Array.from(vipSet).sort((a, b) => Number(a) - Number(b));
      const container = document.getElementById('region-vip-matrix-table');

      if (!regions.length || !vips.length) {
        container.innerHTML = '<div class="no-data">No data available for this selection.</div>';
        document.getElementById('btn-dl-region-vip-matrix').onclick = null;
        return;
      }

      const regionRows = regions.map(region => {
        const total = vips.reduce((s, v) => s + (combined[region][v] ? combined[region][v].size : 0), 0);
        return { region, total };
      }).sort((a, b) => b.total - a.total);

      const grandTotals = vips.map(v => regions.reduce((s, r) => s + (combined[r][v] ? combined[r][v].size : 0), 0));
      const grandTotal = grandTotals.reduce((s, v) => s + v, 0);

      let html = '<div class="table-wrap"><table><thead><tr><th>Region</th>' +
        vips.map(v => '<th class="num">VIP ' + v + '</th>').join('') + '<th class="num">Total</th></tr></thead><tbody>';
      regionRows.forEach(({ region, total }) => {
        html += '<tr><td>' + region + '</td>' +
          vips.map(v => '<td class="num">' + fmt(combined[region][v] ? combined[region][v].size : 0) + '</td>').join('') +
          '<td class="num"><strong>' + fmt(total) + '</strong></td></tr>';
      });
      html += '<tr style="font-weight:700;background:#f9fafb"><td>Total</td>' +
        grandTotals.map(v => '<td class="num">' + fmt(v) + '</td>').join('') + '<td class="num">' + fmt(grandTotal) + '</td></tr>';
      html += '</tbody></table></div>';
      container.innerHTML = html;

      document.getElementById('btn-dl-region-vip-matrix').onclick = () => {
        const rows = regionRows.map(({ region, total }) => {
          const row = { region };
          vips.forEach(v => { row['VIP ' + v] = combined[region][v] ? combined[region][v].size : 0; });
          row.total = total;
          return row;
        });
        const cols = [
          { label: 'Region', render: r => r.region, raw: r => r.region },
          ...vips.map(v => ({ label: 'VIP ' + v, render: r => fmt(r['VIP ' + v]), raw: r => r['VIP ' + v], num: true })),
          { label: 'Total', render: r => fmt(r.total), raw: r => r.total, num: true },
        ];
        downloadExcel(rows, cols, 'Region vs VIP Depositor Matrix', 'region-vip-depositor-matrix-' + rvRange + '.xlsx');
      };
    }

    function rvSetControlVisibility() {
      document.getElementById('region-vip-date-select').style.display = rvRange === 'day' ? '' : 'none';
      document.getElementById('region-vip-date-multiselect').style.display = rvRange === 'multi' ? '' : 'none';
      document.getElementById('region-vip-week-select').style.display = rvRange === 'week' ? '' : 'none';
      document.getElementById('region-vip-month-select').style.display = rvRange === 'month' ? '' : 'none';
    }
    rvSetControlVisibility();

    document.querySelectorAll('#region-vip-range-switch button').forEach(btn => {
      btn.addEventListener('click', () => {
        rvRange = btn.dataset.range;
        document.querySelectorAll('#region-vip-range-switch button').forEach(b => b.classList.toggle('active', b === btn));
        rvSetControlVisibility();
        renderRegionVipMatrix();
      });
    });
    rvDateSelect.addEventListener('change', () => { rvSelectedDate = rvDateSelect.value; renderRegionVipMatrix(); });
    rvMultiSelect.addEventListener('change', () => {
      rvSelectedMultiDates = Array.from(rvMultiSelect.selectedOptions).map(o => o.value);
      renderRegionVipMatrix();
    });
    rvWeekSelect.addEventListener('change', () => { rvSelectedWeekKey = rvWeekSelect.value; renderRegionVipMatrix(); });
    rvMonthSelect.addEventListener('change', () => { rvSelectedMonthKey = rvMonthSelect.value; renderRegionVipMatrix(); });

    renderRegionVipMatrix();
  })();
}

const REASSIGN_ENDPOINT = 'https://08-project-upload.08project.workers.dev/reassign-agent';
const BAN_USER_ENDPOINT = 'https://08-project-upload.08project.workers.dev/ban-user';
const UNBAN_USER_ENDPOINT = 'https://08-project-upload.08project.workers.dev/unban-user';

if (IS_SEARCH_USER) {
  const container = document.getElementById('search-user-app');
  container.innerHTML = \`
    <div class="analysis-heading deposit"><h2>Search User</h2><div class="line"></div><span class="tag">LOOKUP</span></div>
    <div class="su-searchbar">
      <span class="su-searchbar-icon">&#128269;</span>
      <input type="text" id="search-user-input" placeholder="Enter or paste a User ID&hellip;" inputmode="numeric">
      <button id="search-user-btn">Search</button>
    </div>

    \${IS_AGENT_SCOPED ? '' : \`
    <div class="su-reassign-card">
      <div class="su-reassign-title"><span class="badge">&#128100;</span> Reassign Agent</div>
      <div class="su-reassign-row">
        <input type="text" id="reassign-user-input" placeholder="User ID" inputmode="numeric">
        <select id="reassign-agent-select"><option value="">Un-Assigned</option></select>
        <button id="reassign-save-btn">&#128190; Save</button>
      </div>
      <div id="reassign-msg" class="su-reassign-msg"></div>
    </div>

    <div class="su-reassign-card su-bulk-card">
      <div class="su-reassign-title"><span class="badge">&#128203;</span> Bulk Reassign Agent</div>
      <div class="su-bulk-note">Copy a column of User IDs straight from Excel and paste them below &mdash; one ID per line (or comma/tab separated works too).</div>
      <textarea id="bulk-reassign-ids" class="su-bulk-textarea" placeholder="903039&#10;978483&#10;87434"></textarea>
      <div class="su-reassign-row" style="margin-top:10px;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:8px;">
          <select id="bulk-reassign-agent-select"><option value="">Un-Assigned</option></select>
          <span id="bulk-reassign-count" class="su-bulk-count">0 IDs detected</span>
        </div>
        <button id="bulk-reassign-save-btn">&#128190; Apply to all</button>
      </div>
      <div id="bulk-reassign-msg" class="su-reassign-msg"></div>
    </div>

    <div class="su-reassign-card su-ban-card">
      <div class="su-reassign-title"><span class="badge">&#128683;</span> Ban / Unban User</div>
      <div class="su-ban-note">Banning hides this user from every report, listing, export, and search on the dashboard -- their records are NOT deleted and keep updating normally in the background. Unban to make them visible again immediately, with full history intact.</div>
      <div class="su-reassign-row">
        <input type="text" id="ban-user-input" placeholder="User ID" inputmode="numeric">
        <button id="ban-user-btn" class="su-ban-btn">&#128683; Ban</button>
        <button id="unban-user-btn" class="su-unban-btn">&#9989; Unban</button>
      </div>
      <div id="ban-user-msg" class="su-reassign-msg"></div>
    </div>
    \`}

    <div id="search-user-result"></div>
  \`;

  // Agent dropdown options come from the report's agent_list (distinct real
  // agent names already in agent_assignments) -- fetched lazily so the
  // Search User page doesn't have to wait on /data.json before rendering.
  // Reassign Agent is hidden entirely for agent-scoped dashboards, so none
  // of this dropdown/save wiring applies there.
  if (!IS_AGENT_SCOPED) {
  (async () => {
    try {
      const res = await fetch('/data.json');
      const reportData = await res.json();
      const select = document.getElementById('reassign-agent-select');
      const bulkSelect = document.getElementById('bulk-reassign-agent-select');
      (reportData.agent_list || []).forEach(name => {
        [select, bulkSelect].forEach(el => {
          const opt = document.createElement('option');
          opt.value = name;
          opt.textContent = name;
          el.appendChild(opt);
        });
      });
    } catch (e) {
      // Dropdown just falls back to "Un-Assigned" only -- not fatal.
    }
  })();

  // Bulk Reassign: parses one ID per line (or comma/tab separated, matching
  // whatever a pasted Excel column looks like), de-duped, non-numeric
  // entries silently dropped from the count/apply.
  function parseBulkUserIds() {
    const raw = document.getElementById('bulk-reassign-ids').value;
    const ids = raw.split(/[\\s,]+/).map(s => s.trim()).filter(Boolean).map(Number)
      .filter(n => Number.isInteger(n) && n > 0);
    return Array.from(new Set(ids));
  }
  const bulkTextarea = document.getElementById('bulk-reassign-ids');
  const bulkCountEl = document.getElementById('bulk-reassign-count');
  bulkTextarea.addEventListener('input', () => {
    bulkCountEl.textContent = parseBulkUserIds().length + ' IDs detected';
  });

  document.getElementById('bulk-reassign-save-btn').addEventListener('click', async () => {
    const select = document.getElementById('bulk-reassign-agent-select');
    const btn = document.getElementById('bulk-reassign-save-btn');
    const msg = document.getElementById('bulk-reassign-msg');
    const userIds = parseBulkUserIds();
    if (!userIds.length) {
      msg.textContent = 'Paste at least one valid numeric User ID.';
      msg.className = 'su-reassign-msg err';
      return;
    }
    const reassignPassword = promptActionPassword('bulk reassign ' + userIds.length + ' user(s)');
    if (reassignPassword === null) return;
    btn.disabled = true;
    msg.textContent = 'Saving ' + userIds.length + ' user(s)...';
    msg.className = 'su-reassign-msg';
    try {
      const res = await fetch(REASSIGN_ENDPOINT, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ user_ids: userIds, agent: select.value, password: reassignPassword }),
      });
      const resData = await res.json();
      if (!res.ok) throw new Error(resData.error || res.status);
      msg.textContent = 'Saved - ' + userIds.length + ' user(s) will show as ' + (select.value || 'Un-Assigned') + ' within a minute or two.';
      msg.className = 'su-reassign-msg ok';
    } catch (err) {
      msg.textContent = 'Error: ' + err.message;
      msg.className = 'su-reassign-msg err';
    }
    btn.disabled = false;
  });

  document.getElementById('reassign-save-btn').addEventListener('click', async () => {
    const userInput = document.getElementById('reassign-user-input');
    const select = document.getElementById('reassign-agent-select');
    const btn = document.getElementById('reassign-save-btn');
    const msg = document.getElementById('reassign-msg');
    const userId = userInput.value.trim();
    const userIdNum = Number(userId);
    if (!userId || !Number.isInteger(userIdNum) || userIdNum <= 0) {
      msg.textContent = 'Enter a valid numeric User ID.';
      msg.className = 'su-reassign-msg err';
      return;
    }
    const reassignPassword = promptActionPassword('reassign this user');
    if (reassignPassword === null) return;
    btn.disabled = true;
    msg.textContent = 'Saving...';
    msg.className = 'su-reassign-msg';
    try {
      const res = await fetch(REASSIGN_ENDPOINT, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ user_id: Number(userId), agent: select.value, password: reassignPassword }),
      });
      const resData = await res.json();
      if (!res.ok) throw new Error(resData.error || res.status);
      msg.textContent = 'Saved - ' + (select.value || 'Un-Assigned') + ' will show for User #' + userId + ' within a minute or two.';
      msg.className = 'su-reassign-msg ok';
    } catch (err) {
      msg.textContent = 'Error: ' + err.message;
      msg.className = 'su-reassign-msg err';
    }
    btn.disabled = false;
  });

  document.getElementById('ban-user-btn').addEventListener('click', async () => {
    const userInput = document.getElementById('ban-user-input');
    const btn = document.getElementById('ban-user-btn');
    const msg = document.getElementById('ban-user-msg');
    const userId = userInput.value.trim();
    const userIdNum = Number(userId);
    if (!userId || !Number.isInteger(userIdNum) || userIdNum <= 0) {
      msg.textContent = 'Enter a valid numeric User ID.';
      msg.className = 'su-reassign-msg err';
      return;
    }
    btn.disabled = true;
    msg.textContent = 'Checking...';
    msg.className = 'su-reassign-msg';
    // A user_id that's already banned (or never existed) is invisible in
    // the search index, so it 404s here -- same check the Search box uses.
    // Ban should refuse rather than dispatch a no-op.
    const checkRes = await fetch('/api/user-search?user_id=' + encodeURIComponent(userId));
    if (!checkRes.ok) {
      msg.textContent = 'Not valid user';
      msg.className = 'su-reassign-msg err';
      btn.disabled = false;
      return;
    }
    if (!confirm('Ban User #' + userId + '? They will be hidden from every report and search, but no records are deleted.')) {
      btn.disabled = false;
      return;
    }
    const banPassword = promptActionPassword('ban this user');
    if (banPassword === null) {
      btn.disabled = false;
      return;
    }
    msg.textContent = 'Banning...';
    msg.className = 'su-reassign-msg';
    try {
      const res = await fetch(BAN_USER_ENDPOINT, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ user_id: Number(userId), password: banPassword }),
      });
      const resData = await res.json();
      if (!res.ok) throw new Error(resData.error || res.status);
      msg.textContent = 'User #' + userId + ' banned. They will disappear from the dashboard within a minute or two.';
      msg.className = 'su-reassign-msg ok';
      userInput.value = '';
    } catch (err) {
      msg.textContent = 'Error: ' + err.message;
      msg.className = 'su-reassign-msg err';
    }
    btn.disabled = false;
  });

  document.getElementById('unban-user-btn').addEventListener('click', async () => {
    const userInput = document.getElementById('ban-user-input');
    const btn = document.getElementById('unban-user-btn');
    const msg = document.getElementById('ban-user-msg');
    const userId = userInput.value.trim();
    const userIdNum = Number(userId);
    if (!userId || !Number.isInteger(userIdNum) || userIdNum <= 0) {
      msg.textContent = 'Enter a valid numeric User ID.';
      msg.className = 'su-reassign-msg err';
      return;
    }
    // No search pre-check here -- a banned user is, by design, invisible to
    // search, so there's nothing to verify against before unbanning.
    const unbanPassword = promptActionPassword('unban this user');
    if (unbanPassword === null) return;
    btn.disabled = true;
    msg.textContent = 'Unbanning...';
    msg.className = 'su-reassign-msg';
    try {
      const res = await fetch(UNBAN_USER_ENDPOINT, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ user_id: Number(userId), password: unbanPassword }),
      });
      const resData = await res.json();
      if (!res.ok) throw new Error(resData.error || res.status);
      msg.textContent = 'User #' + userId + ' unbanned. Their full history will reappear on the dashboard within a minute or two.';
      msg.className = 'su-reassign-msg ok';
      userInput.value = '';
    } catch (err) {
      msg.textContent = 'Error: ' + err.message;
      msg.className = 'su-reassign-msg err';
    }
    btn.disabled = false;
  });
  }

  function fmtMoney(v) { return '₹' + Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 }); }
  function daysAgoLabel(iso) {
    if (!iso) return null;
    const d = new Date(String(iso).replace(' ', 'T'));
    if (isNaN(d)) return null;
    const gap = Math.floor((Date.now() - d.getTime()) / 86400000);
    return gap <= 0 ? 'Today' : gap + 'd ago';
  }
  function activityPill(label) {
    if (!label) return '<span class="su-pill su-pill-grey">No data</span>';
    return label === 'Today' ? '<span class="su-pill su-pill-green">Active Today</span>' : '<span class="su-pill su-pill-grey">' + label + '</span>';
  }
  function vipBadge(level) {
    let cls = 'su-vip-standard', label = 'Standard';
    if (level >= 10) { cls = 'su-vip-elite'; label = 'Elite'; }
    else if (level >= 5) { cls = 'su-vip-gold'; label = 'Gold'; }
    return '<span class="su-vip-badge ' + cls + '">VIP ' + (level ?? '&mdash;') + ' &middot; ' + label + '</span>';
  }
  function statusPill(status) {
    const s = String(status).toLowerCase();
    let cls = 'su-pill-grey';
    if (s.includes('complete')) cls = 'su-pill-green';
    else if (s.includes('process')) cls = 'su-pill-blue';
    else if (s.includes('review')) cls = 'su-pill-amber';
    else if (s.includes('reject') || s.includes('fail')) cls = 'su-pill-red';
    return '<span class="su-pill ' + cls + '">' + status + '</span>';
  }
  function gameTypeBadge(type) {
    return '<span class="su-pill ' + (type === 'Win' ? 'su-pill-green' : 'su-pill-blue') + '">' + type + '</span>';
  }
  function sumIf(rows, statusMatch) {
    return (rows || [])
      .filter(r => String(r.status).toLowerCase().includes(statusMatch))
      .reduce((s, r) => s + Number(r.amount || 0), 0);
  }
  function recordTable(rows, cols, emptyMsg) {
    if (!rows || !rows.length) return '<div class="no-data">' + (emptyMsg || 'No records in this period.') + '</div>';
    const thead = '<thead><tr>' + cols.map(c => '<th' + (c.num ? ' class="num"' : '') + '>' + c.label + '</th>').join('') + '</tr></thead>';
    const tbody = '<tbody>' + rows.map(r => '<tr>' + cols.map(c => '<td class="' + (c.num ? 'num' : '') + '">' + c.render(r) + '</td>').join('') + '</tr>').join('') + '</tbody>';
    return '<div class="table-wrap"><table>' + thead + tbody + '</table></div>';
  }

  async function runSearch() {
    const input = document.getElementById('search-user-input');
    const resultEl = document.getElementById('search-user-result');
    const userId = input.value.trim();
    if (!userId) return;
    document.getElementById('search-user-btn').disabled = true;
    resultEl.innerHTML = '<div class="su-state">Searching&hellip;</div>';
    try {
      const res = await fetch('/api/user-search?user_id=' + encodeURIComponent(userId));
      const data = await res.json();
      if (!res.ok) {
        resultEl.innerHTML = '<div class="su-state su-state-error">&#9888;&#65039; ' + (data.error || 'User not found') + '</div>';
        return;
      }
      if (IS_AGENT_SCOPED && data.agent !== AGENT_NAME) {
        resultEl.innerHTML = '<div class="su-state su-state-error">&#9888;&#65039; User #' + userId + ' is not assigned to your agent account.</div>';
        return;
      }
      const dep7 = sumIf(data.recent_deposits, 'complete');
      const wd7 = sumIf(data.recent_withdrawals, 'complete');

      resultEl.innerHTML = \`
        <div class="su-profile-card">
          <div class="su-profile-top">
            <div>
              <div class="su-profile-id">User #\${data.user_id}</div>
              <div class="su-profile-meta">Agent \${data.agent || 'Un-Assigned'} &middot; \${data.region || 'Unknown region'} &middot; Channel \${data.acquisition_channel || '&mdash;'} &middot; Registered \${data.registered ? shortDate(String(data.registered).slice(0,10)) : '&mdash;'} &middot; \${activityPill(daysAgoLabel(data.last_active_time))}</div>
            </div>
            <div class="su-profile-balance">
              <div class="lbl">Wallet Balance</div>
              <div class="amt">\${fmtMoney(data.wallet_balance)}</div>
            </div>
            \${vipBadge(data.vip_level)}
          </div>
        </div>

        <div class="analysis-heading withdrawal"><h2>Financial Overview</h2><div class="line"></div><span class="tag">LOOKUP</span></div>
        <div class="su-fin-panel">
          <div class="su-fin-section">
            <div class="su-fin-section-title">Lifetime</div>
            <div class="su-fin-stats">
              <div class="su-fin-stat"><div class="su-fin-label">Total Deposit</div><div class="su-fin-value c-green">\${fmtMoney(data.total_deposit)}</div></div>
              <div class="su-fin-stat"><div class="su-fin-label">Deposit Count</div><div class="su-fin-value c-blue">\${fmt(data.total_deposit_count || 0)}</div></div>
              <div class="su-fin-stat"><div class="su-fin-label">Total Withdraw</div><div class="su-fin-value c-red">\${fmtMoney(data.total_withdraw)}</div></div>
              <div class="su-fin-stat"><div class="su-fin-label">Wallet Balance</div><div class="su-fin-value c-blue">\${fmtMoney(data.wallet_balance)}</div></div>
              <div class="su-fin-stat"><div class="su-fin-label">Net Lifetime (Deposit &minus; Withdraw)</div><div class="su-fin-value \${data.net_lifetime >= 0 ? 'c-blue' : 'c-red'}">\${fmtMoney(data.net_lifetime)}</div></div>
            </div>
          </div>
          <div class="su-fin-section">
            <div class="su-fin-section-title">Last 7 Days <span class="su-fin-note">(completed only)</span></div>
            <div class="su-fin-stats">
              <div class="su-fin-stat"><div class="su-fin-label">Deposits</div><div class="su-fin-value c-green">\${fmtMoney(dep7)}</div></div>
              <div class="su-fin-stat"><div class="su-fin-label">Deposit Count</div><div class="su-fin-value c-blue">\${fmt(data.recent_deposit_count_7d || 0)}</div></div>
              <div class="su-fin-stat"><div class="su-fin-label">Withdrawals</div><div class="su-fin-value c-red">\${fmtMoney(wd7)}</div></div>
              <div class="su-fin-stat"><div class="su-fin-label">Net</div><div class="su-fin-value \${(dep7 - wd7) >= 0 ? 'c-blue' : 'c-red'}">\${fmtMoney(dep7 - wd7)}</div></div>
            </div>
          </div>
        </div>

        <div class="analysis-heading deposit"><h2>Last 7 Days Activity</h2><div class="line"></div><span class="tag">LOOKUP</span></div>
        <div class="row2col">
          <section class="acc-emerald">
            <div class="sec-title"><div class="badge b-emerald">&#128176;</div><h2>Deposits (\${(data.recent_deposits || []).length})</h2></div>
            \${recordTable(data.recent_deposits, [
              { label: 'Date', render: r => r.date },
              { label: 'Amount', render: r => fmtMoney(r.amount), num: true },
              { label: 'Status', render: r => statusPill(r.status) },
              { label: 'Order No', render: r => r.order_no || '&mdash;' },
              { label: 'Channel', render: r => r.channel || '&mdash;' },
            ], 'No deposits in the last 7 days.')}
          </section>
          <section class="acc-rose">
            <div class="sec-title"><div class="badge b-rose">&#128181;</div><h2>Withdrawals (\${(data.recent_withdrawals || []).length})</h2></div>
            \${recordTable(data.recent_withdrawals, [
              { label: 'Date', render: r => r.date },
              { label: 'Amount', render: r => fmtMoney(r.amount), num: true },
              { label: 'Status', render: r => statusPill(r.status) },
              { label: 'Order No', render: r => r.order_no || '&mdash;' },
              { label: 'Channel', render: r => r.channel || '&mdash;' },
            ], 'No withdrawals in the last 7 days.')}
          </section>
        </div>

        <div class="analysis-heading withdrawal"><h2>Recent Games &amp; Bonuses</h2><div class="line"></div><span class="tag">LOOKUP</span></div>
        <div class="row2col">
          <section class="acc-orange">
            <div class="sec-title"><div class="badge b-orange">&#127918;</div><h2>Recent Games Played (\${(data.recent_games || []).length})</h2></div>
            <div class="ac-note">Last 2 days &middot; excludes bonus payouts</div>
            \${recordTable(data.recent_games, [
              { label: 'Game', render: r => r.game_name },
              { label: 'Type', render: r => gameTypeBadge(r.type) },
              { label: 'Amount', render: r => fmtMoney(r.amount), num: true },
              { label: 'Date', render: r => r.date },
            ], 'No games played in the last 2 days.')}
          </section>
          <section class="acc-purple">
            <div class="sec-title"><div class="badge b-purple">&#127873;</div><h2>Bonuses Claimed (\${(data.recent_bonuses || []).length})</h2></div>
            <div class="ac-note">Last 7 days</div>
            \${recordTable(data.recent_bonuses, [
              { label: 'Bonus', render: r => r.category },
              { label: 'Amount', render: r => fmtMoney(r.amount), num: true },
              { label: 'Date', render: r => r.date },
            ], 'No bonuses claimed in the last 7 days.')}
          </section>
        </div>
      \`;
    } catch (e) {
      resultEl.innerHTML = '<div class="su-state su-state-error">Search failed: ' + e.message + '</div>';
    } finally {
      document.getElementById('search-user-btn').disabled = false;
    }
  }
  document.getElementById('search-user-btn').addEventListener('click', runSearch);
  document.getElementById('search-user-input').addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });
  document.getElementById('search-user-input').focus();
}

if (!IS_ACTION_CENTER && !IS_PERFORMANCE && !IS_ANALYTICS && !IS_PLATFORM_ANALYSIS && !IS_SEARCH_USER)
(async () => {
  const res = await fetch('/data.json');
  if (!res.ok) {
    document.getElementById('app').textContent = 'Failed to load report data (' + res.status + ')';
    return;
  }
  const globalData = await res.json();
  let data = globalData;
  if (IS_AGENT_SCOPED) {
    // The per-agent file only has all_time/by_date/withdrawal_analysis/
    // region_vip_analytics (the aggregates that genuinely can't be scoped
    // client-side) -- everything else (dates, amount_ranges, metadata, and
    // withdrawal_orders_full, which already carries an "agent" field per
    // row) comes from the global report, so the two are merged here.
    const agentRes = await fetch('/data.json?agent=' + encodeURIComponent(AGENT_NAME));
    if (!agentRes.ok) {
      document.getElementById('app').textContent = 'Failed to load this agent\\'s report (' + agentRes.status + ')';
      return;
    }
    const agentData = await agentRes.json();
    data = {
      ...globalData,
      ...agentData,
      withdrawal_orders_full: (globalData.withdrawal_orders_full || []).filter(o => o.agent === AGENT_NAME),
    };
  }
  const rangeOrder = data.amount_ranges.concat(['Other']);

  document.getElementById('updated-badge').innerHTML =
    '<span class="dot"></span> Records updated through ' +
    (data.latest_record_time ? new Date(data.latest_record_time).toLocaleString() : 'n/a');

  document.getElementById('app').className = '';
  document.getElementById('app').innerHTML = \`
    <div class="kpi-grid">
      <div class="kpi c-green"><div class="dash"></div><div class="value" id="k-deposit"></div><div class="label">Total Deposit</div><div class="desc">&#10003; Complete orders only</div></div>
      <div class="kpi c-red"><div class="dash"></div><div class="value" id="k-withdraw"></div><div class="label">Total Withdraw</div><div class="desc">&#10003; In-Review + Processing + Complete</div></div>
      <div class="kpi c-amber"><div class="dash"></div><div class="value" id="k-deposit-orders"></div><div class="label">Deposit Orders</div><div class="desc">&#10003; Complete order count for the day</div></div>
      <div class="kpi c-pink"><div class="dash"></div><div class="value" id="k-withdraw-orders"></div><div class="label">Withdraw Orders</div><div class="desc">&#10003; In-Review + Processing + Complete count</div></div>
    </div>

    <div class="net-flow">
      <div class="nf-label">NET FLOW</div>
      <div class="nf-stats">
        <div>Return Users: <b id="nf-return-users">&mdash;</b></div>
        <div>Difference: <b id="nf-difference">&mdash;</b></div>
        <div>Withdraw/Deposit: <b id="nf-ratio">&mdash;</b></div>
      </div>
    </div>

    <div class="kpi-grid row2">
      <div class="kpi c-sky"><div class="dash"></div><div class="value" id="k-deposit-users"></div><div class="label">Deposit Users</div><div class="desc">&#10003; Unique users with complete deposits</div></div>
      <div class="kpi c-orange"><div class="dash"></div><div class="value" id="k-withdraw-users"></div><div class="label">Withdraw Users</div><div class="desc">&#10003; Unique users with active withdrawals</div></div>
      <div class="kpi c-purple"><div class="dash"></div><div class="value" id="k-active-users"></div><div class="label">Active Users</div><div class="desc">&#10003; Unique users with deposit history, active via deposit/withdraw/bets</div></div>
    </div>

    <div class="analysis-heading deposit"><h2>Deposit Analysis</h2><div class="line"></div><span class="tag">DEPOSITS</span></div>

    <section class="acc-blue">
      <div class="section-head">
        <div class="sec-title"><div class="badge b-blue">&#128202;</div><h2>Amount Range</h2></div>
        <button class="download-btn-sm" id="btn-dl-amount-range">&#128190; Excel</button>
      </div>
      <div id="range-table"></div>
    </section>

    <section class="acc-purple">
      <div class="section-head">
        <div class="sec-title"><div class="badge b-purple">&#127974;</div><h2>Deposit Channel Analysis</h2></div>
        <button class="download-btn" id="btn-download">&#128190; Download Excel</button>
      </div>
      <div class="two-col">
        <div class="sub-table">
          <h3>Deposit Success Rate by Amount Range</h3>
          <div id="success-range-table"></div>
        </div>
        <div class="sub-table">
          <h3>Deposit by Channel</h3>
          <div id="success-channel-table"></div>
        </div>
      </div>
    </section>

    <section class="acc-orange">
      <div class="section-head">
        <div class="sec-title"><div class="badge b-orange">&#9200;</div><h2>Hourly Success Rate &mdash; By Amount Range</h2></div>
        <button class="download-btn-sm" id="btn-dl-heatmap-range">&#128190; Excel</button>
      </div>
      <div class="heat-legend">
        <span class="chip good">&ge;41%</span>
        <span class="chip mid">30&ndash;40%</span>
        <span class="chip bad">&lt;30%</span>
        <span class="chip none">&mdash;</span>
      </div>
      <div id="heatmap-range-table" class="table-wrap"></div>
    </section>

    <section class="acc-orange">
      <div class="section-head">
        <div class="sec-title"><div class="badge b-orange">&#9200;</div><h2>Hourly Success Rate &mdash; By Channel</h2></div>
        <button class="download-btn-sm" id="btn-dl-heatmap-channel">&#128190; Excel</button>
      </div>
      <div class="heat-legend">
        <span class="chip good">&ge;41%</span>
        <span class="chip mid">30&ndash;40%</span>
        <span class="chip bad">&lt;30%</span>
        <span class="chip none">&mdash;</span>
      </div>
      <div id="heatmap-channel-table" class="table-wrap"></div>
    </section>

    <div class="analysis-heading withdrawal"><h2>Withdrawal Analysis</h2><div class="line"></div><span class="tag">WITHDRAWALS</span></div>

    <div class="row2col">
      <section class="acc-rose">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-rose">&#9203;</div><h2>Channel-wise Processing Time (create &rarr; review) &mdash; status 1</h2></div>
          <button class="download-btn-sm" id="btn-dl-withdrawal-orders">&#128190; Download Orders (Excel)</button>
        </div>
        <div id="withdrawal-review-table"></div>
      </section>
      <section class="acc-cyan">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-cyan">&#9989;</div><h2>Channel-wise Completion Time (review &rarr; complete) &mdash; status 2</h2></div>
          <button class="download-btn-sm" id="btn-dl-withdrawal-completion">&#128190; Excel</button>
        </div>
        <div id="withdrawal-completion-table"></div>
      </section>
    </div>

    <div class="row2col">
      <section class="acc-rose">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-rose">&#8987;</div><h2>Processing Orders &mdash; Aging</h2></div>
          <button class="download-btn-sm" id="btn-dl-processing-backlog">&#128190; Excel</button>
        </div>
        <canvas id="processing-backlog-chart"></canvas>
      </section>
      <section class="acc-cyan">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-cyan">&#128269;</div><h2>In-Review Orders &mdash; Aging</h2></div>
          <button class="download-btn-sm" id="btn-dl-inreview-backlog">&#128190; Excel</button>
        </div>
        <canvas id="inreview-backlog-chart"></canvas>
      </section>
    </div>

    <div class="row2col">
      <section class="acc-rose">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-rose">&#9989;</div><h2>Completed Orders &mdash; &lt;4h vs &gt;4h (Last 4 Days)</h2></div>
          <button class="download-btn-sm" id="btn-dl-last4days">&#128190; Excel</button>
        </div>
        <div class="ac-note" id="last4days-pct-summary"></div>
        <canvas id="last4days-chart"></canvas>
      </section>
      <section class="acc-cyan">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-cyan">&#128176;</div><h2>Withdrawal Processing &mdash; Amount Range</h2></div>
          <button class="download-btn-sm" id="btn-dl-withdrawal-amount-range">&#128190; Excel</button>
        </div>
        <div id="amount-range-table"></div>
      </section>
    </div>

    <div class="row2col">
      <section class="acc-cyan ac-compact">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-cyan">&#128181;</div><h2>Withdrawal Amount Range</h2></div>
          <button class="download-btn-sm" id="btn-dl-yesterday-wd-range">&#128190; Excel</button>
        </div>
        <div class="date-switch" id="yesterday-wd-switch">
          <button data-day="today">Today</button>
          <button data-day="yesterday" class="active">Yesterday</button>
        </div>
        <div id="yesterday-wd-range-table"></div>
      </section>
      <section class="acc-cyan ac-compact">
        <div class="section-head">
          <div class="sec-title"><div class="badge b-cyan">&#128176;</div><h2>Highest Deposit Users</h2><span class="today-tag" id="highest-deposit-count">&mdash;</span></div>
          <button class="download-btn-sm" id="btn-dl-highest-deposit-users">&#128190; Excel</button>
        </div>
        <div class="ac-note">Users with total deposits of Rs 10,000+ for the selected date</div>
        <div id="highest-deposit-table"></div>
        <div class="ac-pagination" id="highest-deposit-pagination"></div>
      </section>
    </div>
  \`;

  let currentScope = null;

  function render(scope, label) {
    currentScope = scope;

    const s = scope.summary;
    document.getElementById('k-deposit').textContent = money(s.total_deposit);
    document.getElementById('k-withdraw').textContent = money(s.total_withdraw);
    document.getElementById('k-deposit-orders').textContent = fmt(s.deposit_orders);
    document.getElementById('k-withdraw-orders').textContent = fmt(s.withdraw_orders);
    document.getElementById('k-deposit-users').textContent = fmt(s.deposit_users);
    document.getElementById('k-withdraw-users').textContent = fmt(s.withdraw_users);
    document.getElementById('k-active-users').textContent = fmt(s.active_users);

    // % is of YESTERDAY's deposit_users (how many of yesterday's depositors
    // came back today), not today's -- matches return_users' own definition
    // (deposited both today AND the calendar day before).
    const prevDateForReturn = new Date(label + 'T00:00:00');
    prevDateForReturn.setDate(prevDateForReturn.getDate() - 1);
    const prevScopeForReturn = data.by_date[prevDateForReturn.toISOString().slice(0, 10)];
    const prevDepositUsers = prevScopeForReturn ? prevScopeForReturn.summary.deposit_users : null;
    document.getElementById('nf-return-users').textContent = s.return_users == null ? '—' :
      fmt(s.return_users) + (prevDepositUsers ? ' (' + (s.return_users / prevDepositUsers * 100).toFixed(1) + '%)' : '');
    const diffEl = document.getElementById('nf-difference');
    diffEl.textContent = (s.difference < 0 ? '-' : '') + money(Math.abs(s.difference));
    diffEl.className = s.difference < 0 ? 'neg' : 'pos';
    document.getElementById('nf-ratio').textContent = s.withdraw_deposit_pct == null ? '—' : s.withdraw_deposit_pct + '%';

    const rangeRows = rangeOrder.map(r => scope.by_amount_range.find(x => x.range === r) || { range: r, count: 0, users: 0, total_amount: 0 });
    const maxRangeAmount = Math.max(...rangeRows.map(r => r.total_amount), 1);
    sortableTable(
      document.getElementById('range-table'),
      ['Amount Range', 'Count', 'Users', 'Total Amount'],
      rangeRows.map(r => [r.range, r.count, r.users, r.total_amount]),
      r => '<tr><td>' + r[0] + '</td><td class="num">' + fmt(r[1]) + '</td><td class="num">' + fmt(r[2]) + '</td>' +
           '<td class="num bar-cell"><div class="bar" style="width:' + (r[3] / maxRangeAmount * 100) + '%"></div><span>' + money(r[3]) + '</span></td></tr>',
      [1, 2, 3]
    );
    const channels = scope.by_channel.map(c => c.channel);

    // Deposit Success Rate by Amount Range
    const srRows = rangeOrder
      .map(r => scope.success_by_range.find(x => x.range === r) || { range: r, total: 0, completed: 0, success_pct: 0, avg_minutes: null })
      .filter(r => r.total > 0 || r.range !== 'Other');
    sortableTable(
      document.getElementById('success-range-table'),
      ['Amount Range', 'Total', 'Completed', 'Success %', 'Avg Time'],
      srRows.map(r => [r.range, r.total, r.completed, r.success_pct, r.avg_minutes]),
      r => '<tr><td>' + r[0] + '</td><td class="num">' + fmt(r[1]) + '</td><td class="num">' + fmt(r[2]) + '</td>' +
           '<td class="num ' + pctClass(r[3]) + '">' + r[3] + '%</td>' +
           '<td class="num">' + (r[4] == null ? '&mdash;' : r[4] + ' min') + '</td></tr>',
      [1, 2, 3, 4]
    );

    // Deposit by Channel (success rate)
    sortableTable(
      document.getElementById('success-channel-table'),
      ['Channel', 'Total Orders', 'Comp. Orders', 'Comp. Users', 'Comp. Amount', 'Success %', 'Avg Mins'],
      scope.success_by_channel.map(c => [c.channel, c.total, c.comp_orders, c.comp_users, c.comp_amount, c.success_pct, c.avg_minutes]),
      r => '<tr><td>' + r[0] + '</td><td class="num">' + fmt(r[1]) + '</td><td class="num">' + fmt(r[2]) + '</td><td class="num">' + fmt(r[3]) + '</td>' +
           '<td class="num">' + money(r[4]) + '</td>' +
           '<td class="num ' + pctClass(r[5]) + '">' + r[5] + '%</td>' +
           '<td class="num">' + (r[6] == null ? '&mdash;' : r[6] + ' min') + '</td></tr>',
      [1, 2, 3, 4, 5, 6]
    );

    renderHeatmap('channel', 'heatmap-channel-table', channels);
    renderHeatmap('range', 'heatmap-range-table', rangeOrder);

    renderWithdrawalTimingTable('withdrawal-review-table', scope.withdrawal_review_by_channel || [], 'No processing (status 1) withdrawals for this date.');
    renderWithdrawalTimingTable('withdrawal-completion-table', scope.withdrawal_completion_by_channel || [], 'No completed (status 2) withdrawals for this date.');

    const highestDepositCols = [
      { label: 'User ID', render: r => r.user_id },
      { label: 'Total Deposit', num: true, render: r => money(r.total_deposit), raw: r => r.total_deposit },
      { label: 'Total Withdraw', num: true, render: r => money(r.total_withdraw), raw: r => r.total_withdraw },
    ];
    paginatedTable('highest-deposit-table', 'highest-deposit-pagination', scope.top_depositors || [], highestDepositCols, 6, { jumpDropdown: true });
    document.getElementById('highest-deposit-count').textContent = fmt((scope.top_depositors || []).length);
  }

  function renderWithdrawalTimingTable(containerId, matrix, emptyMsg) {
    const procBuckets = data.withdrawal_analysis.processing_time_buckets;
    const channels = [...new Set(matrix.map(r => r.channel))];
    const container = document.getElementById(containerId);
    if (!channels.length) {
      container.innerHTML = '<div class="no-data">' + emptyMsg + '</div>';
      return;
    }
    const rows = channels.map(ch => {
      const row = { channel: ch };
      let total = 0;
      for (const b of procBuckets) {
        const found = matrix.find(x => x.channel === ch && x.bucket === b);
        row[b] = found ? found.count : 0;
        total += row[b];
      }
      row._total = total;
      return row;
    });
    const headers = ['Channel'].concat(procBuckets).concat(['Total']);
    container.innerHTML = '<div class="table-wrap"><table><thead><tr>' +
      headers.map((h, i) => '<th' + (i > 0 ? ' class="num"' : '') + '>' + h + '</th>').join('') + '</tr></thead><tbody>' +
      rows.map(row => '<tr><td>' + row.channel + '</td>' +
        procBuckets.map(b => '<td class="num">' + (row[b] || '') + '</td>').join('') +
        '<td class="num"><strong>' + row._total + '</strong></td></tr>').join('') +
      '</tbody></table></div>';
  }

  function renderAmountRangeMatrix(matrix) {
    const container = document.getElementById('amount-range-table');
    const ageBuckets = data.withdrawal_analysis.processing_backlog_buckets;
    const amountRanges = data.withdrawal_analysis.amount_range_buckets;
    if (!matrix.length) {
      container.innerHTML = '<div class="no-data">No processing (status 1) withdrawals in backlog.</div>';
      return;
    }
    const rows = amountRanges.map(ar => {
      const row = { amount_range: ar };
      let totalCount = 0, totalAmount = 0;
      for (const b of ageBuckets) {
        const found = matrix.find(x => x.amount_range === ar && x.bucket === b);
        row[b] = found ? found.count : 0;
        totalCount += row[b];
        totalAmount += found ? found.amount : 0;
      }
      row._totalCount = totalCount;
      row._totalAmount = totalAmount;
      return row;
    });
    const headers = ['Amount Range'].concat(ageBuckets).concat(['Total Orders', 'Total Amount']);
    container.innerHTML = '<div class="table-wrap"><table><thead><tr>' +
      headers.map((h, i) => '<th' + (i > 0 ? ' class="num"' : '') + '>' + h + '</th>').join('') + '</tr></thead><tbody>' +
      rows.map(row => '<tr><td>' + row.amount_range + '</td>' +
        ageBuckets.map(b => '<td class="num">' + (row[b] || '') + '</td>').join('') +
        '<td class="num"><strong>' + row._totalCount + '</strong></td>' +
        '<td class="num">' + money(row._totalAmount) + '</td></tr>').join('') +
      '</tbody></table></div>';
  }

  let yesterdayWdDay = 'yesterday';
  function renderYesterdayWithdrawalRange() {
    const byDay = data.withdrawal_amount_range_by_day || {};
    const rep = byDay[yesterdayWdDay];
    const container = document.getElementById('yesterday-wd-range-table');
    if (!rep || !rep.rows || !rep.rows.length) {
      if (container) container.innerHTML = '<div class="no-data">No withdrawal orders ' + yesterdayWdDay + '.</div>';
      return;
    }
    const headers = ['Amount Range', 'Total Orders', 'Total Amount'];
    const bodyRows = rep.rows.concat([rep.totals]);
    container.innerHTML = '<div class="table-wrap"><table><thead><tr>' +
      headers.map((h, i) => '<th' + (i > 0 ? ' class="num"' : '') + '>' + h + '</th>').join('') + '</tr></thead><tbody>' +
      bodyRows.map(row => {
        const isTotal = row.range === 'Total';
        return '<tr' + (isTotal ? ' style="font-weight:700;background:#f9fafb"' : '') + '><td>' + row.range + '</td>' +
          '<td class="num"><strong>' + fmt(row.total_orders) + '</strong></td>' +
          '<td class="num">' + money(row.total_amount) + '</td></tr>';
      }).join('') +
      '</tbody></table></div>';
  }

  // Draws each bar's own value, percentage, and (optionally) a total-amount
  // line INSIDE the bar near its top, so the aging/completion breakdown is
  // readable at a glance without hovering. pctMode 'datasetTotal': % of
  // that whole dataset's own total (e.g. this bucket is 29% of all
  // processing-backlog orders). pctMode 'indexTotal': % of the total across
  // all datasets AT THAT SAME x-axis category (e.g. this day's <4h share vs
  // >4h share). getAmount(dsIndex, index), if given, adds a third "money"
  // line (e.g. Rs45,000 sitting in that aging bucket).
  function barValueLabelsPlugin(pctMode, getAmount) {
    return {
      id: 'barValueLabels',
      afterDatasetsDraw(chart) {
        const { ctx } = chart;
        const datasets = chart.data.datasets;
        const datasetTotals = datasets.map(ds => ds.data.reduce((s, v) => s + (Number(v) || 0), 0));
        const indexTotals = (chart.data.labels || []).map((_, i) =>
          datasets.reduce((s, ds) => s + (Number(ds.data[i]) || 0), 0)
        );
        datasets.forEach((dataset, dsIndex) => {
          const meta = chart.getDatasetMeta(dsIndex);
          if (meta.hidden) return;
          meta.data.forEach((bar, index) => {
            const value = Number(dataset.data[index]) || 0;
            if (!value) return;
            const denom = pctMode === 'indexTotal' ? indexTotals[index] : datasetTotals[dsIndex];
            const pct = denom ? (value / denom * 100) : 0;
            const amount = getAmount ? getAmount(dsIndex, index) : null;
            const lines = [fmt(value), pct.toFixed(1) + '%'];
            if (amount != null) lines.push(money(amount));
            const lineHeight = 12;
            const neededHeight = lines.length * lineHeight + 4;
            const barHeight = (bar.base != null ? bar.base : chart.chartArea.bottom) - bar.y;
            // Draw inside the bar (top-anchored) when there's room; for bars
            // too short to fit the text, draw it stacked above the bar
            // instead so it doesn't spill into the axis labels below.
            const fitsInside = barHeight >= neededHeight;
            let y = fitsInside ? bar.y + 14 : bar.y - neededHeight + 8;
            ctx.save();
            ctx.textAlign = 'center';
            ctx.fillStyle = '#000000';
            lines.forEach((line, i) => {
              ctx.font = i === 0 ? 'bold 11px -apple-system, BlinkMacSystemFont, sans-serif' : '10px -apple-system, BlinkMacSystemFont, sans-serif';
              ctx.fillText(line, bar.x, y);
              y += lineHeight;
            });
            ctx.restore();
          });
        });
      },
    };
  }

  let processingBacklogChart = null, inreviewBacklogChart = null, last4daysChart = null;
  function renderBacklogCharts() {
    const wa = data.withdrawal_analysis;
    if (processingBacklogChart) processingBacklogChart.destroy();
    processingBacklogChart = new Chart(document.getElementById('processing-backlog-chart'), {
      type: 'bar',
      plugins: [barValueLabelsPlugin('datasetTotal', (dsIndex, index) => wa.processing_backlog[index] ? wa.processing_backlog[index].amount : null)],
      data: {
        labels: wa.processing_backlog.map(r => r.bucket),
        datasets: [{ label: 'Orders', data: wa.processing_backlog.map(r => r.count), backgroundColor: '#fb7185', borderRadius: 6 }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
    if (inreviewBacklogChart) inreviewBacklogChart.destroy();
    inreviewBacklogChart = new Chart(document.getElementById('inreview-backlog-chart'), {
      type: 'bar',
      plugins: [barValueLabelsPlugin('datasetTotal', (dsIndex, index) => wa.inreview_backlog[index] ? wa.inreview_backlog[index].amount : null)],
      data: {
        labels: wa.inreview_backlog.map(r => r.bucket),
        datasets: [{ label: 'Orders', data: wa.inreview_backlog.map(r => r.count), backgroundColor: '#22d3ee', borderRadius: 6 }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
    if (last4daysChart) last4daysChart.destroy();
    const last4 = wa.last4days_completion || [];
    // % split + point difference, most recent day with any completed orders --
    // e.g. "82.4% <4h vs 17.6% >4h (64.8 point gap)".
    const pctSummaryEl = document.getElementById('last4days-pct-summary');
    if (pctSummaryEl) {
      const latest = [...last4].reverse().find(r => (r.within_4h + r.more_than_4h) > 0);
      if (latest) {
        const total = latest.within_4h + latest.more_than_4h;
        const pctUnder = (latest.within_4h / total) * 100;
        const pctOver = 100 - pctUnder;
        pctSummaryEl.innerHTML = latest.date + ': ' + pctUnder.toFixed(1) + '% &lt;4h vs ' + pctOver.toFixed(1) +
          '% &gt;4h (' + Math.abs(pctUnder - pctOver).toFixed(1) + ' point gap)';
      } else {
        pctSummaryEl.textContent = '';
      }
    }
    last4daysChart = new Chart(document.getElementById('last4days-chart'), {
      type: 'bar',
      plugins: [barValueLabelsPlugin('indexTotal')],
      data: {
        labels: last4.map(r => r.date),
        datasets: [
          { label: '<4h', data: last4.map(r => r.within_4h), backgroundColor: '#34d399', borderRadius: 6 },
          { label: '>4h', data: last4.map(r => r.more_than_4h), backgroundColor: '#f87171', borderRadius: 6 },
        ],
      },
      options: {
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: true },
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              footer: (items) => {
                const total = items.reduce((sum, item) => sum + item.parsed.y, 0);
                if (!total) return 'Total: 0';
                const under = items.find(i => i.dataset.label === '<4h');
                const pctUnder = under ? (under.parsed.y / total) * 100 : 0;
                const pctOver = 100 - pctUnder;
                return 'Total: ' + total.toLocaleString('en-IN') +
                  '\\n' + pctUnder.toFixed(1) + '% <4h vs ' + pctOver.toFixed(1) + '% >4h';
              },
            },
          },
        },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });

    renderAmountRangeMatrix(wa.processing_amount_range_matrix || []);
  }

  function renderHeatmap(mode, containerId, rowKeys) {
    if (!currentScope) return;
    const container = document.getElementById(containerId);
    const hours = Array.from({ length: 24 }, (_, h) => h);
    const source = mode === 'channel' ? currentScope.hourly_success_by_channel : currentScope.hourly_success_by_range;
    const keyField = mode === 'channel' ? 'channel' : 'range';
    const dataRows = rowKeys.map(key => ({
      label: key,
      byHour: hours.map(h => source.find(x => x.hour === h && x[keyField] === key)),
    }));
    if (!dataRows.length) {
      container.innerHTML = '<div class="no-data">No deposits for this date.</div>';
      return;
    }
    const thead = '<thead><tr><th class="row-label">' + (mode === 'channel' ? 'Channel' : 'Amount Range') + '</th>' +
      hours.map(h => '<th>' + h + '</th>').join('') + '<th class="row-total">Total Orders</th></tr></thead>';
    const tbody = '<tbody>' + dataRows.map(row => {
      const rowTotal = row.byHour.reduce((sum, c) => sum + (c ? c.total : 0), 0);
      return '<tr><td class="row-label">' + row.label + '</td>' +
      row.byHour.map(cell => {
        const total = cell ? cell.total : 0;
        const pct = cell ? cell.success_pct : 0;
        const { bg, color } = heatColor(total, pct);
        const text = total ? pct + '%' : '&mdash;';
        return '<td style="background:' + bg + ';color:' + color + '" title="' + (total ? total + ' orders' : 'no orders') + '">' + text + '</td>';
      }).join('') + '<td class="num row-total">' + fmt(rowTotal) + '</td></tr>';
    }).join('') + '</tbody>';
    container.innerHTML = '<table class="heat-table">' + thead + tbody + '</table>';
  }

  document.getElementById('btn-download').addEventListener('click', async () => {
    if (!currentScope) return;
    const wb = new ExcelJS.Workbook();
    const wsRange = wb.addWorksheet('Success by Amount Range');
    const rangeData = currentScope.success_by_range.map(r => ({
      'Amount Range': r.range, Total: r.total, Completed: r.completed, 'Success %': r.success_pct, 'Avg Time (min)': r.avg_minutes,
    }));
    if (rangeData.length) {
      wsRange.columns = Object.keys(rangeData[0]).map(k => ({ header: k, key: k, width: Math.max(12, k.length + 2) }));
      wsRange.addRows(rangeData);
    }
    styleHeaderRow(wsRange);
    const wsChannel = wb.addWorksheet('Success by Channel');
    const channelData = currentScope.success_by_channel.map(c => ({
      Channel: c.channel, 'Total Orders': c.total, 'Comp. Orders': c.comp_orders, 'Comp. Users': c.comp_users, 'Comp. Amount': c.comp_amount, 'Success %': c.success_pct, 'Avg Mins': c.avg_minutes,
    }));
    if (channelData.length) {
      wsChannel.columns = Object.keys(channelData[0]).map(k => ({ header: k, key: k, width: Math.max(12, k.length + 2) }));
      wsChannel.addRows(channelData);
    }
    styleHeaderRow(wsChannel);
    await saveWorkbook(wb, 'deposit-channel-analysis-' + (datePicker.value || 'report') + '.xlsx');
  });

  document.getElementById('btn-dl-amount-range').addEventListener('click', () => {
    if (!currentScope) return;
    const rangeRows = rangeOrder.map(r => currentScope.by_amount_range.find(x => x.range === r) || { range: r, count: 0, users: 0, total_amount: 0 });
    downloadStyledExcel(rangeRows.map(r => ({
      'Amount Range': r.range, Count: r.count, Users: r.users, 'Total Amount': r.total_amount,
    })), 'Amount Range', 'amount-range-' + (datePicker.value || 'report') + '.xlsx');
  });

  function heatColorARGB(total, pct) {
    if (!total) return 'FFF3F4F6';
    if (pct >= 41) return 'FFBBF7D0';
    if (pct >= 30) return 'FFFEF08A';
    return 'FFFECACA';
  }

  async function downloadHeatmapExcel(mode, rowKeys, filenamePrefix, sheetName) {
    if (!currentScope) return;
    const hours = Array.from({ length: 24 }, (_, h) => h);
    const source = mode === 'channel' ? currentScope.hourly_success_by_channel : currentScope.hourly_success_by_range;
    const keyField = mode === 'channel' ? 'channel' : 'range';
    const headerLabel = mode === 'channel' ? 'Channel' : 'Amount Range';

    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet(sheetName);
    ws.columns = [
      { header: headerLabel, key: 'label', width: 26 },
      ...hours.map(h => ({ header: String(h) + 'h', key: 'h' + h, width: 12 })),
      { header: 'Total Orders', key: 'total', width: 14 },
    ];
    ws.getRow(1).font = { bold: true };
    ws.getRow(1).alignment = { horizontal: 'center' };
    ws.getRow(1).eachCell(c => { c.fill = HEADER_FILL; });

    rowKeys.forEach(key => {
      const cellsByHour = hours.map(h => source.find(x => x.hour === h && x[keyField] === key));
      const rowTotal = cellsByHour.reduce((sum, c) => sum + (c ? c.total : 0), 0);
      const rowData = { label: key, total: rowTotal };
      hours.forEach((h, idx) => {
        const cell = cellsByHour[idx];
        const total = cell ? cell.total : 0;
        const pct = cell ? cell.success_pct : 0;
        rowData['h' + h] = total ? (pct + '% (' + total + ')') : '—';
      });
      const row = ws.addRow(rowData);
      hours.forEach((h, idx) => {
        const cell = cellsByHour[idx];
        const total = cell ? cell.total : 0;
        const pct = cell ? cell.success_pct : 0;
        const c = row.getCell(2 + idx);
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: heatColorARGB(total, pct) } };
        c.alignment = { horizontal: 'center' };
      });
      const totalCell = row.getCell(2 + hours.length);
      totalCell.font = { bold: true };
      totalCell.alignment = { horizontal: 'center' };
      totalCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF9FAFB' } };
    });

    ws.eachRow(row => {
      row.eachCell(c => {
        c.border = { top: { style: 'thin', color: { argb: 'FFEDEFF3' } }, bottom: { style: 'thin', color: { argb: 'FFEDEFF3' } },
          left: { style: 'thin', color: { argb: 'FFEDEFF3' } }, right: { style: 'thin', color: { argb: 'FFEDEFF3' } } };
      });
    });

    const buf = await wb.xlsx.writeBuffer();
    const blob = new Blob([buf], { type: 'application/octet-stream' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filenamePrefix + '-' + (datePicker.value || 'report') + '.xlsx';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  document.getElementById('btn-dl-heatmap-range').addEventListener('click', () => {
    downloadHeatmapExcel('range', rangeOrder, 'hourly-success-by-range', 'Hourly Success by Range');
  });

  document.getElementById('btn-dl-heatmap-channel').addEventListener('click', () => {
    if (!currentScope) return;
    const channels = currentScope.by_channel.map(c => c.channel);
    downloadHeatmapExcel('channel', channels, 'hourly-success-by-channel', 'Hourly Success by Channel');
  });

  // Order Number below uses payment_center_order_no (the "TW..."-prefixed
  // field) -- the closest match found to a requested "TP"-prefixed order
  // number; order_no itself is "DIZC..."-prefixed and doesn't match.
  document.getElementById('btn-dl-withdrawal-orders').addEventListener('click', () => {
    if (!currentScope) return;
    const orders = (currentScope.withdrawal_orders || []).filter(o => o.status === 'Processing');
    downloadStyledExcel(orders.map(o => ({
      'User ID': o.user_id, Agent: o.agent || 'Un-Assigned', VIP: o.vip_level, 'Withdraw Amount': o.amount, Channel: o.channel,
      'Order Number': o.payment_center_order_no || o.order_no,
      'Hrs Processing': o.hours_processing == null ? '' : o.hours_processing,
    })), 'Withdrawal Orders (Processing)', 'withdrawal-orders-processing-' + (datePicker.value || 'report') + '.xlsx');
  });

  document.getElementById('btn-dl-withdrawal-completion').addEventListener('click', () => {
    if (!currentScope) return;
    const orders = (currentScope.withdrawal_orders || []).filter(o => o.status === 'Complete');
    downloadStyledExcel(orders.map(o => ({
      'User ID': o.user_id, Agent: o.agent || 'Un-Assigned', VIP: o.vip_level, 'Withdraw Amount': o.amount, Channel: o.channel,
      'Order Number': o.payment_center_order_no || o.order_no,
      'Hrs Completed': o.waiting_hours == null ? '' : o.waiting_hours,
    })), 'Withdrawal Orders (Completed)', 'withdrawal-orders-completed-' + (datePicker.value || 'report') + '.xlsx');
  });

  document.getElementById('btn-dl-processing-backlog').addEventListener('click', () => {
    const orders = (data.withdrawal_orders_full || []).filter(o => o.status === 'Processing');
    downloadStyledExcel(orders.map(o => ({
      'User ID': o.user_id, Agent: o.agent || 'Un-Assigned', VIP: o.vip_level, 'Withdraw Amount': o.amount, Channel: o.channel,
      'Order Number': o.payment_center_order_no || o.order_no,
      'Hrs in Processing': o.hours_processing == null ? '' : o.hours_processing,
    })), 'Processing Backlog', 'processing-orders-aging.xlsx');
  });

  document.getElementById('btn-dl-inreview-backlog').addEventListener('click', () => {
    const orders = (data.withdrawal_orders_full || []).filter(o => o.status === 'In-Review');
    downloadStyledExcel(orders.map(o => ({
      'User ID': o.user_id, Agent: o.agent || 'Un-Assigned', VIP: o.vip_level, 'Withdraw Amount': o.amount, Channel: o.channel,
      'Order Number': o.payment_center_order_no || o.order_no,
      'Hrs in Review': o.hours_in_review == null ? '' : o.hours_in_review,
    })), 'In-Review Backlog', 'inreview-orders-aging.xlsx');
  });

  document.getElementById('btn-dl-last4days').addEventListener('click', () => {
    const last4 = (data.dates || []).slice(-4);
    const orders = (data.withdrawal_orders_full || []).filter(o => o.status === 'Complete' && last4.includes(o.date));
    downloadStyledExcel(orders.map(o => ({
      'User ID': o.user_id, Agent: o.agent || 'Un-Assigned', VIP: o.vip_level, 'Withdraw Amount': o.amount, Channel: o.channel,
      'Order Number': o.payment_center_order_no || o.order_no,
      'Hrs Completed': o.waiting_hours == null ? '' : o.waiting_hours,
    })), 'Last 4 Days Completed Orders', 'completed-orders-last-4-days.xlsx');
  });

  document.getElementById('btn-dl-withdrawal-amount-range').addEventListener('click', () => {
    const orders = (data.withdrawal_orders_full || []).filter(o => o.status === 'Processing');
    downloadStyledExcel(orders.map(o => ({
      'User ID': o.user_id, Agent: o.agent || 'Un-Assigned', VIP: o.vip_level, 'Withdraw Amount': o.amount, Channel: o.channel,
      'Order Number': o.payment_center_order_no || o.order_no,
      'Hrs in Processing': o.hours_processing == null ? '' : o.hours_processing,
    })), 'Processing Orders by Amount Range', 'withdrawal-processing-amount-range.xlsx');
  });

  document.querySelectorAll('#yesterday-wd-switch button').forEach(btn => {
    btn.addEventListener('click', () => {
      yesterdayWdDay = btn.dataset.day;
      document.querySelectorAll('#yesterday-wd-switch button').forEach(b => b.classList.toggle('active', b === btn));
      renderYesterdayWithdrawalRange();
    });
  });

  document.getElementById('btn-dl-yesterday-wd-range').addEventListener('click', () => {
    const rep = (data.withdrawal_amount_range_by_day || {})[yesterdayWdDay];
    if (!rep || !rep.rows) return;
    const bodyRows = rep.rows.concat([rep.totals]);
    const exportRows = bodyRows.map(row => ({
      'Amount Range': row.range,
      'Total Orders': row.total_orders, 'Total Amount': row.total_amount,
    }));
    downloadStyledExcel(exportRows, 'Withdrawal Amount Range - ' + yesterdayWdDay, 'withdrawal-amount-range-' + yesterdayWdDay + '-' + rep.date + '.xlsx');
  });

  document.getElementById('btn-dl-highest-deposit-users').addEventListener('click', () => {
    const rows = (currentScope && currentScope.top_depositors) || [];
    if (!rows.length) return;
    const exportRows = rows.map(r => ({ 'User ID': r.user_id, 'Total Deposit': r.total_deposit, 'Total Withdraw': r.total_withdraw }));
    downloadStyledExcel(exportRows, 'Highest Deposit Users', 'highest-deposit-users-' + datePicker.value + '.xlsx');
  });

  // Date picker wiring
  const dateBar = document.getElementById('date-bar');
  const datePicker = document.getElementById('date-picker');
  const btnToday = document.getElementById('btn-today');
  const dayStatus = document.getElementById('day-status');
  dateBar.style.display = 'flex';

  if (data.total_registered_users != null) {
    document.getElementById('stat-total-users').textContent = fmt(data.total_registered_users);
    document.getElementById('stat-registered-active').textContent = fmt(data.total_registered_users);
  }

  const WEEKDAYS = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];
  function selectDate(dateStr) {
    datePicker.value = dateStr;
    const isToday = dateStr === todayLocalISO();
    btnToday.classList.toggle('active', isToday);
    dayStatus.textContent = isToday ? 'TODAY' : WEEKDAYS[new Date(dateStr + 'T00:00:00').getDay()];
    dayStatus.classList.toggle('past', !isToday);
    const scope = data.by_date[dateStr] || EMPTY_SCOPE;
    render(scope, dateStr);
  }
  datePicker.addEventListener('change', () => selectDate(datePicker.value));
  btnToday.addEventListener('click', () => selectDate(todayLocalISO()));

  selectDate(todayLocalISO());
  renderBacklogCharts();
  renderYesterdayWithdrawalRange();
})();
</script>
</body>
</html>`;

// Must match slugify() in build_deposit_report.py exactly -- this is how
// the Worker maps a decoded agent name from the URL to the R2 object key
// build_deposit_report.py uploaded it under.
function slugifyAgentName(name) {
  const s = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return s || "agent";
}

// --- Server-side login wall ---
// Every route (including /data.json, /api/*) requires a valid signed
// session cookie -- previously there was no auth at all, so anyone with the
// URL could see every user's financial data. The signed cookie (HMAC-SHA256
// over an expiry timestamp, verified with the Web Crypto API) means the
// check is a single fast local computation per request -- no KV/DB lookup,
// no added latency to report loading, and no change to report content.
const LOGIN_PAGE = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in - Project 08</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f3f4f6; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
  .box { background: #fff; padding: 32px; border-radius: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); width: 320px; }
  h1 { font-size: 17px; margin: 0 0 20px; color: #1a1a1a; }
  input { width: 100%; box-sizing: border-box; padding: 11px 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; margin-bottom: 12px; }
  button { width: 100%; padding: 11px; background: #4338ca; color: #fff; border: none; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer; }
  button:hover { background: #3730a3; }
  .err { color: #991b1b; font-size: 13px; margin-bottom: 12px; }
</style>
</head>
<body>
  <div class="box">
    <h1>Project 08 &mdash; Performance &amp; Analysis</h1>
    <form method="POST" action="/login">
      __ERROR__
      <input type="password" name="password" placeholder="Password" autofocus required>
      <button type="submit">Sign in</button>
    </form>
  </div>
</body>
</html>`;

async function hmacSign(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

const SESSION_DURATION_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

// Session payload is "<expiryMs>|<encodedAgentNameOrEmpty>" -- the agent
// identity is signed INTO the cookie at login time (either via the admin
// /login password, which always yields agent="", or via a per-agent
// /agent-access link, which yields agent=<name>). Every later request is
// scoped from this server-verified value, never re-derived from the URL --
// closing the hole where an agent could edit the URL path to reach the
// full, unscoped dashboard.
async function makeSessionCookieValue(env, agentName) {
  const payload = String(Date.now() + SESSION_DURATION_MS) + "|" + (agentName ? encodeURIComponent(agentName) : "");
  const sig = await hmacSign(env.SESSION_SECRET, payload);
  return `${payload}.${sig}`;
}

// Returns null if invalid/expired, otherwise { agent: string|null } --
// agent is null for an admin session (full access), or the agent name for
// an agent session (server-enforced scoping applies to every route below).
async function verifySessionCookieValue(env, value) {
  if (!value) return null;
  const dot = value.lastIndexOf(".");
  if (dot < 0) return null;
  const payload = value.slice(0, dot);
  const sig = value.slice(dot + 1);
  if (!payload || !sig) return null;
  const barIdx = payload.indexOf("|");
  const expiryStr = barIdx < 0 ? payload : payload.slice(0, barIdx);
  const agentEncoded = barIdx < 0 ? "" : payload.slice(barIdx + 1);
  if (!expiryStr || Number(expiryStr) < Date.now()) return null;
  const expected = await hmacSign(env.SESSION_SECRET, payload);
  if (expected !== sig) return null;
  return { agent: agentEncoded ? decodeURIComponent(agentEncoded) : null };
}

// Deterministic per-agent access token -- an HMAC of the agent's name under
// the same server secret used to sign sessions, so any current or future
// agent_assignments name automatically has a valid link with no separate
// per-agent secret to generate or store.
async function agentAccessToken(env, agentName) {
  return await hmacSign(env.SESSION_SECRET, "agent-access:" + agentName);
}

// Per-agent login password: first 2 letters of the agent's name (letters
// only, ignoring any "(WFH)"/"(SL)" tag) + "0987", e.g. "Amar (WFH)" ->
// "AM0987". Auto-bumps to 3 letters for any agent whose 2-letter prefix
// collides with another agent's (e.g. "Sahana (SL)"/"Sathya (WFH)" both
// start "SA" -> "SAH0987"/"SAT0987"), so two different agents never end up
// with the same password. Computed fresh from the current agent list on
// every login/admin-links request -- nothing stored, so it stays correct
// automatically as agents are added, renamed, or removed.
function agentNameLetters(name) {
  return name.split("(")[0].replace(/[^a-zA-Z]/g, "").toUpperCase();
}

function computeAgentPasswords(agentNames) {
  const withLetters = agentNames.map(n => ({ name: n, letters: agentNameLetters(n) }));
  const byPrefix2 = new Map();
  for (const a of withLetters) {
    const p = a.letters.slice(0, 2);
    if (!byPrefix2.has(p)) byPrefix2.set(p, []);
    byPrefix2.get(p).push(a);
  }
  const passwordToAgent = new Map();
  const agentToPassword = new Map();
  for (const a of withLetters) {
    const p2 = a.letters.slice(0, 2);
    const collides = byPrefix2.get(p2).length > 1;
    const prefix = collides ? a.letters.slice(0, 3) : p2;
    const password = prefix + "0987";
    passwordToAgent.set(password, a.name);
    agentToPassword.set(a.name, password);
  }
  return { passwordToAgent, agentToPassword };
}

// Admin-set custom passwords (from the upload page's Agent Logins section)
// live in a small R2 object as { "Agent Name": "CUSTOMPASS", ... } and
// REPLACE that agent's default formula-based password entirely -- once
// changed, the old default stops working. Written by the upload worker's
// /set-agent-password; read here and by /admin/agent-links.
async function applyAgentPasswordOverrides(env, names, passwordToAgent, agentToPassword) {
  const overridesObj = await env.USERLIST_BUCKET.get("config/agent_password_overrides.json");
  if (!overridesObj) return;
  const overrides = await overridesObj.json();
  for (const [agentName, customPassword] of Object.entries(overrides)) {
    if (!names.includes(agentName) || !customPassword) continue;
    const stale = [];
    for (const [pw, name] of passwordToAgent) if (name === agentName) stale.push(pw);
    for (const pw of stale) passwordToAgent.delete(pw);
    const upper = customPassword.toUpperCase();
    passwordToAgent.set(upper, agentName);
    agentToPassword.set(agentName, upper);
  }
}

function getCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  const match = header.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/login") {
      return new Response(LOGIN_PAGE.replace("__ERROR__", ""), {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    if (request.method === "POST" && url.pathname === "/login") {
      const form = await request.formData();
      const submitted = (form.get("password") || "").toString();

      if (submitted === env.DASHBOARD_PASSWORD) {
        const cookieValue = await makeSessionCookieValue(env, null);
        return new Response(null, {
          status: 302,
          headers: {
            "Location": "/",
            "Set-Cookie": `session=${encodeURIComponent(cookieValue)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_DURATION_MS / 1000}`,
          },
        });
      }

      // Not the admin password -- check it against the per-agent password
      // scheme (see computeAgentPasswords). Case-insensitive since agents
      // may type lowercase.
      const listObj = await env.USERLIST_BUCKET.get("reports/agent_list.json");
      if (listObj) {
        const listData = await listObj.json();
        const names = (listData.agent_list || []).filter(n => n && n !== "Un-Assigned");
        const { passwordToAgent, agentToPassword } = computeAgentPasswords(names);
        await applyAgentPasswordOverrides(env, names, passwordToAgent, agentToPassword);
        const matchedAgent = passwordToAgent.get(submitted.toUpperCase());
        if (matchedAgent) {
          const cookieValue = await makeSessionCookieValue(env, matchedAgent);
          return new Response(null, {
            status: 302,
            headers: {
              "Location": "/agent/" + encodeURIComponent(matchedAgent),
              "Set-Cookie": `session=${encodeURIComponent(cookieValue)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_DURATION_MS / 1000}`,
            },
          });
        }
      }

      return new Response(LOGIN_PAGE.replace("__ERROR__", '<div class="err">Incorrect password</div>'), {
        status: 401,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    // Per-agent login link: /agent-access?name=<agent>&token=<hmac>. Visiting
    // this (bookmarked, given privately to that agent) is the ONLY way to
    // get an agent-scoped session -- the shared admin password no longer
    // grants agent access, only a full admin session. The token is
    // deterministic per agent name (see agentAccessToken), so no separate
    // per-agent secret needs to be generated or stored anywhere.
    if (request.method === "GET" && url.pathname === "/agent-access") {
      const name = url.searchParams.get("name");
      const token = url.searchParams.get("token");
      if (!name || !token) {
        return new Response("Missing name or token.", { status: 400 });
      }
      const expected = await agentAccessToken(env, name);
      if (token !== expected) {
        return new Response("Invalid access link. Contact your admin for a new link.", { status: 403 });
      }
      const cookieValue = await makeSessionCookieValue(env, name);
      return new Response(null, {
        status: 302,
        headers: {
          "Location": "/agent/" + encodeURIComponent(name),
          "Set-Cookie": `session=${encodeURIComponent(cookieValue)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_DURATION_MS / 1000}`,
        },
      });
    }

    const session = await verifySessionCookieValue(env, getCookie(request, "session"));
    if (!session) {
      if (url.pathname.startsWith("/api/") || url.pathname === "/data.json") {
        return new Response(JSON.stringify({ error: "Not authenticated" }), {
          status: 401,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(LOGIN_PAGE.replace("__ERROR__", ""), {
        status: 401,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    // Per-agent dashboards: /agent/<name>(/action-center|analytics|search-user)?
    // -- the name is URL-encoded so decodeURIComponent recovers the exact
    // agent_assignments value client-side, with no lookup table needed.
    // Performance and Platform Analysis are never agent-scoped (no
    // /agent/<name>/performance or /agent/<name>/platform-analysis route).
    const agentPageMatch = url.pathname.match(/^\/agent\/([^/]+)(\/(action-center|analytics|search-user))?\/?$/);
    const sessionAgent = session.agent; // null = admin session, full access

    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/action-center" || url.pathname === "/performance" || url.pathname === "/analytics" || url.pathname === "/platform-analysis" || url.pathname === "/search-user" || agentPageMatch)) {
      if (sessionAgent) {
        // An agent session may ONLY render its own /agent/<name>... pages,
        // plus the shared (unscoped) /performance page -- everything else,
        // including bare "/" and any OTHER agent's /agent/<other> URL, gets
        // redirected back to their own page. This is what actually closes
        // the "strip /agent/<name> from the URL" hole: the redirect target
        // comes from the signed session, never from the requested URL.
        const ownPage = agentPageMatch && decodeURIComponent(agentPageMatch[1]) === sessionAgent;
        const sharedPerformance = url.pathname === "/performance";
        if (!ownPage && !sharedPerformance) {
          return new Response(null, { status: 302, headers: { "Location": "/agent/" + encodeURIComponent(sessionAgent) } });
        }
      }
      return new Response(PAGE, { headers: { "content-type": "text/html; charset=utf-8" } });
    }

    if (request.method === "GET" && url.pathname === "/data.json") {
      // Agent-scoped pages fetch /data.json TWICE and merge the results:
      // once bare (for shared structural fields like amount_ranges, dates,
      // agent_list -- fields that live only in the full report) and once
      // with ?agent=<name> (for that agent's own precomputed aggregates,
      // in reports/agent/<slug>.json). Only the SECOND kind is forced to
      // the session's own agent here -- forcing it on the bare request too
      // (an earlier version of this fix did) breaks that merge, since the
      // small per-agent file doesn't have those structural fields at all.
      //
      // The full report itself is NOT filtered server-side for a bare
      // request from an agent session: at 100MB+ it can't be safely
      // parsed and re-filtered in a Worker (confirmed via an actual OOM
      // crash on a similar endpoint -- see /admin/agent-links). The actual
      // security boundary for agent sessions is enforced at the PAGE level
      // (redirected to their own /agent/<name>, never shown the full
      // dashboard UI) and at the ?agent= parameter here, not at the raw
      // bare-JSON layer -- an agent deliberately opening devtools/curl
      // could still pull the full report this way. Closing that fully
      // would need the pipeline to also publish a "safe global" file with
      // sensitive per-agent rows stripped, which is a real follow-up, not
      // something to improvise while this was actively broken.
      const requestedAgentParam = url.searchParams.get("agent");
      const agentParam = requestedAgentParam ? (sessionAgent || requestedAgentParam) : null;
      const key = agentParam ? `reports/agent/${slugifyAgentName(agentParam)}.json` : "reports/deposit_report.json";
      const obj = await env.USERLIST_BUCKET.get(key);
      if (!obj) {
        return new Response(JSON.stringify({ error: agentParam ? "Agent report not generated yet" : "Report not generated yet" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(obj.body, {
        headers: { "content-type": "application/json", "cache-control": "public, max-age=60" },
      });
    }

    // Platform Analysis-only data, split out of the main report so every
    // OTHER page doesn't have to download it (see build_deposit_report.py's
    // platform_analysis_extra for why). No agent-scoping needed here --
    // Platform Analysis is admin-only, enforced at the page level above.
    if (request.method === "GET" && url.pathname === "/api/platform-analysis.json") {
      const obj = await env.USERLIST_BUCKET.get("reports/platform_analysis.json");
      if (!obj) {
        return new Response(JSON.stringify({ error: "Report not generated yet" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(obj.body, {
        headers: { "content-type": "application/json", "cache-control": "public, max-age=60" },
      });
    }

    // A 224MB+ SQLite file can't practically be queried per-request from a
    // Worker -- build_and_upload_user_search_index (build_deposit_report.py)
    // precomputes 40 small JSON shards every pipeline run instead, so a
    // search here is just one cheap R2 GET (shard = user_id % 40).
    if (request.method === "GET" && url.pathname === "/api/user-search") {
      const userIdParam = url.searchParams.get("user_id");
      const userId = parseInt(userIdParam, 10);
      if (!userIdParam || Number.isNaN(userId)) {
        return new Response(JSON.stringify({ error: "user_id must be a number" }), {
          status: 400,
          headers: { "content-type": "application/json" },
        });
      }
      const shard = ((userId % 40) + 40) % 40;
      const key = `user_search/shard_${String(shard).padStart(2, "0")}.json`;
      const obj = await env.USERLIST_BUCKET.get(key);
      if (!obj) {
        return new Response(JSON.stringify({ error: "Search index not built yet" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        });
      }
      const shardData = await obj.json();
      const profile = shardData[String(userId)];
      // An agent session can only look up its own users -- same "not found"
      // response either way so this doesn't leak whether a given user_id
      // exists under a different agent.
      if (!profile || (sessionAgent && profile.agent !== sessionAgent)) {
        return new Response(JSON.stringify({ error: "User not found" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(JSON.stringify(profile), {
        headers: { "content-type": "application/json", "cache-control": "no-store" },
      });
    }

    if (request.method === "GET" && url.pathname === "/api/analytics-history") {
      const date = url.searchParams.get("date");
      if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        return new Response(JSON.stringify({ error: "date must be YYYY-MM-DD" }), {
          status: 400,
          headers: { "content-type": "application/json" },
        });
      }
      // Past-date snapshots are immutable once written (see build_deposit_report.py,
      // only "today"'s object is overwritten each pipeline run) -- cache them at the
      // edge for a full day so repeat/other-user requests skip the R2 round-trip
      // entirely. Today's snapshot still refreshes hourly, so it gets a short TTL.
      const edgeCache = caches.default;
      const cacheKey = new Request(url.toString(), request);
      const cached = await edgeCache.match(cacheKey);
      if (cached) return cached;

      const obj = await env.USERLIST_BUCKET.get(`reports/analytics_history/${date}.json`);
      if (!obj) {
        return new Response(JSON.stringify({ error: "No snapshot for this date" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        });
      }
      const isToday = date === new Date().toISOString().slice(0, 10);
      const maxAge = isToday ? 300 : 86400;
      const response = new Response(obj.body, {
        headers: { "content-type": "application/json", "cache-control": `public, max-age=${maxAge}` },
      });
      ctx.waitUntil(edgeCache.put(cacheKey, response.clone()));
      return response;
    }

    // Admin-only: generates every current agent's private access link,
    // computed from the same server secret /agent-access verifies against
    // -- so any agent already in agent_list (including brand-new ones from
    // the next pipeline run) automatically gets a valid link with nothing
    // to separately provision. Not linked from the UI; visit directly while
    // logged in as admin.
    if (request.method === "GET" && url.pathname === "/admin/agent-links") {
      if (sessionAgent) {
        return new Response(JSON.stringify({ error: "Admin only" }), {
          status: 403,
          headers: { "content-type": "application/json" },
        });
      }
      const listObj = await env.USERLIST_BUCKET.get("reports/agent_list.json");
      if (!listObj) {
        return new Response(JSON.stringify({ error: "Agent list not generated yet -- run the pipeline once after this deploy" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        });
      }
      const listData = await listObj.json();
      const names = (listData.agent_list || []).filter(n => n && n !== "Un-Assigned");
      const { passwordToAgent, agentToPassword } = computeAgentPasswords(names);
      await applyAgentPasswordOverrides(env, names, passwordToAgent, agentToPassword);
      const base = url.origin;
      const links = [];
      for (const name of names) {
        const token = await agentAccessToken(env, name);
        links.push({
          agent: name,
          password: agentToPassword.get(name),
          login_url: `${base}/login`,
          direct_link: `${base}/agent-access?name=${encodeURIComponent(name)}&token=${encodeURIComponent(token)}`,
        });
      }
      links.sort((a, b) => a.agent.localeCompare(b.agent));
      return new Response(JSON.stringify({ links }, null, 2), {
        headers: { "content-type": "application/json" },
      });
    }

    return new Response("Not found", { status: 404 });
  },
};
