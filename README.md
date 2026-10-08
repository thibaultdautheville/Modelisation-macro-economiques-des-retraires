# Modelisation-macro-economiques-des-retraires
Modélisation macroéconomiques de différents réformes du système de retraites français et prévisions sur différents agrégats 

## Lot D - audit du 8 octobre 2026

Documentation : `docs/audit/RAPPORT_AUDIT_D.md`, `docs/REGISTRE_EQUATIONS.md`, `docs/methodologie.md`.

Audit Excel : `data/audit/AUDIT_TRACABILITE_RETRAITES_MAJ.xlsx`.
Trace par cellule : `data/audit/cellules.csv`. Catalogue : `config/source_catalog.yaml`.

Exemples dans l'environnement Python 3.12 installe :

```text
python -m pytest -q
python scripts/audit_sources.py
python -c "from src.simulation import run_aod_simulation,get_simulation_summary; print(get_simulation_summary(run_aod_simulation('statu_quo',768,768)).head())"
```

Le correctif ne remplace pas les 13 Parquet ni les sources. Le croisement CNAV extrait en CSV est une annexe inactive. Le classeur d'audit est un instantane; le script regenere seulement les rapports CSV/JSON et l'annexe CSV.

La reproduction exige `pyarrow` et les dependances du fichier `requirements.txt`, dont Pydantic 2. Lire `docs/audit/VALIDATION_EXECUTION.md` pour les limites de l'execution de controle effectuee hors VM.
