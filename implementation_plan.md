# ResearchScout — Complete AI Agent Platform Architecture

> An autonomous, multi-agent AI platform that discovers, extracts, verifies, ranks, and recommends research opportunities from the global internet.

---

## Table of Contents

1. [Overall Architecture](#1-overall-architecture)
2. [Multi-Agent Architecture](#2-multi-agent-architecture)
3. [Data Flow Diagram](#3-data-flow-diagram)
4. [Database Schema](#4-database-schema)
5. [API Design](#5-api-design)
6. [Folder Structure](#6-folder-structure)
7. [Technology Stack](#7-technology-stack)
8. [Algorithms](#8-algorithms)
9. [Prompt Engineering Strategy](#9-prompt-engineering-strategy)
10. [Memory Architecture](#10-memory-architecture)
11. [Recommendation Engine](#11-recommendation-engine)
12. [Search Pipeline](#12-search-pipeline)
13. [Crawling Strategy](#13-crawling-strategy)
14. [Information Extraction Pipeline](#14-information-extraction-pipeline)
15. [Vector Search Pipeline](#15-vector-search-pipeline)
16. [Knowledge Graph Architecture](#16-knowledge-graph-architecture)
17. [Security Architecture](#17-security-architecture)
18. [Scalability Strategy](#18-scalability-strategy)
19. [Cost Optimization](#19-cost-optimization)
20. [Deployment Plan](#20-deployment-plan)
21. [Testing Strategy](#21-testing-strategy)
22. [Evaluation Metrics](#22-evaluation-metrics)
23. [Future Research Directions](#23-future-research-directions)
24. [Research Paper Ideas](#24-research-paper-ideas)
25. [Resume-Worthy Features](#25-resume-worthy-features)
26. [Step-by-Step Implementation Roadmap](#26-step-by-step-implementation-roadmap)

---

## 1. Overall Architecture

ResearchScout is a **five-tier, event-driven, multi-agent platform** designed for horizontal scalability, fault tolerance, and continuous learning.

```mermaid
graph TB
    subgraph Tier1["Tier 1 — Presentation"]
        WebApp["Next.js Web App"]
        MobileAPI["Mobile API Gateway"]
        Notifications["Notification Services"]
    end

    subgraph Tier2["Tier 2 — API & Orchestration"]
        APIGateway["FastAPI Gateway"]
        AgentOrchestrator["LangGraph Orchestrator"]
        TaskQueue["Celery + Redis Task Queue"]
    end

    subgraph Tier3["Tier 3 — Agent Layer"]
        PlannerAgent["Planner Agent"]
        SearchAgent["Search Agent"]
        CrawlerAgent["Crawler Agent"]
        ExtractorAgent["Extractor Agent"]
        ValidatorAgent["Validator Agent"]
        RankerAgent["Ranker Agent"]
        RecommenderAgent["Recommender Agent"]
        MonitorAgent["Monitor Agent"]
    end

    subgraph Tier4["Tier 4 — Intelligence"]
        LLMService["LLM Service Layer"]
        NLPPipeline["NLP Pipeline"]
        EmbeddingService["Embedding Service"]
        KnowledgeGraph["Knowledge Graph Engine"]
    end

    subgraph Tier5["Tier 5 — Data"]
        PostgreSQL["PostgreSQL"]
        Qdrant["Qdrant Vector DB"]
        Neo4j["Neo4j Graph DB"]
        Redis["Redis Cache"]
        S3["MinIO / S3 Object Storage"]
    end

    Tier1 --> Tier2
    Tier2 --> Tier3
    Tier3 --> Tier4
    Tier4 --> Tier5
```

### Architectural Principles

| Principle | Implementation |
|---|---|
| **Event-Driven** | All agents communicate via Redis Streams / RabbitMQ message bus |
| **Stateful Orchestration** | LangGraph state machines with PostgreSQL-backed checkpoints |
| **Fault Tolerance** | Every agent has retry policies, circuit breakers, dead-letter queues |
| **Observability** | OpenTelemetry tracing across all agent handoffs |
| **Deterministic Guardrails** | Critical decisions (dedup, auth) use deterministic code; LLMs handle reasoning |
| **Schema-First** | Pydantic models enforce typed contracts between every agent |
| **Horizontal Scaling** | Each agent type is a separate containerized microservice |

---

## 2. Multi-Agent Architecture

### 2.1 Agent Hierarchy

```mermaid
graph TD
    Orchestrator["🧠 Orchestrator Agent<br/>(LangGraph Supervisor)"]

    subgraph Discovery["Discovery Division"]
        Planner["📋 Planner Agent"]
        Search["🔍 Search Agent"]
        Crawler["🕷️ Crawler Agent"]
        Browser["🌐 Browser Agent"]
    end

    subgraph Intelligence["Intelligence Division"]
        Extractor["📄 Extractor Agent"]
        NLP["🗣️ NLP Agent"]
        Validator["✅ Validator Agent"]
        Dedup["🔗 Dedup Agent"]
    end

    subgraph Knowledge["Knowledge Division"]
        KGBuilder["🗺️ KG Builder Agent"]
        Embedding["📐 Embedding Agent"]
        Memory["🧠 Memory Agent"]
    end

    subgraph UserFacing["User-Facing Division"]
        Recommender["⭐ Recommender Agent"]
        Ranker["📊 Ranker Agent"]
        ProfileMatcher["👤 Profile Matcher Agent"]
        Notifier["🔔 Notifier Agent"]
    end

    subgraph MetaAgents["Meta-Agents"]
        Scheduler["⏰ Scheduler Agent"]
        Monitor["📡 Monitor Agent"]
        Learning["📈 Learning Agent"]
        Analytics["📊 Analytics Agent"]
        Feedback["💬 Feedback Agent"]
    end

    Orchestrator --> Discovery
    Orchestrator --> Intelligence
    Orchestrator --> Knowledge
    Orchestrator --> UserFacing
    Orchestrator --> MetaAgents
```

### 2.2 Detailed Agent Specifications

#### 🧠 Orchestrator Agent (Supervisor)

| Attribute | Detail |
|---|---|
| **Responsibility** | Decompose high-level goals into sub-tasks; route to specialized agents; manage state transitions; handle failures |
| **Framework** | LangGraph `StateGraph` with conditional edges |
| **Inputs** | User requests, scheduled triggers, system events |
| **Outputs** | Task assignments with typed payloads to child agents |
| **Memory** | PostgreSQL-backed LangGraph checkpoints (supports time-travel debugging) |
| **Tools** | Task router, agent registry, priority queue manager |
| **Communication** | Redis Streams pub/sub; direct function calls for synchronous sub-graphs |
| **Failure Recovery** | Exponential backoff with jitter; dead-letter queue for unrecoverable tasks; fallback to simpler agent chains |
| **Retry** | 3 retries with 2^n × 1s backoff + 500ms jitter |

---

#### 📋 Planner Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Convert user goals or scheduled triggers into structured execution plans (DAGs of agent tasks) |
| **Inputs** | Natural language goal, system context, historical performance data |
| **Outputs** | `ExecutionPlan` — ordered list of `AgentTask` objects with dependencies |
| **Memory** | Past execution plans and their success rates (long-term memory in PostgreSQL) |
| **Tools** | Goal decomposer, dependency resolver, cost estimator |
| **Communication** | Receives goals from Orchestrator; emits plans back to Orchestrator |
| **Failure Recovery** | Falls back to cached plan templates; requests human escalation if decomposition confidence < 0.6 |
| **Retry** | 2 retries; on failure, use template-based plan |

**Pydantic Contract:**
```python
class AgentTask(BaseModel):
    task_id: str
    agent_type: AgentType  # enum
    priority: int  # 1-10
    payload: dict[str, Any]
    depends_on: list[str]  # task_ids
    timeout_seconds: int
    retry_policy: RetryPolicy

class ExecutionPlan(BaseModel):
    plan_id: str
    goal: str
    tasks: list[AgentTask]
    estimated_duration_seconds: int
    estimated_cost_usd: float
```

---

#### 🔍 Search Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Execute intelligent searches across multiple APIs and engines to discover opportunity URLs |
| **Inputs** | `SearchQuery` (keywords, domains, filters, search type) |
| **Outputs** | `SearchResults` — ranked list of URLs with relevance scores |
| **Memory** | Query history, URL cache (Redis TTL 24h), search effectiveness scores |
| **Tools** | Google Custom Search API, Bing Web Search API, SerpAPI, Tavily, GitHub Search API, Semantic Scholar API, OpenAlex API, site-specific searchers |
| **Communication** | Receives tasks from Orchestrator; emits URLs to Crawler Agent via Redis Stream |
| **Failure Recovery** | API fallback chain (Google → Bing → Tavily → SerpAPI); rate limit detection and backoff |
| **Retry** | Per-API: 3 retries with exponential backoff; circuit breaker opens after 5 consecutive failures |

**Search Strategy Matrix:**

| Source Type | Search Method | API/Tool |
|---|---|---|
| General web | Keyword + site-restricted | Google CSE, Bing |
| Academic | Structured query | Semantic Scholar, OpenAlex |
| Code/OSS | Repository search | GitHub API, HuggingFace API |
| Social | Keyword monitoring | Twitter/X API, Reddit API |
| Job boards | Structured query | Indeed API, LinkedIn (scrape) |
| RSS/Feeds | Feed polling | feedparser |
| University | Site-restricted crawl | Crawl4AI + Playwright |

---

#### 🕷️ Crawler Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Fetch and render web pages; extract raw HTML/content; respect robots.txt; handle dynamic pages |
| **Inputs** | `CrawlRequest` (URL, depth, render_js, auth_config) |
| **Outputs** | `CrawlResult` (raw_html, rendered_text, markdown, metadata, status_code, headers) |
| **Memory** | URL frontier (Redis sorted set by priority), crawl history (PostgreSQL), robots.txt cache |
| **Tools** | Crawl4AI (primary), Firecrawl API (fallback), Playwright (complex interactions), httpx (static), feedparser (RSS) |
| **Communication** | Receives URLs from Search Agent; emits content to Extractor Agent |
| **Failure Recovery** | Fallback chain: httpx → Crawl4AI → Playwright → Firecrawl; timeout escalation |
| **Retry** | 3 retries; 429/503 → exponential backoff; 404 → mark dead, skip |

**Crawl Priority Formula:**
```
priority = (relevance_score × 0.4) + (freshness_score × 0.3)
         + (domain_authority × 0.2) + (crawl_success_rate × 0.1)
```

---

#### 🌐 Browser Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Handle JavaScript-heavy pages, infinite scroll, pagination, login-protected content, shadow DOM |
| **Inputs** | `BrowserTask` (URL, interaction_script, selectors, auth_credentials) |
| **Outputs** | `RenderedPage` (full DOM snapshot, screenshots, extracted elements) |
| **Memory** | Session cookies, authentication tokens (encrypted in Vault) |
| **Tools** | Playwright (headless Chromium), browser-use library, stealth plugins |
| **Communication** | Invoked by Crawler Agent for JS-heavy pages |
| **Failure Recovery** | Retry with different user agents; fallback to cached version |
| **Retry** | 2 retries with 5s delay; timeout at 30s |

---

#### 📄 Extractor Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Extract structured `ResearchOpportunity` objects from raw content using NLP + LLM |
| **Inputs** | `CrawlResult` (markdown text, metadata) |
| **Outputs** | `ResearchOpportunity` (fully typed Pydantic model) |
| **Memory** | Extraction templates per domain, few-shot examples, extraction accuracy history |
| **Tools** | LLM structured output (Gemini/GPT-4o), spaCy NER, regex patterns, PDF parser (PyMuPDF), DOCX parser |
| **Communication** | Receives content from Crawler; emits structured data to Validator |
| **Failure Recovery** | Multi-model fallback: Gemini → GPT-4o → Claude → regex-based extraction |
| **Retry** | 2 retries; on LLM failure, fall back to rule-based extraction |

**Core Schema (`ResearchOpportunity`):**
```python
class ResearchOpportunity(BaseModel):
    # Identity
    opportunity_id: str  # UUID
    title: str
    opportunity_type: OpportunityType  # enum: PhD, Internship, Fellowship, etc.

    # Organization
    organization: str
    department: str | None
    research_lab: str | None
    professor: str | None
    professor_email: str | None

    # Location
    country: str
    city: str | None
    location_type: LocationType  # Remote / Hybrid / Onsite

    # Research
    research_areas: list[str]
    keywords: list[str]
    required_skills: list[str]
    programming_languages: list[str]

    # Eligibility
    required_gpa: float | None
    eligibility_criteria: list[str]
    degree_level: list[DegreeLevel]
    publications_required: bool
    recommendation_letters: int | None
    visa_requirements: str | None

    # Compensation
    funding: FundingType  # Fully Funded / Partial / Self-funded / Unknown
    salary_range: str | None
    stipend: str | None

    # Timeline
    duration: str | None
    deadline: datetime | None
    start_date: datetime | None

    # Application
    application_link: str
    documents_required: list[str]
    contact_email: str | None

    # Metadata
    source_url: str
    date_discovered: datetime
    last_verified: datetime
    confidence_score: float  # 0.0 – 1.0
    authenticity_score: float  # 0.0 – 1.0
    raw_text: str
    summary: str
```

---

#### ✅ Validator Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Verify extracted data accuracy; cross-reference with known sources; detect hallucinations; validate URLs/emails |
| **Inputs** | `ResearchOpportunity` (raw extraction) |
| **Outputs** | `ValidatedOpportunity` (with confidence + authenticity scores) |
| **Memory** | Known trusted domains, historical validation patterns, known scam patterns |
| **Tools** | URL validator, email validator, domain WHOIS lookup, LLM fact-checker, cross-reference checker |
| **Communication** | Receives from Extractor; emits to Dedup Agent |
| **Failure Recovery** | Low-confidence items flagged for human review queue |
| **Retry** | 1 retry; on failure, pass through with low confidence score |

**Validation Pipeline:**
1. **URL Validation** — Is the application link live? HTTP 200?
2. **Domain Trust** — Is the source a known university/company domain?
3. **Temporal Consistency** — Is the deadline in the future?
4. **Cross-Reference** — Does the professor/lab exist on the university website?
5. **LLM Fact-Check** — Does the extracted data match the raw text? (Hallucination detection)
6. **Scam Detection** — Does it match known scam patterns (asks for money, suspicious email)?

**Scoring:**
```
authenticity = (url_valid × 0.2) + (domain_trust × 0.3) + (temporal_ok × 0.15)
             + (cross_ref × 0.2) + (llm_consistent × 0.1) + (not_scam × 0.05)
```

---

#### 🔗 Dedup Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Detect and merge duplicate opportunities using multi-signal similarity |
| **Inputs** | `ValidatedOpportunity` |
| **Outputs** | `DeduplicatedOpportunity` (merged record or link to canonical) |
| **Memory** | MinHash/LSH index, embedding similarity cache |
| **Tools** | MinHash LSH (datasketch), semantic embedding similarity, fuzzy string matching (rapidfuzz) |
| **Communication** | Receives from Validator; emits to KG Builder + Embedding Agent |
| **Failure Recovery** | Conservative dedup — when uncertain, keep both and flag for review |
| **Retry** | N/A (deterministic) |

**Dedup Algorithm:**
```
1. Compute MinHash signature of title + organization + description
2. Query LSH index for candidates (Jaccard > 0.6)
3. For each candidate:
   a. Compute embedding cosine similarity (threshold > 0.92)
   b. Compare (organization, deadline, research_area) — exact match
   c. Fuzzy match title (ratio > 0.85)
4. If 2+ signals match → DUPLICATE → merge fields, keep highest confidence
5. Else → UNIQUE → insert into LSH index
```

---

#### 🗺️ Knowledge Graph Builder Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Insert opportunities, entities, and relationships into the Neo4j knowledge graph |
| **Inputs** | `DeduplicatedOpportunity` |
| **Outputs** | Graph mutations (nodes + edges created/updated) |
| **Memory** | Entity resolution cache, graph schema |
| **Tools** | Neo4j Python driver, entity linker, relation extractor |
| **Communication** | Receives from Dedup Agent; graph is queried by Recommender Agent |
| **Failure Recovery** | Transaction rollback on partial write; retry with idempotent merge operations |
| **Retry** | 3 retries with 1s backoff |

---

#### 📐 Embedding Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Generate vector embeddings for opportunities, user profiles, and skills |
| **Inputs** | Text content (opportunity descriptions, resumes, skills) |
| **Outputs** | Vector embeddings stored in Qdrant |
| **Memory** | Embedding model version registry, normalization parameters |
| **Tools** | `text-embedding-3-large` (OpenAI), `voyage-3-large` (Voyage AI — backup), sentence-transformers (local fallback) |
| **Communication** | Receives from Dedup Agent + User Profile updates; writes to Qdrant |
| **Failure Recovery** | Model fallback chain; batch retry for failed embeddings |
| **Retry** | 3 retries; fallback to local model |

---

#### ⭐ Recommender Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Generate personalized, explainable opportunity recommendations |
| **Inputs** | User profile, query (optional), filter preferences |
| **Outputs** | `RecommendationList` — ranked opportunities with match scores and explanations |
| **Memory** | User interaction history, feedback signals, preference model |
| **Tools** | Qdrant vector search, Neo4j graph traversal, LLM reasoning, ranking algorithm |
| **Communication** | Serves API requests; reads from Qdrant + Neo4j + PostgreSQL |
| **Failure Recovery** | Degrade to simpler ranking (keyword match) if vector/graph unavailable |
| **Retry** | 2 retries |

---

#### 📊 Ranker Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Score and rank opportunities using a multi-signal fusion algorithm |
| **Inputs** | Candidate opportunities, user profile, contextual signals |
| **Outputs** | Ranked list with composite scores |
| **Memory** | Feature weights (learned from feedback), ranking model parameters |
| **Tools** | LightGBM/XGBoost ranker, feature engineering pipeline |
| **Communication** | Invoked by Recommender Agent |
| **Failure Recovery** | Fallback to rule-based scoring |
| **Retry** | N/A (deterministic) |

---

#### 👤 Profile Matcher Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Analyze user profiles (resume, GitHub, LinkedIn) and compute match scores |
| **Inputs** | User resume (PDF/DOCX), GitHub profile URL, LinkedIn data, stated preferences |
| **Outputs** | `UserProfile` — structured skills, experience, preferences + match explanations |
| **Memory** | Profile versions, skill taxonomy |
| **Tools** | LLM resume parser, GitHub API, skill extractor, GPA normalizer |
| **Communication** | Updates user profile in PostgreSQL + embeddings in Qdrant |
| **Failure Recovery** | Partial profile extraction; prompt user for missing fields |
| **Retry** | 2 retries for external API calls |

---

#### 🔔 Notifier Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Deliver personalized notifications across channels |
| **Inputs** | Notification events (new matches, deadline reminders, digests) |
| **Outputs** | Delivered notifications (email, Telegram, Discord, Slack, push) |
| **Memory** | User notification preferences, delivery history, engagement metrics |
| **Tools** | SendGrid (email), Telegram Bot API, Discord webhooks, Slack webhooks, Firebase Cloud Messaging |
| **Communication** | Subscribes to notification events from Redis Streams |
| **Failure Recovery** | Retry with exponential backoff; fallback channels; dead-letter for persistent failures |
| **Retry** | 5 retries with 2^n × 2s backoff |

---

#### ⏰ Scheduler Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Manage periodic crawl schedules, re-verification cycles, digest generation |
| **Inputs** | Schedule definitions (cron expressions, intervals) |
| **Outputs** | Triggered tasks submitted to the Orchestrator |
| **Memory** | Schedule registry, execution history, adaptive frequency parameters |
| **Tools** | APScheduler, Celery Beat, cron parser |
| **Communication** | Emits scheduled tasks to Orchestrator |
| **Failure Recovery** | Missed schedule detection and catch-up execution |
| **Retry** | Automatic rescheduling on failure |

---

#### 📡 Monitor Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Track system health, agent performance, data quality metrics |
| **Inputs** | Agent telemetry, system metrics, data quality signals |
| **Outputs** | Dashboards, alerts, performance reports |
| **Memory** | Historical metrics, SLA thresholds, anomaly baselines |
| **Tools** | Prometheus, Grafana, custom health checks |
| **Communication** | Reads OpenTelemetry traces; emits alerts to Notifier |
| **Failure Recovery** | Self-healing: restarts failed agents, scales up on queue buildup |
| **Retry** | N/A (continuous monitoring loop) |

---

#### 📈 Learning Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Continuously improve system quality from user feedback and performance data |
| **Inputs** | User clicks, saves, dismissals, explicit ratings, extraction accuracy metrics |
| **Outputs** | Updated ranking weights, improved extraction prompts, adaptive crawl priorities |
| **Memory** | Feedback corpus, A/B test results, model performance history |
| **Tools** | Online learning algorithms, prompt optimization, weight tuning |
| **Communication** | Reads feedback from PostgreSQL; updates agent configurations |
| **Failure Recovery** | Rollback to previous model weights if quality degrades |
| **Retry** | N/A (batch learning cycles) |

---

#### 💬 Feedback Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Collect, process, and route user feedback on recommendations and data quality |
| **Inputs** | User feedback events (thumbs up/down, corrections, reports) |
| **Outputs** | Structured feedback records; correction signals to relevant agents |
| **Memory** | Feedback history per user and per opportunity |
| **Tools** | Feedback classifier, sentiment analyzer |
| **Communication** | Receives from API; routes corrections to Validator, preferences to Learning Agent |
| **Failure Recovery** | Queue feedback for batch processing if real-time processing fails |
| **Retry** | 2 retries |

---

#### 📊 Analytics Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Generate insights on opportunity trends, user engagement, and system effectiveness |
| **Inputs** | Aggregated data from all system components |
| **Outputs** | Analytics dashboards, trend reports, weekly summaries |
| **Memory** | Historical analytics, computed aggregates |
| **Tools** | Pandas, DuckDB (OLAP queries), chart generators |
| **Communication** | Scheduled by Scheduler Agent; outputs to API and Notifier |
| **Failure Recovery** | Stale data tolerance — serve cached analytics if computation fails |
| **Retry** | 1 retry |

---

#### 🗣️ NLP Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Run the full NLP pipeline: NER, relation extraction, classification, summarization |
| **Inputs** | Raw text from crawled pages |
| **Outputs** | Annotated text with entities, relations, topics, and summaries |
| **Memory** | Custom NER models, domain-specific dictionaries, topic model state |
| **Tools** | spaCy (NER, POS), KeyBERT (keywords), BERTopic (topics), LLM (summarization, classification) |
| **Communication** | Invoked by Extractor Agent as a sub-pipeline |
| **Failure Recovery** | Degrade gracefully — skip optional annotations, ensure core extraction completes |
| **Retry** | 2 retries for LLM calls |

---

#### 🧠 Memory Agent

| Attribute | Detail |
|---|---|
| **Responsibility** | Manage multi-tier memory system for all agents |
| **Inputs** | Memory read/write requests from any agent |
| **Outputs** | Retrieved memories, memory consolidation results |
| **Memory** | Meta-memory (tracks what each agent has stored and accessed) |
| **Tools** | Redis (short-term), PostgreSQL (long-term), Qdrant (semantic), LangGraph checkpoints |
| **Communication** | Exposed as an internal service; all agents can read/write |
| **Failure Recovery** | Read-through cache; eventual consistency for non-critical memories |
| **Retry** | 3 retries for writes |

---

### 2.3 Agent Communication Protocol

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant S as Search Agent
    participant C as Crawler Agent
    participant E as Extractor Agent
    participant V as Validator Agent
    participant D as Dedup Agent
    participant K as KG Builder
    participant Em as Embedding Agent
    participant R as Recommender

    O->>S: SearchTask(queries, sources)
    S-->>O: SearchResults(urls[])
    O->>C: CrawlTask(urls[])
    C-->>O: CrawlResults(content[])
    O->>E: ExtractTask(content[])
    E-->>O: Opportunities(raw[])
    O->>V: ValidateTask(raw[])
    V-->>O: ValidatedOpportunities[]
    O->>D: DedupTask(validated[])
    D-->>O: UniqueOpportunities[]

    par Parallel Writes
        O->>K: GraphInsert(opportunities[])
        O->>Em: Embed(opportunities[])
    end

    Note over R: User requests recommendation
    R->>Em: VectorSearch(user_profile)
    R->>K: GraphTraversal(user_skills)
    R-->>O: RankedRecommendations[]
```

**Message Format:**
```python
class AgentMessage(BaseModel):
    message_id: str  # UUID
    source_agent: str
    target_agent: str
    task_id: str
    payload: dict[str, Any]
    timestamp: datetime
    priority: int  # 1-10
    ttl_seconds: int
    trace_id: str  # OpenTelemetry
```

---

## 3. Data Flow Diagram

```mermaid
flowchart LR
    subgraph Sources["🌐 Sources"]
        Web["Websites"]
        APIs["APIs"]
        Feeds["RSS/Feeds"]
        Social["Social Media"]
        Academic["Academic DBs"]
    end

    subgraph Discovery["🔍 Discovery"]
        Search["Search Agent"]
        Crawl["Crawler Agent"]
        Browser["Browser Agent"]
    end

    subgraph Processing["⚙️ Processing"]
        Extract["Extractor Agent"]
        NLP["NLP Pipeline"]
        Validate["Validator Agent"]
        Dedup["Dedup Agent"]
    end

    subgraph Storage["💾 Storage"]
        PG["PostgreSQL<br/>(Structured Data)"]
        QD["Qdrant<br/>(Embeddings)"]
        N4J["Neo4j<br/>(Knowledge Graph)"]
        RD["Redis<br/>(Cache + Queues)"]
        OBJ["MinIO<br/>(Raw Files)"]
    end

    subgraph UserLayer["👤 User Layer"]
        Profile["Profile Matcher"]
        Recommend["Recommender"]
        Rank["Ranker"]
        Notify["Notifier"]
        UI["Web UI"]
    end

    Sources --> Search --> Crawl
    Crawl --> Browser
    Crawl --> Extract
    Browser --> Extract
    Extract --> NLP --> Validate --> Dedup

    Dedup --> PG
    Dedup --> QD
    Dedup --> N4J

    PG --> Recommend
    QD --> Recommend
    N4J --> Recommend

    Profile --> Recommend --> Rank --> Notify --> UI
```

---

## 4. Database Schema

### 4.1 PostgreSQL — Relational Data

```sql
-- ============================================
-- CORE TABLES
-- ============================================

CREATE TABLE opportunities (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               TEXT NOT NULL,
    opportunity_type    VARCHAR(50) NOT NULL,  -- PhD, Internship, Fellowship, etc.
    organization        TEXT NOT NULL,
    department          TEXT,
    research_lab        TEXT,
    professor           TEXT,
    professor_email     TEXT,

    -- Location
    country             VARCHAR(100),
    city                VARCHAR(100),
    location_type       VARCHAR(20),  -- Remote / Hybrid / Onsite

    -- Research
    research_areas      TEXT[],       -- PostgreSQL array
    keywords            TEXT[],
    required_skills     TEXT[],
    programming_languages TEXT[],

    -- Eligibility
    required_gpa        DECIMAL(3,2),
    eligibility_criteria JSONB,
    degree_levels       TEXT[],
    publications_required BOOLEAN DEFAULT FALSE,
    recommendation_letters INTEGER,
    visa_requirements   TEXT,

    -- Compensation
    funding_type        VARCHAR(30),  -- Fully Funded / Partial / Self-funded
    salary_range        TEXT,
    stipend             TEXT,

    -- Timeline
    duration            TEXT,
    deadline            TIMESTAMPTZ,
    start_date          TIMESTAMPTZ,

    -- Application
    application_link    TEXT NOT NULL,
    documents_required  TEXT[],
    contact_email       TEXT,

    -- Metadata
    source_url          TEXT NOT NULL,
    date_discovered     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confidence_score    DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    authenticity_score  DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    is_active           BOOLEAN DEFAULT TRUE,
    is_expired          BOOLEAN DEFAULT FALSE,
    raw_text            TEXT,
    summary             TEXT,

    -- Vector reference
    qdrant_point_id     UUID,

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_opp_type ON opportunities(opportunity_type);
CREATE INDEX idx_opp_country ON opportunities(country);
CREATE INDEX idx_opp_deadline ON opportunities(deadline);
CREATE INDEX idx_opp_org ON opportunities(organization);
CREATE INDEX idx_opp_active ON opportunities(is_active, is_expired);
CREATE INDEX idx_opp_research_areas ON opportunities USING GIN(research_areas);
CREATE INDEX idx_opp_skills ON opportunities USING GIN(required_skills);
CREATE INDEX idx_opp_keywords ON opportunities USING GIN(keywords);

-- ============================================
-- USER TABLES
-- ============================================

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT UNIQUE NOT NULL,
    password_hash       TEXT NOT NULL,
    full_name           TEXT NOT NULL,
    university          TEXT,
    degree_level        VARCHAR(30),  -- Undergraduate, Masters, PhD
    gpa                 DECIMAL(3,2),
    country             TEXT,
    preferred_countries TEXT[],
    preferred_domains   TEXT[],
    career_goals        TEXT,
    linkedin_url        TEXT,
    github_url          TEXT,
    resume_url          TEXT,  -- MinIO path
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_name  TEXT NOT NULL,
    proficiency VARCHAR(20),  -- Beginner / Intermediate / Advanced / Expert
    years       INTEGER,
    UNIQUE(user_id, skill_name)
);

CREATE TABLE user_publications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    venue       TEXT,
    year        INTEGER,
    url         TEXT,
    citation_count INTEGER DEFAULT 0
);

CREATE TABLE user_projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT,
    technologies TEXT[],
    url         TEXT,
    start_date  DATE,
    end_date    DATE
);

CREATE TABLE user_research_interests (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    topic       TEXT NOT NULL,
    weight      DECIMAL(3,2) DEFAULT 1.0
);

-- ============================================
-- INTERACTION TABLES
-- ============================================

CREATE TABLE user_interactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    opportunity_id  UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL,  -- view, save, apply, dismiss, share
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    opportunity_id  UUID REFERENCES opportunities(id),
    feedback_type   VARCHAR(20) NOT NULL,  -- thumbs_up, thumbs_down, correction, report
    feedback_text   TEXT,
    corrections     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE saved_opportunities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    opportunity_id  UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    notes           TEXT,
    status          VARCHAR(20) DEFAULT 'saved',  -- saved, applying, applied, rejected, accepted
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, opportunity_id)
);

CREATE TABLE notification_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    channel         VARCHAR(20) NOT NULL,  -- email, telegram, discord, slack, push
    enabled         BOOLEAN DEFAULT TRUE,
    frequency       VARCHAR(20) DEFAULT 'daily',  -- instant, daily, weekly
    config          JSONB,  -- channel-specific config (chat_id, webhook_url, etc.)
    UNIQUE(user_id, channel)
);

-- ============================================
-- CRAWL MANAGEMENT
-- ============================================

CREATE TABLE crawl_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url             TEXT UNIQUE NOT NULL,
    domain          TEXT NOT NULL,
    source_type     VARCHAR(30),  -- university, company, government, lab, conference
    trust_score     DECIMAL(3,2) DEFAULT 0.5,
    crawl_frequency INTERVAL DEFAULT '7 days',
    last_crawled    TIMESTAMPTZ,
    last_status     INTEGER,  -- HTTP status code
    success_rate    DECIMAL(3,2) DEFAULT 1.0,
    robots_txt      TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    config          JSONB,  -- custom crawl config per source
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE crawl_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID REFERENCES crawl_sources(id),
    url             TEXT NOT NULL,
    status_code     INTEGER,
    content_hash    TEXT,  -- SHA-256 for change detection
    opportunities_found INTEGER DEFAULT 0,
    duration_ms     INTEGER,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4.2 Neo4j — Knowledge Graph Schema

```cypher
// Node Types
(:Opportunity {id, title, type, deadline, funding})
(:Organization {name, type, country, ranking})
(:Researcher {name, email, h_index, affiliation})
(:ResearchLab {name, focus_areas, organization})
(:Topic {name, parent_topic})
(:Skill {name, category})
(:Technology {name, category})
(:User {id, name, degree_level})
(:Publication {title, venue, year})
(:FundingAgency {name, country, type})
(:Conference {name, acronym, tier})

// Relationships
(:Opportunity)-[:OFFERED_BY]->(:Organization)
(:Opportunity)-[:SUPERVISED_BY]->(:Researcher)
(:Opportunity)-[:IN_LAB]->(:ResearchLab)
(:Opportunity)-[:COVERS_TOPIC]->(:Topic)
(:Opportunity)-[:REQUIRES_SKILL]->(:Skill)
(:Opportunity)-[:USES_TECHNOLOGY]->(:Technology)
(:Opportunity)-[:FUNDED_BY]->(:FundingAgency)
(:Opportunity)-[:RELATED_TO]->(:Opportunity)

(:Researcher)-[:AFFILIATED_WITH]->(:Organization)
(:Researcher)-[:LEADS]->(:ResearchLab)
(:Researcher)-[:PUBLISHED]->(:Publication)
(:Researcher)-[:RESEARCHES]->(:Topic)

(:ResearchLab)-[:PART_OF]->(:Organization)
(:ResearchLab)-[:FOCUSES_ON]->(:Topic)

(:Topic)-[:SUBTOPIC_OF]->(:Topic)
(:Topic)-[:RELATED_TO]->(:Topic)

(:User)-[:HAS_SKILL {proficiency}]->(:Skill)
(:User)-[:INTERESTED_IN {weight}]->(:Topic)
(:User)-[:APPLIED_TO]->(:Opportunity)
(:User)-[:SAVED]->(:Opportunity)
(:User)-[:STUDIED_AT]->(:Organization)

(:Organization)-[:LOCATED_IN]->(:Country)
(:Conference)-[:COVERS]->(:Topic)
```

### 4.3 Qdrant — Vector Collections

```python
# Collection: opportunities
{
    "name": "opportunities",
    "vectors": {
        "description": {"size": 3072, "distance": "Cosine"},     # text-embedding-3-large
        "title": {"size": 3072, "distance": "Cosine"},
    },
    "payload_schema": {
        "opportunity_id": "uuid",
        "opportunity_type": "keyword",
        "country": "keyword",
        "research_areas": "keyword[]",
        "required_skills": "keyword[]",
        "deadline": "datetime",
        "funding_type": "keyword",
        "is_active": "bool",
        "confidence_score": "float",
        "organization": "keyword",
        "embedding_model": "keyword",
        "model_version": "keyword"
    }
}

# Collection: user_profiles
{
    "name": "user_profiles",
    "vectors": {
        "profile": {"size": 3072, "distance": "Cosine"},
        "resume": {"size": 3072, "distance": "Cosine"},
    },
    "payload_schema": {
        "user_id": "uuid",
        "skills": "keyword[]",
        "research_interests": "keyword[]",
        "degree_level": "keyword",
        "country": "keyword"
    }
}

# Collection: skills
{
    "name": "skills",
    "vectors": {"default": {"size": 3072, "distance": "Cosine"}},
    "payload_schema": {
        "skill_name": "keyword",
        "category": "keyword",
        "aliases": "keyword[]"
    }
}
```

---

## 5. API Design

### 5.1 RESTful API (FastAPI)

```
Base URL: /api/v1

# ── Authentication ──────────────────────────────────────
POST   /auth/register              # User registration
POST   /auth/login                 # JWT login
POST   /auth/refresh               # Refresh token
POST   /auth/forgot-password       # Password reset
GET    /auth/me                    # Current user info

# ── User Profile ────────────────────────────────────────
GET    /users/profile              # Get user profile
PUT    /users/profile              # Update profile
POST   /users/profile/resume       # Upload resume (PDF/DOCX)
POST   /users/profile/parse-github # Parse GitHub profile
POST   /users/profile/parse-linkedin # Parse LinkedIn data
GET    /users/profile/skills       # Get extracted skills
PUT    /users/profile/preferences  # Update notification & search preferences

# ── Opportunities ───────────────────────────────────────
GET    /opportunities              # List with filters, pagination, sorting
GET    /opportunities/:id          # Get single opportunity detail
GET    /opportunities/:id/similar  # Get similar opportunities
GET    /opportunities/search       # Full-text + semantic search
GET    /opportunities/trending     # Trending opportunities
GET    /opportunities/expiring-soon # Deadlines within 7 days

# ── Recommendations ─────────────────────────────────────
GET    /recommendations            # Personalized recommendations
GET    /recommendations/explore    # Discovery feed (diversified)
GET    /recommendations/explain/:id # Why this opportunity matches

# ── User Actions ────────────────────────────────────────
POST   /opportunities/:id/save     # Save opportunity
DELETE /opportunities/:id/save     # Unsave
POST   /opportunities/:id/dismiss  # Dismiss (not interested)
POST   /opportunities/:id/apply    # Mark as applied
POST   /opportunities/:id/feedback # Submit feedback (thumbs up/down/correction)
GET    /saved                      # List saved opportunities
GET    /applied                    # List applied opportunities

# ── AI Features ─────────────────────────────────────────
POST   /ai/summarize/:id           # Generate opportunity summary
POST   /ai/compare                 # Compare multiple opportunities
POST   /ai/cover-letter            # Generate cover letter
POST   /ai/email-draft             # Generate professor email
POST   /ai/eligibility-check/:id   # Check user eligibility
POST   /ai/preparation-plan/:id    # Generate preparation roadmap
POST   /ai/reading-list/:id        # Generate research reading list
POST   /ai/interview-prep/:id      # Generate interview prep plan

# ── Notifications ───────────────────────────────────────
GET    /notifications              # List notifications
PUT    /notifications/:id/read     # Mark as read
PUT    /notifications/preferences  # Update notification settings

# ── Analytics ───────────────────────────────────────────
GET    /analytics/trends           # Opportunity trends
GET    /analytics/skills-demand    # In-demand skills
GET    /analytics/top-organizations # Top organizations posting

# ── Knowledge Graph ─────────────────────────────────────
GET    /graph/explore              # Explore knowledge graph
GET    /graph/researchers/:name    # Researcher profile + opportunities
GET    /graph/topics/:topic        # Topic → related opportunities, researchers
GET    /graph/paths                # Find paths between entities

# ── Admin ───────────────────────────────────────────────
POST   /admin/crawl/trigger        # Manually trigger a crawl cycle
GET    /admin/crawl/status         # Crawl pipeline status
GET    /admin/agents/status        # Agent health dashboard
GET    /admin/metrics              # System metrics
POST   /admin/sources              # Add new crawl source
GET    /admin/review-queue         # Low-confidence items for human review
```

### 5.2 WebSocket API

```
WS /ws/notifications      # Real-time notifications
WS /ws/crawl-status        # Live crawl progress (admin)
WS /ws/recommendations     # Streaming recommendations
```

---

## 6. Folder Structure

```
researchscout/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── README.md
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── cd.yml
│       └── tests.yml
│
├── backend/                           # Python (FastAPI + LangGraph)
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic/                       # Database migrations
│   │   ├── alembic.ini
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application factory
│   │   ├── config.py                  # Pydantic Settings
│   │   │
│   │   ├── api/                       # API layer
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # Dependency injection
│   │   │   ├── middleware.py          # Auth, CORS, rate limiting
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py          # Root router
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── opportunities.py
│   │   │       ├── recommendations.py
│   │   │       ├── ai_features.py
│   │   │       ├── notifications.py
│   │   │       ├── analytics.py
│   │   │       ├── graph.py
│   │   │       └── admin.py
│   │   │
│   │   ├── models/                    # SQLAlchemy + Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── db/                    # SQLAlchemy ORM models
│   │   │   │   ├── opportunity.py
│   │   │   │   ├── user.py
│   │   │   │   ├── interaction.py
│   │   │   │   ├── crawl.py
│   │   │   │   └── notification.py
│   │   │   └── schemas/               # Pydantic schemas (API contracts)
│   │   │       ├── opportunity.py
│   │   │       ├── user.py
│   │   │       ├── recommendation.py
│   │   │       ├── agent.py
│   │   │       └── common.py
│   │   │
│   │   ├── services/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── opportunity_service.py
│   │   │   ├── user_service.py
│   │   │   ├── recommendation_service.py
│   │   │   ├── notification_service.py
│   │   │   ├── analytics_service.py
│   │   │   └── ai_service.py
│   │   │
│   │   ├── agents/                    # Multi-Agent System
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py        # LangGraph supervisor
│   │   │   ├── state.py              # Shared agent state definitions
│   │   │   │
│   │   │   ├── discovery/             # Discovery Division
│   │   │   │   ├── __init__.py
│   │   │   │   ├── planner.py
│   │   │   │   ├── search_agent.py
│   │   │   │   ├── crawler_agent.py
│   │   │   │   └── browser_agent.py
│   │   │   │
│   │   │   ├── intelligence/          # Intelligence Division
│   │   │   │   ├── __init__.py
│   │   │   │   ├── extractor_agent.py
│   │   │   │   ├── nlp_agent.py
│   │   │   │   ├── validator_agent.py
│   │   │   │   └── dedup_agent.py
│   │   │   │
│   │   │   ├── knowledge/             # Knowledge Division
│   │   │   │   ├── __init__.py
│   │   │   │   ├── kg_builder_agent.py
│   │   │   │   ├── embedding_agent.py
│   │   │   │   └── memory_agent.py
│   │   │   │
│   │   │   ├── user_facing/           # User-Facing Division
│   │   │   │   ├── __init__.py
│   │   │   │   ├── recommender_agent.py
│   │   │   │   ├── ranker_agent.py
│   │   │   │   ├── profile_matcher.py
│   │   │   │   └── notifier_agent.py
│   │   │   │
│   │   │   ├── meta/                  # Meta-Agents
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scheduler_agent.py
│   │   │   │   ├── monitor_agent.py
│   │   │   │   ├── learning_agent.py
│   │   │   │   ├── feedback_agent.py
│   │   │   │   └── analytics_agent.py
│   │   │   │
│   │   │   ├── tools/                 # Shared agent tools
│   │   │   │   ├── __init__.py
│   │   │   │   ├── search_tools.py    # Google CSE, Bing, Tavily, SerpAPI
│   │   │   │   ├── crawl_tools.py     # Crawl4AI, Firecrawl, httpx
│   │   │   │   ├── browser_tools.py   # Playwright
│   │   │   │   ├── llm_tools.py       # LLM wrappers
│   │   │   │   ├── db_tools.py        # Database operations
│   │   │   │   ├── vector_tools.py    # Qdrant operations
│   │   │   │   ├── graph_tools.py     # Neo4j operations
│   │   │   │   ├── notification_tools.py
│   │   │   │   └── validation_tools.py
│   │   │   │
│   │   │   └── prompts/               # Prompt templates
│   │   │       ├── extraction.py
│   │   │       ├── validation.py
│   │   │       ├── summarization.py
│   │   │       ├── recommendation.py
│   │   │       ├── cover_letter.py
│   │   │       └── email_draft.py
│   │   │
│   │   ├── nlp/                       # NLP Pipeline
│   │   │   ├── __init__.py
│   │   │   ├── ner.py                 # Named Entity Recognition
│   │   │   ├── keyword_extraction.py  # KeyBERT
│   │   │   ├── topic_modeling.py      # BERTopic
│   │   │   ├── text_classification.py
│   │   │   ├── skill_extraction.py
│   │   │   ├── deadline_parser.py
│   │   │   └── language_detection.py
│   │   │
│   │   ├── knowledge_graph/           # KG operations
│   │   │   ├── __init__.py
│   │   │   ├── schema.py
│   │   │   ├── queries.py
│   │   │   ├── entity_linker.py
│   │   │   └── graph_algorithms.py
│   │   │
│   │   ├── vector/                    # Vector operations
│   │   │   ├── __init__.py
│   │   │   ├── embeddings.py
│   │   │   ├── search.py
│   │   │   └── collections.py
│   │   │
│   │   ├── ranking/                   # Ranking algorithms
│   │   │   ├── __init__.py
│   │   │   ├── scorer.py
│   │   │   ├── features.py
│   │   │   └── learning_to_rank.py
│   │   │
│   │   ├── core/                      # Core utilities
│   │   │   ├── __init__.py
│   │   │   ├── database.py            # SQLAlchemy async engine
│   │   │   ├── redis.py               # Redis connection
│   │   │   ├── security.py            # JWT, hashing
│   │   │   ├── logging.py             # Structured logging
│   │   │   ├── telemetry.py           # OpenTelemetry
│   │   │   └── exceptions.py
│   │   │
│   │   └── workers/                   # Background workers
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       ├── crawl_worker.py
│   │       ├── embedding_worker.py
│   │       └── notification_worker.py
│   │
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       │   ├── test_extractor.py
│       │   ├── test_validator.py
│       │   ├── test_dedup.py
│       │   ├── test_ranker.py
│       │   └── test_nlp.py
│       ├── integration/
│       │   ├── test_crawl_pipeline.py
│       │   ├── test_recommendation_pipeline.py
│       │   └── test_api.py
│       └── e2e/
│           └── test_full_pipeline.py
│
├── frontend/                          # Next.js App
│   ├── package.json
│   ├── next.config.js
│   ├── Dockerfile
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # Landing / Dashboard
│   │   │   ├── opportunities/
│   │   │   │   ├── page.tsx           # Browse opportunities
│   │   │   │   └── [id]/page.tsx      # Opportunity detail
│   │   │   ├── recommendations/
│   │   │   │   └── page.tsx
│   │   │   ├── saved/
│   │   │   │   └── page.tsx
│   │   │   ├── profile/
│   │   │   │   └── page.tsx
│   │   │   ├── explore/
│   │   │   │   └── page.tsx           # Knowledge graph explorer
│   │   │   ├── analytics/
│   │   │   │   └── page.tsx
│   │   │   └── auth/
│   │   │       ├── login/page.tsx
│   │   │       └── register/page.tsx
│   │   ├── components/
│   │   │   ├── ui/                    # Base UI components
│   │   │   ├── opportunity/           # Opportunity cards, lists
│   │   │   ├── recommendation/        # Recommendation cards
│   │   │   ├── profile/               # Profile forms
│   │   │   ├── graph/                 # KG visualization
│   │   │   └── layout/               # Header, sidebar, footer
│   │   ├── hooks/
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client
│   │   │   └── utils.ts
│   │   └── styles/
│   │       └── globals.css
│   └── tests/
│
├── infrastructure/
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   ├── Dockerfile.worker
│   │   └── Dockerfile.crawler
│   ├── k8s/
│   │   ├── namespace.yml
│   │   ├── backend-deployment.yml
│   │   ├── frontend-deployment.yml
│   │   ├── worker-deployment.yml
│   │   ├── crawler-deployment.yml
│   │   ├── postgres.yml
│   │   ├── redis.yml
│   │   ├── qdrant.yml
│   │   ├── neo4j.yml
│   │   └── ingress.yml
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── modules/
│   └── monitoring/
│       ├── prometheus.yml
│       ├── grafana/
│       │   └── dashboards/
│       └── alertmanager.yml
│
├── scripts/
│   ├── seed_sources.py                # Seed initial crawl sources
│   ├── init_db.py
│   ├── init_vector_collections.py
│   ├── init_graph_schema.py
│   └── benchmark.py
│
├── data/
│   ├── seed/
│   │   ├── sources.json               # Initial crawl sources
│   │   ├── skill_taxonomy.json
│   │   └── topic_taxonomy.json
│   └── models/                        # Trained NLP models
│
└── docs/
    ├── architecture.md
    ├── api.md
    ├── agents.md
    ├── deployment.md
    └── research.md
```

---

## 7. Technology Stack

### 7.1 Complete Stack

| Layer | Technology | Justification |
|---|---|---|
| **Backend Framework** | FastAPI (Python 3.12+) | Async-native, type-safe, OpenAPI auto-docs |
| **Agent Orchestration** | LangGraph | Stateful graph-based agent orchestration; industry standard for production |
| **Task Queue** | Celery + Redis | Distributed task processing; mature, battle-tested |
| **Frontend** | Next.js 15 (App Router) + TypeScript | SSR, RSC, modern React patterns |
| **CSS** | Tailwind CSS v4 (if user prefers) or Vanilla CSS | Utility-first or custom design system |
| **Relational DB** | PostgreSQL 16 | ACID, JSONB, array types, full-text search, pg_cron |
| **Vector DB** | Qdrant | Best price-performance; Rust-based; excellent filtering |
| **Graph DB** | Neo4j Community | Industry-standard graph DB; Cypher query language |
| **Cache / Message Bus** | Redis 7 (Streams + Pub/Sub) | In-memory cache, message broker, rate limiting |
| **Object Storage** | MinIO (self-hosted S3) | Store raw crawl data, resumes, PDFs |
| **LLM — Primary** | Google Gemini 2.5 Flash | Fast, cheap, excellent structured output |
| **LLM — Complex Reasoning** | GPT-4o / Claude Sonnet 4 | High-quality reasoning for validation, cover letters |
| **Embedding Model** | `text-embedding-3-large` (OpenAI) | 3072-dim, best retrieval quality |
| **Embedding — Local Fallback** | `all-MiniLM-L6-v2` (sentence-transformers) | Free, fast, 384-dim |
| **NER** | spaCy (en_core_web_trf) | Transformer-based NER, fast inference |
| **Keyword Extraction** | KeyBERT | BERT-based keyword extraction |
| **Topic Modeling** | BERTopic | Neural topic modeling |
| **Web Crawling** | Crawl4AI (primary), httpx (static), Playwright (complex) | Open-source, AI-native, full JS rendering |
| **Crawling — Managed Fallback** | Firecrawl API | Handles anti-bot, proxies, CAPTCHAs |
| **PDF Parsing** | PyMuPDF (fitz) | Fast, accurate PDF text extraction |
| **Deduplication** | datasketch (MinHash LSH) + rapidfuzz | Probabilistic + fuzzy string matching |
| **Search APIs** | Google CSE, Bing API, Tavily, SerpAPI, Semantic Scholar, OpenAlex | Multi-engine search coverage |
| **Auth** | JWT (python-jose) + OAuth2 (Google, GitHub) | Standard token-based auth |
| **Monitoring** | Prometheus + Grafana | Metrics collection + visualization |
| **Tracing** | OpenTelemetry + Jaeger | Distributed tracing across agent handoffs |
| **Logging** | structlog + Loki | Structured JSON logging with Grafana Loki |
| **Containerization** | Docker + Docker Compose | Local development and deployment |
| **Orchestration** | Kubernetes (production) | Container orchestration, auto-scaling |
| **CI/CD** | GitHub Actions | Automated testing and deployment |
| **IaC** | Terraform | Infrastructure as code for cloud deployment |
| **Email** | SendGrid / Resend | Transactional email delivery |
| **Notifications** | Telegram Bot API, Discord Webhooks, Slack Webhooks | Multi-channel notifications |
| **Rate Limiting** | Redis-based token bucket | API and crawl rate limiting |
| **Scheduling** | APScheduler + Celery Beat | Cron-based job scheduling |

### 7.2 Python Dependencies (Key)

```toml
[project]
dependencies = [
    # Web Framework
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.10",
    "pydantic-settings>=2.6",

    # Agent Orchestration
    "langgraph>=0.3",
    "langchain-core>=0.3",
    "langchain-openai>=0.3",
    "langchain-google-genai>=2.1",

    # Database
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",          # Async PostgreSQL
    "alembic>=1.14",
    "redis>=5.2",

    # Vector DB
    "qdrant-client>=1.12",

    # Graph DB
    "neo4j>=5.26",

    # LLMs
    "openai>=1.60",
    "google-genai>=1.5",
    "anthropic>=0.40",

    # NLP
    "spacy>=3.8",
    "keybert>=0.8",
    "bertopic>=0.16",
    "sentence-transformers>=3.4",

    # Crawling
    "crawl4ai>=0.5",
    "httpx>=0.28",
    "playwright>=1.49",
    "feedparser>=6.0",
    "beautifulsoup4>=4.12",

    # Parsing
    "pymupdf>=1.25",        # PDF
    "python-docx>=1.1",     # DOCX
    "markdownify>=0.14",    # HTML → Markdown

    # Dedup
    "datasketch>=1.6",
    "rapidfuzz>=3.10",

    # Task Queue
    "celery[redis]>=5.4",

    # Auth
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "python-multipart>=0.0.18",

    # Observability
    "opentelemetry-api>=1.29",
    "opentelemetry-sdk>=1.29",
    "opentelemetry-instrumentation-fastapi>=0.50",
    "structlog>=24.4",
    "prometheus-client>=0.21",

    # Utilities
    "tenacity>=9.0",        # Retry library
    "apscheduler>=3.10",
    "python-dateutil>=2.9",
    "tldextract>=5.1",
]
```

---

## 8. Algorithms

### 8.1 Opportunity Ranking Algorithm (Multi-Signal Fusion)

```python
def compute_rank_score(opportunity, user_profile, context) -> RankScore:
    """
    Multi-signal fusion ranking with learned weights.

    Score = Σ (wᵢ × fᵢ)  where wᵢ are learned weights
    """

    features = {
        # Relevance signals (0.0 – 1.0)
        "semantic_similarity":     cosine_sim(opp.embedding, user.embedding),      # w=0.25
        "skill_overlap":           jaccard(opp.required_skills, user.skills),       # w=0.15
        "topic_relevance":         topic_match(opp.research_areas, user.interests), # w=0.12
        "keyword_match":           bm25_score(opp.keywords, user.query),            # w=0.05

        # Quality signals
        "confidence_score":        opp.confidence_score,                            # w=0.08
        "authenticity_score":      opp.authenticity_score,                          # w=0.07
        "organization_ranking":    normalize(org_ranking(opp.organization)),        # w=0.05
        "professor_reputation":    normalize(h_index(opp.professor)),               # w=0.03

        # Urgency signals
        "deadline_urgency":        deadline_decay(opp.deadline),                    # w=0.06
        "freshness":               freshness_decay(opp.date_discovered),            # w=0.04

        # User-specific signals
        "eligibility_match":       eligibility_score(opp, user),                    # w=0.05
        "location_preference":     location_match(opp.country, user.preferences),   # w=0.03
        "funding_quality":         funding_score(opp.funding_type),                 # w=0.02

        # Popularity signals (from collective behavior)
        "save_rate":               opp.saves / max(opp.views, 1),                   # w=0.02
        "apply_rate":              opp.applies / max(opp.views, 1),                 # w=0.01
    }

    # Weighted sum with learned weights (initialized as above, updated by Learning Agent)
    score = sum(weights[k] * features[k] for k in features)

    return RankScore(
        total=score,
        breakdown=features,
        explanation=generate_explanation(features, weights)
    )


def deadline_decay(deadline: datetime) -> float:
    """Sigmoid decay: urgency increases as deadline approaches."""
    if deadline is None:
        return 0.5
    days_left = (deadline - now()).days
    if days_left < 0:
        return 0.0  # Expired
    return 1.0 / (1.0 + math.exp(0.1 * (days_left - 14)))  # Peak at 14 days


def freshness_decay(discovered: datetime) -> float:
    """Exponential decay: newer is better."""
    days_old = (now() - discovered).days
    return math.exp(-0.05 * days_old)  # Half-life ≈ 14 days
```

### 8.2 Semantic Deduplication Algorithm

```python
def deduplicate(new_opp: ResearchOpportunity, lsh_index, vector_db) -> DeduplicateResult:
    """
    Multi-signal dedup: MinHash LSH + embedding similarity + field comparison
    """
    # Stage 1: MinHash LSH (fast, approximate)
    text = f"{new_opp.title} {new_opp.organization} {new_opp.summary}"
    minhash = MinHash(num_perm=128)
    for word in text.lower().split():
        minhash.update(word.encode('utf-8'))

    candidates = lsh_index.query(minhash)  # Jaccard > 0.5

    if not candidates:
        lsh_index.insert(new_opp.id, minhash)
        return DeduplicateResult(is_duplicate=False)

    # Stage 2: Embedding similarity (semantic)
    new_embedding = embed(new_opp.summary)
    for cand_id in candidates:
        cand = load_opportunity(cand_id)
        cand_embedding = vector_db.get_vector(cand_id)

        sim = cosine_similarity(new_embedding, cand_embedding)
        title_sim = rapidfuzz.ratio(new_opp.title, cand.title) / 100
        org_match = new_opp.organization.lower() == cand.organization.lower()

        # Stage 3: Multi-signal decision
        signals = [
            sim > 0.92,          # Semantic similarity
            title_sim > 0.85,    # Title fuzzy match
            org_match,           # Same organization
        ]

        if sum(signals) >= 2:
            # DUPLICATE: merge, keeping highest confidence
            merged = merge_opportunities(new_opp, cand)
            return DeduplicateResult(is_duplicate=True, canonical_id=cand_id, merged=merged)

    lsh_index.insert(new_opp.id, minhash)
    return DeduplicateResult(is_duplicate=False)
```

### 8.3 Adaptive Crawl Scheduling Algorithm

```python
def compute_crawl_priority(source: CrawlSource) -> float:
    """
    Prioritize sources that yield high-quality, fresh opportunities.

    Uses a multi-armed bandit (UCB1) approach:
    priority = exploitation + exploration
    """
    # Exploitation: historical yield rate
    yield_rate = source.total_opportunities_found / max(source.total_crawls, 1)
    quality_avg = source.avg_confidence_score
    exploitation = yield_rate * quality_avg

    # Exploration: UCB1 upper confidence bound
    total_crawls_all = sum(s.total_crawls for s in all_sources)
    exploration = math.sqrt(2 * math.log(total_crawls_all) / max(source.total_crawls, 1))

    # Recency boost: penalize sources not crawled recently
    hours_since_crawl = (now() - source.last_crawled).total_seconds() / 3600
    recency_factor = 1 - math.exp(-0.01 * hours_since_crawl)  # Grows over time

    # Domain trust
    domain_trust = source.trust_score

    priority = (
        exploitation * 0.4 +
        exploration * 0.2 +
        recency_factor * 0.25 +
        domain_trust * 0.15
    )

    return priority
```

### 8.4 Recommendation Explanation Generation

```python
def generate_match_explanation(
    opportunity: ResearchOpportunity,
    user: UserProfile,
    features: dict[str, float]
) -> MatchExplanation:
    """Generate human-readable explanation for why an opportunity matches."""

    strengths = []
    gaps = []

    # Skill analysis
    matched_skills = set(opportunity.required_skills) & set(user.skills)
    missing_skills = set(opportunity.required_skills) - set(user.skills)
    if matched_skills:
        strengths.append(f"Strong match on: {', '.join(sorted(matched_skills))}")
    if missing_skills:
        gaps.append(f"Consider developing: {', '.join(sorted(missing_skills))}")

    # Topic analysis
    topic_overlap = set(opportunity.research_areas) & set(user.research_interests)
    if topic_overlap:
        strengths.append(f"Aligns with your research in: {', '.join(sorted(topic_overlap))}")

    # Eligibility
    if user.gpa and opportunity.required_gpa:
        if user.gpa >= opportunity.required_gpa:
            strengths.append(f"GPA {user.gpa} exceeds minimum {opportunity.required_gpa}")
        else:
            gaps.append(f"GPA {user.gpa} below preferred {opportunity.required_gpa}")

    # Publications
    if opportunity.publications_required and user.publications:
        strengths.append(f"You have {len(user.publications)} publications")
    elif opportunity.publications_required:
        gaps.append("Publications recommended — consider submitting to workshops")

    return MatchExplanation(
        match_score=round(features['semantic_similarity'] * 100),
        strengths=strengths,
        gaps=gaps,
        overall=f"Match Score: {round(features['semantic_similarity'] * 100)}%"
    )
```

---

## 9. Prompt Engineering Strategy

### 9.1 Prompt Architecture

| Layer | Strategy |
|---|---|
| **System Prompts** | Role-specific personas for each agent with guardrails |
| **Few-Shot Examples** | Domain-specific examples per opportunity type (PhD, internship, etc.) |
| **Structured Output** | Pydantic model → JSON Schema → LLM structured output mode |
| **Chain-of-Thought** | Explicit reasoning steps for validation and eligibility checking |
| **Prompt Versioning** | All prompts versioned in `prompts/` directory with A/B testing support |
| **Dynamic Context** | Inject relevant user profile data, skill taxonomy, and examples |

### 9.2 Key Prompts

**Extraction Prompt (Gemini 2.5 Flash — Structured Output):**
```python
EXTRACTION_SYSTEM_PROMPT = """
You are an expert research opportunity information extractor.

Given a webpage's text content, extract structured information about research
opportunities (internships, PhD positions, fellowships, etc.).

Rules:
1. Extract ONLY information explicitly stated in the text. Never infer or hallucinate.
2. If a field is not mentioned, set it to null.
3. For deadlines, normalize to ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).
4. For research areas, use standardized terms from computer science taxonomy.
5. Assign a confidence_score (0.0-1.0) based on how clearly the information
   was stated in the text.
6. Extract ALL opportunities if the page lists multiple.

Output must conform to the provided JSON schema.
"""

EXTRACTION_FEW_SHOT = [
    {
        "input": "We are looking for a PhD student in NLP at ETH Zurich...",
        "output": {
            "title": "PhD Position in Natural Language Processing",
            "opportunity_type": "PhD",
            "organization": "ETH Zurich",
            # ... complete example
        }
    },
    # 3-5 diverse examples covering different opportunity types
]
```

**Validation Prompt (GPT-4o — Chain-of-Thought):**
```python
VALIDATION_SYSTEM_PROMPT = """
You are a fact-checking agent for research opportunities.

Given:
1. The original webpage text
2. The extracted structured data

Your task:
Step 1: Verify each extracted field against the original text.
Step 2: Flag any field where the extraction doesn't match the source.
Step 3: Check for logical consistency (e.g., deadline in the future,
        valid country names, reasonable GPA range).
Step 4: Assign a confidence score for each field.
Step 5: Assign an overall authenticity score.

Output a ValidationReport with field-level scores and any corrections.
"""
```

**Recommendation Explanation Prompt:**
```python
RECOMMENDATION_EXPLAIN_PROMPT = """
You are a career advisor explaining why a research opportunity matches a student.

Given:
- Student Profile: {user_profile}
- Opportunity: {opportunity}
- Match Features: {feature_breakdown}

Generate a concise, encouraging explanation covering:
1. Why this is a strong match (2-3 specific reasons)
2. Any gaps the student should address (0-2 items)
3. A concrete next step

Tone: Professional, encouraging, specific. Avoid generic advice.
Max length: 150 words.
"""
```

---

## 10. Memory Architecture

```mermaid
graph TB
    subgraph ShortTerm["Short-Term Memory (Redis)"]
        ST1["Active crawl URLs (TTL: 1h)"]
        ST2["Recent search results (TTL: 24h)"]
        ST3["Rate limit counters (TTL: 1min)"]
        ST4["Agent task state (TTL: 1h)"]
        ST5["User session cache (TTL: 30min)"]
    end

    subgraph LongTerm["Long-Term Memory (PostgreSQL)"]
        LT1["All extracted opportunities"]
        LT2["User profiles & preferences"]
        LT3["Interaction history"]
        LT4["Crawl history & success rates"]
        LT5["Feedback records"]
        LT6["Agent execution logs"]
    end

    subgraph Vector["Vector Memory (Qdrant)"]
        V1["Opportunity embeddings"]
        V2["User profile embeddings"]
        V3["Skill embeddings"]
        V4["Query embeddings (search history)"]
    end

    subgraph Graph["Knowledge Memory (Neo4j)"]
        G1["Entity relationships"]
        G2["Topic hierarchies"]
        G3["Researcher networks"]
        G4["Organization connections"]
    end

    subgraph Conversation["Conversation Memory (LangGraph Checkpoints)"]
        C1["Agent state snapshots"]
        C2["Task execution DAGs"]
        C3["Decision audit trail"]
    end

    subgraph Learning["Learning Memory (PostgreSQL + Redis)"]
        L1["Ranking weight history"]
        L2["Extraction accuracy metrics"]
        L3["User preference models"]
        L4["A/B test results"]
        L5["Prompt performance scores"]
    end

    subgraph Feedback["Feedback Memory (PostgreSQL)"]
        F1["User corrections"]
        F2["Quality reports"]
        F3["Relevance signals"]
    end
```

### Memory Access Patterns

| Agent | Short-Term | Long-Term | Vector | Graph | Conversation | Learning |
|---|---|---|---|---|---|---|
| Planner | R/W | R | — | — | R/W | R |
| Search | R/W | R | R | — | — | — |
| Crawler | R/W | R/W | — | — | — | R |
| Extractor | R | W | — | — | — | R |
| Validator | R | R/W | — | R | — | R |
| Dedup | R/W | R/W | R/W | — | — | — |
| KG Builder | — | R | — | R/W | — | — |
| Embedding | — | R | R/W | — | — | — |
| Recommender | R | R | R | R | — | R |
| Ranker | R | R | R | — | — | R/W |
| Profile Matcher | — | R/W | R/W | — | — | — |
| Notifier | R | R/W | — | — | — | — |
| Learning | — | R/W | — | — | — | R/W |

---

## 11. Recommendation Engine

### 11.1 Architecture

```mermaid
flowchart TD
    UserReq["User Request<br/>(profile + optional query)"]

    subgraph Retrieval["Stage 1: Candidate Retrieval (fast, broad)"]
        VS["Vector Search<br/>Top-100 by embedding similarity"]
        KG["Graph Traversal<br/>2-hop neighbors in KG"]
        FTS["Full-Text Search<br/>BM25 on PostgreSQL"]
    end

    Merge["Candidate Merger<br/>(union + dedup)"]

    subgraph Scoring["Stage 2: Scoring (precise, per-candidate)"]
        FS["Feature Scorer<br/>15 features × learned weights"]
        Elig["Eligibility Filter<br/>Hard constraints check"]
    end

    subgraph Ranking["Stage 3: Ranking & Diversification"]
        LTR["Learning-to-Rank<br/>(LightGBM)"]
        MMR["MMR Diversification<br/>λ=0.7"]
    end

    subgraph Explanation["Stage 4: Explanation"]
        Explain["LLM Explanation Generator"]
    end

    UserReq --> Retrieval
    VS --> Merge
    KG --> Merge
    FTS --> Merge
    Merge --> Scoring
    FS --> Ranking
    Elig --> Ranking
    LTR --> MMR
    MMR --> Explain
    Explain --> Output["Ranked, Explained Recommendations"]
```

### 11.2 Retrieval Strategy

```python
async def retrieve_candidates(user: UserProfile, query: str | None, limit: int = 100):
    """Multi-source candidate retrieval with reciprocal rank fusion."""

    # Source 1: Vector similarity (Qdrant)
    vector_results = await qdrant.search(
        collection="opportunities",
        query_vector=embed(user.profile_text + (query or "")),
        limit=limit,
        filter=Filter(
            must=[
                FieldCondition(key="is_active", match=MatchValue(value=True)),
            ]
        )
    )

    # Source 2: Knowledge Graph (Neo4j) — 2-hop traversal
    graph_results = await neo4j.query("""
        MATCH (u:User {id: $user_id})-[:INTERESTED_IN]->(t:Topic)
              <-[:COVERS_TOPIC]-(o:Opportunity)
        WHERE o.is_active = true
        RETURN o.id, count(t) AS topic_overlap
        ORDER BY topic_overlap DESC
        LIMIT $limit
    """, user_id=user.id, limit=limit)

    # Source 3: Full-text search (PostgreSQL)
    fts_results = await db.execute("""
        SELECT id, ts_rank(search_vector, plainto_tsquery($1)) AS rank
        FROM opportunities
        WHERE search_vector @@ plainto_tsquery($1)
          AND is_active = true
        ORDER BY rank DESC
        LIMIT $2
    """, user.search_query, limit)

    # Reciprocal Rank Fusion (RRF)
    k = 60  # RRF constant
    scores = defaultdict(float)
    for rank, result in enumerate(vector_results):
        scores[result.id] += 1.0 / (k + rank + 1)
    for rank, result in enumerate(graph_results):
        scores[result.id] += 1.0 / (k + rank + 1)
    for rank, result in enumerate(fts_results):
        scores[result.id] += 1.0 / (k + rank + 1)

    # Return top candidates sorted by fused score
    sorted_ids = sorted(scores, key=scores.get, reverse=True)[:limit]
    return sorted_ids
```

### 11.3 Maximal Marginal Relevance (MMR) Diversification

```python
def mmr_diversify(
    candidates: list[ScoredOpportunity],
    embeddings: dict[str, np.ndarray],
    lambda_: float = 0.7,
    top_k: int = 20
) -> list[ScoredOpportunity]:
    """
    Select diverse set of recommendations using MMR.
    λ = 0.7 balances relevance (70%) vs diversity (30%).
    """
    selected = []
    remaining = list(candidates)

    # Select first item (highest score)
    selected.append(remaining.pop(0))

    while len(selected) < top_k and remaining:
        best_score = -inf
        best_idx = 0

        for i, cand in enumerate(remaining):
            # Relevance to user
            relevance = cand.score

            # Max similarity to already-selected items
            max_sim = max(
                cosine_similarity(embeddings[cand.id], embeddings[s.id])
                for s in selected
            )

            # MMR score
            mmr = lambda_ * relevance - (1 - lambda_) * max_sim

            if mmr > best_score:
                best_score = mmr
                best_idx = i

        selected.append(remaining.pop(best_idx))

    return selected
```

---

## 12. Search Pipeline

```mermaid
flowchart TD
    Trigger["Trigger<br/>(Scheduled / Manual / Event)"]

    subgraph Planning["1. Query Planning"]
        QGen["Query Generator<br/>Generate diverse search queries"]
        SrcSelect["Source Selector<br/>Pick optimal sources per query"]
    end

    subgraph Execution["2. Multi-Engine Search"]
        Google["Google CSE"]
        Bing["Bing Web API"]
        Tavily["Tavily Search"]
        Scholar["Semantic Scholar"]
        OpenAlex["OpenAlex API"]
        GitHub["GitHub Search"]
        Site["Site-Specific<br/>RSS + API"]
    end

    subgraph PostProcess["3. Post-Processing"]
        Dedup["URL Deduplication"]
        Filter["Domain Filtering<br/>(whitelist/blacklist)"]
        Priority["Priority Scoring"]
        Cache["Cache Check<br/>(skip recently crawled)"]
    end

    Output["URL Queue<br/>(Redis Sorted Set)"]

    Trigger --> Planning
    QGen --> SrcSelect
    SrcSelect --> Execution
    Google --> PostProcess
    Bing --> PostProcess
    Tavily --> PostProcess
    Scholar --> PostProcess
    OpenAlex --> PostProcess
    GitHub --> PostProcess
    Site --> PostProcess
    Dedup --> Filter --> Priority --> Cache --> Output
```

### Query Generation Strategy

```python
QUERY_TEMPLATES = [
    # Broad discovery
    "{opportunity_type} {research_area} {year}",
    "site:{domain} {opportunity_type} {research_area}",

    # Targeted
    '"{organization}" {opportunity_type} open positions {year}',
    '"{professor_name}" research {opportunity_type} {year}',

    # Deadline-aware
    "{opportunity_type} {research_area} deadline {month} {year}",

    # Funding-specific
    "fully funded {opportunity_type} {research_area} {country}",
    "{funding_body} fellowship {research_area} {year}",
]

OPPORTUNITY_TYPES = [
    "PhD position", "research internship", "postdoc",
    "research assistant", "fellowship", "scholarship",
    "summer school", "AI residency", "research program",
    "master thesis", "undergraduate research"
]

RESEARCH_AREAS = [
    "machine learning", "NLP", "computer vision",
    "reinforcement learning", "robotics", "AI safety",
    "knowledge graphs", "information retrieval"
    # ... expanded from user interest data
]
```

---

## 13. Crawling Strategy

### 13.1 Crawl Architecture

```mermaid
flowchart TD
    URLQueue["URL Priority Queue<br/>(Redis Sorted Set)"]

    subgraph Router["Crawl Router"]
        Classify["Classify URL Type"]
        Static["Static HTML?"]
        Dynamic["JS-Heavy?"]
        API["Has API?"]
        PDF["PDF/Doc?"]
        RSS["RSS Feed?"]
    end

    subgraph Engines["Crawl Engines"]
        HTTPX["httpx<br/>(Static HTML)"]
        C4AI["Crawl4AI<br/>(AI-Native)"]
        PW["Playwright<br/>(Complex JS)"]
        FC["Firecrawl<br/>(Anti-Bot)"]
        FP["feedparser<br/>(RSS/Atom)"]
        PyMu["PyMuPDF<br/>(PDF)"]
    end

    subgraph QC["Quality Control"]
        Robots["robots.txt Check"]
        Rate["Rate Limiter<br/>(per domain)"]
        Timeout["Timeout Handler"]
        Retry["Retry Manager"]
        Change["Change Detector<br/>(content hash)"]
    end

    Output["Raw Content Queue"]

    URLQueue --> Router
    Classify --> Static --> HTTPX
    Classify --> Dynamic --> C4AI
    Dynamic --> PW
    Classify --> API --> HTTPX
    Classify --> PDF --> PyMu
    Classify --> RSS --> FP

    HTTPX --> QC
    C4AI --> QC
    PW --> QC
    FC --> QC
    FP --> QC
    PyMu --> QC

    QC --> Output
```

### 13.2 Rate Limiting Strategy

```python
class DomainRateLimiter:
    """Token bucket rate limiter per domain, stored in Redis."""

    DEFAULT_RATE = 1.0        # 1 request/second
    POLITE_RATE = 0.2         # 1 request/5 seconds (for sensitive domains)
    AGGRESSIVE_RATE = 5.0     # 5 requests/second (for APIs)

    DOMAIN_RATES = {
        "*.edu": 0.5,         # Universities: be polite
        "*.gov": 0.3,         # Government: very polite
        "github.com": 2.0,    # GitHub API allows more
        "scholar.google.com": 0.1,  # Very restrictive
    }

    async def acquire(self, domain: str) -> bool:
        rate = self._get_rate(domain)
        key = f"ratelimit:{domain}"
        # Redis-based token bucket
        ...
```

### 13.3 Robots.txt Compliance

```python
class RobotsTxtChecker:
    """Cache and respect robots.txt for every domain."""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.cache_ttl = 86400  # 24 hours

    async def can_fetch(self, url: str, user_agent: str = "ResearchScoutBot/1.0") -> bool:
        domain = extract_domain(url)
        robots_txt = await self._get_cached_robots(domain)
        parser = RobotFileParser()
        parser.parse(robots_txt.splitlines())
        return parser.can_fetch(user_agent, url)
```

---

## 14. Information Extraction Pipeline

```mermaid
flowchart TD
    Raw["Raw Content<br/>(HTML/Markdown/PDF)"]

    subgraph Preprocessing["1. Preprocessing"]
        Clean["HTML Cleaning<br/>(remove nav, ads, footer)"]
        Convert["Convert to Markdown"]
        Segment["Text Segmentation<br/>(split into sections)"]
        Lang["Language Detection"]
    end

    subgraph NLPipe["2. NLP Pipeline"]
        NER["Named Entity Recognition<br/>(spaCy)"]
        KW["Keyword Extraction<br/>(KeyBERT)"]
        Topic["Topic Classification<br/>(BERTopic / LLM)"]
        Skill["Skill Extraction<br/>(custom model)"]
        Date["Deadline Parsing<br/>(dateutil + LLM)"]
    end

    subgraph LLMExtract["3. LLM Structured Extraction"]
        Classify["Classify: Is this an opportunity?<br/>(binary, fast)"]
        Extract["Extract all fields<br/>(Gemini structured output)"]
        Enrich["Enrich missing fields<br/>(GPT-4o reasoning)"]
    end

    subgraph PostProc["4. Post-Processing"]
        Normalize["Normalize fields<br/>(dates, countries, skills)"]
        Score["Compute confidence scores"]
        Link["Entity linking<br/>(match to KG entities)"]
    end

    Output["ResearchOpportunity<br/>(Pydantic model)"]

    Raw --> Preprocessing
    Clean --> Convert --> Segment --> Lang
    Lang --> NLPipe
    NER --> LLMExtract
    KW --> LLMExtract
    Topic --> LLMExtract
    Skill --> LLMExtract
    Date --> LLMExtract
    Classify -->|yes| Extract --> Enrich --> PostProc
    Classify -->|no| Discard["Discard"]
    Normalize --> Score --> Link --> Output
```

### Extraction Confidence Scoring

```python
def compute_field_confidence(field_name: str, value: Any, raw_text: str) -> float:
    """Per-field confidence based on extraction source and verifiability."""

    if value is None:
        return 0.0

    # Check if the extracted value appears verbatim in the raw text
    verbatim_match = str(value).lower() in raw_text.lower()

    # Field-specific heuristics
    match field_name:
        case "title":
            return 0.95 if verbatim_match else 0.7
        case "organization":
            return 0.9 if verbatim_match else 0.6
        case "deadline":
            return 0.85 if verbatim_match else 0.5  # Date parsing can be ambiguous
        case "required_skills":
            return 0.8 if any(s.lower() in raw_text.lower() for s in value) else 0.4
        case "funding_type":
            return 0.7  # Often inferred
        case _:
            return 0.75 if verbatim_match else 0.5
```

---

## 15. Vector Search Pipeline

```mermaid
flowchart TD
    subgraph Ingestion["Ingestion Pipeline"]
        NewOpp["New Opportunity"]
        Chunk["Chunking Strategy<br/>(title + summary + skills)"]
        Embed["Generate Embedding<br/>(text-embedding-3-large)"]
        Meta["Attach Payload Metadata"]
        Upsert["Upsert to Qdrant"]
    end

    subgraph Query["Query Pipeline"]
        UserQ["User Query / Profile"]
        QEmbed["Embed Query"]
        QFilter["Build Metadata Filters"]
        Search["Qdrant Search<br/>(ANN + filters)"]
        Rerank["Cross-Encoder Reranking<br/>(Top-50 → Top-20)"]
    end

    subgraph Maintenance["Maintenance"]
        Expire["Mark expired vectors"]
        Refresh["Re-embed on model update"]
        Compact["Collection compaction"]
    end

    NewOpp --> Chunk --> Embed --> Meta --> Upsert
    UserQ --> QEmbed --> QFilter --> Search --> Rerank
```

### Embedding Strategy

```python
class EmbeddingService:
    """Multi-model embedding service with versioning."""

    PRIMARY_MODEL = "text-embedding-3-large"      # 3072 dims
    FALLBACK_MODEL = "all-MiniLM-L6-v2"           # 384 dims (local)

    def embed_opportunity(self, opp: ResearchOpportunity) -> dict[str, list[float]]:
        """Generate named vectors for multi-vector search."""

        # Description vector: rich semantic content
        desc_text = f"""
        {opp.title}. {opp.organization}. {opp.department or ''}.
        Research areas: {', '.join(opp.research_areas)}.
        Required skills: {', '.join(opp.required_skills)}.
        {opp.summary}
        """

        # Title vector: for title-to-title matching
        title_text = f"{opp.title} at {opp.organization}"

        return {
            "description": self.embed(desc_text.strip()),
            "title": self.embed(title_text.strip()),
        }

    def embed_user_profile(self, user: UserProfile) -> dict[str, list[float]]:
        """Generate user profile embedding."""

        profile_text = f"""
        {user.full_name}. {user.degree_level} at {user.university}.
        Skills: {', '.join(user.skills)}.
        Research interests: {', '.join(user.research_interests)}.
        Career goals: {user.career_goals}.
        Preferred domains: {', '.join(user.preferred_domains)}.
        """

        resume_text = user.parsed_resume_text or ""

        return {
            "profile": self.embed(profile_text.strip()),
            "resume": self.embed(resume_text[:8000]),  # Truncate long resumes
        }
```

---

## 16. Knowledge Graph Architecture

### 16.1 Graph Schema (Visual)

```mermaid
graph LR
    O["🎓 Opportunity"] -->|OFFERED_BY| Org["🏛️ Organization"]
    O -->|SUPERVISED_BY| R["👨‍🔬 Researcher"]
    O -->|COVERS_TOPIC| T["📚 Topic"]
    O -->|REQUIRES_SKILL| S["💻 Skill"]
    O -->|FUNDED_BY| F["💰 Funding Agency"]
    O -->|RELATED_TO| O2["🎓 Opportunity"]

    R -->|AFFILIATED_WITH| Org
    R -->|LEADS| Lab["🔬 Research Lab"]
    R -->|PUBLISHED| Pub["📄 Publication"]
    R -->|RESEARCHES| T

    Lab -->|PART_OF| Org
    Lab -->|FOCUSES_ON| T

    T -->|SUBTOPIC_OF| T2["📚 Parent Topic"]

    U["👤 User"] -->|HAS_SKILL| S
    U -->|INTERESTED_IN| T
    U -->|SAVED| O
    U -->|STUDIED_AT| Org

    Conf["📢 Conference"] -->|COVERS| T
```

### 16.2 Key Graph Queries

```cypher
// 1. Personalized opportunity discovery (2-hop)
MATCH (u:User {id: $userId})-[:INTERESTED_IN]->(t:Topic)
      <-[:COVERS_TOPIC]-(o:Opportunity)
WHERE o.is_active = true AND o.deadline > datetime()
WITH o, count(t) AS topicOverlap
OPTIONAL MATCH (o)-[:REQUIRES_SKILL]->(s:Skill)<-[:HAS_SKILL]-(u)
WITH o, topicOverlap, count(s) AS skillOverlap
RETURN o, topicOverlap, skillOverlap
ORDER BY topicOverlap + skillOverlap DESC
LIMIT 50

// 2. Find related opportunities through shared researchers
MATCH (o1:Opportunity {id: $oppId})-[:SUPERVISED_BY]->(r:Researcher)
      -[:LEADS]->(lab:ResearchLab)-[:FOCUSES_ON]->(t:Topic)
      <-[:COVERS_TOPIC]-(o2:Opportunity)
WHERE o2.is_active = true AND o2.id <> o1.id
RETURN DISTINCT o2, r.name, lab.name, collect(t.name) AS shared_topics
LIMIT 10

// 3. Researcher network exploration
MATCH path = (r1:Researcher {name: $name})-[:PUBLISHED]->(:Publication)
      <-[:PUBLISHED]-(r2:Researcher)-[:LEADS]->(lab:ResearchLab)
WHERE r1 <> r2
RETURN r2, lab, length(path) AS distance
ORDER BY distance
LIMIT 20

// 4. Trending topics by opportunity count (last 30 days)
MATCH (o:Opportunity)-[:COVERS_TOPIC]->(t:Topic)
WHERE o.date_discovered > datetime() - duration({days: 30})
RETURN t.name, count(o) AS opportunity_count
ORDER BY opportunity_count DESC
LIMIT 20

// 5. Skill gap analysis for a user
MATCH (u:User {id: $userId})-[:INTERESTED_IN]->(t:Topic)
      <-[:COVERS_TOPIC]-(o:Opportunity)-[:REQUIRES_SKILL]->(s:Skill)
WHERE NOT (u)-[:HAS_SKILL]->(s)
RETURN s.name, count(o) AS demand_count
ORDER BY demand_count DESC
LIMIT 10
```

### 16.3 Entity Resolution

```python
class EntityLinker:
    """Link extracted entities to canonical KG nodes."""

    async def link_organization(self, name: str) -> str | None:
        """Fuzzy-match organization to existing KG node."""
        # 1. Exact match
        result = await neo4j.query(
            "MATCH (o:Organization) WHERE toLower(o.name) = toLower($name) RETURN o.id",
            name=name
        )
        if result:
            return result[0]["o.id"]

        # 2. Fuzzy match (using Qdrant skill embeddings for org names)
        candidates = await qdrant.search("organizations", embed(name), limit=5)
        for cand in candidates:
            if rapidfuzz.ratio(name.lower(), cand.payload["name"].lower()) > 80:
                return cand.id

        # 3. Create new node
        return await neo4j.create_node("Organization", {"name": name})
```

---

## 17. Security Architecture

| Layer | Measure | Implementation |
|---|---|---|
| **Authentication** | JWT + OAuth2 | `python-jose`, Google/GitHub OAuth |
| **Authorization** | RBAC (Role-Based) | Roles: `user`, `admin`, `crawler_service` |
| **API Security** | Rate limiting | Redis token bucket — 100 req/min per user |
| **Input Validation** | Pydantic models | All API inputs validated via Pydantic v2 |
| **SQL Injection** | Parameterized queries | SQLAlchemy ORM — no raw SQL |
| **XSS** | Content Security Policy | Next.js built-in CSP headers |
| **CORS** | Strict origin whitelist | FastAPI CORS middleware |
| **Secrets** | Environment variables | `.env` files, Docker secrets, HashiCorp Vault (prod) |
| **Data Encryption** | TLS + AES-256 | HTTPS everywhere, encrypted credentials at rest |
| **Crawler Identity** | Custom User-Agent | `ResearchScoutBot/1.0 (+https://researchscout.io/bot)` |
| **Credential Storage** | Encrypted vault | Crawl credentials encrypted with Fernet |
| **Audit Logging** | Structured logs | All auth events, data modifications logged |
| **Dependency Scanning** | Automated | GitHub Dependabot, `pip-audit` |
| **Container Security** | Non-root, minimal images | `python:3.12-slim`, non-root user in Dockerfile |

---

## 18. Scalability Strategy

### 18.1 Horizontal Scaling Points

```mermaid
graph LR
    subgraph Stateless["Stateless (Easy to Scale)"]
        API["API Servers<br/>(HPA: CPU > 70%)"]
        Workers["Celery Workers<br/>(scale by queue depth)"]
        Crawlers["Crawler Instances<br/>(scale by URL queue size)"]
    end

    subgraph Stateful["Stateful (Scale Carefully)"]
        PG["PostgreSQL<br/>(Read replicas → PgBouncer)"]
        QD["Qdrant<br/>(Sharded collections)"]
        N4J["Neo4j<br/>(Causal cluster)"]
        RD["Redis<br/>(Redis Cluster / Sentinel)"]
    end
```

### 18.2 Scaling Targets

| Metric | MVP | Growth | Scale |
|---|---|---|---|
| Opportunities in DB | 10K | 100K | 1M+ |
| Users | 100 | 10K | 100K+ |
| Crawl URLs / day | 1K | 50K | 500K+ |
| API requests / second | 10 | 100 | 1,000+ |
| Vector collection size | 10K | 100K | 1M+ |
| Recommendation latency (p99) | 2s | 500ms | 200ms |
| Crawl throughput | 1 worker | 10 workers | 50+ workers |

### 18.3 Caching Strategy

| Cache Layer | Storage | TTL | What |
|---|---|---|---|
| L1 — In-Process | `lru_cache` / `cachetools` | 5 min | Hot config, skill taxonomy |
| L2 — Redis | Redis | 1-24h | Search results, API responses, recommendations |
| L3 — CDN | Cloudflare/Vercel | 1h | Static frontend assets, public opportunity data |

---

## 19. Cost Optimization

### 19.1 LLM Cost Management

| Strategy | Implementation |
|---|---|
| **Model tiering** | Gemini Flash for extraction (cheap); GPT-4o only for complex reasoning |
| **Caching** | Cache LLM responses by input hash (Redis, 24h TTL) |
| **Structured output** | Use JSON mode to reduce token waste |
| **Batching** | Batch multiple extractions into single LLM call where possible |
| **Prompt optimization** | Minimize system prompt size; use few-shot only when accuracy drops |
| **Local models** | Use `sentence-transformers` for embeddings during development |

### 19.2 Monthly Cost Estimates

| Component | MVP (Dev) | Growth | Scale |
|---|---|---|---|
| **Cloud Compute** | $50 (single VPS) | $300 (3 VMs) | $1,500 (K8s cluster) |
| **LLM API** | $30 | $200 | $1,000 |
| **Embedding API** | $10 | $50 | $200 |
| **Search APIs** | $0 (free tiers) | $100 | $500 |
| **Databases** | $0 (self-hosted) | $100 (managed) | $500 (managed) |
| **Email/Notifications** | $0 (free tiers) | $20 | $100 |
| **Total** | **~$90/mo** | **~$770/mo** | **~$3,800/mo** |

### 19.3 Free Tier Optimization (Student Budget)

| Service | Free Tier |
|---|---|
| Google CSE | 100 queries/day |
| Bing Search | 1,000 queries/month |
| Tavily | 1,000 queries/month |
| OpenAI | $5 free credit (new accounts) |
| Gemini Flash | Generous free tier |
| Qdrant | Self-hosted (free) |
| Neo4j Community | Self-hosted (free) |
| PostgreSQL | Self-hosted (free) |
| SendGrid | 100 emails/day free |
| Telegram Bot | Free |
| Railway / Render | Free tier for hosting |

---

## 20. Deployment Plan

### 20.1 Development (Local)

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/researchscout
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URL=bolt://neo4j:7687
    depends_on: [postgres, redis, qdrant, neo4j]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker -l info -c 4
    depends_on: [backend, redis]

  crawler:
    build: ./backend
    command: celery -A app.workers.celery_app worker -l info -Q crawl -c 2
    depends_on: [backend, redis]

  scheduler:
    build: ./backend
    command: celery -A app.workers.celery_app beat -l info
    depends_on: [worker]

  postgres:
    image: postgres:16-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: researchscout
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant:latest
    volumes: [qdrant_data:/qdrant/storage]
    ports: ["6333:6333"]

  neo4j:
    image: neo4j:5-community
    volumes: [neo4j_data:/data]
    environment:
      NEO4J_AUTH: neo4j/password
    ports: ["7474:7474", "7687:7687"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]
    ports: ["9000:9000", "9001:9001"]

volumes:
  postgres_data:
  qdrant_data:
  neo4j_data:
  minio_data:
```

### 20.2 Production (Kubernetes)

```mermaid
graph TB
    subgraph Cloud["Cloud Provider (GCP/AWS/Azure)"]
        subgraph K8s["Kubernetes Cluster"]
            subgraph App["Application Pods"]
                API["FastAPI<br/>3 replicas, HPA"]
                Frontend["Next.js<br/>2 replicas"]
                Worker["Celery Workers<br/>5 replicas, HPA"]
                Crawler["Crawl Workers<br/>3 replicas, HPA"]
                Beat["Celery Beat<br/>1 replica"]
            end
            subgraph Data["Data Layer"]
                PG["PostgreSQL<br/>(Cloud SQL / RDS)"]
                RD["Redis<br/>(Memorystore / ElastiCache)"]
                QD["Qdrant<br/>(Managed or StatefulSet)"]
                N4J["Neo4j<br/>(AuraDB or StatefulSet)"]
            end
            Ingress["Ingress Controller<br/>(nginx + cert-manager)"]
        end
        CDN["CDN<br/>(Cloudflare)"]
        DNS["DNS<br/>(researchscout.io)"]
    end

    DNS --> CDN --> Ingress
    Ingress --> API
    Ingress --> Frontend
```

### 20.3 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:16, ... }
      redis: { image: redis:7, ... }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/ --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4

  lint:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check .
      - run: mypy app/
      - run: ruff format --check .

  build-and-push:
    needs: [test, lint]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/researchscout/backend:${{ github.sha }}

  deploy:
    needs: build-and-push
    if: github.ref == 'refs/heads/main'
    steps:
      - run: kubectl set image deployment/backend backend=ghcr.io/researchscout/backend:${{ github.sha }}
```

---

## 21. Testing Strategy

### 21.1 Test Pyramid

| Level | Framework | Coverage Target | What |
|---|---|---|---|
| **Unit** | pytest | 80%+ | Individual agent logic, NLP functions, scoring algorithms |
| **Integration** | pytest + testcontainers | 60%+ | Agent-to-agent pipelines, DB operations, API endpoints |
| **E2E** | pytest + httpx | Key flows | Full crawl→extract→recommend pipeline |
| **LLM Eval** | Custom eval harness | Per-prompt | Extraction accuracy, recommendation relevance |
| **Load** | Locust | Key endpoints | API throughput, recommendation latency |
| **Contract** | Pydantic | 100% | All inter-agent message schemas |

### 21.2 LLM Evaluation Framework

```python
class ExtractionEvaluator:
    """Evaluate LLM extraction quality against ground truth."""

    def evaluate(self, predictions: list[ResearchOpportunity],
                 ground_truth: list[ResearchOpportunity]) -> EvalMetrics:
        results = []
        for pred, truth in zip(predictions, ground_truth):
            field_scores = {}
            for field in ResearchOpportunity.model_fields:
                pred_val = getattr(pred, field)
                truth_val = getattr(truth, field)

                if truth_val is None:
                    continue  # Skip fields not in ground truth

                if isinstance(truth_val, list):
                    # Set overlap for list fields
                    field_scores[field] = jaccard(set(pred_val or []), set(truth_val))
                elif isinstance(truth_val, str):
                    field_scores[field] = rapidfuzz.ratio(
                        str(pred_val or "").lower(),
                        truth_val.lower()
                    ) / 100
                else:
                    field_scores[field] = 1.0 if pred_val == truth_val else 0.0

            results.append(field_scores)

        return EvalMetrics(
            field_accuracy={f: mean(r[f] for r in results if f in r)
                           for f in ResearchOpportunity.model_fields},
            overall_accuracy=mean(mean(r.values()) for r in results),
        )
```

---

## 22. Evaluation Metrics

### 22.1 System-Level Metrics

| Category | Metric | Target |
|---|---|---|
| **Discovery** | URLs crawled per day | 10K+ |
| **Discovery** | Opportunities extracted per day | 500+ |
| **Extraction** | Field-level accuracy (vs. ground truth) | > 85% |
| **Extraction** | Hallucination rate | < 5% |
| **Dedup** | Duplicate detection precision | > 95% |
| **Dedup** | Duplicate detection recall | > 90% |
| **Validation** | Authenticity score accuracy | > 90% |
| **Recommendation** | Precision@10 | > 0.6 |
| **Recommendation** | Recall@50 | > 0.7 |
| **Recommendation** | NDCG@10 | > 0.65 |
| **Recommendation** | MRR (Mean Reciprocal Rank) | > 0.5 |
| **Recommendation** | Diversity (intra-list distance) | > 0.3 |
| **User** | Click-through rate | > 15% |
| **User** | Save rate | > 8% |
| **User** | Apply rate | > 3% |
| **Freshness** | Avg. time from posting to discovery | < 48h |
| **Latency** | Recommendation API p99 | < 500ms |
| **Latency** | Search API p99 | < 1s |
| **Uptime** | System availability | > 99.5% |

### 22.2 Agent-Level Metrics

| Agent | Metric |
|---|---|
| Search Agent | Query → relevant URL rate, API success rate, cost per query |
| Crawler Agent | Pages/second, success rate, timeout rate, bytes/page |
| Extractor Agent | Fields extracted / total fields, confidence distribution |
| Validator Agent | False positive rate, false negative rate |
| Dedup Agent | True dedup rate, false merge rate |
| Recommender Agent | User engagement (CTR, save, apply), explanation quality |
| Notifier Agent | Delivery rate, open rate, unsubscribe rate |

---

## 23. Future Research Directions

### 23.1 High-Impact Research Extensions

| # | Direction | Novelty | Difficulty | Publication Venue |
|---|---|---|---|---|
| 1 | **Learning-to-Crawl**: RL agent that learns optimal crawl policies to maximize opportunity yield per dollar spent | High | Hard | WWW, SIGIR |
| 2 | **Self-Correcting Extraction**: Multi-agent debate protocol where extractor and validator iteratively refine extractions | Medium | Medium | EMNLP, ACL |
| 3 | **Temporal Knowledge Graphs**: Model how research opportunities, lab activities, and funding evolve over time | High | Hard | KDD, ICLR |
| 4 | **Hallucination-Aware Extraction**: Calibrated confidence scores with theoretical guarantees on extraction correctness | High | Hard | NeurIPS, ICML |
| 5 | **Explainable Graph Recommendations**: Use KG paths as natural language explanations for recommendations | Medium | Medium | RecSys, SIGIR |
| 6 | **Cold-Start Problem for New Users**: Few-shot user profiling from minimal information (1 resume) | Medium | Medium | RecSys, UMAP |
| 7 | **Autonomous Agent Evaluation**: Benchmarks and metrics for evaluating multi-agent systems in real-world web tasks | High | Medium | NeurIPS Datasets, AAAI |
| 8 | **Privacy-Preserving Recommendations**: Federated learning for collaborative filtering without sharing user data | High | Hard | PETS, CCS |
| 9 | **Cross-Lingual Opportunity Discovery**: Extract opportunities from non-English sources (German, French, Chinese, Japanese) | Medium | Medium | EMNLP, ACL |
| 10 | **Adaptive Agent Orchestration**: Meta-learning which agent configurations work best for which source types | High | Hard | ICML, ICLR |

### 23.2 Benchmark Dataset Contributions

1. **ResearchOpp-Bench**: Annotated dataset of 10K+ research opportunity web pages with ground-truth structured extractions
2. **WebCrawl-Quality**: Dataset measuring extraction quality vs. crawling strategy (static vs. JS rendering vs. API)
3. **OpportunityMatch**: User-opportunity relevance judgments for recommendation evaluation
4. **AgentTrace**: Execution traces of multi-agent pipelines with success/failure annotations

### 23.3 Ablation Study Design

```
Experiment 1: Extraction Quality
- Baseline: Regex-only extraction
- Variant A: LLM-only extraction (Gemini Flash)
- Variant B: NLP + LLM hybrid (proposed)
- Variant C: Multi-model ensemble (Gemini + GPT-4o + Claude)
- Metric: Field-level F1, overall accuracy, cost per extraction

Experiment 2: Recommendation Quality
- Baseline: BM25 keyword matching
- Variant A: Vector search only
- Variant B: Knowledge graph only
- Variant C: Hybrid retrieval (proposed RRF)
- Variant D: Hybrid + LTR reranking
- Metric: NDCG@10, Precision@10, diversity, user satisfaction

Experiment 3: Deduplication Quality
- Baseline: Exact URL match
- Variant A: Title fuzzy matching
- Variant B: MinHash LSH only
- Variant C: Embedding similarity only
- Variant D: Multi-signal fusion (proposed)
- Metric: Precision, recall, F1

Experiment 4: Crawling Efficiency
- Baseline: Round-robin crawling
- Variant A: Priority-based (domain authority)
- Variant B: UCB1 adaptive (proposed)
- Variant C: RL-based policy
- Metric: Opportunities/crawl, quality/crawl, cost efficiency
```

---

## 24. Research Paper Ideas

### Paper 1: "ResearchScout: A Multi-Agent Architecture for Autonomous Research Opportunity Discovery"
- **Venue**: WWW, CIKM, or AAAI
- **Contribution**: Novel multi-agent architecture with specialized discovery, intelligence, and user-facing divisions. Evaluation on real-world crawling of 50K+ pages across 200+ sources.
- **Key Results**: Extraction F1, recommendation NDCG, system throughput, agent failure recovery rates

### Paper 2: "Learning to Crawl: Adaptive Web Crawling with Multi-Armed Bandits for Opportunity Discovery"
- **Venue**: SIGIR, WWW
- **Contribution**: UCB1-based adaptive crawl scheduler that maximizes opportunity yield. Comparison with round-robin, priority-based, and RL policies.
- **Key Results**: 3× improvement in opportunity yield per crawl dollar

### Paper 3: "Hallucination-Aware Structured Extraction from Heterogeneous Web Sources"
- **Venue**: EMNLP, ACL Findings
- **Contribution**: Multi-model extraction with calibrated confidence scores. Maker-checker architecture reduces hallucination rate from 12% to 2.3%.
- **Key Results**: Field-level confidence calibration, verbatim verification scores

### Paper 4: "GraphRecX: Explainable Research Opportunity Recommendations via Knowledge Graph Reasoning"
- **Venue**: RecSys, SIGIR
- **Contribution**: Hybrid recommendation engine combining vector search, KG traversal, and LTR with natural language explanations from graph paths.
- **Key Results**: NDCG@10 improvements, explanation quality (human evaluation)

### Paper 5: "ResearchOpp-Bench: A Benchmark for Evaluating Autonomous Web Intelligence Systems"
- **Venue**: NeurIPS Datasets & Benchmarks
- **Contribution**: First large-scale benchmark for research opportunity extraction + recommendation, with 10K+ annotated pages and relevance judgments.

---

## 25. Resume-Worthy Features

> [!TIP]
> Each feature below maps to specific technical skills that hiring managers look for.

| Feature | Skills Demonstrated |
|---|---|
| Multi-agent architecture with LangGraph | Agentic AI, distributed systems, state machines |
| Production FastAPI backend with async I/O | Backend engineering, API design, Python async |
| Knowledge graph with Neo4j + Cypher | Graph databases, knowledge representation |
| Vector search with Qdrant + embeddings | Information retrieval, semantic search, ML engineering |
| LLM-powered structured extraction | Prompt engineering, NLP, LLM integration |
| Learning-to-rank recommendation engine | Machine learning, recommendation systems, feature engineering |
| Adaptive web crawling with UCB1 | Algorithms, online learning, web intelligence |
| Multi-signal deduplication (LSH + embeddings) | Data engineering, probabilistic data structures |
| Real-time notifications (Telegram/Discord/Email) | Event-driven architecture, messaging systems |
| Docker + K8s deployment with CI/CD | DevOps, containerization, cloud infrastructure |
| OpenTelemetry distributed tracing | Observability, production engineering |
| Comprehensive test suite (unit + integration + LLM eval) | Software quality, testing practices |
| NER + keyword extraction + topic modeling pipeline | NLP engineering, text mining |
| Explainable AI recommendations | XAI, user experience, trust & safety |
| Research paper publication | Research skills, technical writing, academic communication |

---

## 26. Step-by-Step Implementation Roadmap

### Phase 1: Foundation (Weeks 1–3) — MVP

> Goal: Core crawl-extract-store pipeline working end-to-end.

```
Week 1: Project Setup
├── [ ] Initialize monorepo (backend + frontend)
├── [ ] Docker Compose with PostgreSQL, Redis, Qdrant
├── [ ] FastAPI project structure + config
├── [ ] SQLAlchemy models + Alembic migrations
├── [ ] Pydantic schemas (ResearchOpportunity, User)
├── [ ] Basic auth (JWT registration + login)
└── [ ] CI pipeline (GitHub Actions: lint + test)

Week 2: Core Pipeline
├── [ ] Search Agent (Google CSE + 1 more API)
├── [ ] Crawler Agent (httpx for static + Crawl4AI for JS)
├── [ ] Extractor Agent (Gemini Flash structured output)
├── [ ] Basic NLP (spaCy NER + KeyBERT)
├── [ ] Celery + Redis task queue
└── [ ] End-to-end test: URL → extracted opportunity → PostgreSQL

Week 3: Basic Frontend + API
├── [ ] Next.js project setup
├── [ ] Opportunity list page with filters
├── [ ] Opportunity detail page
├── [ ] User registration + login
├── [ ] API endpoints: /opportunities, /auth
├── [ ] Seed 50+ real sources
└── [ ] First batch crawl → 100+ opportunities in DB
```

### Phase 2: Intelligence (Weeks 4–6)

> Goal: Smart extraction, validation, deduplication, and embeddings.

```
Week 4: Extraction Quality
├── [ ] Multi-model extraction (Gemini + GPT-4o fallback)
├── [ ] Validator Agent (URL check, domain trust, LLM fact-check)
├── [ ] Confidence scoring per field
├── [ ] PDF parsing (PyMuPDF)
└── [ ] Extraction evaluation harness + 50 annotated samples

Week 5: Vector Search + Dedup
├── [ ] Qdrant collection setup
├── [ ] Embedding Agent (text-embedding-3-large)
├── [ ] Semantic search API endpoint
├── [ ] Dedup Agent (MinHash LSH + embedding similarity)
├── [ ] Semantic similarity search on frontend
└── [ ] User profile embedding

Week 6: Knowledge Graph
├── [ ] Neo4j setup + schema creation
├── [ ] KG Builder Agent (entities → nodes, relations → edges)
├── [ ] Entity linking (organization, researcher, topic)
├── [ ] Basic graph queries (related opportunities, trending topics)
├── [ ] Graph exploration API endpoint
└── [ ] Scale to 1,000+ opportunities
```

### Phase 3: Recommendations (Weeks 7–9)

> Goal: Personalized, explainable recommendations.

```
Week 7: User Profiling
├── [ ] Resume upload + LLM parsing
├── [ ] GitHub profile analysis
├── [ ] Skill extraction + taxonomy mapping
├── [ ] User profile embedding in Qdrant
└── [ ] Profile completion UI

Week 8: Recommendation Engine
├── [ ] Multi-source retrieval (vector + graph + FTS)
├── [ ] Reciprocal Rank Fusion
├── [ ] Feature-based scoring (15 features)
├── [ ] MMR diversification
├── [ ] Recommendation API + UI
└── [ ] Match explanation generation (LLM)

Week 9: Ranking + Feedback Loop
├── [ ] User interaction tracking (views, saves, applies)
├── [ ] Feedback collection (thumbs up/down)
├── [ ] Learning Agent (weight updates from feedback)
├── [ ] A/B testing framework
├── [ ] Recommendation evaluation metrics
└── [ ] AI features: compare opportunities, eligibility check
```

### Phase 4: Agent Orchestration (Weeks 10–12)

> Goal: Full LangGraph multi-agent orchestration with memory.

```
Week 10: LangGraph Integration
├── [ ] Orchestrator Agent (LangGraph StateGraph)
├── [ ] Planner Agent (goal → execution plan)
├── [ ] State checkpointing (PostgreSQL-backed)
├── [ ] Agent communication via Redis Streams
├── [ ] Error handling + retry policies
└── [ ] Agent health monitoring

Week 11: Notifications + Scheduling
├── [ ] Notifier Agent (email via SendGrid)
├── [ ] Telegram bot integration
├── [ ] Discord webhook integration
├── [ ] Scheduler Agent (Celery Beat)
├── [ ] Daily digest generation
├── [ ] Deadline reminder system
└── [ ] User notification preferences UI

Week 12: Advanced Features
├── [ ] AI cover letter generator
├── [ ] AI email draft to professors
├── [ ] Interview preparation plans
├── [ ] Research reading list generation
├── [ ] Opportunity comparison tool
├── [ ] Saved opportunities with status tracking
└── [ ] Analytics dashboard (trends, top orgs, skills demand)
```

### Phase 5: Production Hardening (Weeks 13–15)

> Goal: Production-ready deployment with monitoring and scale.

```
Week 13: Observability + Security
├── [ ] OpenTelemetry instrumentation
├── [ ] Prometheus metrics + Grafana dashboards
├── [ ] Structured logging (structlog + Loki)
├── [ ] Security audit (rate limiting, input validation)
├── [ ] OAuth2 (Google + GitHub login)
└── [ ] API documentation (OpenAPI/Swagger)

Week 14: Performance + Scale
├── [ ] Database query optimization + indexes
├── [ ] Redis caching layer
├── [ ] Crawler parallelization (multiple workers)
├── [ ] Load testing (Locust)
├── [ ] CDN for frontend static assets
└── [ ] Scale to 10,000+ opportunities

Week 15: Deployment
├── [ ] Production Docker Compose
├── [ ] Kubernetes manifests (or cloud deployment)
├── [ ] CI/CD pipeline (test → build → deploy)
├── [ ] Domain setup + SSL
├── [ ] Monitoring alerts
└── [ ] Documentation (README, API docs, architecture docs)
```

### Phase 6: Research & Publication (Weeks 16–20)

> Goal: Experimental evaluation and paper writing.

```
Week 16-17: Benchmark Creation
├── [ ] Annotate 200+ ground-truth extractions
├── [ ] Collect user relevance judgments
├── [ ] Run ablation experiments (extraction, recommendation, dedup)
├── [ ] Record metrics across all variants
└── [ ] Statistical significance tests

Week 18-19: Paper Writing
├── [ ] Draft paper (ResearchScout system paper)
├── [ ] Create figures + tables
├── [ ] Related work section
├── [ ] Experimental results + analysis
└── [ ] Internal review + revision

Week 20: Submission + Open Source
├── [ ] Submit to target venue (WWW / RecSys / CIKM)
├── [ ] Open-source the project (GitHub)
├── [ ] Write blog post / demo video
├── [ ] Create project website
└── [ ] Plan next research extensions
```

---

## Open Questions

> [!IMPORTANT]
> Please review these design decisions before implementation begins.

1. **LLM Provider Priority**: Should we use Gemini Flash (cheaper, faster) or GPT-4o (higher quality) as the primary extraction model? Or a hybrid approach?

2. **Frontend Framework**: Next.js (as spec'd) or would you prefer a simpler SPA with Vite + React for faster iteration?

3. **Deployment Target**: Cloud provider preference (GCP / AWS / Azure) or self-hosted VPS (Hetzner, DigitalOcean)?

4. **MVP Scope**: Should Phase 1 include only the backend pipeline, or do you want a minimal frontend from day one?

5. **Team Size**: How many engineers are implementing this? The roadmap assumes 2–3 developers. Should we adjust scope?

6. **Budget Constraints**: Do you have API budgets for OpenAI/Google, or should we prioritize free/open-source models (Ollama + Llama 3)?

7. **Academic Focus**: Should the research paper aspect take priority over production features, or equal weight?
