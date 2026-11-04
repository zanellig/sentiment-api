# Largo máximo de audio, timeout de reentrega y cupo por defecto

Cada Job admite como máximo 3 h de audio (configurable por Tenant). El `visibility_timeout` de Celery es de 1 h, y el cupo por defecto es de 4 Jobs en curso por Tenant (ADR-0017). El largo máximo es lo que permite elegir un timeout seguro: sin él, un audio muy largo superaría cualquier `visibility_timeout`, y Redis lo entregaría otra vez mientras todavía se está transcribiendo. Los tres números se revisan con el benchmark en la RTX 3070.
