"""
ZenK banking integrations (ICICI and related).

Layout:
  models/    — DB models (VAN, inbound txns, events)
  services/  — eCollection handlers + circle dashboard/simulate
  routers/   — bank webhooks + JWT dashboard APIs

HTTP paths stay stable (/webhooks/icici/..., /sponsor-circle/ecollection).
Migrations stay under app/db/migrations (do not move numbered migrations).
"""
