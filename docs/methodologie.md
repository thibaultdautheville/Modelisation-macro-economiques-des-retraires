# Methodologie du prototype - etat audite

Ce document decrit le code du projet transmis, pas un modele officiel CNAV/COR/DG Tresor. Voir `docs/audit/RAPPORT_AUDIT_D.md` et `config/methodology.yaml` pour les controles, les hypotheses et leurs limites.

## Chaine des donnees

Les originaux sont conserves sans modification dans `data/sources`. Le MASTER est leur consolidation historique. `scripts/build_data.py` prepare les 13 Parquet. `scripts/audit_sources.py` compare les niveaux sources/MASTER/Parquet; il n'est pas un generateur complet du MASTER depuis les sources.

## Chaine active

`simulation.py` applique le calendrier AOD aux cohortes, calcule une exposition observee historique puis une exposition reconstruite provisoire. Cette masse est repartie uniformement entre les mois de naissance et retenue entre les deux dates d'eligibilite. Les stocks sont agreges sur douze mois puis ajustes par le facteur de maturite du prototype. La branche principale applique deux coefficients globaux. La branche diagnostique ventile par sexe et statut.

## Hypotheses actives a afficher

- Repartition 1/12 des cohortes; chaque cellule est homogene.
- Independance age/categorie conditionnelle au sexe. Une table croisee DREES est maintenant extraite, mais n'est pas encore active.
- Repositionnement de liquidants estimes de droit commun 62-63 ans vers 64 ans. Ce n'est pas un hazard conditionnel de liquidation.
- Calibration CNAV 2024 fixe, sans ajustement deja integre aux tailles futures des generations.
- Dates d'eligibilite utilisees comme approximation du depart; date d'effet de la nouvelle reforme non encore modelisee.
- Facteur lineaire entre 62 et 64 ans, non institutionnel, sans validation causale.
- Statuts moyens des 60-64 ans comme proxy; leur inactivite inclut des personnes deja retraitees.
- Plein effet emploi si les coefficients globaux valent 1 : ce n'est pas un gel des statuts Prisme.

## Scenario neutre corrige

Le scenario doit etre neutre dans le YAML ET dans les ages de calibration. Avec `statu_quo, 768, 768`, aucune cohorte n'est decalee. Les tables vides conservent leurs colonnes et les sorties couvrent 2026-2070 avec des ecarts nuls. Cette correction ne change aucune hypothese du benchmark positif.

## Unites et identites

Un stock est mesure en personnes. Le stock annuel moyen est la moyenne des douze stocks mensuels. Les personnes-annees sont la somme des personnes-mois divisee par douze : meme valeur numerique, usage different. Stock brut, facteur et stock ajuste sont separes. Le maximum mensuel brut n'est pas un maximum ajuste. Les personnes-annees ajustees sont desormais une colonne distincte.

Les taux sont des proportions (0,07 = 7 %). Les pourcentages et les points ne sont pas interchangeables. Aucun chomeur additionnel avec une population active en hausse ne signifie pas un taux de chomage inchange.

## Validation et tracabilite

Les adresses Excel, filtres, transformations, arrondis et differences sont dans `data/audit/cellules.csv`. Le catalogue relie sources, chemins et empreintes. Les sources fournies sont auditees, pas certifiees par consultation de leur producteur.

Les tests prouvent la mise en oeuvre et les identites, pas la causalite economique. Les instantanes protegent la non-regression du prototype. Certaines decisions ont ete prises apres comparaison aux benchmarks : cette comparaison n'est donc pas une validation independante. Les intervalles entre modeles ne sont pas des intervalles de confiance.

Les changements futurs doivent mettre a jour `methodology.yaml`, `source_catalog.yaml`, `REGISTRE_EQUATIONS.md` et les tests avant integration dans la trajectoire active.
