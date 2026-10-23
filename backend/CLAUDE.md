# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroBOM is a BOM (Bill of Materials) management system with a graph-based data model. It combines a FastAPI REST API backend with a NiceGUI-powered web frontend (engineer, purchasing, workshop views), using SQLite as the database.

## Data Model (the core design)

The system uses **"万物皆对象" (everything is an object)** with polymorphic single-table inheritance via SQLAlchemy:

### Three tables:
1. **`objects`** — universal node table with `object_type` discriminator column + JSON `properties`
2. **`files`** — file metadata, primary key `object_id` is also FK to `objects.id` (1:1)
3. **`relations`** — directed edges (`source_id` → `target_id`) with `relation_type` discriminator + JSON `properties`

### Polymorphic subclasses (in `business.py`):
- **Nodes**: `PartModel`, `DocumentModel`, `DrawingModel`, `AttachmentModel` — each maps to a different `object_type` value, stored in the single `objects` table
- **Edges**: `BOMRelation`, `PartDocRelation`, `PartDrawingRelation`, `DocAttachmentRelation`, `DrawingAttachmentRelation`

### Key patterns:
- `ObjectModel.file_info` is a 1:1 relationship to `FileModel` (cascade delete)
- `RelationModel` has FK `source_id` → `objects.id` and `target_id` → `objects.id`
- Properties are stored as JSON dicts; subclasses expose typed `@property` accessors (e.g., `PartModel.part_number`)
- Foreign keys use `ON DELETE CASCADE` — deleting an object auto-deletes its edges and files

## Database Session (single async engine)

The project uses a single async engine (`sqlite+aiosqlite`) shared by both FastAPI routes and NiceGUI views:

| Layer | Engine | Usage |
|---|---|---|
| Async (`engine`) | `sqlite+aiosqlite` | FastAPI routes via `Depends(get_db)`; NiceGUI views via `async with AsyncSessionLocal()` |

A PRAGMA listener on `engine.sync_engine` sets `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`.

`AsyncGraphCrudEngine` exposes async-only methods; all view-layer DB access is `await`-ed.

## NiceGUI vs FastAPI in this project

- **FastAPI** (`app.main:app`): REST API at `/api/v1/*`, static file mounts at `/static/uploads/*`
- **NiceGUI**: HTML pages registered via `@ui.page(...)` decorators in `main.py`, rendered by the views layer
- NiceGUI pages use the same **async** database session (`async with AsyncSessionLocal()`) and `await` all DB calls
- `ui.run_with(app, ...)` makes NiceGUI piggyback on the FastAPI/uvicorn server

## File Upload Flow

1. User uploads via `ui.upload` in engineer_detail page → `_handle_upload()` (async, reads `e.file.read()`)
2. Creates DrawingModel/DocumentModel node + relation edge + FileModel record all in one transaction
3. MD5 deduplication: same file hash → reuse existing physical file path
4. Files stored in `settings.UPLOAD_DIR` (default `./uploads`)
5. Download endpoint: `GET /api/v1/files/download/{object_id}`

## Key Implementation Details

- NiceGUI `ui.tree` uses Quasar QTree — `on_select` only fires for leaf nodes, `on_expand` fires for parent nodes. Use both channels (with debounce dedup) to reliably capture all node clicks (see `render_bom_tree` in `components.py`)
- NiceGUI `ui.upload` callback receives `UploadEventArguments` — file data is at `e.file` (a `FileUpload` object), `read()` is async
- Schema is managed by Alembic migrations (`alembic upgrade head`), not `Base.metadata.create_all`
- The `requirements.txt` file has encoding issues (garbled Chinese comments) — be careful when editing

## Recurring Patterns

### URL Type Mapper (API layer)

`nodes.py`, `relations.py`, and `file.py` each use a dict mapping URL path segments to SQLAlchemy model classes:

```python
FILE_TYPE_MAPPER = {"attachment": AttachmentModel, "drawing": DrawingModel, "document": DocumentModel}
```

This enables generic endpoints like `POST /api/v1/nodes/{object_type}` where `object_type` is `part`, `document`, etc. — the router looks up the correct polymorphic class at runtime.

### CTE Tree Traversal

`AsyncGraphCrudEngine.get_node_tree_by_cte()` recursively walks the BOM graph in a single SQL query. The flat result list (depth-annotated edges + target nodes) is converted to nested `[{id, label, children}]` structure by `cte_flat_to_nested_tree()` for the `ui.tree` component.

### ECN Notification Bus

`ECNNotifier` in `views/base.py` is a thread-safe in-memory singleton. Engineer page publishes change notifications; purchase and workshop pages poll for updates. No message queue needed — works across same-process sessions.

## Seed Data Structure

`seed_data.py` generates 100 parts across 10 categories (WD=减速机, ZL=轴类, GJ=紧固件, MF=密封件, DQ=电机, CJ=传感器, GL=控制, LJ=材料, BZ=标准件, ASM=总成). Each part gets 2 drawings + 1 document (randomly assigned to 40 parts) + BOM parent-child relations. Understanding this data shape helps when testing UI features.

## Known Issues

- `s3_service.py` is an empty placeholder (no usage anywhere)
- `app/api/v1/nodes.py` defines its own `NodeResponseSchema` that differs from the one in `schemas/graph_batch.py` — be aware of the duplication
- Schema changes are managed by Alembic (`alembic revision --autogenerate` + `alembic upgrade head`); do not delete the database manually
