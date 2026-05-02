import pandas as pd

from classifier import classify_company
from retriever import query_vectorstore
from safety import pre_screen, should_escalate


import json
import os
from openai import OpenAI
from prompts import SYSTEM_PROMPT, build_prompt

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _generate_response(issue, subject, domain, retrieved_docs) -> dict:
    prompt = build_prompt(issue, subject, domain, retrieved_docs)
    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    
    raw = completion.choices[0].message.content.strip()
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "status": "escalated",
            "product_area": domain,
            "response": "Failed to parse LLM response.",
            "justification": f"LLM returned non-JSON output: {raw[:100]}",
            "request_type": "invalid",
        }


def run_pipeline(
    row: pd.Series,
    vectorstores: dict,
    verbose: bool = False
) -> dict:
    """
    Process a single support ticket row end-to-end.

    Returns:
        {
            "status": ...,
            "product_area": ...,
            "response": ...,
            "justification": ...,
            "request_type": ...
        }
    """
    issue = str(row.get("Issue", "") or "").strip()
    subject = str(row.get("Subject", "") or "").strip()
    company = str(row.get("Company", "") or "").strip().lower()

    if verbose:
        print(f"[pipeline] Issue: {issue[:80]}")
        print(f"[pipeline] Subject: {subject[:80]}")
        print(f"[pipeline] Company: {company}")

    # Step 1 — pre-screen malicious or invalid input
    if pre_screen(issue):
        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "This request requires human review.",
            "justification": "Ticket was flagged by pre-screen as malicious or invalid.",
            "request_type": "invalid",
        }

    # Step 2 — determine domain
    if company in {"hackerrank", "claude", "visa"}:
        domain = company
    else:
        domain = classify_company(issue, subject)

    if verbose:
        print(f"[pipeline] Routed domain: {domain}")

    # Step 3 — escalate if routing failed
    if domain == "unknown":
        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "We could not determine the correct support domain for this request.",
            "justification": "Company field was unknown and classifier could not infer a domain.",
            "request_type": "invalid",
        }

    # Step 4 — retrieve relevant docs
    ticket_text = f"{subject}\n{issue}".strip()
    retrieved_docs = query_vectorstore(
        ticket_text=ticket_text,
        domain=domain,
        vectorstores=vectorstores,
        top_k=3,
    )

    if verbose:
        print(f"[pipeline] Retrieved docs: {len(retrieved_docs)}")
        for i, doc in enumerate(retrieved_docs, start=1):
            print(f"[pipeline] Doc {i}: source={doc.get('source', '')}, score={doc.get('score', '')}")

    # Step 5 — safety / escalation gate after retrieval
    if should_escalate(issue, retrieved_docs):
        return {
            "status": "escalated",
            "product_area": domain,
            "response": "This request requires human review.",
            "justification": "Ticket triggered escalation rules or retrieval confidence was too low.",
            "request_type": "invalid",
        }

    # Step 6 — generate grounded response
    return _generate_response(issue, subject, domain, retrieved_docs)