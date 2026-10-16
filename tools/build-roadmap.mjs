// Builds the roadmap data the website shows, from the project's own status files.
//   node tools/build-roadmap.mjs           write frontend/static/data/roadmap.json and the README progress block
//   node tools/build-roadmap.mjs --check   fail (exit 1) if either is out of date; used by check-docs.mjs
//
// Nothing here invents progress. Inputs:
//   docs/project/EVIDENCE_REGISTER.md   claim statuses (PLANNED ... VERIFIED)
//   docs/project/DECISIONS.md           decision statuses (OPEN blocks the work that needs it)
//   docs/project/PROJECT_STATUS.md      checkpoint statuses
//   docs/project/roadmap-phases.json    authored phase text and which claims, files and decisions each task depends on
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const CHECK = process.argv.includes('--check');
const read = (p) => readFileSync(join(ROOT, p), 'utf8');

function tableRows(text, firstCol) {
  const lines = text.split('\n');
  const start = lines.findIndex((l) => l.startsWith('|') && l.split('|')[1].trim() === firstCol);
  if (start < 0) throw new Error(`table starting with "${firstCol}" not found`);
  const header = lines[start].split('|').slice(1, -1).map((c) => c.trim());
  const rows = [];
  for (let i = start + 2; i < lines.length && lines[i].startsWith('|'); i++) {
    const cells = lines[i].split('|').slice(1, -1).map((c) => c.trim());
    rows.push(Object.fromEntries(header.map((h, k) => [h, cells[k] ?? ''])));
  }
  return rows;
}

const evidence = new Map(tableRows(read('docs/project/EVIDENCE_REGISTER.md'), 'ID').map((r) => [r.ID, r]));
const checkpoints = tableRows(read('docs/project/PROJECT_STATUS.md'), 'CP');
const decisions = new Map([...read('docs/project/DECISIONS.md').matchAll(/^## (D-\d+) .* — ([A-Z]+)/gm)].map((m) => [m[1], m[2]]));
const authored = JSON.parse(read('docs/project/roadmap-phases.json'));

const LABEL = { completed: 'Completed', in_progress: 'In progress', planned: 'Planned', blocked: 'Blocked' };
const fail = [];

function evidenceState(ids, implementedInCode) {
  const rows = ids.map((id) => {
    const r = evidence.get(id);
    if (!r) fail.push(`unknown evidence id ${id}`);
    return r;
  });
  const st = rows.map((r) => (r ? r.Status : 'PLANNED'));
  if (st.some((s) => s === 'BLOCKED' || s === 'FAILED')) return 'blocked';
  if (st.every((s) => s === 'VERIFIED')) return 'completed';
  if (st.some((s) => s === 'VERIFIED' || s === 'IMPLEMENTED' || s === 'IN PROGRESS') || implementedInCode) return 'in_progress';
  return 'planned';
}

function taskState(t) {
  if (t.kind === 'deliverable') {
    const missing = t.files.filter((f) => !existsSync(join(ROOT, f)));
    return { state: missing.length ? 'planned' : 'completed', refs: t.files, why: missing.length ? `missing: ${missing.join(', ')}` : 'document exists' };
  }
  if (t.kind === 'manual') return { state: t.status, refs: [], why: 'no evidence possible yet' };
  let state = evidenceState(t.evidence, !!t.implementedInCode);
  const open = (t.needs || []).filter((d) => decisions.get(d) === 'OPEN');
  let why;
  if (open.length && state !== 'completed') {
    state = 'blocked';
    why = `waiting on open decision${open.length > 1 ? 's' : ''} ${open.join(', ')}`;
  } else {
    const st = t.evidence.map((id) => `${id} ${(evidence.get(id)?.Status ?? '?').toLowerCase()}`).join(', ');
    why = (t.implementedInCode && state === 'in_progress' ? 'code written; ' : '') + st;
  }
  for (const d of t.needs || []) if (!decisions.has(d)) fail.push(`unknown decision ${d}`);
  return { state, refs: t.evidence, why };
}

const phases = authored.phases.map((p) => {
  const tasks = p.tasks.map((t) => {
    const s = taskState(t);
    return { text: t.text, status: s.state, statusLabel: LABEL[s.state], refs: s.refs, why: s.why, detail: t.detail || '' };
  });
  const c = { completed: 0, in_progress: 0, planned: 0, blocked: 0 };
  tasks.forEach((t) => c[t.status]++);
  let status = 'planned';
  if (c.blocked) status = 'blocked';
  else if (c.completed === tasks.length) status = 'completed';
  else if (c.completed || c.in_progress) status = 'in_progress';
  return {
    id: p.id, number: p.number, title: p.title, short: p.short, summary: p.summary, objective: p.objective,
    status, statusLabel: LABEL[status], counts: c, tasks, validation: p.validation, notInScope: p.notInScope,
  };
});

const count = (rows) => {
  const out = { total: rows.length, verified: 0, implemented: 0, inProgress: 0, planned: 0, blocked: 0, failed: 0 };
  for (const r of rows) {
    const k = { VERIFIED: 'verified', IMPLEMENTED: 'implemented', 'IN PROGRESS': 'inProgress', PLANNED: 'planned', BLOCKED: 'blocked', FAILED: 'failed' }[r.Status];
    out[k]++;
  }
  return out;
};
const all = [...evidence.values()];
const local = all.filter((r) => r.CP === 'CP8');
const aws = all.filter((r) => r.CP !== 'CP8');
const openDecisions = [...decisions].filter(([, s]) => s === 'OPEN').map(([d]) => d);

const data = {
  source: ['docs/project/EVIDENCE_REGISTER.md', 'docs/project/DECISIONS.md', 'docs/project/PROJECT_STATUS.md', 'docs/project/roadmap-phases.json'],
  summary: {
    evidence: count(all), local: count(local), aws: count(aws), openDecisions,
    claims: all.map((r) => ({ id: r.ID, scope: r.CP === 'CP8' ? 'local' : 'aws', cp: r.CP, status: r.Status.toLowerCase().replace(' ', '_'), claim: r.Claim })),
    checkpoints: checkpoints.map((c) => ({ id: c.CP, name: c.Name, status: c.Status })),
  },
  phases,
};
const json = JSON.stringify(data, null, 2) + '\n';

// README block
const s = data.summary;
const blockedPhase = phases.find((p) => p.status === 'blocked');
const progress = [
  '<!-- progress:start (generated by tools/build-roadmap.mjs; do not edit by hand) -->',
  `**Evidence, computed from the register:** local build ${s.local.verified} of ${s.local.total} claims verified; AWS build ${s.aws.verified} of ${s.aws.total} verified (${s.aws.planned} planned).` +
    (openDecisions.length ? ` Open decisions waiting on the owner: ${openDecisions.join(', ')}.` : ''),
  '',
  '| Phase | Status | What the status rests on |',
  '|---|---|---|',
  ...phases.map((p) => {
    const bits = [];
    if (p.counts.completed) bits.push(`${p.counts.completed} done`);
    if (p.counts.in_progress) bits.push(`${p.counts.in_progress} in progress`);
    if (p.counts.blocked) bits.push(`${p.counts.blocked} blocked`);
    if (p.counts.planned) bits.push(`${p.counts.planned} planned`);
    return `| ${p.number}. ${p.title} | ${p.statusLabel} | ${bits.join(', ')} of ${p.tasks.length} tasks |`;
  }),
  '<!-- progress:end -->',
].join('\n');

const readmePath = join(ROOT, 'README.md');
const readme = readFileSync(readmePath, 'utf8');
const re = /<!-- progress:start[\s\S]*?<!-- progress:end -->/;
if (!re.test(readme)) fail.push('README.md has no progress markers');
const newReadme = readme.replace(re, () => progress);

const jsonPath = join(ROOT, 'frontend', 'static', 'data', 'roadmap.json');
if (fail.length) { console.error('build-roadmap: ' + fail.join('; ')); process.exit(1); }

if (CHECK) {
  const stale = [];
  if (!existsSync(jsonPath) || readFileSync(jsonPath, 'utf8') !== json) stale.push('frontend/static/data/roadmap.json');
  if (readme !== newReadme) stale.push('README.md progress block');
  if (stale.length) { console.error(`roadmap data is out of date: ${stale.join(', ')}. Run: node tools/build-roadmap.mjs`); process.exit(1); }
  console.log(`roadmap data in sync (${phases.length} phases; ${s.local.verified}/${s.local.total} local and ${s.aws.verified}/${s.aws.total} AWS claims verified)`);
} else {
  mkdirSync(dirname(jsonPath), { recursive: true });
  writeFileSync(jsonPath, json);
  writeFileSync(readmePath, newReadme);
  console.log(`wrote roadmap.json and the README progress block (${phases.map((p) => `${p.number}:${p.status}`).join(' ')})`);
}
