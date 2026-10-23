# Parking AI

Parking AI is a FastAPI application that uses a LangGraph workflow to route parking-related questions to specialized agents.

## What It Does

- Routes user questions through a supervisor agent.
- Handles reservation, pricing, and support intents.
- Reviews generated answers with a judge agent.
- Supports optional human-review routing.
- Stores short-term session memory while the server is running.
- Runs locally without API keys using the default `local` LLM provider.

## Architecture

```text
User / Postman
    ↓
FastAPI /chat
    ↓
WorkflowState
    ↓
SupervisorAgent
    ↓
ReservationAgent | PricingAgent | SupportAgent
    ↓
JudgeAgent
    ↓
HumanAgent, if needed
    ↓
ResponseAgent
    ↓
JSON response
```

## Project Structure

```text
.
├── main.py
├── requirements.txt
└── app
    ├── agents
    ├── api
    ├── graph
    ├── llm
    ├── config.py
    ├── memory.py
    └── state.py
```

## Setup

Create a virtual environment:

```bash
python3 -m venv .venv
```

Install dependencies:

```bash
./.venv/bin/python -m pip install -r requirements.txt
```

If `chromadb` causes slow installs on your machine, install the currently used runtime dependencies:

```bash
./.venv/bin/python -m pip install fastapi uvicorn langgraph langchain-openai langchain-anthropic python-dotenv pydantic pytest
```

## Run

```bash
./.venv/bin/uvicorn main:app --reload
```

The API runs at:

```text
http://127.0.0.1:8000
```

## Test With Postman

Use:

```text
POST http://127.0.0.1:8000/chat
```

Headers:

```text
Content-Type: application/json
```

Body:

```json
{
  "question": "How much does parking cost today?"
}
```

Example response:

```json
{
  "question": "How much does parking cost today?",
  "session_id": "...",
  "response": "Today's parking price is $12 USD."
}
```

## Test Memory

First request:

```json
{
  "question": "How much does parking cost today?"
}
```

Copy the returned `session_id`, then send:

```json
{
  "session_id": "PASTE_SESSION_ID_HERE",
  "question": "Can you repeat that?"
}
```

The app uses the previous session history to route the follow-up question.

## Environment Variables

By default, the app uses:

```text
LLM_PROVIDER=local
```

To use OpenAI:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
```

To use Anthropic:

```text
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key
CLAUDE_MODEL=claude-sonnet-4-20250514
```

## Talking Points

- FastAPI is the HTTP API layer.
- LangGraph is the orchestration layer.
- `WorkflowState` carries request context between agents.
- The supervisor routes requests to specialized agents.
- The judge decides whether a response needs human review.
- The LLM factory decouples the app from a specific model provider.
- Session memory is currently in-process and resets when the server restarts.

## Current Limitations

- Reservation, pricing, and support agents return mocked responses.
- Memory is not persistent across server restarts.
- `redis` and `chromadb` are listed as future-oriented dependencies but are not currently used by the app.
- Production use should add authentication, persistent storage, logging, and real parking/payment API integrations.

## RAG Implementation

The project now includes RAG (Retrieval-Augmented Generation) capabilities:

- **Document Store**: Loads parking-related documents from `documents/` directory
- **Retrievers**: ChromaDB-based (if installed) or keyword-based fallback
- **Embeddings**: Simple hash-based embeddings for local provider, extensible for OpenAI/Anthropic
- **Agent Integration**: Pricing, Reservation, and Support agents use RAG to enhance responses

Sample documents included:
- `pricing.txt` - Parking rates and policies
- `reservations.txt` - Booking and cancellation policies
- `policies.txt` - Facility rules and regulations
- `faq.txt` - Frequently asked questions

## Guardrails

Response validation through guardrails:

- **EmptyResponseGuardrail** - Prevents empty responses
- **MinLengthGuardrail** - Ensures minimum response length
- **MaxLengthGuardrail** - Prevents excessively long responses
- **ProfanityGuardrail** - Filters inappropriate language
- **PIIGuardrail** - Detects potential PII (emails, phones, SSNs)
- **ParkingDomainGuardrail** - Ensures parking-relevant content

Guardrails are applied in the ResponseAgent before returning to the user.

## Evaluation Framework

Run evaluations to test system quality:

```bash
./.venv/bin/python tests/test_eval.py
```

Evaluators included:
- **ResponseQualityEvaluator** - Tests response quality and keyword matching
- **AgentRoutingEvaluator** - Tests supervisor routing accuracy
- **GuardrailEvaluator** - Tests guardrail effectiveness

Metrics tracked:
- Pass rate, average score, guardrail pass rate
- Response times, agent usage distribution
- Error rates and failure reasons

## Monitoring

View runtime metrics via API:

```bash
GET http://127.0.0.1:8000/metrics
```

Reset metrics:

```bash
POST http://127.0.0.1:8000/metrics/reset
```

Metrics include:
- Total requests and error rate
- Agent usage distribution
- Guardrail pass/fail rates
- Average response times

## Configuration

RAG and guardrails can be configured via environment variables:

```text
ENABLE_RAG=true              # Enable/disable RAG (default: true)
RAG_TOP_K=3                  # Number of documents to retrieve
DOCUMENTS_DIR=documents      # Documents directory path
```
