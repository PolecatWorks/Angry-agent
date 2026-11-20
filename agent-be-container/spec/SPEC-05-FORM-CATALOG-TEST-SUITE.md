# SPEC-05: Form Catalog Registry, Reference Sample Forms & Integration Test Suite

## 1. Scope & Objective
Define the specifications for:
1. Serving a formal **Form Catalog** (`/api/forms` and `/api/forms/{form_id}`) so frontend MFE loaders and agents can dynamically discover and instantiate registered form workflows.
2. Integrating reference sample forms (`vendor_onboarding_v2.json` and `expense_claim_v1.json`) with strict Draft 2020-12 schemas.
3. Specifying automated integration test scenarios covering bidirectional state sync, focus collision protection, dynamic SSE emission, and commit guardrails.

## 2. API Endpoints

### 2.1 List Catalog Forms (`GET /api/forms`)
- Response: `200 OK`
```json
{
  "forms": [
    {
      "form_id": "vendor_onboarding_v2",
      "title": "Vendor Onboarding Form",
      "description": "Standard vendor compliance and tax details onboarding",
      "json_schema": { ... }
    },
    {
      "form_id": "expense_claim_v1",
      "title": "Corporate Expense Claim",
      "description": "Employee expenditure declaration and reimbursement",
      "json_schema": { ... }
    }
  ]
}
```

### 2.2 Get Catalog Form (`GET /api/forms/{form_id}`)
- Parameters: `form_id` path variable.
- Response: `200 OK` with full form descriptor (`form_id`, `title`, `json_schema`, `initial_data`), or `404 Not Found` if the form is not cataloged.

## 3. Reference Sample Form Schemas
- `vendor_onboarding_v2.json`:
  - Required fields: `companyName`, `country`, `currency`, `vatNumber`.
  - Properties: String constraints, Country & Currency ENUMs.
- `expense_claim_v1.json`:
  - Required fields: `claimantName`, `category`, `amount`, `currency`.
  - Properties: Minimum number constraint, category ENUM.

## 4. Test Suite Requirements
1. **Catalog API Tests**: Verify retrieval of catalog forms by listing and ID lookup.
2. **End-to-End Workflow Tests**:
   - Register active form from catalog schema.
   - Synchronize human keystrokes with RFC 6902 JSON Patches (`POST /api/form/sync`).
   - Run conversational agent with live SSE stream asserting `RUN_STARTED`, `STATE_DELTA`, `RUN_FINISHED`.
   - Conversational form switching (`LOAD_MFE`).
   - Commit guardrails (`REQUEST_SUBMIT_APPROVAL`).
3. **Pipeline Tests**: Robot Framework test suite (`integration-tests/tests/test_rs_be.robot`).
