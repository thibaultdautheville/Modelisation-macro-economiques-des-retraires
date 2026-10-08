# Étape E — Calendrier explicite par cohorte : diagnostic isolé

## État et règle testée
- Branche `src/effective_calendar.py` **diagnostique uniquement**, sans changement de `run_aod_simulation` ou de la trajectoire principale.
- `date_effet` désigne dans cette étude une **hypothèse candidate**, appliquée aux cohortes dont l'éligibilité de référence apparaît à compter du mois choisi.
- L'indication du **1er septembre 2026** dans le classeur COR doit être rattachée à un dispositif précis et à son champ juridique : **elle n'est pas validée comme date universelle applicable au benchmark AOD +1 an**.
- Le filtre par cohortes ne suspend pas un report déjà initié avant la date d'effet : par définition, la cohorte entière est exclue ou incluse. D'autres conventions (liquidation effective, droits acquis, entrée en vigueur de la loi) devront être testées et justifiées.

## Equations
Pour une cohorte de naissance `c=(a,m)`, `d_c` désigne son premier mois d'éligibilité sous le droit de référence et `t0` la date candidate :

`g_c(t0) = 1{d_c >= t0} * 1{delta_AOD_c > 0}`.

Le stock brut du moteur est `S_t = (1/12) sum_{mois k du t} sum_{c,s} N_{c,s,k}`.

Le stock candidat est `S_t^date = (1/12) sum_{k du t} sum_{c,s} g_c(t0) N_{c,s,k}`.

L'ancien stock ajusté vaut `S_t^legacy = f_t S_t`, avec `f_t = (AOD_moyen-744)/24` sous hypothèse de maturité linéaire annuelle. On expose **sans l'adopter** `S_t^double = f_t S_t^date`, qui peut cumuler deux approximations de transition.

## Test et interprétation
- Cinq tests ciblés couvrent la sélection de cohortes, la moyenne sur douze mois, une date trop tardive, les mois invalides et les cohortes manquantes.
- La sortie principale reste `annual_delayed_stock` (stock brut, stock corrigé) et les blocs historiques d'emploi sont inchangés.
- La comparaison `S_t^date - S_t^legacy` **n'est pas une estimation économiquement validée** : elle mesure l'écart de deux conventions.
- Le scénario `benchmark_aod_plus_1` s'applique dans l'actuel calendrier légal à des cohortes antérieures à 2026 ; l'expérience de date candidate illustre ce problème, sans l'effacer de l'historique.
- Le prochain jalon exige l'identification juridique de la date d'effet et du dispositif, la définition du champ des cohortes, puis la réestimation des liquidations déplacées à partir du croisement DREES/CNAV.

## Reproduction

`python -m scripts.compare_effective_calendar --date-effet 2026-09-01`

Les CSV sont produits localement après calcul avec le vrai moteur sur la VM ; aucune valeur chiffrée filtrée n'est simulée artificiellement dans cette livraison.
