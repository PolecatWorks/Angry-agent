*** Settings ***
Documentation    Verifies Angry Agent Backend API and health/alive checks
Library          RequestsLibrary

*** Variables ***
${BASE_URL}    http://agent-be

*** Test Cases ***
Backend Health Check
    [Documentation]    Test to verify the agent backend is responding to alive checks without requiring authentication.
    ${response}=    GET    ${BASE_URL}/health    expected_status=200
    Log    Response was: ${response.content}
    Should Contain    ${response.text}    ok

Backend Prefixed Health Check
    [Documentation]    Test to verify the agent backend is responding to alive checks under the service prefix.
    ${response}=    GET    ${BASE_URL}/api/angry-agent/v1/health    expected_status=200
    Log    Response was: ${response.content}
    Should Contain    ${response.text}    ok

Backend Unauthenticated Threads Fails Closed
    [Documentation]    Test to verify protected business endpoints require valid bearer authentication and fail closed with 401.
    ${response}=    GET    ${BASE_URL}/agent-be/api/threads    expected_status=401
    Log    Response was: ${response.content}
    Should Contain    ${response.text}    Bearer token required
