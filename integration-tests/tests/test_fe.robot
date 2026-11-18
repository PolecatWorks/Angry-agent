*** Settings ***
Documentation    Verifies Angry Agent MFE UI static assets and configurable /mfe/ prefix behavior
Library          RequestsLibrary
Library          Collections

*** Variables ***
${BASE_URL}    http://agent-ui-nginx-view

*** Test Cases ***
Positive: Remote Entry Is Served Under MFE Prefix
    [Documentation]    Verify remoteEntry.json is accessible under the configured /mfe/angry-agent/ path.
    ${response}=    GET    ${BASE_URL}/mfe/angry-agent/remoteEntry.json    expected_status=200
    Log    remoteEntry content: ${response.content}
    Should Contain    ${response.headers}    Content-Type

Positive: Frontend Index Check
    [Documentation]    Verify the agent frontend index.html is accessible under /mfe/angry-agent/.
    ${response}=    GET    ${BASE_URL}/mfe/angry-agent/index.html    expected_status=200
    Log    Response was: ${response.content}

Positive: MFE Static Assets Return CORS Headers On Options
    [Documentation]    Verify OPTIONS preflight on /mfe/angry-agent/ returns CORS headers.
    ${headers}=    Create Dictionary    Origin=http://mfe-shell.dev.k8s    Access-Control-Request-Method=GET
    ${response}=    OPTIONS    ${BASE_URL}/mfe/angry-agent/remoteEntry.json    headers=${headers}    expected_status=204
    Dictionary Should Contain Key    ${response.headers}    Access-Control-Allow-Origin

Negative: Root Path Without Prefix Returns 404
    [Documentation]    Verify accessing assets without the /mfe/angry-agent/ prefix returns 404 Not Found.
    ${response}=    GET    ${BASE_URL}/index.html    expected_status=404
    Log    Response status: ${response.status_code}

Negative: Wrong Service Prefix Returns 404
    [Documentation]    Verify accessing with a mismatched prefix returns 404 Not Found.
    ${response}=    GET    ${BASE_URL}/mfe/unknown-service/remoteEntry.json    expected_status=404
    Log    Response status: ${response.status_code}
