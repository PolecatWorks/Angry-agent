export interface DataEngineCanvasMeta {
  remoteName: 'data-engine';
  exposedModule: string;
  displayName: string;
  badge: string;
  defaultDescription: string;
  supportedActions: string[];
}

export const DATA_ENGINE_CANVAS_REGISTRY: Record<string, DataEngineCanvasMeta> = {
  './DataVisualExplorerWrapper': {
    remoteName: 'data-engine',
    exposedModule: './DataVisualExplorerWrapper',
    displayName: 'Data Visual Explorer',
    badge: 'Vega-Lite / ECharts',
    defaultDescription: 'Interactive chart studio with provenance & sampling badges',
    supportedActions: [
      'run_statistical_check',
      'open_provenance',
      'save_visual',
      'drill_down_rows',
      'export_spec',
    ],
  },
  './SemanticTopologyWrapper': {
    remoteName: 'data-engine',
    exposedModule: './SemanticTopologyWrapper',
    displayName: 'Semantic & Structural Topology',
    badge: 'Cytoscape + ELK',
    defaultDescription: '3-layer concept, dataset ER, and field-to-field join anatomy',
    supportedActions: [
      'verify_join',
      'reject_forbidden_join',
      'probe_join',
      'inspect_dataset_form',
      'explore_data_visual',
      'open_provenance',
    ],
  },
  './StatisticalDiagnosticsWrapper': {
    remoteName: 'data-engine',
    exposedModule: './StatisticalDiagnosticsWrapper',
    displayName: 'Statistical Diagnostics',
    badge: 'Assumptions & Traits',
    defaultDescription: 'Statistical assumption checks and non-parametric recommendations',
    supportedActions: ['verify_statistical_trait', 'open_provenance'],
  },
  './DataAssetFormWrapper': {
    remoteName: 'data-engine',
    exposedModule: './DataAssetFormWrapper',
    displayName: 'Dataset Steward Form',
    badge: 'Schema & Units',
    defaultDescription: 'Interactive dataset grain, field units, and epistemic metadata editor',
    supportedActions: [],
  },
  './JoinHypothesisReviewWrapper': {
    remoteName: 'data-engine',
    exposedModule: './JoinHypothesisReviewWrapper',
    displayName: 'Join Hypothesis Review',
    badge: 'HITL Stewardship',
    defaultDescription: 'Approve or reject empirical join hypotheses',
    supportedActions: ['verify_join', 'reject_join'],
  },
  './AlgorithmSandboxWrapper': {
    remoteName: 'data-engine',
    exposedModule: './AlgorithmSandboxWrapper',
    displayName: 'Algorithm Sandbox',
    badge: 'SQL / Python',
    defaultDescription: 'Sandboxed algorithm inspection and execution canvas',
    supportedActions: [],
  },
  './ProvenanceLineageWrapper': {
    remoteName: 'data-engine',
    exposedModule: './ProvenanceLineageWrapper',
    displayName: 'Provenance & Decision Lineage',
    badge: 'Audit DAG',
    defaultDescription: 'Cryptographic provenance run lineage and rule trust summary',
    supportedActions: [],
  },
};

export function resolveDataEngineCanvasMeta(
  provider?: string | null,
  component?: string | null,
): DataEngineCanvasMeta | null {
  if (provider !== 'data-engine' || !component) {
    return null;
  }
  const normalized = component.startsWith('./') ? component : `./${component}`;
  return DATA_ENGINE_CANVAS_REGISTRY[normalized] ?? null;
}
