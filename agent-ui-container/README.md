# AgentUi


This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 21.1.2.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## 🎨 AI Workspace
The application features a "Digital Atrium" design with a dual-pane layout:
- **Chat Window**: Primary conversational interface.
- **AI Workspace**: A resizable visualization panel (320px - 850px) that renders dynamic Micro-Frontend (MFE) components and Mermaid diagrams.

### Key Workspace Features:
- **Reactive Updates**: Synchronized instantly with agent state via `BehaviorSubject`.
- **JSON Inspector**: Toggleable raw data view for any pinned visualization.
- **Two-Way Interaction**: MFEs can send actions back to the AI agent, allowing users to interact with generated data tools (e.g. submitting forms or filtering charts).
- **Glassmorphism Design**: Editorial typography and semi-transparent UI elements for a premium feel.

## Additional Resources
For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
- **Specifications**: See the [UI PRD](./spec/prd.md) for detailed requirements.
