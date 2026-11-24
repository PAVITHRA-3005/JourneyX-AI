# JourneyX AI
## Intelligent Travel Planning Assistant
### Executive Summary | Capstone Project — Track B (API-Side)

> **Implementation and capstone compliance:** see **[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)** (canonical architecture, schedule, and Track B requirement traceability).  
> **Idea, agents, and end-to-end flow:** see **[docs/IDEA_AND_AGENT_FLOW.md](./docs/IDEA_AND_AGENT_FLOW.md)**.

### 1. Project Overview

JourneyX AI is an intelligent, conversational travel planning assistant designed to simplify trip planning through destination discovery, transportation comparison, accommodation recommendations, budget estimation, and personalized itinerary generation.

The application uses a multi-agent architecture to understand user requirements, retrieve relevant travel information, execute specialized tools, and validate recommendations before presenting a consolidated travel plan.

The project demonstrates practical applications of Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), agent orchestration, tool calling, persistent conversational state, and systematic AI evaluation.

### 2. Problem Statement

Planning a trip involves researching destinations, comparing transportation options, finding suitable accommodation, estimating expenses, and organizing activities into a practical itinerary.

This information is distributed across multiple sources, making the planning process time-consuming and difficult to manage.

JourneyX AI addresses this challenge through a unified conversational interface that understands travel preferences and generates structured, budget-conscious travel recommendations.

### 3. Project Objectives and Features

JourneyX AI will provide the following capabilities:

- **Conversational Travel Planning:** Understand destination, travel dates, number of travellers, budget, preferences, and trip requirements.
- **Destination Discovery:** Recommend destinations, tourist attractions, and activities based on user preferences.
- **Transportation Comparison:** Compare sample flight, train, bus, petrol/diesel vehicle, and electric vehicle travel options.
- **Route Information:** Provide approximate distances, travel durations, and basic route details.
- **Accommodation Discovery:** Recommend suitable accommodation options based on destination, budget, and preferences.
- **Attractions and Activities:** Discover sightseeing locations, experiences, and activities relevant to the selected destination.
- **Budget Estimation:** Calculate estimated transportation, accommodation, food, and activity expenses using deterministic Python calculations.
- **Day-wise Itinerary Generation:** Generate structured daily travel plans based on available time, budget, and user preferences.
- **Context-aware Refinement:** Update existing travel plans when users change their budget, dates, transportation preferences, or other requirements while retaining conversational context.

### 4. AI Architecture

The solution will use three logical agents operating through a controlled workflow.

**Planner Agent**
- Understands user intent and extracts travel requirements.
- Identifies constraints and missing information.
- Decomposes the request into executable planning tasks.

**Executor Agent**
- Invokes specialized Python tools for transportation comparison, route information, accommodation discovery, destination discovery, and budget calculation.
- Retrieves relevant information from the travel knowledge base.
- Consolidates tool outputs into structured results.

**Critic Agent**
- Validates recommendations against user requirements.
- Checks budget constraints, consistency, missing information, and grounding.
- Identifies incomplete or incorrect results and requests corrections.

**Execution workflow:**

Planner → Executor → Critic → Final Response

The workflow will support bounded execution, structured outputs, error handling, and persistent conversational state.

### 5. Technology Stack

| Component | Technology |
|---|---|
| Language model | Shared hosted OpenAI-compatible instruct model (maximum 8B parameters) |
| Embeddings | Provided hosted embeddings endpoint |
| Backend | Python, FastAPI |
| Agent orchestration | LangGraph |
| Retrieval | Hybrid BM25 and dense retrieval |
| Vector storage | FAISS or Chroma |
| Reranking | Local cross-encoder reranker (CPU); no third-party rerank API |
| Structured outputs | Pydantic and JSON Schema |
| Frontend | Streamlit |
| Evaluation and tracing | Langfuse OSS, OpenTelemetry, or JSONL traces |
| Deployment | Docker Compose (rate limiting + caching) |

**Data:** Team-owned travel knowledge base only — no live travel, maps, booking, or web-search APIs at runtime. The application uses the shared hosted model and embeddings services provided for the capstone.

### 6. Data Strategy

JourneyX AI will use curated travel datasets and a structured travel knowledge base.

The initial dataset will cover selected Indian destinations and include:

- Destination descriptions, highlights, and activities.
- Accommodation information and indicative prices.
- Sample transportation options.
- Approximate routes and travel distances.
- Indicative expenses and travel recommendations.

The RAG knowledge base will contain approximately 500–2,000 travel-related documents or information records.

The retrieval pipeline will combine:
- Keyword-based BM25 retrieval.
- Dense semantic retrieval using embeddings.
- Hybrid result fusion.
- Reranking to improve relevance.
- Citation-grounded response generation.

Sample and indicative prices will be identified as estimates.

### 7. Evaluation and Responsible AI

A frozen evaluation dataset of 60–100 realistic travel queries will be prepared with expected answers and evaluation criteria before implementation.

The application will be evaluated using:

- Response accuracy and task completion rate.
- Retrieval Recall@K.
- Citation correctness and grounding.
- Structured output validity.
- Tool execution success and failure rates.
- Average tool calls per task.
- Response latency and token usage/cost.
- Failure classification and error analysis.

Responsible AI and reliability measures will include prompt-injection testing, input validation, PII protection, bounded agent execution, appropriate refusal behaviour, and validation of tool outputs.

### 8. Phased execution plan

| Phase | Focus | Expected deliverables |
|---|---|---|
| Foundation | Domain definition, dataset preparation, baseline LLM application and evaluation questions | Working baseline and frozen evaluation dataset |
| Retrieval | Document processing, embeddings, hybrid retrieval, reranking and RAG | Grounded retrieval and citation-enabled responses |
| Agent | LangGraph orchestration, Planner/Executor/Critic agents, tools, state management and error handling | Functional multi-agent workflow |
| Release | Frontend integration, evaluation, observability, testing and Docker deployment | Deployed application and final demonstration |

### 9. Team Structure

The project will be executed by six members, with approximately 8–10 focused hours per member per week.

| Member | Responsibility |
|---|---|
| Member 1 | Domain definition, travel datasets and evaluation design |
| Member 2 | RAG pipeline, embeddings and hybrid retrieval |
| Member 3 | Planner Agent and LangGraph orchestration |
| Member 4 | Executor Agent and specialized Python tools |
| Member 5 | Critic Agent, evaluation, reliability and observability |
| Member 6 | Frontend, integration, testing and deployment |

All members will contribute to integration, testing, documentation, and the final demonstration.

### 10. Expected Deliverables

1. Complete source-code repository with documented architecture.
2. Functional JourneyX AI conversational travel planning application.
3. RAG pipeline with hybrid retrieval, reranking, and citations.
4. Multi-agent workflow with tool integration and persistent state.
5. Evaluation dataset, results, and failure analysis report.
6. Execution tracing and observability dashboard.
7. Containerized application with deployment instructions.
8. Technical project report of approximately 12 pages.
9. Final 10-minute project demonstration.

### 11. Expected Outcome

JourneyX AI will demonstrate how a hosted small language model can be combined with retrieval, specialized tools, controlled agent orchestration, deterministic calculations, and systematic evaluation to build a practical AI-powered travel planning application.

The outcome will be a functional, measurable, and maintainable conversational travel assistant that generates personalized travel recommendations and structured itineraries within the four-week capstone timeline.