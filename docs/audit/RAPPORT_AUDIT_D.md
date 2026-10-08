# Audit D - Sources, concordance et scenario sans reforme

**8 octobre 2026 - Base : archive `modelisation_retraite.zip`.**
Le classeur `AUDIT_TRACABILITE_RETRAITES.xlsx` initial a servi de liste de controles de depart. Le present lot remplace ses mentions « a verifier » par des controles de valeurs, sans declarer une validation economique finale.

## 1. Resultats et perimetre

- Neuf classeurs fournis, dont le MASTER de 17 feuilles; huit fichiers dans `data/sources`.
- Treize Parquet compares au MASTER : toutes les colonnes, valeurs manquantes et valeurs presentes. Aucun ecart hors tolerances.
- 80 controles et 57 091 comparaisons de valeurs : ce nombre inclut des relectures de valeurs, des identites et des champs texte. Ce n'est pas un nombre d'observations institutionnelles distinctes.
- Lecture des valeurs OOXML en cache. Aucun recalcul de formule Excel, aucune verification d'authenticite sur Internet.
- Le MASTER, les huit sources et les treize Parquet sont conserves a l'identique, empreintes SHA-256 controlees.

`CONFORME` signifie concordance dans les tolerances indiquees, pas validation causale d'une reforme. `PARTIEL` signale une verification incomplete. `ALERTE` appelle une decision methodologique. Un hash prouve l'identite des octets, pas une certification de l'organisme producteur.

## 2. Verifications par source

| Tables | Controle effectue |
|---|---|
| Demographie | Toutes les cellules du perimetre present : 2025-2070, ages 15-100, F/H, contre populationF et populationH. Le MASTER ne couvre pas tous les ages. |
| EV65 | F/H dans hyp_mortaliteF/H, plus ligne T ponderee par les populations a 65 ans. Esperance de vie de periode, non de generation. |
| Macro, retraite, sensibilites | Lignes du COR P1/P2 : figures et cellules identifiees, ratios et valeurs manquantes conserves. |
| Activite seniors | 18 ancrages COR verifies. Les 414 taux annuels INSEE 2023 ne sont pas confrontes a leur fichier original ECRT2023-E2, absent. |
| Marche du travail | Effectifs et taux PACT00/PEMP01, identites derivees du MASTER et controle independant CHOM01. |
| Calendriers | AOD et DAR compares aux tableaux 1.4/1.5 fournis; expansion mensuelle et prolongation de la derniere regle. Ce controle ne valide ni l'AAD a 67 ans ni la date d'effet Legifrance. |
| CNAV | Age/sexe dans B-Liquidants; motifs et pensions moyennes ponderees dans H-Conditions_liq. |
| Benchmarks | Neuf fourchettes du tableau 2.10; aucune interpolation ou cible obtenue par moyenne. |

### Arrondis CHOM01

Le MASTER derive les chomeurs par difference entre actifs et emplois. Les sources publient les effectifs en milliers a une decimale. Le controle independant accepte jusqu'a 151 personnes d'ecart (trois arrondis possibles de 50, plus marge numerique) et 0,0501 point de taux. Les ecarts bruts restent dans `cellules.csv`. Il ne s'agit pas d'une egalite exacte entre sources arrondies. Les autres controles utilisent generalement atol=1e-10, rtol=1e-12, et atol=1e-7 pour certaines identites derivees.

## 3. Croisement DREES disponible

`H-Conditions_liq` (Part 2) contient le croisement age x sexe x motif pour la CNAV : flux 2024, code CC 0015, taux Ensemble. Neuf motifs exclusifs sont regroupes en quatre categories. Les attributs `mico` et `Cpte Perso Penibilite` sont exclus des sommes car ils se recouvrent avec les motifs.

`data/derived/cnav_age_group_2024.csv` conserve 144 cellules avec les numeros de lignes source et le filtre. F et H constituent les cellules du moteur. T reste un controle et ne doit pas etre additionne a F/H. Une combinaison absente n'est pas convertie arbitrairement en zero.

| Champ historique 2024, F+H | Effectif |
|---|---:|
| Tous motifs, tous ages disponibles, y compris >70 | 648 346 |
| Droit commun, age 64 | 46 606 |
| Droit commun, ages 62+63+64 | 220 814 |
| Tous motifs, classe >70 | 15 581 |

Ces nombres ne sont PAS des emplois supplementaires ni une projection de futurs liquidants. Le croisement peut remplacer une hypothese d'independance, mais le contrefactuel 62-63 ->64, les delais et les comportements restent a justifier. La nouvelle extraction n'est donc pas branchee dans `simulation.py` dans ce lot.

## 4. Corrections de code

1. `run_aod_simulation('statu_quo', 768, 768)` produit 45 annees completes avec des deltas nuls. Les tables mensuelles vides gardent leurs schemas, et la branche F/H conserve 90 lignes.
2. `benchmark_aod_plus_1` avec deux AOD de calibration identiques est refuse : le scenario contient toujours une hausse juridique. Le precedent test propose avec ce preset et 768/768 etait conceptuellement incorrect.
3. Rejet explicite des parametres non finis, decalages uniformes contradictoires, pivot/EV non implementes et baisses non prises en charge. Aucune baisse n'est simulee par simple inversion de signe.
4. La synthese exige ses colonnes au lieu de masquer les manquantes. Ajout de `delayed_person_years_transition_adjusted`, distinct des personnes-annees brutes.
5. Le test `test_simulation_returns_expected_blocks` avait une liste de cles mais aucune assertion. L'assertion manquante est ajoutee.
6. Ajout de `pydantic>=2,<3` aux dependances. Cela n'est pas un verrouillage complet des versions.

## 5. Non-regression et points non resolus

Le benchmark positif et la branche comportementale sont compares sur leurs 45 annees / 90 cellules a des instantanes extraits du code ORIGINAL de l'archive. Les deux trajectoires sont inchangees dans les tolerances des tests.

Restent a traiter : classe >70 eliminee par le groupby numerique du prototype; statut des liquidants non identifiable par les taux de tous les 60-64 ans; facteur lineaire de maturite propre au prototype; date d'effet de la nouvelle reforme absente; difference CNAV / tous regimes; original ECRT2023-E2 manquant; metadonnees Fig 2.4 incoherentes.

Fig 2.4 B10 mentionne fecondite 1,8 / migration 70 000 / chomage cible 2032, contre 1,45 / 150 000 / 2040 dans Fig 2.2 B8. La concordance des valeurs copiees ne valide pas leur interpretation.

## 6. Reproduction

Dans l'environnement Python 3.12 de la VM, avec PyArrow installe :

```text
python -m pytest -q
python scripts/audit_sources.py
```

Le script ecrit `data/audit/controles.csv`, `cellules.csv`, `inventaire.csv`, `synthese.json` et regenere l'annexe CNAV. Il ne reecrit aucune source ni les 13 Parquet. Des alertes methodologiques peuvent subsister avec un code de retour 0 : seuls les ecarts numeriques/structurels bloquent ce controle. Le XLSX fourni est un instantane date de ce lot; il n'est pas actualise automatiquement par ce script.

Les chemins et empreintes sont dans `config/source_catalog.yaml` et `data/audit/integrite_sources.json`. Les adresses de cellules et transformations sont dans `cellules.csv`. Les URL sont des references documentaires du projet, non des liens reverifies en ligne durant cet audit.

## 7. Prochaine etape

1. Ajouter ECRT2023-E2 et terminer la verification des profils d'activite.
2. Definir la liquidation de reference a partir du croisement observe, avec traitement explicite de >70 et des cellules absentes.
3. Fixer le contrefactuel et la date d'effet, sans facteur choisi seulement pour entrer dans une fourchette.
4. Rechercher une source sur le statut avant liquidation.
5. Raccorder les hypotheses approuvees, puis calculer PIB, cotisations, pensions et soldes.
