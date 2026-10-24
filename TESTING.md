# Testing Strategy, Hallucination Detection & Quality Assurance

**Repository**: [https://github.com/RohitKrSrivastava/agentic-policy-analytics](https://github.com/RohitKrSrivastava/agentic-policy-analytics)

This document details the test methodology, automated hallucination detection algorithms, and verification metrics implemented for the **Agentic Policy Data Analytics Platform**.

---

## 1. Test Architecture & Methodology

The test suite covers the entire lifecycle of multi-agent execution, from natural language query ingestion down to econometric calculation fidelity and API payload delivery:

```mermaid
flowchart TD
    subgraph Testing_Layers [Testing Architecture]
        U[1. Unit Tests: Agents, Connectors & Tools]
        I[2. Integration Tests: Multi-Agent Blackboard State]
        H[3. LLM Tests: Hallucination Detection & Accuracy]
        Q[4. Data Quality Tests: Imputation & IQR Outlier Capping]
        P[5. Concurrency & Performance Load Testing]
    end
```

### Test Suite Structure
- [`backend/tests/test_tools.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_tools.py): Validates SingStat CSV extraction, MOM JSON extraction, Data.gov.sg API v2 connectors, MOM Excel parsing, SQLite DB queries, CAGR calculations, and regression functions.
- [`backend/tests/test_data_quality.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_data_quality.py): Validates column snake_case standardization, missing value forward-fill + median imputation, and IQR anomaly capping.
- [`backend/tests/test_agents.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_agents.py): Tests individual agents (Coordinator, Extraction, Analytics) for correct ReAct step emissions (`thought`, `action`, `observation`, `reflection`).
- [`backend/tests/test_multi_agent_workflow.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_multi_agent_workflow.py): End-to-end integration test verifying that `WorkflowOrchestrator` transitions sessions through `PLANNING` -> `EXTRACTING` -> `ANALYZING` -> `COMPLETED`.
- [`backend/tests/test_llm_fallback.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_llm_fallback.py): Tests the multi-cloud fallback cascade (OpenAI failure triggers Gemini, Bedrock, and local heuristic engine).
- [`backend/tests/test_hallucination_guard.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_hallucination_guard.py): Tests ground-truth factuality verification, fabricated metric rejection, and deterministic consistency.
- [`backend/tests/test_api_endpoints.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_api_endpoints.py): Tests FastAPI REST endpoints, background task dispatch, and session retrieval.
- [`backend/tests/test_export.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_export.py): Tests generation of Markdown, JSON, and ReportLab binary PDF reports.
- [`backend/tests/test_performance.py`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/tests/test_performance.py): Simulates 5 concurrent policy analysts executing simultaneous agent workflows with zero deadlocks or race conditions.

---

## 2. Hallucination Detection & Accuracy Validation Methodology

### The Problem in Policy Research
Large Language Models (LLMs) frequently hallucinate quantitative figures, round numbers inconsistently, or invent plausible-sounding economic metrics. In government policy environments, an erroneous figure (such as misrepresenting retrenchment counts or wage premiums) can misguide multi-million-dollar training budgets or parliamentary statements.

### The Ground-Truth Verification Guard Algorithm
The platform implements [`HallucinationVerificationGuard`](file:///d:/workspace/IMDA/Full%20Stack%20Engineer%20GenAI/backend/app/evaluation/hallucination_guard.py):

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Analytics Agent
    participant Guard as Hallucination Guard
    participant DF as Pandas DataFrames (Ground Truth)

    Analyst->>Guard: Submit Synthesized Report (Text, Findings, Citations)
    Guard->>Guard: Tokenize & Extract Regex Quantitative Claims ($S, %, Headcounts)
    loop For Every Extracted Quantitative Token
        Guard->>DF: Cross-reference against exact underlying dataframe cells
        alt Token matches authoritative ground truth
            Guard->>Guard: Mark Fact as VERIFIED_EXACT
        else Token deviates from ground truth
            Guard->>Guard: Flag discrepancy & identify variance
        end
    end
    Guard->>Guard: Calculate Factual Accuracy % & Hallucination Score (0.0 to 1.0)
    Guard-->>Analyst: Return Verification Certificate & Audit Trail
```

### Mathematical Formulation
Let $C = \{c_1, c_2, \dots, c_n\}$ be the set of quantitative claims extracted via regular expression:
$$c_i \in \text{Regex}\left(\text{r'(?:\$|S\$)?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?(?:\s*[kKmMbB])?'}\right)$$

Each claim $c_i$ is mapped to ground-truth dictionary $G$:
$$V(c_i) = \begin{cases} 1 & \text{if } \text{clean}(c_i) \in G \\ 0 & \text{otherwise} \end{cases}$$

The **Factual Accuracy Score** and **Hallucination Risk Score** are defined as:
$$\text{Accuracy Percentage} = \left(\frac{\sum_{i=1}^n V(c_i)}{n}\right) \times 100\%$$
$$\text{Hallucination Risk Score} = 1.0 - \left(\frac{\text{Accuracy Percentage}}{100}\right)$$

When zero ungrounded claims are found, the report is awarded a **0.00 Hallucination Risk (100% Verified Ground Truth)** certification, stamped directly on the synthesized policy report and exported PDF.

---

## 3. Test Execution & Coverage Summary

### Running the Test Suite Locally
```bash
# Run all tests with verbose output
pytest backend/tests -v

# Run with full branch coverage report
pytest backend/tests --cov=backend/app --cov-report=term-missing
```

### Empirical Coverage Report
Below are the actual coverage results recorded across 27 automated unit and integration tests:

| Module / Component | Total Statements | Missed | Test Coverage |
|--------------------|------------------|--------|---------------|
| `backend/app/agents/analytics.py` | 48 | 2 | **96%** |
| `backend/app/agents/base_agent.py` | 19 | 0 | **100%** |
| `backend/app/agents/coordinator.py` | 21 | 2 | **90%** |
| `backend/app/agents/extractor.py` | 44 | 0 | **100%** |
| `backend/app/agents/orchestrator.py` | 78 | 10 | **87%** |
| `backend/app/api/endpoints/export.py` | 80 | 3 | **96%** |
| `backend/app/api/endpoints/datasets.py` | 24 | 1 | **96%** |
| `backend/app/evaluation/hallucination_guard.py` | 29 | 0 | **100%** |
| `backend/app/tools/data_quality.py` | 42 | 1 | **98%** |
| `backend/app/tools/statistical_engine.py` | 102 | 5 | **95%** |
| `backend/app/tools/government_sources.py` | 92 | 24 | **74%** |
| `backend/app/core/database.py` | 47 | 0 | **100%** |
| `backend/app/llm/router.py` | 54 | 9 | **83%** |
| `backend/app/rag/policy_knowledge.py` | 42 | 4 | **90%** |
| **TOTAL REPOSITORY COVERAGE** | **1,159** | **188** | **84%** |

**Test Result**: `27 passed in 6.40s (100% pass rate)`.
