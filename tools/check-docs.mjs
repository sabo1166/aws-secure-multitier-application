// Documentation consistency checks. Run: node tools/check-docs.mjs
// Uses only Node built-ins. Exits 1 if any check fails.
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, dirname, resolve, relative, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const STATUSES = ['PLANNED', 'IN PROGRESS', 'IMPLEMENTED', 'VERIFIED', 'FAILED', 'BLOCKED'];
const failures = [];
const notes = [];
const fail = (check, msg) => failures.push(`[${check}] ${msg}`);

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    if (['node_modules', '.git', '.venv', '__pycache__', '.pytest_cache'].includes(name)) continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      if (relative(ROOT, p).replaceAll('\\', '/') === 'evidence/raw') continue;
      out.push(...walk(p));
    } else out.push(p);
  }
  return out;
}

const files = walk(ROOT);
const mdFiles = files.filter((f) => extname(f) === '.md');
const rel = (f) => relative(ROOT, f).replaceAll('\\', '/');
const read = (f) => readFileSync(f, 'utf8');
const stripFences = (t) => t.replace(/^```[\s\S]*?^```/gm, '');

const slug = (h) =>
  h.trim().toLowerCase().replace(/[`*_]/g, '').replace(/[^\w\- ]/g, '').replace(/ /g, '-');

// 1. Relative links and anchors
let linkCount = 0;
for (const f of mdFiles) {
  const text = stripFences(read(f)).replace(/`[^`\n]*`/g, '');
  for (const m of text.matchAll(/\[[^\]]*\]\(([^)\s]+)\)/g)) {
    const target = m[1];
    if (/^(https?:|mailto:)/.test(target)) continue;
    linkCount++;
    const [pathPart, anchor] = target.split('#');
    const dest = pathPart ? resolve(dirname(f), pathPart) : f;
    if (!existsSync(dest)) {
      fail('links', `${rel(f)}: broken link -> ${target}`);
      continue;
    }
    if (anchor && extname(dest) === '.md') {
      const heads = [...stripFences(read(dest)).matchAll(/^#{1,6}\s+(.+)$/gm)].map((h) => slug(h[1]));
      if (!heads.includes(anchor)) fail('links', `${rel(f)}: missing anchor #${anchor} in ${rel(dest)}`);
    }
  }
}
notes.push(`links checked: ${linkCount}`);

// 2. Mermaid fences: closed, known type, balanced brackets, subgraph/end balance
let diagrams = 0;
for (const f of mdFiles) {
  const text = read(f);
  const opens = (text.match(/^```mermaid\s*$/gm) || []).length;
  const blocks = [...text.matchAll(/^```mermaid\s*\n([\s\S]*?)^```\s*$/gm)];
  if (opens !== blocks.length) fail('mermaid', `${rel(f)}: unclosed mermaid fence`);
  for (const b of blocks) {
    diagrams++;
    const body = b[1];
    const first = body.trim().split('\n')[0];
    if (!/^(flowchart|graph|sequenceDiagram|classDiagram|erDiagram)\b/.test(first))
      fail('mermaid', `${rel(f)}: unknown diagram type "${first}"`);
    for (const [o, c] of [['[', ']'], ['(', ')'], ['{', '}']]) {
      const no = body.split(o).length - 1;
      const nc = body.split(c).length - 1;
      if (no !== nc) fail('mermaid', `${rel(f)}: unbalanced ${o}${c} (${no} vs ${nc})`);
    }
    const sg = (body.match(/^\s*subgraph\b/gm) || []).length;
    const en = (body.match(/^\s*end\s*$/gm) || []).length;
    if (sg !== en) fail('mermaid', `${rel(f)}: subgraph/end mismatch (${sg} vs ${en})`);
  }
}
notes.push(`mermaid diagrams checked (structure only, not rendered): ${diagrams}`);

// Table helper: rows of a markdown table whose header starts with the given first column
function tableRows(file, firstCol) {
  const lines = read(file).split('\n');
  const start = lines.findIndex((l) => l.startsWith('|') && l.split('|')[1].trim() === firstCol);
  if (start < 0) return [];
  const header = lines[start].split('|').slice(1, -1).map((c) => c.trim());
  const rows = [];
  for (let i = start + 2; i < lines.length && lines[i].startsWith('|'); i++) {
    const cells = lines[i].split('|').slice(1, -1).map((c) => c.trim());
    rows.push(Object.fromEntries(header.map((h, k) => [h, cells[k] ?? ''])));
  }
  return rows;
}

// 3. Evidence register rules
const reg = tableRows(join(ROOT, 'docs', 'project', 'EVIDENCE_REGISTER.md'), 'ID');
const regById = new Map();
for (const r of reg) {
  regById.set(r.ID, r);
  if (!STATUSES.includes(r.Status)) fail('register', `${r.ID}: invalid status "${r.Status}"`);
  const paths = [...r['Evidence files'].matchAll(/`([^`]+)`/g)].map((m) => m[1]);
  const needsEvidence = ['IMPLEMENTED', 'VERIFIED'].includes(r.Status);
  if (needsEvidence && paths.length === 0) fail('register', `${r.ID}: ${r.Status} without evidence files`);
  for (const p of paths) {
    if (!['evidence/redacted/', 'evidence/raw/', 'screenshots/'].some((pre) => p.startsWith(pre)))
      fail('register', `${r.ID}: evidence path must be under evidence/ or screenshots/: ${p}`);
    else if (needsEvidence && !existsSync(join(ROOT, p))) fail('register', `${r.ID}: evidence file missing: ${p}`);
  }
  if (r.Status === 'VERIFIED' && r['Missing evidence'].toLowerCase() !== 'none')
    fail('register', `${r.ID}: VERIFIED but missing evidence is "${r['Missing evidence']}"`);
  if (r.Status === 'VERIFIED' && !r['Proves']) fail('register', `${r.ID}: VERIFIED with empty Proves`);
}
notes.push(`evidence claims: ${reg.length} (${reg.filter((r) => r.Status === 'VERIFIED').length} VERIFIED)`);

// 4. Project status rules and cross-references
const cps = tableRows(join(ROOT, 'docs', 'project', 'PROJECT_STATUS.md'), 'CP');
const cpIds = new Set();
for (const c of cps) {
  cpIds.add(c.CP);
  if (!STATUSES.includes(c.Status)) fail('status', `${c.CP}: invalid status "${c.Status}"`);
  const ids = c['Evidence IDs'].split(',').map((s) => s.trim()).filter(Boolean);
  for (const id of ids) {
    if (!regById.has(id)) fail('status', `${c.CP}: unknown evidence ID ${id}`);
    else if (c.Status === 'VERIFIED' && regById.get(id).Status !== 'VERIFIED')
      fail('status', `${c.CP} is VERIFIED but ${id} is ${regById.get(id).Status}`);
  }
}
for (const r of reg) if (!cpIds.has(r.CP)) fail('register', `${r.ID}: unknown checkpoint ${r.CP}`);
for (const r of reg) {
  const owners = cps.filter((c) => c['Evidence IDs'].split(',').map((s) => s.trim()).includes(r.ID));
  if (owners.length === 0) fail('status', `${r.ID} is not listed under any checkpoint in docs/project/PROJECT_STATUS.md`);
}

// 5. Every E-xxx / CPn / D-xxx reference in prose must exist
const decisions = new Set([...read(join(ROOT, 'docs', 'project', 'DECISIONS.md')).matchAll(/^## (D-\d+)/gm)].map((m) => m[1]));
const placeholderOk = new Set();
for (const f of mdFiles) {
  const text = read(f);
  for (const m of text.matchAll(/\bE-\d{3}\b/g)) if (!regById.has(m[0]) && !/E-<id>/.test(m[0]))
    fail('refs', `${rel(f)}: unknown evidence ID ${m[0]}`);
  for (const m of text.matchAll(/\bD-\d{3}\b/g))
    if (!decisions.has(m[0]) && !placeholderOk.has(m[0])) fail('refs', `${rel(f)}: unknown decision ${m[0]}`);
  for (const m of text.matchAll(/\bCP\d+\b/g)) if (!cpIds.has(m[0])) fail('refs', `${rel(f)}: unknown checkpoint ${m[0]}`);
}

// 6. Runbooks: nine required sections present
const REQUIRED = [
  /^## 1\. Objective/m, /^## 2\. Console navigation/m, /^## 3\. Configuration/m,
  /^## 4\. Security and cost/m, /^## 5\. Expected result/m, /^## 6\. Verification/m,
  /^## 7\. Evidence/m, /^## 8\. Common failures/m, /^## 9\. Gate/m,
];
const runbooks = mdFiles.filter((f) => /docs\/checkpoints\/CP\d/.test(rel(f)));
for (const f of runbooks) {
  REQUIRED.forEach((re, i) => { if (!re.test(read(f))) fail('runbook', `${rel(f)}: missing section ${i + 1}`); });
  const m = rel(f).match(/CP\d/)[0];
  if (!read(f).includes(`Status: **`)) fail('runbook', `${rel(f)}: missing status line`);
  if (!cpIds.has(m)) fail('runbook', `${rel(f)}: checkpoint ${m} not in PROJECT_STATUS`);
}
notes.push(`runbooks checked: ${runbooks.length}`);

// 7. Secret / account-ID scan (markdown and text files outside evidence/raw)
const scanFiles = files.filter((f) => ['.md', '.txt', '.json', '.mjs', '.py', '.html', '.svg', '.css', '.js', '.example', '.ini'].includes(extname(f)) || f.endsWith('.env.example'));
for (const f of scanFiles) {
  const t = read(f);
  if (/\bAKIA[0-9A-Z]{16}\b/.test(t)) fail('secrets', `${rel(f)}: looks like an AWS access key ID`);
  // 000000000000 is the documented fake account ID used in tests; any other 12-digit number is suspect.
  const twelve = [...t.matchAll(/(?<![\d.\-])\d{12}(?![\d.\-])/g)].map((m) => m[0]).filter((n) => n !== '000000000000');
  if (twelve.length) fail('secrets', `${rel(f)}: contains a 12-digit number (possible account ID)`);
  const arns = [...t.matchAll(/arn:aws:[a-z0-9-]*:[a-z0-9-]*:(\d{12}):/g)].map((m) => m[1]).filter((n) => n !== '000000000000');
  if (arns.length) fail('secrets', `${rel(f)}: ARN with account ID`);
  if (/-----BEGIN [A-Z ]*PRIVATE KEY-----/.test(t)) fail('secrets', `${rel(f)}: private key material`);
}
notes.push(`secret scan files: ${scanFiles.length}`);


// 7b. Screenshots README: a CAPTURED row must point at a file that exists (no claims without evidence)
{
  const lines = read(join(ROOT, 'screenshots', 'README.md')).split('\n');
  let folder = '';
  let captured = 0;
  for (const line of lines) {
    const h = line.match(/^### (\S+)/);
    if (h) folder = h[1];
    if (!line.startsWith('|') || !folder) continue;
    const cells = line.split('|').slice(1, -1).map((c) => c.trim());
    if (cells.length < 3 || !/^CAPTURED/.test(cells[cells.length - 1])) continue;
    for (const [, name] of cells[0].matchAll(/`([^`]+)`/g)) {
      if (name.includes('*')) continue;
      captured++;
      if (!existsSync(join(ROOT, 'screenshots', folder.replace(/\s.*/, ''), name)))
        fail('screenshots', `README marks ${folder}/${name} CAPTURED but the file does not exist`);
    }
  }
  notes.push(`screenshots marked CAPTURED and present: ${captured}`);
}

// 7c. Manual-only project: no automation or infrastructure-as-code files
{
  const forbidden = [
    [/(^|\/)\.github\/workflows\//, 'GitHub Actions workflow'], [/(^|\/)Jenkinsfile$/i, 'Jenkins pipeline'],
    [/\.tf$|\.tfvars$|(^|\/)\.terraform\//, 'Terraform'], [/(^|\/)(cloudformation|template)[^/]*\.(ya?ml|json)$/i, 'CloudFormation template'],
    [/(^|\/)(Dockerfile|docker-compose[^/]*\.ya?ml)$/i, 'Docker'], [/(^|\/)(Chart\.yaml|helmfile\.ya?ml)$/i, 'Helm'],
    [/(^|\/)(k8s|kubernetes)\//i, 'Kubernetes manifests'], [/(^|\/)(buildspec|appspec)\.ya?ml$/i, 'AWS CodeBuild/CodeDeploy'],
    [/(^|\/)(\.gitlab-ci\.yml|azure-pipelines\.yml|\.circleci\/)/, 'CI pipeline'], [/(^|\/)serverless\.ya?ml$|(^|\/)template\.ya?ml$/i, 'SAM/Serverless'],
  ];
  for (const f of files) {
    const r = rel(f);
    for (const [re, label] of forbidden) if (re.test(r)) fail('automation', `${r}: ${label} file found (project is manual Console only)`);
  }
  notes.push('automation/IaC file scan: done');
}

// 7d. Files that must never exist in the repository folder
for (const f of files) {
  const r = rel(f);
  if (/(^|\/)\.env$/.test(r) || /\.pem$/.test(r) || /\.(db|sqlite)$/.test(r) || /(^|\/)id_(rsa|ed25519)/.test(r))
    fail('private-files', `${r}: must not be present (ignored by .gitignore, delete before publishing)`);
}

// 7e. Exactly one evidence register
{
  const registers = files.filter((f) => /EVIDENCE_REGISTER.*\.md$/i.test(f));
  if (registers.length !== 1) fail('register', `expected exactly one EVIDENCE_REGISTER.md, found ${registers.length}: ${registers.map(rel).join(', ')}`);
}

// 7f. Layout rules: backend/ and frontend/ are the only homes of application code; no leftover app/ package or duplicate sources
{
  if (existsSync(join(ROOT, 'app'))) fail('layout', 'an app/ folder exists; the application lives in backend/ and frontend/ (duplicate sources?)');
  for (const stray of ['backend/templates', 'backend/static', 'frontend/main.py'])
    if (existsSync(join(ROOT, stray))) fail('layout', `${stray} must not exist (templates and static files belong in frontend/, Python in backend/)`);
  const pyInFrontend = files.filter((f) => rel(f).startsWith('frontend/') && f.endsWith('.py'));
  for (const f of pyInFrontend) fail('layout', `${rel(f)}: Python file inside frontend/`);
}

// 8. Required top-level files
for (const name of ['README.md', 'CLAUDE.md', '.gitignore', '.gitattributes', '.env.example', 'requirements.txt', 'requirements-dev.txt', 'pytest.ini', 'architecture.png', 'frontend/README.md', 'frontend/templates/base.html', 'frontend/static/css/site.css', 'backend/README.md', 'backend/main.py', 'tools/README.md', 'screenshots/README.md', 'docs/README.md', 'docs/architecture.md', 'docs/implementation-guide.md', 'docs/security.md', 'docs/troubleshooting.md', 'docs/project-summary.md', 'docs/rds-setup-guide.md', 'docs/project/PROJECT_STATUS.md', 'docs/project/DECISIONS.md', 'docs/project/EVIDENCE_REGISTER.md', 'docs/project/QUALITY_REVIEW.md', 'docs/project/NEXT_STEPS.md'])
  if (!existsSync(join(ROOT, name))) fail('files', `missing ${name}`);

console.log(notes.map((n) => `  ${n}`).join('\n'));
console.log('Not performed: live-Console accuracy of menu paths, AWS-side verification, human review. (SVG diagrams are checked by viewing, not by this tool.)');
if (failures.length) {
  console.error(`\nFAILED (${failures.length}):`);
  for (const f of failures) console.error(`  ${f}`);
  process.exit(1);
}
console.log('\nOK: all documentation checks passed.');
