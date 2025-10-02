from typing import Dict


def render_prometheus_text(counters: Dict[str, int]) -> str:
    """Render a very small subset of metrics in Prometheus text format.

    This is intentionally tiny: it treats every counter as a gauge with _total suffix when present.
    """
    lines = []
    for name, value in sorted(counters.items()):
        # normalize name: replace dots/spaces with underscore
        metric_name = name.replace(".", "_").replace(" ", "_")
        # If counter already looks like a total, keep it; else append _total
        if metric_name.endswith("_total"):
            out_name = metric_name
        else:
            out_name = f"{metric_name}_total"
        lines.append(f"# HELP {out_name} auto_generated\n# TYPE {out_name} counter")
        lines.append(f"{out_name} {int(value)}")

    return "\n".join(lines) + "\n"


__all__ = ["render_prometheus_text"]
