"""The /roadmap and /architecture pages: they must show only what the project's files support."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ROADMAP = json.loads((ROOT / "frontend/static/data/roadmap.json").read_text(encoding="utf-8"))
ARCH = json.loads((ROOT / "frontend/static/data/architecture.json").read_text(encoding="utf-8"))


def register_status() -> dict[str, str]:
    """Independent re-parse of the evidence register (the generator is Node; this is a second implementation)."""
    rows = {}
    for line in (ROOT / "docs/project/EVIDENCE_REGISTER.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 4 and re.fullmatch(r"E-\d{3}", cells[0]):
            rows[cells[0]] = cells[3]
    return rows


def open_decisions() -> set[str]:
    text = (ROOT / "docs/project/DECISIONS.md").read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"^## (D-\d+) .* — OPEN", text, re.M)}


# ------------------------------------------------------------------ roadmap
def test_roadmap_page_renders_every_phase_with_its_status(client):
    r = client.get("/roadmap")
    assert r.status_code == 200
    for p in ROADMAP["phases"]:
        assert f'id="phase-{p["number"]}"' in r.text
        assert p["title"] in r.text
    assert "How these statuses are computed" in r.text


def test_roadmap_uses_all_four_status_words_only_as_computed(client):
    html = client.get("/roadmap").text
    for p in ROADMAP["phases"]:
        # the node for each phase carries exactly its computed label
        node = re.search(rf'data-phase="{p["number"]}">.*?<span class="node-status">([^<]+)</span>', html, re.S)
        assert node and node.group(1) == p["statusLabel"]


def test_roadmap_numbers_match_the_evidence_register(client):
    reg = register_status()
    local = [s for k, s in reg.items() if int(k[2:]) >= 15]
    aws = [s for k, s in reg.items() if int(k[2:]) < 15]
    summary = ROADMAP["summary"]
    assert summary["local"]["total"] == len(local) and summary["local"]["verified"] == local.count("VERIFIED")
    assert summary["aws"]["total"] == len(aws) and summary["aws"]["verified"] == aws.count("VERIFIED")
    html = client.get("/roadmap").text
    assert f'<strong>{summary["aws"]["verified"]} of {summary["aws"]["total"]}</strong> claims verified' in html
    assert f'<strong>{summary["local"]["verified"]} of {summary["local"]["total"]}</strong> claims verified' in html


def test_every_task_status_follows_the_rules_from_the_register():
    """No task may be Completed without verified evidence, and verified evidence may not be hidden."""
    reg = register_status()
    blocking = open_decisions()
    authored = json.loads((ROOT / "docs/project/roadmap-phases.json").read_text(encoding="utf-8"))
    by_text = {t["text"]: t for p in authored["phases"] for t in p["tasks"]}
    for phase in ROADMAP["phases"]:
        for task in phase["tasks"]:
            src = by_text[task["text"]]
            if src["kind"] == "evidence":
                states = [reg[e] for e in src["evidence"]]
                waiting = [d for d in src.get("needs", []) if d in blocking]
                if all(s == "VERIFIED" for s in states):
                    assert task["status"] == "completed", task["text"]
                elif waiting:
                    assert task["status"] == "blocked", task["text"]
                else:
                    assert task["status"] != "completed", task["text"]
            elif src["kind"] == "deliverable":
                exists = all((ROOT / f).exists() for f in src["files"])
                assert (task["status"] == "completed") == exists, task["text"]


def test_phase_status_is_derived_from_its_tasks():
    for p in ROADMAP["phases"]:
        statuses = [t["status"] for t in p["tasks"]]
        if "blocked" in statuses:
            assert p["status"] == "blocked"
        elif all(s == "completed" for s in statuses):
            assert p["status"] == "completed"
        elif any(s in ("completed", "in_progress") for s in statuses):
            assert p["status"] == "in_progress"
        else:
            assert p["status"] == "planned"


def test_no_aws_phase_is_reported_complete_while_aws_claims_are_unverified():
    reg = register_status()
    aws_verified = [k for k, s in reg.items() if int(k[2:]) < 15 and s == "VERIFIED"]
    build = next(p for p in ROADMAP["phases"] if p["id"] == "implementation")
    verify = next(p for p in ROADMAP["phases"] if p["id"] == "verification")
    if not aws_verified:
        assert build["status"] in ("planned", "blocked")
        assert verify["status"] != "completed"


def test_open_owner_decisions_are_shown_as_the_blocker(client):
    html = client.get("/roadmap").text
    for d in open_decisions():
        assert d in html


def test_roadmap_page_works_without_javascript(client):
    """All phase content is server-rendered; JavaScript only adds tabs."""
    html = client.get("/roadmap").text
    assert html.count('class="phase-panel') == len(ROADMAP["phases"])
    assert "hidden" not in re.findall(r'<article class="phase-panel[^>]*>', html)[0]


# ------------------------------------------------------------------ architecture
def test_architecture_page_carries_the_pending_label(client):
    r = client.get("/architecture")
    assert r.status_code == 200
    assert "Target Architecture — AWS Deployment Pending" in r.text
    assert "TARGET ARCHITECTURE · AWS DEPLOYMENT PENDING" in r.text       # also stamped inside the diagram
    for word in ("Deployed", "Running", "Healthy", "Verified", "Completed"):
        assert f">{word}<" not in r.text, f"architecture page must not claim '{word}'"


def test_every_component_is_drawn_and_has_a_card(client):
    html = client.get("/architecture").text
    for c in ARCH["components"]:
        assert f'data-component="{c["id"]}"' in html, c["id"]
        assert f'id="c-{c["id"]}"' in html, c["id"]
        assert c["status"] == "planned" if "status" in c else True
    assert html.count("chip-planned") >= len(ARCH["components"])


def test_every_flow_edge_and_focus_target_exists_in_the_diagram(client):
    html = client.get("/architecture").text
    ids = {c["id"] for c in ARCH["components"]}
    for flow in ARCH["flows"]:
        assert flow["steps"], flow["id"]
        for step in flow["steps"]:
            assert step["focus"] and set(step["focus"]) <= ids, (flow["id"], step["label"])
            for edge in step["edges"]:
                assert f'id="{edge["id"]}"' in html, edge["id"]


def test_architecture_data_agrees_with_the_documentation():
    doc = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    for zone in ARCH["zones"]:
        for cidr in zone.get("cidrs", []):
            assert cidr in doc, f"{cidr} missing from docs/architecture.md"
        if zone.get("sg"):
            assert zone["sg"] in doc
    for port in ("80", "8080", "3306", "443"):
        assert port in doc
    for c in ARCH["components"]:
        for d in c["decisions"]:
            assert re.search(rf"^## {d} ", (ROOT / "docs/project/DECISIONS.md").read_text(encoding="utf-8"), re.M), d
        for e in c["evidence"]:
            assert e in register_status(), e


def test_architecture_page_is_complete_without_javascript(client):
    html = client.get("/architecture").text
    assert "Trust zones" in html and "The four flows, step by step" in html
    assert html.count('class="component-card"') == len(ARCH["components"])
    for flow in ARCH["flows"]:
        assert flow["title"] in html
        for step in flow["steps"]:
            assert step["label"] in html


def test_new_pages_load_their_own_assets_and_data(client):
    for path in ["/static/css/engineering.css", "/static/js/roadmap.js", "/static/js/architecture.js",
                 "/static/data/roadmap.json", "/static/data/architecture.json"]:
        assert client.get(path).status_code == 200, path


def test_pages_are_linked_from_the_site(client):
    home = client.get("/").text
    assert 'href="/architecture"' in home and 'href="/roadmap"' in home


@pytest.mark.parametrize("path", ["/roadmap", "/architecture"])
def test_new_pages_keep_the_security_headers(client, path):
    h = client.get(path).headers
    assert "script-src 'self'" in h["content-security-policy"] and h["x-frame-options"] == "DENY"
