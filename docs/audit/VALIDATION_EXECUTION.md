# Validation d'execution - transparence sur l'environnement

## Avant modification

- Suite originale de l'archive : 117 tests.
- Environnement de travail ici : Python 3.13.5, pandas 2.2.3, NumPy 2.3.5, Pydantic 2.13.5, Pytest 9.0.2.
- PyArrow absent; installation impossible car acces reseau indisponible dans cet environnement.
- Execution native originale : 102 tests passes, 4 echecs et 11 erreurs, tous bloques a la lecture Parquet faute de moteur. Ce n'est pas une validation native du pipeline.

## Verification locale complementaire

Un lecteur temporaire des fichiers Parquet fournis a servi uniquement a charger leurs valeurs en DataFrames pour le rejeu local. Il lit les structures plates, les dictionnaires et la compression Snappy de ces fichiers. Les donnees lues sont comparees au MASTER sur toutes les cellules des 13 tables, sans ecart hors precision flottante.

Ce lecteur est un outil de controle, NON une nouvelle dependance du projet. Il n'est pas livre, n'est pas branche dans le code et ne remplace pas PyArrow sur la VM. Dans le rejeu seulement, pandas.read_parquet est temporairement redirige vers lui.

- Suite originale avec ce lecteur de controle : **117 tests passes**.
- Suite corrigee : **164 tests passes** avec ce lecteur (**47 nouveaux tests**, aucun ancien test supprime).
- Sous-suite ne lisant pas de Parquet, executee SANS adaptateur : **121 tests passes**, 13 deselectionnes et 3 fichiers de tests non charges.
- Compilation de tous les scripts Python : reussie.
- Audit de valeurs : 80 controles, 57 091 comparaisons, aucun ecart hors tolerances declarees.
- Reference positive : comparaison des 45 annees avant/apres et des 90 cellules comportementales, inchangees.
- Neutralite : 45 annees d'ecarts nuls, schemas vides conserves et diagnostic F/H de 90 lignes.
- Integrite : 9 classeurs et 13 Parquet identiques aux octets du ZIP initial.

**La suite complete n'a pas ete executee nativement sous Windows/Python 3.12 avec PyArrow ici.** La recette finale doit donc etre faite sur la VM deja equipee.

## Recette sur la VM

```text
python -m pytest -q
python scripts/audit_sources.py
```

Resultat attendu des tests : 164 reussites si le projet correspond a l'archive de depart. Des alertes PARTIEL/ALERTE doivent rester dans l'audit : elles documentent les limites et ne sont pas effacees pour obtenir un tableau vert.

Les nombres de tests n'ont pas valeur de pourcentage d'avancement ni de certification economique.
