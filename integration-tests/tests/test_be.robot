*** Settings ***
Documentation    Verifies Angry Agent Backend API and configurable prefix behavior
Library          RequestsLibrary
Library          Collections

*** Variables ***
${BASE_URL}    http://agent-be

*** Test Cases ***
Positive: Backend Health At Root
    [Documentation]    Verify root /health responds for Kubernetes probes.
    ${response}=    GET    ${BASE_URL}/health    expected_status=200
    Log    Response was: ${response.content}
    Should Contain    ${response.text}    ok

Positive: Backend Health Under Configured Prefix
    [Documentation]    Verify /api/angry-agent/v1/health responds.
    ${response}=    GET    ${BASE_URL}/api/angry-agent/v1/health    expected_status=200
    Log    Response was: ${response.content}
    Should Contain    ${response.text}    ok

Positive: Backend Threads Under Configured Prefix
    [Documentation]    Verify /api/angry-agent/v1/threads responds.
    ${headers}=    Create Dictionary    X-User-ID=robot-test-user
    ${response}=    GET    ${BASE_URL}/api/angry-agent/v1/threads    headers=${headers}    expected_status=200
    Log    Response was: ${response.content}

Positive: Backend Backward Compatibility Alias
    [Documentation]    Verify /api/v1/threads responds via backward-compatibility alias.
    ${headers}=    Create Dictionary    X-User-ID=robot-test-user
    ${response}=    GET    ${BASE_URL}/api/v1/threads    headers=${headers}    expected_status=200
    Log    Response was: ${response.content}

Negative: Invalid API Prefix Returns 404
    [Documentation]    Verify requests to non-existent API prefixes return 404.
    ${headers}=    Create Dictionary    X-User-ID=robot-test-user
    ${response}=    GET    ${BASE_URL}/api/wrong-agent/v1/threads    headers=${headers}    expected_status=404
    Log    Response status: ${response.status_code}

Negative: Unprefixed API Path Returns 404
    [Documentation]    Verify unprefixed business endpoints like /threads return 404.
    ${headers}=    Create Dictionary    X-User-ID=robot-test-user
    ${response}=    GET    ${BASE_URL}/threads    headers=${headers}    expected_status=404
    Log    Response status: ${response.status_code}
