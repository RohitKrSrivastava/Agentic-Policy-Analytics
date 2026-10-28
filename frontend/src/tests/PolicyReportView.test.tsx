import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PolicyReportView } from '../components/PolicyReportView';
import { PolicyReport } from '../types';

const baseMockReport: PolicyReport = {
  session_id: 'sess-test-verified',
  query: 'Analyze ICT sector workforce and wage growth',
  title: 'Policy Analysis: Singapore Information & Communications Workforce Dynamics',
  executive_summary: 'Between 2020 and 2024, Singapore ICT expanded with strong wage growth.',
  key_findings: [
    {
      heading: 'Workforce Expansion',
      body: 'The ICT sector added net new jobs over the 5-year observation window.',
      sentiment: 'positive',
      statistical_evidence: 'Employment rose from 120.5k to 142.1k.',
      citation_id: 'SINGSTAT-M015661',
    },
  ],
  statistical_metrics: {
    cagr_wage: 8.14,
    net_jobs_added: 21600,
  },
  policy_recommendations: [
    'Scale up conversion programmes for AI engineering roles.',
  ],
  citations: [
    {
      citation_id: 'SINGSTAT-M015661',
      source_agency: 'DOS SingStat',
      dataset_title: 'M015661 - Employment Trends',
      time_period: '2020-2024',
      access_method: 'API Gateway',
    },
  ],
  quality_score: 95.0,
  hallucination_score: 0.0,
  verification_status: 'verified',
  discrepancy_count: 0,
  generated_at: '2025-01-01T10:00:00Z',
};

describe('PolicyReportView Component', () => {
  it('renders verified state with green badge and no 100% FACTUAL claim', () => {
    render(<PolicyReportView report={baseMockReport} sessionId="sess-test-verified" />);

    const badge = screen.getByTestId('verification-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('VERIFIED');
    expect(badge.className).toContain('bg-emerald-500');

    // Confirm overclaiming phrase is not present
    expect(screen.queryByText(/100% FACTUAL/i)).toBeNull();
  });

  it('renders partially_verified state with amber badge and discrepancy count', () => {
    const partialReport: PolicyReport = {
      ...baseMockReport,
      hallucination_score: 0.12,
      verification_status: 'partially_verified',
      discrepancy_count: 2,
    };

    render(<PolicyReportView report={partialReport} sessionId="sess-test-partial" />);

    const badge = screen.getByTestId('verification-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(/PARTIALLY VERIFIED/i);
    expect(badge).toHaveTextContent(/2 discrepancies/i);
    expect(badge.className).toContain('bg-amber-500');

    // Confirm overclaiming phrase is not present
    expect(screen.queryByText(/100% FACTUAL/i)).toBeNull();
  });

  it('renders unverified state with red badge', () => {
    const unverifiedReport: PolicyReport = {
      ...baseMockReport,
      hallucination_score: 0.45,
      verification_status: 'unverified',
      discrepancy_count: 4,
    };

    render(<PolicyReportView report={unverifiedReport} sessionId="sess-test-unverified" />);

    const badge = screen.getByTestId('verification-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('UNVERIFIED');
    expect(badge.className).toContain('bg-rose-500');
    expect(screen.queryByText(/100% FACTUAL/i)).toBeNull();
  });

  it('renders unverifiable state with red badge when source coverage is missing', () => {
    const unverifiableReport: PolicyReport = {
      ...baseMockReport,
      hallucination_score: 0.5,
      verification_status: 'unverifiable',
      discrepancy_count: 0,
    };

    render(<PolicyReportView report={unverifiableReport} sessionId="sess-test-unverifiable" />);

    const badge = screen.getByTestId('verification-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('UNVERIFIABLE');
    expect(badge.className).toContain('bg-rose-500');
  });

  it('renders title, key findings, and recommendations correctly', () => {
    render(<PolicyReportView report={baseMockReport} sessionId="sess-test-content" />);

    expect(screen.getByText(baseMockReport.title)).toBeInTheDocument();
    expect(screen.getByText('Workforce Expansion')).toBeInTheDocument();
    expect(screen.getByText('Scale up conversion programmes for AI engineering roles.')).toBeInTheDocument();
  });
});
