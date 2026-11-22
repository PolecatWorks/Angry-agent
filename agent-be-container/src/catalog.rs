use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormCatalogItem {
    pub form_id: String,
    pub title: String,
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mfe: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub component: Option<String>,
    pub json_schema: Value,
    pub initial_data: Value,
}

#[derive(Clone)]
pub struct FormCatalog {
    forms: Arc<HashMap<String, FormCatalogItem>>,
}

impl Default for FormCatalog {
    fn default() -> Self {
        Self::new()
    }
}

impl FormCatalog {
    pub fn new() -> Self {
        let mut map = HashMap::new();

        let bundled: [(&str, &str, &str, &str); 5] = [
            (
                include_str!("../tests/sample_forms/vendor_onboarding_v2.json"),
                "vendor_onboarding_v2",
                "Vendor Onboarding",
                "Standard vendor compliance and tax details onboarding",
            ),
            (
                include_str!("../tests/sample_forms/expense_claim_v1.json"),
                "expense_claim_v1",
                "Corporate Expense Claim",
                "Employee expenditure declaration and reimbursement",
            ),
            (
                include_str!("../tests/sample_forms/data_visual_explorer_v1.json"),
                "data_visual_explorer_v1",
                "Data Visual Explorer (data-engine)",
                "Interactive Vega-Lite v5 / Apache ECharts data explorer backed by Data-Engine provenance",
            ),
            (
                include_str!("../tests/sample_forms/semantic_topology_v1.json"),
                "semantic_topology_v1",
                "Semantic & Structural Data Topology (data-engine)",
                "3-layer Cytoscape.js + ELK semantic concept, ER join, and field-to-field anatomy explorer",
            ),
            (
                include_str!("../tests/sample_forms/statistical_diagnostics_v1.json"),
                "statistical_diagnostics_v1",
                "Statistical Diagnostics Scorecard (data-engine)",
                "Assumption check scorecard, non-parametric fallbacks, and epistemic trait verification",
            ),
        ];

        for (raw, default_id, default_title, desc) in bundled {
            if let Ok(val) = serde_json::from_str::<Value>(raw) {
                let item = FormCatalogItem {
                    form_id: val["form_id"].as_str().unwrap_or(default_id).to_string(),
                    title: val["title"].as_str().unwrap_or(default_title).to_string(),
                    description: Some(desc.to_string()),
                    mfe: val["mfe"].as_str().map(ToString::to_string),
                    component: val["component"].as_str().map(ToString::to_string),
                    json_schema: val["json_schema"].clone(),
                    initial_data: val["initial_data"].clone(),
                };
                map.insert(item.form_id.clone(), item);
            }
        }

        Self {
            forms: Arc::new(map),
        }
    }

    pub fn list(&self) -> Vec<FormCatalogItem> {
        self.forms.values().cloned().collect()
    }

    pub fn get(&self, form_id: &str) -> Option<FormCatalogItem> {
        self.forms.get(form_id).cloned()
    }
}
