#!/usr/bin/env python3
"""Deterministically scaffold a council CTR alignment to SI 2012/2886.

The generator deliberately emits TODO parameter records for council-local text:
those records require human selection of verbatim proof excerpts.  Paragraphs
whose numbered headings align with the default scheme become non-executable
``restates`` source relations to every output in the corresponding 2886 module.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


PACK_DIVERGENCE = re.compile(
    r"^### page-(?P<page>\d+) diverges from "
    r"uk/regulation(?:s)?/uksi/2012/2886/(?P<path>[^ ]+)"
    r" \(sim (?P<similarity>0(?:\.\d+)?)\)",
    re.MULTILINE,
)
RULE_NAME = re.compile(r"(?m)^\s{2}- name:\s*([A-Za-z0-9_]+)\s*$")
SOURCE_PATH = re.compile(
    r"uk/regulations/uksi/2012/2886/(?P<path>[^#\s\"']+)"
)


@dataclass(frozen=True)
class Page:
    number: int
    citation_path: str
    body: str


def load_pages(path: Path) -> list[Page]:
    pages: list[Page] = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row.get("kind") != "page" or not row.get("body"):
                continue
            pages.append(
                Page(
                    int(row["metadata"]["page_number"]),
                    row["citation_path"],
                    row["body"],
                )
            )
    return pages


def module_outputs(module_dir: Path) -> dict[str, list[str]]:
    outputs: dict[str, list[str]] = {}
    for yaml_path in sorted(module_dir.rglob("*.yaml")):
        if yaml_path.name.endswith(".test.yaml"):
            continue
        text = yaml_path.read_text(encoding="utf-8")
        names = RULE_NAME.findall(text)
        if not names:
            continue
        relative = yaml_path.relative_to(module_dir).with_suffix("").as_posix()
        outputs[relative] = names
    return outputs


def paragraph_paths(outputs: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in outputs:
        match = re.fullmatch(r"schedule/paragraph/(\d{1,3}[A-Z]?)", path)
        if match:
            result[match.group(1)] = path
    return result


def yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def generate(
    slug: str,
    provisions: Path,
    divergence_pack: Path,
    module_dir: Path,
    output: Path,
    report: Path,
    threshold: float,
) -> None:
    pages = load_pages(provisions)
    outputs = module_outputs(module_dir)
    numbered_paths = paragraph_paths(outputs)
    pack_text = divergence_pack.read_text(encoding="utf-8")
    divergences = {
        item.group("path"): (int(item.group("page")), float(item.group("similarity")))
        for item in PACK_DIVERGENCE.finditer(pack_text)
    }

    seen: dict[str, tuple[Page, str]] = {}
    # PDF extraction often places a heading and its numbered provision on
    # separate lines (or collapses them onto one line).  Match the operative
    # ``N.—(1)``/``N. (1)`` marker, which is stable across both layouts.
    for number in numbered_paths:
        marker = re.compile(
            rf"(?<![\d.]){re.escape(number)}\.\s*(?:—\s*)?\(\s*1\s*\)"
        )
        for page in pages:
            found = marker.search(page.body)
            if not found:
                continue
            start = max(page.body.rfind("\n", 0, found.start()) + 1, 0)
            title = " ".join(page.body[start : found.start()].split())[-180:]
            seen[number] = (page, title or f"Paragraph {number}")
            break

    matches: list[tuple[str, Page, str]] = []
    local: list[tuple[str, int, float]] = []
    for number, path in sorted(numbered_paths.items(), key=lambda pair: int(re.sub(r"\D", "", pair[0]))):
        divergent = divergences.get(path)
        if divergent:
            local.append((path, divergent[0], divergent[1]))
        elif number in seen:
            page, title = seen[number]
            matches.append((path, page, title))

    lines = [
        "format: rulespec/v1",
        "module:",
        "  proof_validation:",
        "    required: true",
        "  source_verification:",
        f"    corpus_citation_path: {pages[0].citation_path}",
        "  summary: >-",
        f"    Generated {slug} alignment skeleton against SI 2012/2886.",
        "rules:",
    ]
    for path, page, title in matches:
        for name in outputs[path]:
            lines.extend(
                [
                    f"  - name: {slug.replace('-', '_')}_{name}_restatement",
                    "    kind: source_relation",
                    "    source_relation:",
                    "      type: restates",
                    f"      target: uk:regulations/uksi/2012/2886/{path}#{name}",
                    f"    source: {yaml_quote(title)}",
                    "    metadata:",
                    "      match:",
                    f"        corpus_citation_path: {page.citation_path}",
                    "",
                ]
            )
    for index, (path, page, similarity) in enumerate(local, 1):
        lines.extend(
            [
                f"  - name: TODO_{slug.replace('-', '_')}_local_parameter_{index}",
                "    kind: parameter",
                "    dtype: Number",
                f"    source: 'TODO: council-local divergence from SI 2012/2886/{path}'",
                "    metadata:",
                "      todo:",
                f"        corpus_citation_path: uk-{slug}/manual/council-tax-reduction-scheme-2026-2027/page-{page}",
                f"        pack_similarity: {similarity:.2f}",
                "    versions:",
                "      - effective_from: '2026-04-01'",
                "        formula: |-\n          0",
                "",
            ]
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    total = len(matches) + len(local)
    report.write_text(
        "\n".join(
            [
                f"council: {slug}",
                f"similarity_threshold: {threshold:.2f}",
                f"matched_paragraphs: {len(matches)}",
                f"unmatched_local_paragraphs: {len(local)}",
                f"match_rate: {(100 * len(matches) / total if total else 0):.2f}%",
                "method: numbered-heading alignment, excluding divergence-pack paths",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("council_slug")
    parser.add_argument("provisions_jsonl", type=Path)
    parser.add_argument("divergence_pack", type=Path)
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--threshold", type=float, default=0.90)
    args = parser.parse_args()
    output = args.output or Path(f"uk-{args.council_slug}/policies/{args.council_slug}/council-tax-reduction.yaml")
    report = args.report or Path(f"{args.council_slug}-restates-match-report.txt")
    generate(
        args.council_slug,
        args.provisions_jsonl,
        args.divergence_pack,
        args.module_dir,
        output,
        report,
        args.threshold,
    )


if __name__ == "__main__":
    main()
