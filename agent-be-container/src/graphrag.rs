use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

/// Agent Descriptor (Agent-as-Data)
/// Encapsulates agent definitions, tools, version, and execution parameters as data records
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentDescriptor {
    pub id: String,
    pub name: String,
    pub description: String,
    pub version: String,
    pub system_prompt_template: String,
    pub tool_definitions: Vec<ToolDefinitionData>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolDefinitionData {
    pub name: String,
    pub description: String,
    pub parameters_schema: Value,
}

/// Form Workflow Definition as structured data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormWorkflowDefinition {
    pub form_id: String,
    pub title: String,
    pub category: String,
    pub json_schema: Value,
    pub field_relationships: HashMap<String, Vec<String>>,
}

/// Graph Node for GraphRAG Relational Context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphEntityNode {
    pub entity_id: String,
    pub entity_type: String, // e.g. "Vendor", "Field", "Form", "Claim"
    pub properties: Value,
}

/// Graph Edge for GraphRAG Relational Context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphRelationshipEdge {
    pub source_id: String,
    pub target_id: String,
    pub relationship: String, // e.g. "CONTAINS_FIELD", "DEPENDS_ON", "ASSOCIATED_WITH"
}

/// In-memory graph context index for fast semantic lookup
#[derive(Default, Clone)]
pub struct GraphContextIndex {
    nodes: HashMap<String, GraphEntityNode>,
    edges: Vec<GraphRelationshipEdge>,
}

impl GraphContextIndex {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_node(&mut self, node: GraphEntityNode) {
        self.nodes.insert(node.entity_id.clone(), node);
    }

    pub fn add_edge(&mut self, edge: GraphRelationshipEdge) {
        self.edges.push(edge);
    }

    pub fn find_related(&self, entity_id: &str) -> Vec<&GraphEntityNode> {
        let related_ids: Vec<&str> = self
            .edges
            .iter()
            .filter_map(|e| {
                if e.source_id == entity_id {
                    Some(e.target_id.as_str())
                } else if e.target_id == entity_id {
                    Some(e.source_id.as_str())
                } else {
                    None
                }
            })
            .collect();

        related_ids
            .into_iter()
            .filter_map(|id| self.nodes.get(id))
            .collect()
    }
}
