from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HighlightCandidate:
    candidate_id: str
    text: str
    score: float
    standalone_value: float
    novelty: float
    reason: str
    source_type: str | None = None
    start: float | None = None
    end: float | None = None
    paragraph_id: str | None = None
    section_id: str | None = None

    def to_dict(self) -> dict:
        data = {
            "candidate_id": self.candidate_id,
            "text": self.text,
            "score": round(self.score, 3),
            "standalone_value": round(self.standalone_value, 3),
            "novelty": round(self.novelty, 3),
            "reason": self.reason,
            "source_type": self.source_type,
            "paragraph_id": self.paragraph_id,
            "section_id": self.section_id,
        }
        if self.start is not None and self.end is not None:
            data["start"] = round(self.start, 3)
            data["end"] = round(self.end, 3)
            data["duration"] = round(max(0.0, self.end - self.start), 3)
        else:
            data["start"] = None
            data["end"] = None
            data["duration"] = None
        return data


class HighlightMiner:
    """Mine highlights by standalone propagation value instead of uniform segmentation."""

    def run(self, cleaned_json_file: Path, output_dir: Path, source_type: str = "video") -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)

        segments = self._load_segments(cleaned_json_file)
        candidates = self._build_candidates(segments, source_type=source_type)
        round2 = self._round2_select(candidates)
        top10 = round2[:10]

        round1_file = output_dir / "candidates_round1.json"
        round2_file = output_dir / "selected_round2.json"
        final_file = output_dir / "top10_final.json"
        table_file = output_dir / "highlights_table.md"
        plan_file = output_dir / "clip_plan.csv"

        round1_file.write_text(json.dumps([c.to_dict() for c in candidates], ensure_ascii=False, indent=2), encoding="utf-8")
        round2_file.write_text(json.dumps([c.to_dict() for c in round2], ensure_ascii=False, indent=2), encoding="utf-8")
        final_file.write_text(json.dumps([c.to_dict() for c in top10], ensure_ascii=False, indent=2), encoding="utf-8")

        table_file.write_text(self._to_markdown_table(top10), encoding="utf-8")
        self._write_clip_plan_csv(top10, plan_file)

        return {
            "candidates_round1": round1_file,
            "selected_round2": round2_file,
            "top10_final": final_file,
            "highlights_table": table_file,
            "clip_plan": plan_file,
        }

    def run_from_canonical(self, source_type: str, text: str, output_dir: Path) -> dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs and text.strip():
            paragraphs = [text.strip()]
        segments = [
            {"text": para, "paragraph_id": f"p{idx:03d}"}
            for idx, para in enumerate(paragraphs, start=1)
        ]
        candidates = self._build_candidates(segments, source_type=source_type, paragraph_mode=True)
        round2 = self._round2_select(candidates)
        top10 = round2[:10]

        round1_file = output_dir / "candidates_round1.json"
        round2_file = output_dir / "selected_round2.json"
        final_file = output_dir / "top10_final.json"
        table_file = output_dir / "highlights_table.md"
        plan_file = output_dir / "clip_plan.csv"

        round1_file.write_text(json.dumps([c.to_dict() for c in candidates], ensure_ascii=False, indent=2), encoding="utf-8")
        round2_file.write_text(json.dumps([c.to_dict() for c in round2], ensure_ascii=False, indent=2), encoding="utf-8")
        final_file.write_text(json.dumps([c.to_dict() for c in top10], ensure_ascii=False, indent=2), encoding="utf-8")

        table_file.write_text(self._to_markdown_table(top10), encoding="utf-8")
        self._write_clip_plan_csv(top10, plan_file)

        return {
            "candidates_round1": round1_file,
            "selected_round2": round2_file,
            "top10_final": final_file,
            "highlights_table": table_file,
            "clip_plan": plan_file,
        }

    def parse_candidates_file(self, path: Path) -> list[HighlightCandidate]:
        data = json.loads(path.read_text(encoding="utf-8"))
        out = []
        for item in data:
            out.append(
                HighlightCandidate(
                    candidate_id=item["candidate_id"],
                    text=str(item["text"]),
                    score=float(item["score"]),
                    standalone_value=float(item.get("standalone_value", 0.0)),
                    novelty=float(item.get("novelty", 0.0)),
                    reason=str(item.get("reason", "")),
                    source_type=item.get("source_type"),
                    start=float(item["start"]) if item.get("start") is not None else None,
                    end=float(item["end"]) if item.get("end") is not None else None,
                    paragraph_id=item.get("paragraph_id"),
                    section_id=item.get("section_id"),
                )
            )
        return out

    def _load_segments(self, cleaned_json_file: Path) -> list[dict]:
        payload = json.loads(cleaned_json_file.read_text(encoding="utf-8"))
        return payload.get("segments", [])

    def _build_candidates(self, segments: list[dict], source_type: str, paragraph_mode: bool = False) -> list[HighlightCandidate]:
        candidates: list[HighlightCandidate] = []
        seen_text: set[str] = set()

        for idx, seg in enumerate(segments, start=1):
            text = " ".join(str(seg.get("text", "")).split())
            if len(text) < 20:
                continue
            key = text.lower()
            if key in seen_text:
                continue
            seen_text.add(key)

            start = float(seg.get("start", 0.0)) if not paragraph_mode else None
            end = float(seg.get("end", start if start is not None else 0.0)) if not paragraph_mode else None
            score, standalone, novelty, reason = self._score_text(text)
            if score < 30:
                continue
            candidates.append(
                HighlightCandidate(
                    candidate_id=f"h_{idx:04d}",
                    text=text,
                    score=score,
                    standalone_value=standalone,
                    novelty=novelty,
                    reason=reason,
                    source_type=source_type,
                    start=start,
                    end=end,
                    paragraph_id=seg.get("paragraph_id") if paragraph_mode else None,
                    section_id=seg.get("section_id"),
                )
            )

        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates

    def _score_text(self, text: str) -> tuple[float, float, float, str]:
        length = len(text)
        words = re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]", text)
        unique_ratio = len(set(words)) / len(words) if words else 0.0

        length_score = 25 if 35 <= length <= 180 else 12 if 20 <= length <= 260 else 5
        actionable_boost = 12 if re.search(r"建议|方法|步骤|原则|should|how|步骤|关键|策略", text, re.I) else 0
        hook_boost = 10 if re.search(r"为什么|如何|不要|必须|核心|关键|误区|本质", text, re.I) else 0
        data_boost = 8 if re.search(r"\d+", text) else 0
        standalone = min(40.0, length_score + actionable_boost + hook_boost)
        novelty = max(0.0, min(30.0, unique_ratio * 30))
        score = min(100.0, standalone + novelty + data_boost)

        reason_parts = []
        if actionable_boost:
            reason_parts.append("actionable")
        if hook_boost:
            reason_parts.append("hook")
        if data_boost:
            reason_parts.append("contains_numbers")
        if not reason_parts:
            reason_parts.append("informative")
        return score, standalone, novelty, ", ".join(reason_parts)

    def _round2_select(self, candidates: list[HighlightCandidate]) -> list[HighlightCandidate]:
        selected: list[HighlightCandidate] = []
        used_terms: set[str] = set()
        for c in candidates:
            terms = set(re.findall(r"[A-Za-z]{4,}|[\u4e00-\u9fff]{2,4}", c.text.lower()))
            overlap = len(terms & used_terms)
            if selected and overlap > 10:
                continue
            selected.append(c)
            used_terms.update(terms)
            if len(selected) >= 24:
                break
        return selected

    def _to_markdown_table(self, candidates: list[HighlightCandidate]) -> str:
        lines = [
            "# Highlights Table",
            "",
            "| Rank | Candidate ID | Start | End | Paragraph | Score | Reason | Text |",
            "|---|---|---:|---:|---|---:|---|---|",
        ]
        for i, c in enumerate(candidates, start=1):
            text = c.text.replace("|", "/")[:120]
            start = f"{c.start:.2f}" if c.start is not None else "-"
            end = f"{c.end:.2f}" if c.end is not None else "-"
            para = c.paragraph_id or "-"
            lines.append(f"| {i} | {c.candidate_id} | {start} | {end} | {para} | {c.score:.1f} | {c.reason} | {text} |")
        return "\n".join(lines) + "\n"

    def _write_clip_plan_csv(self, candidates: list[HighlightCandidate], out: Path) -> None:
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "rank",
                    "candidate_id",
                    "source_type",
                    "paragraph_id",
                    "section_id",
                    "start",
                    "end",
                    "duration",
                    "score",
                    "reason",
                    "text",
                ],
            )
            writer.writeheader()
            for i, c in enumerate(candidates, start=1):
                writer.writerow(
                    {
                        "rank": i,
                        "candidate_id": c.candidate_id,
                        "source_type": c.source_type or "",
                        "paragraph_id": c.paragraph_id or "",
                        "section_id": c.section_id or "",
                        "start": f"{c.start:.3f}" if c.start is not None else "",
                        "end": f"{c.end:.3f}" if c.end is not None else "",
                        "duration": f"{max(0.0, c.end - c.start):.3f}" if c.start is not None and c.end is not None else "",
                        "score": f"{c.score:.3f}",
                        "reason": c.reason,
                        "text": c.text,
                    }
                )
