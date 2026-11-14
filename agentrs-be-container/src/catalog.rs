use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormCatalogItem {
    pub form_id: String,
    pub title: String,
    pub description: Option<String>,
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

        // 1. Vendor Onboarding reference form
        let vendor_raw = include_str!("../tests/sample_forms/vendor_onboarding_v2.json");
        if let Ok(vendor_val) = serde_json::from_str::<Value>(vendor_raw) {
            let item = FormCatalogItem {
                form_id: vendor_val["form_id"]
                    .as_str()
                    .unwrap_or("vendor_onboarding_v2")
                    .to_string(),
                title: vendor_val["title"]
                    .as_str()
                    .unwrap_or("Vendor Onboarding")
                    .to_string(),
                description: Some(
                    "Standard vendor compliance and tax details onboarding".to_string(),
                ),
                json_schema: vendor_val["json_schema"].clone(),
                initial_data: vendor_val["initial_data"].clone(),
            };
            map.insert(item.form_id.clone(), item);
        }

        // 2. Expense Claim reference form
        let expense_raw = include_str!("../tests/sample_forms/expense_claim_v1.json");
        if let Ok(expense_val) = serde_json::from_str::<Value>(expense_raw) {
            let item = FormCatalogItem {
                form_id: expense_val["form_id"]
                    .as_str()
                    .unwrap_or("expense_claim_v1")
                    .to_string(),
                title: expense_val["title"]
                    .as_str()
                    .unwrap_or("Corporate Expense Claim")
                    .to_string(),
                description: Some("Employee expenditure declaration and reimbursement".to_string()),
                json_schema: expense_val["json_schema"].clone(),
                initial_data: expense_val["initial_data"].clone(),
            };
            map.insert(item.form_id.clone(), item);
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
