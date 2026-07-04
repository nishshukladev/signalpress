"""Summarize eval results into the warnings block rendered atop the digest."""

from signalpress.evals.invariants import CheckResult


def failures(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results if not r.passed]


def warnings_block(results: list[CheckResult]) -> str:
    failed = failures(results)
    if not failed:
        return ""
    lines = [f"> ⚠️ {len(failed)} eval gate failure(s) this run:"]
    lines += [f"> - `{r.check_name}`: {r.detail or 'failed'}" for r in failed]
    return "\n".join(lines)


def run_status(results: list[CheckResult]) -> str:
    return "gated" if failures(results) else "ok"
