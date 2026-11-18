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

Negative: Wrong Service Prefix Returns 404
    [Documentation]    Verify accessing with a mismatched prefix returns 404 Not Found.
    ${response}=    GET    ${BASE_URL}/mfe/unknown-service/remoteEntry.json    expected_status=404
    Log    Response status: ${response.status_code}

Negative: Non Existent Asset Under Prefix Returns 404
    [Documentation]    Verify requesting a non-existent asset under the MFE prefix returns 404 Not Found.
    ${response}=    GET    ${BASE_URL}/mfe/angry-agent/non-existent-asset.js    expected_status=404
    Log    Response status: ${response.status_code}
