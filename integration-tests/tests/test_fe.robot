*** Settings ***
Library    RequestsLibrary

*** Variables ***
${BASE_URL}    http://agent-ui-nginx-view

*** Test Cases ***
Frontend index Check
    [Documentation]    Test to verify the agent frontend is responding.
    ${response}=    GET    ${BASE_URL}/mfe/angry-agent/index.html    expected_status=200
    Log    Response was: ${response.content}
