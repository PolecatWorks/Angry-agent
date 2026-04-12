*** Settings ***
Library    RequestsLibrary

*** Variables ***
${BASE_URL}    http://agent-be:8080

*** Test Cases ***
Backend Health Check
    [Documentation]    Test to verify the agent backend is responding to alive checks.
    Create Session    backend    ${BASE_URL}
    ${response}=    GET On Session    backend    /hams/alive
    Status Should Be    200    ${response}
