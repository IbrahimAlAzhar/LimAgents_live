"""
LimGen – Multi-Agent Limitation Generator
Single-file backend that also serves the frontend.
Deploy on Render (free) — no separate frontend hosting needed.
"""

import asyncio
import json
import os
import traceback
from typing import AsyncGenerator

import fitz  # PyMuPDF
import tiktoken
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from openai import OpenAI

# ─── App ────────────────────────────────────────────────────────────────
app = FastAPI(title="LimGen API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SAFE_TOKEN_LIMIT = 44_000


# ─── Serve frontend ────────────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "index.html"),
        media_type="text/html",
    )


# ─── PDF Parsing ────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text_parts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


# ─── Token helpers ──────────────────────────────────────────────────────
def _get_encoding():
    try:
        return tiktoken.get_encoding("o200k_base")
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def truncate(text: str, max_tokens: int = SAFE_TOKEN_LIMIT) -> str:
    if not text:
        return ""
    enc = _get_encoding()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens]) + "\n... [TRUNCATED]"


# ─── Specialist Prompts ─────────────────────────────────────────────────
def _build_prompts(paper: str) -> dict[str, str]:
    return {
        "Novelty & Significance": (
            "You are a highly skeptical expert focused exclusively on limitations related to novelty and significance of a scientific paper. "
            "Scrutinize whether the contributions are truly novel or merely incremental, whether claims of importance are overstated, "
            "whether the problem addressed is impactful, and whether motivations or real-world relevance are weakly justified.\n"
            "Look for issues like rebranding existing ideas without substantial improvement, lack of clear differentiation from prior work, "
            "exaggerated claims of breakthrough, narrow scope that limits broader significance, or failure to articulate why the work matters.\n"
            "Provide a concise bullet list of novelty- and significance-related limitations with explanations and evidence from the paper.\n\n"
            f"PAPER CONTENT:\n{paper}"
        ),
        "Theoretical & Methodological": (
            "You are an expert in theoretical and methodological soundness, including ablations and component analysis. "
            "Scrutinize the core method, theoretical claims, and component breakdowns for flaws, unrealistic assumptions, "
            "missing proofs, logical gaps, oversimplifications, or failure to explain why the method works.\n"
            "Identify issues like unstated or overly strong assumptions, incomplete theoretical analysis, errors in derivations, "
            "methods that only work under restricted conditions, missing ablations, or ablations that do not convincingly attribute gains.\n"
            "Provide a bullet list of theoretical, methodological, and ablation-related limitations with supporting evidence.\n\n"
            f"PAPER CONTENT:\n{paper}"
        ),
        "Experimental Evaluation": (
            "You specialize in experimental evaluation, including validation, rigor, comparisons, baselines, and metrics. "
            "Find weaknesses in empirical support such as insufficient runs, lack of statistical significance, cherry-picked results, "
            "narrow conditions, inappropriate baselines, incomplete comparisons, misleading metrics, or superficial analysis.\n"
            "Highlight issues like small-scale experiments, missing error bars, unreported failed experiments, outdated baselines, "
            "missing key competitors, unfair hyperparameter tuning, reliance on misleading metrics, or overemphasis on minor gains.\n"
            "Provide a bullet list of experimental evaluation-related limitations.\n\n"
            f"PAPER CONTENT:\n{paper}"
        ),
        "Generalization & Robustness": (
            "Your expertise covers generalization, robustness, computational efficiency, and real-world applicability. "
            "Evaluate whether the method performs well beyond tested settings, is practical in terms of resources, "
            "and addresses genuine deployment needs without ignoring real-world constraints.\n"
            "Point out limitations like overfitting to benchmarks, lack of out-of-distribution testing, sensitivity to hyperparameters, "
            "excessive resource demands, reliance on synthetic data, or over-optimistic assumptions about environments.\n"
            "Provide a bullet list of generalization-, robustness-, efficiency-, and applicability-related limitations.\n\n"
            f"PAPER CONTENT:\n{paper}"
        ),
        "Clarity & Reproducibility": (
            "You focus on clarity, interpretability, and reproducibility. "
            "Scrutinize for unclear explanations, lack of explainability or insights into decisions, "
            "and insufficient details for replication such as code, data, hyperparameters, or protocols.\n"
            "Identify issues like ambiguities, unstated assumptions, vague terms, black-box behavior without explanations, "
            "missing code/data release, unreported seeds, or lack of open science practices.\n"
            "Provide a bullet list of clarity-, interpretability-, and reproducibility-related limitations.\n\n"
            f"PAPER CONTENT:\n{paper}"
        ),
        "Data & Ethics": (
            "You specialize in data integrity, bias, fairness, and ethical considerations. "
            "Scrutinize datasets for issues in collection, labeling, cleaning, representativeness; "
            "and the overall work for biases, fairness problems, privacy risks, dual-use concerns, or societal impacts.\n"
            "Point out limitations such as small or non-diverse data, labeling errors, data leakage, "
            "biased outcomes, lack of fairness metrics, unreported subgroup performance, or failure to discuss misuse potential.\n"
            "Provide a bullet list of data integrity-, bias-, fairness-, and ethics-related limitations.\n\n"
            f"PAPER CONTENT:\n{paper}"
        ),
    }


# ─── OpenAI caller ──────────────────────────────────────────────────────
def _call_openai(client: OpenAI, model: str, system: str, user: str,
                 temperature: float = 0.2, max_tokens: int = 1500) -> str:
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


# ─── Streaming pipeline ─────────────────────────────────────────────────
async def run_pipeline(api_key: str, pdf_bytes: bytes, model: str) -> AsyncGenerator[str, None]:
    def event(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    try:
        # 1. Parse PDF
        yield event({"type": "status", "message": "Extracting text from PDF..."})
        raw_text = await asyncio.to_thread(extract_text_from_pdf, pdf_bytes)
        if len(raw_text.strip()) < 100:
            yield event({"type": "error", "message": "Could not extract enough text from the PDF. Please try a different file."})
            return
        paper_text = truncate(raw_text, max_tokens=SAFE_TOKEN_LIMIT)
        word_count = len(paper_text.split())
        yield event({"type": "status", "message": f"Extracted ~{word_count:,} words from paper."})

        client = OpenAI(api_key=api_key)
        prompts = _build_prompts(paper_text)

        # 2. Run each specialist
        specialist_outputs: dict[str, str] = {}
        for idx, (agent_name, sys_prompt) in enumerate(prompts.items(), 1):
            yield event({
                "type": "status",
                "message": f"Agent {idx}/{len(prompts)}: {agent_name} is analyzing...",
                "agent": agent_name,
            })
            output = await asyncio.to_thread(
                _call_openai, client, model, sys_prompt,
                "Analyze the paper above and provide your limitation findings as a bullet list.",
            )
            specialist_outputs[agent_name] = output
            yield event({"type": "agent", "agent": agent_name, "content": output})

        # 3. Leader Agent – compile handoff
        yield event({"type": "status", "message": "Leader Agent is compiling findings..."})
        handoff_sections = "\n\n".join(
            f"[{name}]\n{out}" for name, out in specialist_outputs.items()
        )
        leader_system = (
            "You are the Leader Agent. You have received limitation analyses from multiple specialist agents. "
            "Review each agent's output. If any finding is vague, strengthen it with specifics from the paper. "
            "Remove clearly duplicated points across agents but keep distinct perspectives. "
            "Output the cleaned compilation in the exact format provided, preserving agent sections."
        )
        leader_output = await asyncio.to_thread(
            _call_openai, client, model, leader_system,
            f"Here are the specialist outputs. Clean, de-duplicate, and strengthen them:\n\n{handoff_sections}",
            temperature=0.1, max_tokens=2500,
        )
        yield event({"type": "agent", "agent": "Leader Agent", "content": leader_output})

        # 4. Master Agent – final merge
        yield event({"type": "status", "message": "Master Agent is producing final limitations..."})
        master_system = (
            "You are the **Master Agent**. Your job is to merge specialist limitations into one final, non-redundant list.\n"
            "Rules:\n"
            "- Use ONLY what appears in the handoff (do not invent new limitations).\n"
            "- Merge duplicates, keep specificity and evidence.\n"
            "- Group by category.\n"
            "- Output format:\n"
            "Here is the consolidated list of key limitations identified in the paper:\n"
            "- **Category:** Description\n"
        )
        final_output = await asyncio.to_thread(
            _call_openai, client, model, master_system,
            f"Leader Agent compiled these limitation analyses from the team.\n"
            f"Synthesize them into a single consolidated list, grouped by category.\n\n{leader_output}",
            temperature=0.0, max_tokens=2000,
        )
        yield event({"type": "result", "content": final_output})

    except Exception as e:
        traceback.print_exc()
        yield event({"type": "error", "message": str(e)})


# ─── API Endpoints ──────────────────────────────────────────────────────
@app.post("/api/generate")
async def generate_limitations(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model: str = Form("gpt-4o-mini"),
):
    pdf_bytes = await file.read()
    return StreamingResponse(
        run_pipeline(api_key, pdf_bytes, model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
