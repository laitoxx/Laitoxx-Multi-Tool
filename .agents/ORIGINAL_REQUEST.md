# Original User Request

## Initial Request — 2026-06-11T13:34:09Z

Upgrade the Laitoxx Graph Editor to an interactive, professional OSINT tool by replacing Mermaid.js with Vis-network, adding entity resolution (node merging), drag-and-drop metadata extraction, temporal graph analysis, and graph algorithms (shortest path, centrality).

Working directory: ~/github_repos/Laitoxx-Multi-Tool

Integrity mode: development

## Requirements

### R1. Vis-network Integration
Replace the static Mermaid.js renderer in `_center_panel` (`QWebEngineView`) with Vis-network.
- **Constraint**: `vis-network.min.js` must be downloaded and bundled locally (offline support).
- **Architecture**: Establish two-way communication between Python and JS (e.g., using `QWebChannel`) so interactions in the graph (like selecting a node) trigger Python logic.

### R2. Entity Resolution (Merge Nodes)
Implement a programmatic API in the `Graph` model to merge two nodes. Consolidate their metadata and rewire all connected edges without duplicating connections. Add a UI trigger for this.

### R3. Drag-and-Drop Automation
Support dropping files onto the `QWebEngineView` or `_center_panel`. Intercept the drop event, extract metadata using `MetadataEngine`, and automatically create a `Document` node connected to relevant entities (e.g., `Person` for Author).

### R4. Temporal Graph
Add `valid_from` and `valid_to` fields to the `Edge` and `Node` models. Implement a QSlider in the PyQt UI to filter the graph by time, pushing only valid nodes/edges to the Vis-network frontend.

### R5. Graph Algorithms (NetworkX)
All graph algorithms must be calculated in Python using `networkx`. 
- Shortest Path: Calculate path and update node/edge styling in the JS frontend to highlight it.
- Centrality: Calculate degree centrality and adjust the size/weight of nodes accordingly.

## Verification Resources
A test script must be created (`tests/test_graph_api.py`) to verify the core Python logic programmatically.

## Acceptance Criteria

### API & Logic Verification
- [ ] `pytest tests/test_graph_api.py` passes successfully.
- [ ] Test covers merging two nodes (verifying edges are re-routed and no duplicates exist).
- [ ] Test covers Shortest Path calculation using `networkx` on a dummy graph.
- [ ] `vis-network.min.js` is physically present in the repository resources.

### UI Verification (Manual/Agent-as-judge)
- [ ] Nodes bounce with physics and can be dragged around interactively in the viewer.
- [ ] Dropping a file onto the UI updates the underlying Python graph model and visualizes the result.

## Follow-up — 2026-06-11T14:37:55Z

Реализовать Фазу 2 (Milestone 2) для проекта Laitoxx Graph Editor OSINT Upgrade: заменить рендеринг графа на локальную библиотеку vis-network и настроить двусторонний мост PyQt-JS через QWebChannel.

Working directory: /home/vdox/github_repos/Laitoxx-Multi-Tool
Integrity mode: demo

## Requirements

### R1. Локальный бандл Vis-Network
Загрузить и интегрировать библиотеку `vis-network.min.js` локально в директорию `resources/js` (при необходимости создать её). Изменить генерацию HTML, чтобы она ссылалась на локальный скрипт, а не на CDN. Обратите внимание, что для загрузки файла вам может потребоваться запросить разрешение.

### R2. Двусторонний мост (QWebChannel)
Настроить двустороннюю связь между Python и JavaScript. Python-бэкенд (`graph_editor.py`) должен предоставлять объект bridge для JS. JS должен вызывать методы Python (например, `onNodeSelected`, `onContextMenu`), а Python должен иметь возможность выполнять JS-код (например, для подсветки пути).

### R3. Автоматизированная проверка
Команда агентов должна самостоятельно разработать способ автоматизированной проверки (например, небольшой headless PyQt-тест или скрипт-валидатор), который объективно докажет, что объект QWebChannel инициализируется и сообщения успешно передаются в обе стороны без необходимости ручного запуска полноценного GUI.

## Acceptance Criteria

### Проверка результата
- [ ] Скрипт проверки (тест) написан, запускается без ошибок и подтверждает работу QWebChannel.
- [ ] Файл `vis-network.min.js` физически присутствует в `resources/js/` и загружается в HTML локально.
- [ ] Не используются внешние сетевые CDN ссылки для инициализации графа.


## Follow-up — 2026-06-11T18:19:00+03:00

Реализовать Фазу 3 (Milestone 3) для Laitoxx Graph Editor: поддержка Drag-and-Drop извлечения метаданных. Нужно перехватывать брошенные в окно файлы, прогонять их через `MetadataEngine`, создавать узлы документов и связанных сущностей в графе и обновлять интерфейс.

Working directory: /home/vdox/github_repos/Laitoxx-Multi-Tool
Integrity mode: demo

## Requirements

### R1. Обработка Drag-and-Drop
В `graph_editor.py` настроить перехват событий DragEnter и Drop. Если перетаскивается неподдерживаемый тип файла (определяется логикой приложения), необходимо показать всплывающее предупреждение пользователю (через `QMessageBox`) и прервать обработку.

### R2. Интеграция MetadataEngine
Извлекать метаданные из поддерживаемых перехваченных файлов с помощью `MetadataEngine` (если он еще не реализован в проекте, создать базовую реализацию или заглушку). На основе полученных данных автоматически создавать новые объекты `Node` (например, тип `Document` и связанные с ним авторы) и добавлять их в модель графа.

### R3. Динамическое обновление UI
После пополнения графа новыми узлами и связями, использовать уже настроенный `QWebChannel`, чтобы отправить JS-команду на добавление этих элементов в `vis-network` (canvas) без полной перезагрузки страницы.

### R4. Автоматизированная проверка
Обязательно написать автоматизированный тест (например, с использованием `QTest`), который программно эмулирует Drop-событие и проверяет:
1) Создание узлов в графе при валидном файле.
2) Отображение (или вызов) QMessageBox при невалидном файле.

## Acceptance Criteria

### Проверка результата
- [ ] Написан и успешно выполняется тест, имитирующий drag-and-drop события.
- [ ] Код корректно вызывает QMessageBox (можно замокать для теста), если передан невалидный файл.
- [ ] В модели графа (Python) появляются новые узлы после перетаскивания валидного файла.
- [ ] Код отправляет соответствующую команду обновления через QWebChannel.

