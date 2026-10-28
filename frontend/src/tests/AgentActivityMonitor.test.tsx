import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentActivityMonitor } from '../components/AgentActivityMonitor';
import { AgentStepLog, SessionStatus } from '../types';

describe('AgentActivityMonitor Component', () => {
  const mockLogs: AgentStepLog[] = [
    {
      id: 'step-1',
      session_id: 'test-sess',
      agent: 'Data Coordinator Agent',
      step_type: 'thought',
      title: 'Formulating Multi-Source Research Plan',
      content: 'Determining primary public datasets: SingStat for employment, MOM for retrenchments.',
      timestamp: '2025-01-01T10:00:00Z',
    },
    {
      id: 'step-2',
      session_id: 'test-sess',
      agent: 'Data Extraction Agent',
      step_type: 'action',
      title: 'Action: Executing Data Extraction Tool',
      content: 'Invoked query_singstat_api with sector=Information & Communications.',
      tool_name: 'query_singstat_api',
      timestamp: '2025-01-01T10:00:05Z',
    },
    {
      id: 'step-3',
      session_id: 'test-sess',
      agent: 'Data Extraction Agent',
      step_type: 'observation',
      title: 'Observation: Acquired 20 quarterly records',
      content: 'Dataset acquired with 100% schema integrity.',
      timestamp: '2025-01-01T10:00:08Z',
    },
    {
      id: 'step-4',
      session_id: 'test-sess',
      agent: 'Hallucination Verification Guard',
      step_type: 'reflection',
      title: 'Reflection: Audit Grounding of Quantitative Claims',
      content: 'Reconciled 16 statistical metrics against SingStat ground truth.',
      timestamp: '2025-01-01T10:00:15Z',
    },
  ];

  it('renders all four agent architecture modules with accurate role descriptions', () => {
    render(
      <AgentActivityMonitor
        logs={mockLogs}
        status="completed"
        progressPct={100}
        currentAgent="Analytics Agent"
        currentStep="Synthesis complete"
      />
    );

    expect(screen.getByText('Coordinator Agent')).toBeInTheDocument();
    expect(screen.getByText('Plans workflow & delegates')).toBeInTheDocument();

    expect(screen.getByText('Extraction Agent')).toBeInTheDocument();
    expect(screen.getByText('SingStat, MOM, Data.gov.sg')).toBeInTheDocument();

    expect(screen.getByText('Analytics Agent')).toBeInTheDocument();
    expect(screen.getByText('Econometric models & RAG')).toBeInTheDocument();

    expect(screen.getByText('Hallucination Guard')).toBeInTheDocument();
    expect(screen.getByText('Factuality & Grounding Audit')).toBeInTheDocument();

    // Confirm overclaiming phrase is absent
    expect(screen.queryByText(/100% Factuality Verification/i)).toBeNull();
  });

  it('displays progress bar percentage and status label', () => {
    render(
      <AgentActivityMonitor
        logs={mockLogs}
        status="analyzing"
        progressPct={65}
        currentAgent="Analytics Agent"
        currentStep="Running regression models"
      />
    );

    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('analyzing')).toBeInTheDocument();
  });

  it('renders step logs and badges correctly', () => {
    render(
      <AgentActivityMonitor
        logs={mockLogs}
        status="completed"
        progressPct={100}
      />
    );

    expect(screen.getByText('Formulating Multi-Source Research Plan')).toBeInTheDocument();
    expect(screen.getByText('Action: Executing Data Extraction Tool')).toBeInTheDocument();
    expect(screen.getByText('Observation: Acquired 20 quarterly records')).toBeInTheDocument();
    expect(screen.getByText('Reflection: Audit Grounding of Quantitative Claims')).toBeInTheDocument();

    expect(screen.getByText(/Thought \(Reasoning\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Action \(Tool Execution\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Observation \(Result\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Reflection \(Audit\)/i)).toBeInTheDocument();
  });
});
