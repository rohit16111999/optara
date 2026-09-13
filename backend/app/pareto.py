def dominates(a, b):
    """Maximize quality; minimize cost and latency. Equal points do not dominate."""
    if a.expected_cost is None or b.expected_cost is None:
        return False
    weak = a.expected_quality >= b.expected_quality and a.expected_cost <= b.expected_cost and a.expected_latency <= b.expected_latency
    strict = a.expected_quality > b.expected_quality or a.expected_cost < b.expected_cost or a.expected_latency < b.expected_latency
    return weak and strict


def frontier(candidates):
    return [c for c in candidates if not any(d is not c and dominates(d.metrics,c.metrics) for d in candidates)]
