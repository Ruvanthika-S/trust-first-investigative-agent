import json
import os
import re

from dotenv import load_dotenv
from groq import Groq

from tools.search_tool import search_web

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None


def score_source_credibility(source):
    url = (source.get("url") or "").lower()
    domain = url.split("//")[-1].split("/")[0] if url else ""
    if domain.endswith(".gov") or domain.endswith(".org"):
        return {"label": "high", "score": 4}
    if domain.endswith(".com"):
        return {"label": "medium", "score": 3}
    return {"label": "low", "score": 1}


def build_evidence_summary(trace):
    claim_count = sum(1 for item in trace if item.get("step") == "decompose")
    evidence_by_claim = []
    current_claim = None
    support = 0
    contradict = 0
    irrelevant = 0

    for step in trace:
        if step.get("step") == "search":
            detail = step.get("detail", "")
            current_claim = detail.replace("Searched: '", "").replace("'", "") if "Searched:" in detail else current_claim
            continue
        if step.get("step") == "evaluate" and current_claim:
            detail = step.get("detail", "")
            if detail.upper().startswith("SUPPORT"):
                support += 1
            elif detail.upper().startswith("CONTRADICT"):
                contradict += 1
            else:
                irrelevant += 1
            evidence_by_claim.append({
                "claim": current_claim,
                "support": support,
                "contradict": contradict,
                "irrelevant": irrelevant,
            })
            support = 0
            contradict = 0
            irrelevant = 0

    if not evidence_by_claim:
        evidence_by_claim = [{"claim": "Overall", "support": 0, "contradict": 0, "irrelevant": 0}]

    return {
        "claim_count": max(claim_count, len(evidence_by_claim)),
        "overall_support": sum(item["support"] for item in evidence_by_claim),
        "overall_contradict": sum(item["contradict"] for item in evidence_by_claim),
        "overall_irrelevant": sum(item["irrelevant"] for item in evidence_by_claim),
        "evidence_by_claim": evidence_by_claim,
    }


def call_llm(prompt):
    if client is None:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to the .env file before running the app.")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc


def decompose(question):
    prompt = f"""Break this question into 2-3 short, specific checkable sub-claims.
Return ONLY a JSON list of strings, nothing else.
Question: {question}"""
    try:
        text = call_llm(prompt)
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            return parsed
    except Exception:
        pass

    fallback = [
        part.strip(" -:;,.")
        for part in re.split(r"\b(and|or|but|while)\b", question, flags=re.IGNORECASE)
        if part and part.strip() and part.strip().lower() not in {"and", "or", "but", "while"}
    ]
    normalized = [part.strip(" -:;,.") for part in fallback if len(part.strip(" -:;,.")) > 4]
    return normalized[:3] or [question.strip()]


def evaluate_source(claim, source):
    title = source.get("title", "")
    snippet = source.get("snippet", "")
    prompt = f"""Claim: {claim}
Source title: {title}
Source snippet: {snippet}
In one short sentence, does this source support, contradict, or is irrelevant to the claim? Start with SUPPORT, CONTRADICT, or IRRELEVANT."""
    return call_llm(prompt).strip()


def synthesize(question, trace):
    summary = json.dumps(trace, indent=2)
    prompt = f"""Question: {question}
Here is the full research trace:
{summary}
Give a final answer in 2-3 sentences. Then add a line starting with 'Confidence:' followed by high, medium, or low, and a one-line reason. Keep it concise."""
    return call_llm(prompt).strip()


def extract_confidence(answer):
    lowered = answer.lower()
    if "confidence: high" in lowered:
        return "high"
    if "confidence: low" in lowered:
        return "low"
    return "medium"


def run_agent(question):
    trace = []
    cleaned_question = (question or "").strip()

    if not cleaned_question:
        return {"answer": "Please enter a question to investigate.", "trace": trace, "confidence": "low"}

    try:
        claims = decompose(cleaned_question)
        trace.append({"step": "decompose", "detail": f"Split into: {claims}"})

        for claim in claims:
            results = search_web(claim, max_results=2)
            trace.append({"step": "search", "detail": f"Searched: '{claim}'", "sources": results})

            if not results:
                trace.append({"step": "evaluate", "detail": "No web results were returned for this claim.", "source_url": None})
                continue

            for source in results:
                verdict = evaluate_source(claim, source)
                credibility = score_source_credibility(source)
                trace.append({
                    "step": "evaluate",
                    "detail": verdict,
                    "source_url": source.get("url"),
                    "credibility": credibility,
                })

        final_answer = synthesize(cleaned_question, trace)
        trace.append({"step": "synthesize", "detail": final_answer})
        evidence_summary = build_evidence_summary(trace)
        return {
            "answer": final_answer,
            "trace": trace,
            "confidence": extract_confidence(final_answer),
            "evidence_summary": evidence_summary,
        }
    except Exception as exc:
        trace.append({"step": "error", "detail": str(exc)})
        return {"answer": f"I hit an issue while investigating: {exc}", "trace": trace, "confidence": "low"}


def follow_up(original_question, original_answer, trace, user_message, chat_history):
    trace_summary = "\n".join(
        f"- {step.get('detail', '')}" for step in trace if step.get("step") in ("search", "evaluate", "synthesize")
    )
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in chat_history)

    prompt = f"""You are answering follow-up questions about an investigation you already completed.

Original question: {original_question}
Original answer: {original_answer}
Evidence gathered:
{trace_summary}

Conversation so far:
{history_text}

New user message: {user_message}

Answer the follow-up clearly and briefly, using the evidence above. If the evidence doesn't cover it, say so honestly."""
    return call_llm(prompt)

if __name__ == "__main__":
    result = run_agent("Is it true that coffee stunts your growth?")
    print(json.dumps(result, indent=2))