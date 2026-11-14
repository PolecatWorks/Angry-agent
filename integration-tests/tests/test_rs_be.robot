*** Settings ***
Library    RequestsLibrary

*** Variables ***
${BASE_URL}    http://agentrs-be:8081

*** Test Cases ***
AgentRS Backend Health Check
    [Documentation]    Test to verify the Rust agent backend is responding to health checks.
    ${response}=    GET    ${BASE_URL}/health    expected_status=200
    Log    Response was: ${response.content}
    Should Contain    ${response.text}    "container":"agentrs-be-container"
    Should Contain    ${response.text}    "status":"ok"

AgentRS Backend Threads Check
    [Documentation]    Test to verify listing threads for a user.
    ${headers}=    Create Dictionary    X-User-ID=robot-test-user
    ${response}=    GET    ${BASE_URL}/api/threads    headers=${headers}    expected_status=200
    Log    Response was: ${response.content}
    Should Contain    ${response.text}    "threads"
