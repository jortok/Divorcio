# Scripts del proyecto

Resumen rápido de los scripts en `scripts/`.

Scripts activos (útiles / mantenidos):
- `apply_pending_renames.py` — Aplica renombres listados en `PENDIENTES_VERIFICAR.txt` con backups y logging.
- `apply_renames_safe.py` — Aplica `moves_map_suggested.tsv` de forma segura sobre `1_Evidencia_Cronologica/` y actualiza referencias en markdown.
- `extract_cfdi_data.py` — (Específico) Extrae montos/fechas de PDFs CFDI en carpetas de recibos; depende de PyPDF2.
- `finalize_link_repairs.py` — Convierte mapeos en `moves_map*.tsv` a enlaces relativos en markdown.
- `organize_evidence.py` — Organización principal de `1_Evidencia_Cronologica`, crea índices y TOC.
- `repair_markdown_links.py` — Reemplaza referencias en markdown usando `moves_map_applied.tsv`.

Scripts archivados (moved to `scripts/archived/`):
- `fix_readme_toc_links.py` — Pequeña utilidad muy específica; archivada.
- `fix_toc_refs.py` — Reemplaza `toc.md`->`TOC.md`; funcionalidad subsumida por `organize_evidence.py`.
- `prune_and_apply_pending.py` — Flujograma grande y automatizado que llama a varios scripts y hace commits automáticos; archivado para evitar acciones no deseadas.
- `rename_dryrun.py` — Generaba `moves_map_suggested.tsv`; archivado porque generó multiples versiones anteriores y su lógica se puede combinar en `apply_renames_safe.py` si se requiere.

Notas y recomendaciones:
- Antes de eliminar o aplicar renombres masivos, crea un commit y/o copia del repo. Los scripts crean backups automáticos pero conviene tener un punto de restauración en git.
- Para futuras consolidaciones: se puede combinar `rename_dryrun.py` y `apply_renames_safe.py` en una sola herramienta con flags `--dry-run` y `--apply`.
- Si quieres que archive adicionalmente otros scripts o los elimine definitivamente, dime cuáles y procedo.

