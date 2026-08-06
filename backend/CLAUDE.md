# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MicroBOM is a BOM (Bill of Materials) management system with a graph-based data model. It combines a FastAPI REST API backend with a NiceGUI-powered web frontend (engineer, purchasing, workshop views), using SQLite as the database.

## Commands

```bash
# Run the app (dev mode with auto-reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Seed test data (100 parts + BOM tree + drawings + documents)
python seed_data.py

# Delete and recreate the database (for schema changes during early dev)
rm sql_app.db sql_app.db-shm sql_app.db-wal
# Then restart the app — Base.metadata.create_all runs on startup
```

No tests, linting, or build steps exist yet.

## Architecture

```
app/
├── main.py              # FastAPI app + NiceGUI lifecycle, static mounts, page routes
├── config.py            # Pydantic Settings (reads .env, defaults)
├── database/
│   └── session.py       # Dual engines (async for FastAPI, sync for NiceGUI), session factories
├── models/
│   ├── base.py          # ObjectModel, FileModel, RelationModel — the 3 core tables
│   ├── business.py      # PartModel, DocumentModel, DrawingModel, BOMRelation, etc.
│   └── __init__.py      # Re-exports Base, FileModel, ObjectModel, RelationModel
├── api/v1/
│   ├── __init__.py      # api_router: mounts /files, /nodes, /relations
│   ├── file.py          # POST /{file_type}/upload, GET /download/{object_id}
│   ├── nodes.py         # CRUD for polymorphic graph nodes
│   └── relations.py     # CRUD + CTE traversal for graph edges
├── services/
│   ├── graph.py         # AsyncGraphCrudEngine: node/edge CRUD, CTE tree traversal, batch ops
│   ├── file_service.py  # MD5-deduped async file upload + physical storage
│   └── s3_service.py    # MinIO/S3 integration (placeholder)
├── views/
│   ├── base.py          # render_header, ECNNotifier (engineering change notification bus)
│   ├── components.py    # render_bom_tree, render_card_header, render_file_row, render_industrial_table
│   ├── engineer.py      # Part list page with release control
│   ├── engineer_detail.py  # BOM tree + drawings + documents + child-BOM detail page
│   ├── purchase.py      # Purchasing audit page
│   ├── workshop.py      # Workshop view page
│   └── styles.py        # Global CSS constants (24px industrial-style tables, etc.)
├── middleware/
│   └── exceptions.py    # UnifiedResponse schema, BusinessException, global exception handlers
└── schemas/
    └── graph_batch.py   # Request schemas for batch graph operations
```

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

## Two Database Sessions

| Layer | Engine | Usage |
|---|---|---|
| Async (`engine`) | `sqlite+aiosqlite` | FastAPI route handlers via `Depends(get_db)` |
| Sync (`sync_engine`) | `sqlite` | NiceGUI views via `get_sync_db()` context manager |

Both engines have PRAGMA listeners for `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`.

`AsyncGraphCrudEngine` provides both `async` and `_sync` variants of all methods.

## NiceGUI vs FastAPI in this project

- **FastAPI** (`app.main:app`): REST API at `/api/v1/*`, static file mounts at `/static/uploads/*`
- **NiceGUI**: HTML pages registered via `@ui.page(...)` decorators in `main.py`, rendered by the views layer
- NiceGUI pages use the **sync** database session (`get_sync_db()`) because they run inside the asyncio event loop
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
- `Base.metadata.create_all` only creates tables that don't exist; schema changes require manual DB deletion during early dev
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
- `Base.metadata.create_all` cannot alter existing tables — schema changes require `rm sql_app.db*` and restart
