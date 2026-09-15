# Claude Customer Support Ops

Production-style customer support AI built around Anthropic Claude with context management, memory, policy retrieval, escalation logic, evaluation, observability, and API reliability.

## Why this project exists

Customer-support chatbots fail in predictable ways: they forget earlier details, hallucinate policies, contradict themselves, over-send conversation history, mishandle prompt injection, and claim to perform actions they are not authorized to execute. This project demonstrates how to diagnose and solve those problems with a modular architecture.

## Real-world capabilities

- Anthropic Claude API integration with a deterministic demo fallback
- Policy-grounded responses for returns, cancellations, refunds, and shipping
- Persistent conversation memory with fact updates
- Context selection and summarization for long chats
- Human escalation for chargebacks, repeated failures, and high-value refunds
- Prompt-injection detection and system-policy protection
- Structured observability: latency, context sources, escalation reason, and model mode
- Baseline-vs-optimized evaluation suite
- FastAPI REST service and Streamlit operations dashboard
- Pytest regression tests
- Docker support and GitHub Actions CI

## Architecture

```text
Customer
   |
FastAPI
   |
Intent + Safety Router
   |
+-------------------------------+
| Conversation Memory           |
| Customer / Order Data         |
| Policy Knowledge Base         |
+-------------------------------+
   |
Context Builder + Token Budget
   |
Prompt Engine
   |
Claude API / Deterministic Demo Engine
   |
Response Validation
   |
AI Reply -----> Human Escalation when required
   |
Logs + Evaluation Dashboard
```

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API explorer.

Run the dashboard in another terminal:

```bash
streamlit run dashboard.py
```

Run tests and evaluations:

```bash
pytest -q
python -m evaluation.runner
```

## Demo mode

The project works without an Anthropic API key. If `ANTHROPIC_API_KEY` is not present, the service uses a deterministic local response engine so the full memory, retrieval, escalation, testing, and observability pipeline can still be demonstrated safely.

To use Claude, add your key to `.env`:

```text
ANTHROPIC_API_KEY=your_key_here
```

Never commit a real API key.

## Example scenario

A customer starts with: `My order NC-48392 has not arrived.` Later they ask: `Can I just get my money back?` The system retains the order reference, retrieves the delayed-shipment and refund policies, decides whether the refund requires human approval, and gives a response grounded in the actual order state instead of inventing information.

## Portfolio talking points

This project is designed to demonstrate production chatbot troubleshooting rather than simple API usage. It shows how to inspect context, isolate failure modes, improve prompt architecture, protect system instructions, handle API failures, build regression tests, and measure whether changes actually improve multi-turn behavior.
