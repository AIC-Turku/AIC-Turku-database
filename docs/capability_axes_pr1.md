# Capability axes and route_type foundations (PR1)

This PR introduces canonical schema/vocabulary foundations for capability axes while preserving legacy compatibility.

- `modalities` remains a legacy mixed-axis field during migration.
- New canonical axes are introduced under `capabilities`:
  - `imaging_modes`
  - `contrast_methods`
  - `readouts`
  - `workflows`
  - `assay_operations`
  - `non_optical`
- `light_paths[].id` is a stable local route identifier.
- `light_paths[].route_type` is the controlled optical route type.
- `light_paths[].readouts` captures route-associated measurement readouts.
- Workflow and non-optical capability tags are not optical light-path routes.

Full active instrument migration is deferred to later PRs.

> **Status (updated):** Active instrument migration is now complete. All 22 active instruments use canonical `capabilities` axes. Top-level `modalities` is rejected at build time for active instruments.

- `optical_routes` is limited to optical route families only.
- Readouts belong in `measurement_readouts`, workflows in `workflow_tags`, assay operations in `assay_operations`, and non-optical capabilities in `non_optical_capabilities`.
- Legacy/meta terms such as `shared` and `all` are not canonical `route_type` values.
