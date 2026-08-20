# Project architecture

Laitoxx uses a feature-oriented architecture with a small application layer.
The goal is to keep feature code independent, make startup predictable and
prevent the GUI from becoming the owner of business logic.

## Runtime flow

```text
start.py
  -> environment and update checks
  -> gui.py / python -m laitoxx
  -> laitoxx.app.bootstrap
  -> QApplication + network policy + settings
  -> MainWindow
  -> tool catalog
  -> input controller -> execution controller -> feature handler
```

## Package responsibilities

### `laitoxx.app`

Application assembly and orchestration:

- `bootstrap.py` is the only composition root.
- `catalog.py` defines `ToolSpec` and resolves feature handlers lazily.
- `tool_registry.py` contains declarative tool and category metadata.
- `plugins/` owns the Lua runtime and its host API.

This layer may depend on `core`, `features`, `interfaces` and `shared` when it
assembles the application. It must not contain feature-specific algorithms.

### `laitoxx.core`

Process-wide infrastructure: settings, resource paths, localization, network
policy and connectivity checks. It must not import concrete feature modules.

### `laitoxx.features`

User-facing capabilities grouped by domain. Feature modules may use `core` and
`shared`, but should not import the GUI or sibling features. A feature exposes a
small callable entrypoint for the tool catalog; optional dependencies belong
behind that entrypoint.

### `laitoxx.interfaces.gui`

PyQt widgets, dialogs and presentation controllers. GUI classes collect input,
display output and delegate execution. Reusable analysis and transformation
logic belongs in `features` or `shared`.

### `laitoxx.shared`

Stable reusable domain primitives. The graph package owns entities, relations,
serialization, correlation and layout-independent algorithms.

`shared.execution` owns cooperative pause, cancellation and progress contracts.
`shared.report_export` owns safe JSON and CSV serialization. Long running
features use these contracts instead of calling GUI classes or repeating
thread lifecycle logic.

## Long running feature services

Network features expose a synchronous service that accepts configuration,
progress callbacks and `JobControl`. The service returns a structured report.
The GUI owns `QThread`, widgets and dialogs, while the service owns queueing,
network policy, parsing and result classification.

The Web Crawler follows this split under `features/web_audit/crawler`. Domain
Intelligence owns passive subdomain discovery under `features/web_audit`.
Username OSINT keeps provider validation, health history and inference inside
its feature package. None of these services import `interfaces.gui`.

## Domain Intelligence composition

Subdomain discovery is a Domain Intelligence panel, not a standalone catalog
tool. Certificate Transparency produces candidates. Optional DNS and HTTP
verification add evidence before export or graph conversion. Provider errors
remain attached to the report and do not discard partial results.

## Adding a built-in tool

1. Add the implementation under the appropriate `features/<domain>` package.
2. Expose one callable that accepts the input expected by the execution layer.
3. Add a `ToolSpec` to `app/tool_registry.py` using
   `package.module:callable`; do not import the feature into the registry.
4. Add the tool name to exactly one category.
5. Add specialized GUI only when the standard input controllers cannot express
   the workflow.

## Runtime data

Source and runtime data are separate by convention:

- `resources/` contains shipped, read-only application assets.
- `settings/` contains mutable settings, caches and generated investigation data.
- `logs/` contains runtime logs.
- `lua_plugins/` contains user-installable extensions.

Code must obtain these locations through `core.settings.paths`; feature modules
should not derive repository-relative paths independently.
