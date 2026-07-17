import json
import os
import re

from dotenv import load_dotenv
from groq import Groq

from tools.search_tool import search_web

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None


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
                trace.append({"step": "evaluate", "detail": verdict, "source_url": source.get("url")})

        final_answer = synthesize(cleaned_question, trace)
        trace.append({"step": "synthesize", "detail": final_answer})
        return {"answer": final_answer, "trace": trace, "confidence": extract_confidence(final_answer)}
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