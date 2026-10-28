# Testing Strategy, Factuality Verification & Quality Assurance

**Repository**: [https://github.com/RohitKrSrivastava/agentic-policy-analytics](https://github.com/RohitKrSrivastava/agentic-policy-analytics)

This document details the test methodology, automated factuality verification algorithms, discrepancy auditing, and verification metrics implemented for the **Agentic Policy Data Analytics Platform**.

---

## 1. Test Architecture & Methodology

The test suite covers the entire lifecycle of multi-agent execution, from query scope validation down to econometric calculation fidelity and discrepancy auditing:

```mermaid
flowchart TD
    subgraph Testing_Layers [Testing Architecture]
        U["1. Unit Tests: Agents, Connectors & Tools"]
        I["2. Integration Tests: Multi-Agent Blackboard State"]
        H["3. Factuality & Hallucination Guard: Ground-Truth Audit"]
        Q["4. Data Quality Tests: Imputation & IQR Outlier Capping"]
        P["5. Concurrency & Performance Load Testing"]
        G["6. Domain Scope Guardrail Tests"]
    end
```

### Test Suite Structure
- [`backend/tests/test_tools.py`](backend/tests/test_tools.py): Validates SingStat CSV extraction, MOM JSON extraction, Data.gov.sg API v2 connectors with schema validation, MOM Excel parsing, SQLite DB queries, CAGR calculations, and regression functions.
- [`backend/tests/test_data_quality.py`](backend/tests/test_data_quality.py): Validates column snake_case standardization, missing value forward-fill + median imputation, IQR anomaly capping, and empirical completeness calculation without artificial clamping.
- [`backend/tests/test_agents.py`](backend/tests/test_agents.py): Tests individual agents (Coordinator, Extraction, Analytics) for ReAct step emissions (`thought`, `action`, `observation`), parameter extraction, and domain guardrails on out-of-scope queries (e.g. Malaysia, weather).
- [`backend/tests/test_multi_agent_workflow.py`](backend/tests/test_multi_agent_workflow.py): End-to-end integration test verifying that `WorkflowOrchestrator` executes parameterized workflows through `PLANNING` -> `EXTRACTING` -> `ANALYZING` -> `COMPLETED`, as well as graceful domain guardrail completion.
- [`backend/tests/test_llm_fallback.py`](backend/tests/test_llm_fallback.py): Tests multi-cloud fallback cascades (OpenAI failure triggers Gemini, Bedrock, and local heuristic engine).
- [`backend/tests/test_hallucination_guard.py`](backend/tests/test_hallucination_guard.py): Tests source-grounded factuality verification, adversarial fabrication detection (populating discrepancies for inflated headcounts or wages), subtle numeric mutation catching (e.g. S$17,350 vs S$7,350), and dynamic ground truth datasets.
- [`backend/tests/test_api_endpoints.py`](backend/tests/test_api_endpoints.py): Tests FastAPI REST endpoints, background task dispatch, and session retrieval.
- [`backend/tests/test_export.py`](backend/tests/test_export.py): Tests generation of Markdown, JSON, and ReportLab binary PDF reports.
- [`backend/tests/test_performance.py`](backend/tests/test_performance.py): Simulates concurrent policy analyst workloads with thread-safe SQLite operations.

---

## 2. Factuality Verification & Discrepancy Auditing Methodology

### The Challenge in Public Policy LLM Reports
Large Language Models (LLMs) frequently hallucinate numerical figures, round numbers inconsistently, or invent plausible-sounding economic metrics. In government policy environments, an erroneous figure (such as misrepresenting retrenchment counts or wage premiums) can misguide multi-million-dollar training budgets or parliamentary statements.

### Ground-Truth Verification Guard Architecture
The platform implements [`HallucinationVerificationGuard`](backend/app/evaluation/hallucination_guard.py) with the following verification stages:

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Analytics Agent
    participant Guard as Hallucination Guard
    participant DF as Extracted Datasets & Econometric Models

    Analyst->>Guard: Submit Synthesized Report (Text, Findings, Citations) + Ground Truth
    Guard->>Guard: Extract numeric tokens with sentence context via regex
    Guard->>Guard: Filter out benign structural tokens (calendar years, version numbers, table IDs)
    Guard->>DF: Build exhaustive ground truth index across all records & metrics
    loop For Every Quantitative Claim
        Guard->>Guard: Classify semantic claim category (WAGE, RETRENCHMENT, CAGR, PERCENTAGE, VACANCY, RATIO, HEADCOUNT)
        Guard->>Guard: Parse candidate numerical values (handling $, %, k/m multipliers)
        Guard->>DF: Semantic type matching & domain-calibrated tolerance comparison
        alt Claim semantically binds to compatible ground-truth metric within strict tolerance
            Guard->>Guard: Append to verified_facts with source provenance & metric type
        else Claim is fabricated, semantically mismatched, or ungrounded
            Guard->>Guard: Append to discrepancies with claim context, category mismatch, and deviation
        end
    end
    Guard->>Guard: Calculate Empirical Accuracy % & Hallucination Score
    Guard-->>Analyst: Return Verification Audit Report (verified facts + discrepancies)
```

### Mathematical Formulation & Semantic Type Binding
Let $C = \{(c_1, \text{type}_1), (c_2, \text{type}_2), \dots, (c_m, \text{type}_m)\}$ be the set of extracted quantitative claims classified into semantic categories (`WAGE`, `RETRENCHMENT`, `CAGR`, `PERCENTAGE`, `VACANCY`, `RATIO`, `HEADCOUNT`) excluding structural metadata (e.g. years 1990-2035).

For each candidate claim $c_i$, let $\text{Val}(c_i)$ be its numerical value. Let $G = \{(g_j, \text{type}_j, \text{src}_j, \text{desc}_j, \text{tol}_j)\}$ be the ground-truth index built dynamically from the underlying datasets and computed models.

A claim $(c_i, \text{type}_i)$ is verified if and only if there exists $(g_j, \text{type}_j) \in G$ such that:
1. **Semantic Type Compatibility**: $\text{Compatible}(\text{type}_i, \text{type}_j) = \text{True}$ (e.g., a wage claim cannot match a retrenchment metric; CAGR cannot match total growth percentage).
2. **Strict Domain-Calibrated Tolerance**:
$$|\text{Val}(c_i) - g_j| \le \text{tol}_j$$
where $\text{tol}_j = \$2.00$ for monthly wages (preventing $\text{S}\$7,400$ from matching $\text{S}\$7,350$), $0.05\%$ for CAGR, $1.0$ for retrenchments and headcount counts, and $0.05$ for ratios.

Claims satisfying both conditions are placed in $V$ (`verified_facts`); non-matching or cross-domain mutated claims are placed in $D$ (`discrepancies`).

The **Factual Accuracy Score** and **Hallucination Score** are defined as:
$$\text{Accuracy Percentage} = \frac{|V|}{|V| + |D|} \times 100\%$$
$$\text{Hallucination Score} = \frac{|D|}{|V| + |D|}$$

A report is considered factually consistent only when $|D| = 0$ and $|V| > 0$. If any fabricated or ungrounded metrics are present, they are explicitly surfaced in `discrepancies` with their context and deviation.

---

## 3. Test Execution & Coverage Summary

### Running the Test Suite Locally
```bash
# Run all tests with verbose output
pytest backend/tests -v

# Run with full branch coverage report
pytest backend/tests --cov=backend/app --cov-report=term
```

### Empirical Coverage Report
Below are the actual coverage results recorded across 47 automated unit, integration, and guardrail tests:

| Module / Component | Total Statements | Missed | Test Coverage |
|--------------------|------------------|--------|---------------|
| `backend/app/agents/analytics.py` | 103 | 13 | **87%** |
| `backend/app/agents/base_agent.py` | 20 | 0 | **100%** |
| `backend/app/agents/coordinator.py` | 94 | 12 | **87%** |
| `backend/app/agents/extractor.py` | 104 | 5 | **95%** |
| `backend/app/agents/orchestrator.py` | 93 | 10 | **89%** |
| `backend/app/api/endpoints/export.py` | 80 | 3 | **96%** |
| `backend/app/api/endpoints/datasets.py` | 24 | 1 | **96%** |
| `backend/app/evaluation/hallucination_guard.py` | 236 | 19 | **92%** |
| `backend/app/tools/data_quality.py` | 41 | 1 | **98%** |
| `backend/app/tools/statistical_engine.py` | 127 | 17 | **87%** |
| `backend/app/tools/government_sources.py` | 145 | 42 | **71%** |
| `backend/app/core/database.py` | 54 | 4 | **93%** |
| `backend/app/llm/router.py` | 53 | 9 | **83%** |
| `backend/app/llm/local_fallback.py` | 109 | 19 | **83%** |
| `backend/app/rag/policy_knowledge.py` | 42 | 4 | **90%** |
| **TOTAL REPOSITORY COVERAGE** | **1,981** | **305** | **85%** |

**Test Result**: `47 passed in 9.32s (100% pass rate)`.
