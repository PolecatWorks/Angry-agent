# Agent UI Container Specification (PRD)

## 1. Introduction

The `agent-ui-container` is the frontend application of the AI Agent application. It provides an intuitive web interface for users to interact with the LangGraph-powered AI agent backend. The container is designed as an independent Micro-Frontend (MFE) that can be developed, tested, and deployed in isolation or embedded within a larger shell application.

## 2. Goals

- Provide a user-friendly chat interface to communicate with the AI agent.
- Ensure multi-user isolation where chats are specific to individual users.
- Support seamless integration as a Module Federation remote.
- Maintain a high level of testing and reliability.
- Run independently as a standalone Docker container.

## 3. Architecture & Tech Stack

- **Framework:** Angular.
- **UI & Styling:** Tailwind CSS and Angular Material.
- **Design Philosophy:** "The Digital Atrium" — An architectural intelligence framework characterized by structural clarity, glassmorphism, and editorial typography (Manrope & Inter).
- **Package Management:** npm.
- **Micro-Frontend Architecture:** The application is built using the `@angular-architects/native-federation` package, allowing it to act as a remote module.
- **Testing:** Unit and integration testing are handled by Vitest, running via the `ng test` command.

## 4. Features & Functionality

### 4.1 Chat Interface
The primary interface is a chat window that allows users to send messages to the backend AI agent and view responses. The history of the chat is fetched from and persisted by the backend. The interface uses a polling mechanism to retrieve the agent's progress, continuously polling until an AI message with the `packaged: True` flag in `additional_kwargs` is received, indicating the completion of the turn.

The interface supports rendering rich media:
- **Image Blocks**: Renders full-width images via `image_url` metadata.
- **Mermaid Diagrams**: Renders interactive Mermaid diagrams using the `MermaidShow` component from the `mfe1` remote. Diagrams are dynamically loaded for any message containing `mermaid_diagrams` metadata.
- **Dynamic MFE Rendering**: Supports loading and rendering any remote MFE component dynamically via the `MfeRenderer`. This is used to display interactive or structured content (e.g., `JsonShow` from `mfe1`) based on `mfe_contents` metadata returned by agent tools.
- **Conditional Content Rendering**: To reduce visual redundancy, the text content of an AI message is automatically hidden if it contains one or more `mfe_contents`. In these cases, the MFE is shown as the primary response.

### 4.2 Multi-User Isolation
Chats are isolated by a `User ID`. Currently, this is handled via a mocked login screen that captures the user ID and passes it to the backend via an HTTP header (e.g., `X-User-ID`).

*Note: Future iterations plan to replace this mocked authentication with standard OAuth2 flows.*

### 4.3 Module Federation Integration
To support embedding within a shell application, the container exposes its core functionality via a specific route configuration (`./routes`), which is mapped to `remote.routes.ts`. This allows internal navigation when loaded as a remote.

### 4.4 Dockerization
The frontend application must be packaged and run inside a Docker container without relying on Docker Compose, aligning with the project's strategy for eventual Kubernetes migration.

### 4.5 Resizable Workspace
The main layout features a draggable splitter between the central chat area and the right-side visualization panel (AI WORKSPACE). This allows users to dynamically adjust the proportions of the interface to focus on either the conversation or the generated visualizations and data MFEs. The panel width is persisted during the session and constrained between 320px and 850px to maintain layout integrity.

## 5. Development Guidelines

- Run tests using `ng test --watch=false`.
- Ensure any modifications to the MFE structure or routing are reflected in this PRD and the native federation configuration.
- The UI should remain stateless where possible, deferring state persistence to the backend database.
