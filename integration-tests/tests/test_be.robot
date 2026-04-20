*** Settings ***
Library    RequestsLibrary

*** Variables ***
${BASE_URL}    http://agent-be

*** Test Cases ***
Backend Threads Check
    [Documentation]    Test to verify the agent backend is responding to alive checks.
    ${response}=    GET    ${BASE_URL}/agent-be/api/threads    expected_status=200
    Log    Response was: ${response.content}
