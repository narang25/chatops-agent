"""Fetch real public SRE postmortems and official troubleshooting docs into data/external/.

Targets:
  - Live failure stories linked from https://k8s.af/
  - Official Kubernetes debug/troubleshooting docs (CC BY 4.0)
  - Official Prometheus docs (Apache-2.0)
  - Official PostgreSQL docs (PostgreSQL License)
  - Official Docker docs (Apache-2.0)

Stores concise structured summaries with exact source_url, source_type, and license
(never full-page copies and never synthetic LLM-padded docs).
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXTERNAL_DIR = PROJECT_ROOT / "data" / "external"
EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

OFFICIAL_DOC_SOURCES: list[tuple[str, str, str]] = [
    # Kubernetes official troubleshooting & lifecycle docs
    ("https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/debug/debug-application/debug-init-containers/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/debug/debug-application/determine-reason-pod-failure/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-usage-monitoring/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/debug/debug-cluster/crictl/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/administer-cluster/out-of-resource/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/", "external_doc", "CC BY 4.0"),
    # Prometheus official docs
    ("https://prometheus.io/docs/prometheus/latest/getting_started/", "external_doc", "Apache-2.0"),
    ("https://prometheus.io/docs/prometheus/latest/storage/", "external_doc", "Apache-2.0"),
    ("https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/", "external_doc", "Apache-2.0"),
    ("https://prometheus.io/docs/prometheus/latest/querying/basics/", "external_doc", "Apache-2.0"),
    ("https://prometheus.io/docs/practices/instrumentation/", "external_doc", "Apache-2.0"),
    ("https://prometheus.io/docs/practices/alerting/", "external_doc", "Apache-2.0"),
    ("https://prometheus.io/docs/alerting/latest/alertmanager/", "external_doc", "Apache-2.0"),
    # PostgreSQL official docs
    ("https://www.postgresql.org/docs/current/runtime-config-connection.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/runtime-config-resource.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/explicit-locking.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/routine-vacuuming.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/wal-configuration.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/monitoring-stats.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/errcodes-appendix.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/auth-pg-hba-conf.html", "external_doc", "PostgreSQL License"),
    # Docker official docs
    ("https://docs.docker.com/engine/containers/resource_constraints/", "external_doc", "Apache-2.0"),
    ("https://docs.docker.com/engine/containers/start-containers-automatically/", "external_doc", "Apache-2.0"),
    ("https://docs.docker.com/engine/logging/configure/", "external_doc", "Apache-2.0"),
    ("https://docs.docker.com/engine/network/", "external_doc", "Apache-2.0"),
    ("https://docs.docker.com/engine/storage/overlayfs/", "external_doc", "Apache-2.0"),
    ("https://docs.docker.com/compose/how-tos/startup-order/", "external_doc", "Apache-2.0"),
    ("https://docs.docker.com/reference/dockerfile/", "external_doc", "Apache-2.0"),
    # Additional official Kubernetes / Prometheus / Postgres troubleshooting docs
    ("https://kubernetes.io/docs/concepts/workloads/controllers/deployment/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/services-networking/ingress/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/concepts/storage/persistent-volumes/", "external_doc", "CC BY 4.0"),
    ("https://kubernetes.io/docs/tasks/debug/debug-cluster/", "external_doc", "CC BY 4.0"),
    ("https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/", "external_doc", "Apache-2.0"),
    ("https://prometheus.io/docs/prometheus/latest/querying/operators/", "external_doc", "Apache-2.0"),
    ("https://www.postgresql.org/docs/current/high-availability.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/runtime-config-locks.html", "external_doc", "PostgreSQL License"),
    ("https://www.postgresql.org/docs/current/mvcc-intro.html", "external_doc", "PostgreSQL License"),
]

_BOILERPLATE_SNIPPETS = (
    "i'm gordon",
    "your ai assistant for docker",
    "reached the maximum of questions",
    "when enabled, gordon considers",
    "personal blog covering",
    "llm-generated content is being restricted",
    "sign in",
    "cookie policy",
    "accept all cookies",
)

_BLOCKED_DOMAINS = (
    "youtube.com",
    "youtu.be",
    ".pdf",
    "slideshare.net",
    "github.com/hjacobs",
    "codeberg.org",
    "twitter.com",
    "x.com",
    "srcco.de",
    "adammargherio.com",
)


class _ArticleExtractor(HTMLParser):
    """Lightweight HTML parser extracting <title> and readable body paragraphs."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self._in_block = False
        self.title_parts: list[str] = []
        self.blocks: list[str] = []
        self._cur_block: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in ("script", "style", "noscript", "nav", "footer", "aside", "svg"):
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if t == "title":
            self._in_title = True
        elif t in ("p", "h1", "h2", "h3", "li"):
            self._in_block = True
            self._cur_block = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("script", "style", "noscript", "nav", "footer", "aside", "svg"):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth > 0:
            return
        if t == "title":
            self._in_title = False
        elif t in ("p", "h1", "h2", "h3", "li") and self._in_block:
            txt = " ".join("".join(self._cur_block).split())
            low = txt.lower()
            if len(txt) > 35 and not any(b in low for b in _BOILERPLATE_SNIPPETS):
                self.blocks.append(txt)
            self._in_block = False
            self._cur_block = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title_parts.append(data)
        elif self._in_block:
            self._cur_block.append(data)


def _slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "doc"


def _infer_failure_type(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("oomkilled", "out of memory", "memory limit", "oom")):
        return "out_of_memory"
    if any(k in low for k in ("crashloop", "crash loop", "exit code 1", "restart")):
        return "crash_loop"
    if any(k in low for k in ("no space left", "disk full", "eviction", "storage", "wal")):
        return "disk_full"
    if any(k in low for k in ("timeout", "latency", "conntrack", "dns", "network")):
        return "network_timeout"
    if any(k in low for k in ("cpu limit", "throttl", "cpu")):
        return "cpu_saturation"
    if any(k in low for k in ("502", "500", "5xx", "error rate")):
        return "high_error_rate"
    if any(k in low for k in ("liveness", "readiness", "health check", "probe")):
        return "health_check_failure"
    if any(k in low for k in ("config", "environment", "auth", "permission")):
        return "bad_config"
    return "other"


def _collect_k8s_af_urls(client: httpx.Client) -> list[tuple[str, str, str]]:
    """Collect real failure-story URLs from https://k8s.af/."""
    resp = client.get("https://k8s.af/", timeout=12.0)
    resp.raise_for_status()
    hrefs = re.findall(r'href=["\']([^"\'#]+)["\']', resp.text)
    results: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for url in hrefs:
        if not url.startswith("http"):
            continue
        if any(skip in url.lower() for skip in _BLOCKED_DOMAINS):
            continue
        if url not in seen:
            seen.add(url)
            results.append((url, "external_postmortem", "Public Postmortem Summary"))
    return results


def _existing_urls() -> set[str]:
    urls: set[str] = set()
    for md in EXTERNAL_DIR.glob("*.md"):
        txt = md.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"source_url:\s*(.+)", txt)
        if m:
            urls.add(m.group(1).strip().strip('"').strip("'"))
    return urls


def fetch_and_save(target_new: int = 55) -> list[Path]:
    client = httpx.Client(
        follow_redirects=True,
        timeout=10.0,
        headers={"User-Agent": "ChatOps-SRE-Agent-Academic/1.0"},
    )
    existing = _existing_urls()
    candidates = list(OFFICIAL_DOC_SOURCES)
    try:
        candidates.extend(_collect_k8s_af_urls(client))
    except Exception as exc:
        print(f"Warning: could not fetch k8s.af index: {exc}")

    created: list[Path] = []
    for url, source_type, license_str in candidates:
        if len(created) >= target_new:
            break
        if url in existing:
            continue
        try:
            resp = client.get(url)
            if resp.status_code != 200:
                continue
            ctype = resp.headers.get("content-type", "").lower()
            if "html" not in ctype and "text" not in ctype and "markdown" not in ctype:
                continue

            parser = _ArticleExtractor()
            parser.feed(resp.text)
            raw_title = html.unescape("".join(parser.title_parts)).strip()
            raw_title = re.sub(r"\s*[|\-–—]\s*(Kubernetes|Prometheus|Docker|PostgreSQL).*$", "", raw_title).strip()
            if not raw_title or len(raw_title) < 6 or any(b in raw_title.lower() for b in ("403", "404", "just a moment", "cloudflare")):
                continue

            summary_blocks = parser.blocks[:6]
            summary_text = "\n\n".join(summary_blocks)[:1600].strip()
            if len(summary_text) < 120:
                continue

            domain_tag = _slugify(urlparse(url).netloc.replace("www.", ""), 16)
            title_slug = _slugify(raw_title, 36)
            filename = f"fetched-{domain_tag}-{title_slug}.md"
            out_path = EXTERNAL_DIR / filename
            if out_path.exists():
                continue

            ft = _infer_failure_type(raw_title + " " + summary_text)
            safe_title = raw_title.replace('"', "'")
            md_body = (
                f"---\n"
                f'title: "{safe_title}"\n'
                f"failure_type: {ft}\n"
                f"source_type: {source_type}\n"
                f"source_url: {url}\n"
                f"license: {license_str}\n"
                f"status: external\n"
                f"---\n\n"
                f"## Summary\n"
                f"{summary_text}\n\n"
                f"## Reference\n"
                f"Full article / official documentation: {url}\n"
            )
            out_path.write_text(md_body, encoding="utf-8")
            created.append(out_path)
            existing.add(url)
            print(f"  [{len(created):2d}] Saved {filename} ({source_type}, {ft})")
        except Exception:
            continue

    return created


if __name__ == "__main__":
    print(f"Existing external docs: {len(list(EXTERNAL_DIR.glob('*.md')))}")
    saved = fetch_and_save(target_new=55)
    print(f"Newly fetched external docs: {len(saved)}")
    print(f"Total external docs now: {len(list(EXTERNAL_DIR.glob('*.md')))}")

