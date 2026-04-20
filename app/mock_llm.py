from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .incidents import STATE


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    def generate(self, prompt: str) -> FakeResponse:
        time.sleep(0.15)
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = random.randint(80, 180)
        if STATE["cost_spike"]:
            output_tokens *= 4
        answer = self._build_answer(prompt)
        return FakeResponse(text=answer, usage=FakeUsage(input_tokens, output_tokens), model=self.model)

    def _build_answer(self, prompt: str) -> str:
        docs_section = ""
        if "Docs=" in prompt:
            docs_section = prompt.split("Docs=", 1)[1].split("\n")[0]

        question = ""
        if "Question=" in prompt:
            question = prompt.split("Question=", 1)[1].strip().lower()

        if docs_section and "No domain document matched" not in docs_section:
            context = docs_section.strip("[]'\"")
            return f"Based on our documentation: {context}"

        if any(w in question for w in ["pii", "log", "sensitive", "appear"]):
            return "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries and hashed identifiers only."
        if any(w in question for w in ["metric", "trace", "log", "together", "work"]):
            return "Metrics detect incidents, traces localize them, and logs explain the root cause. Together they form the observability triad."
        if any(w in question for w in ["alert", "design", "threshold"]):
            return "Alerts should be symptom-based with clear thresholds, severity levels, runbook links, and avoid alert fatigue."
        if any(w in question for w in ["latency", "tail", "debug", "p95", "p99"]):
            return "To debug tail latency, compare P50/P95/P99 in metrics, find the slow span in traces, then correlate with logs using correlation_id."
        if any(w in question for w in ["summary", "observability", "workflow"]):
            return "The observability workflow: instrument code with logs and traces, define SLOs, set alerts on SLI breaches, and use runbooks for incident response."

        return "Please refer to the documentation for details on this topic. Ensure all sensitive data is handled according to the observability policy."
