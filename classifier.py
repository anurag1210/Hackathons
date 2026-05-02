def classify_company(issue: str, subject: str) -> str:
    """
    Returns: "hackerrank", "claude", "visa", or "unknown"
    """
    text = f"{issue} {subject}".lower()

    keyword_map = {
        "hackerrank": ["test", "assessment", "candidate", "interview", "score", "hackerrank"],
        "claude": ["claude", "api", "conversation", "model", "prompt", "bedrock", "anthropic"],
        "visa": ["visa", "card", "charge", "dispute", "merchant", "atm", "transaction", "payment"],
    }

    scores = {}

    for domain, keywords in keyword_map.items():
        scores[domain] = sum(1 for keyword in keywords if keyword in text)

    best_domain = max(scores, key=scores.get)

    if scores[best_domain] == 0:
        return "unknown"

    return best_domain
