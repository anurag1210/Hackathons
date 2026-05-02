def pre_screen(issue: str) -> bool:
    """
    Returns True if the ticket looks malicious or invalid.
    """
    text = (issue or "").lower()

    malicious_signals = [
        "ignore previous instructions",
        "disregard earlier instructions",
        "reveal system prompt",
        "show hidden prompt",
        "bypass safety",
        "jailbreak",
        "<script",
        "drop table",
        "delete database",
        "sudo",
        "rm -rf",
    ]

    if len(text) < 5:
        return True

    return any(signal in text for signal in malicious_signals)


def should_escalate(issue: str, retrieved_docs: list) -> bool:
    """
    Returns True if the ticket should be escalated.
    """
    text = (issue or "").lower()

    escalation_signals = [
        "refund",
        "chargeback",
        "fraud",
        "identity theft",
        "lawsuit",
        "legal action",
        "human agent",
        "speak to a person",
        "speak to support",
        "account hacked",
        "stolen card",
        "disputed charge",
    ]

    if any(signal in text for signal in escalation_signals):
        return True

    if not retrieved_docs:
        return True

    worst_distance = max(doc.get("score", 1.0) for doc in retrieved_docs)
    if worst_distance > 1.5:
        return True

    return False
