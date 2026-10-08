# Étape E — Liquidations CNAV/DREES, cadrage des écarts et calendrier

## État du lot

**Diagnostic et contrôles préparatoires, pas encore substitution au moteur.** Le benchmark +1 an et les sorties 2026–2070 restent inchangés. La création d'une nouvelle calibration nécessite de définir un contre-factuel par génération, l'année d'entrée en vigueur du scénario et le transfert CNAV → tous régimes.

## Sources et calculs

- `data/derived/cnav_age_group_2024.csv`, issue de DREES EACR `H-Conditions_liq`, CNAV 2024. Croisement 144 lignes incluant F/H/T, 55 à 70 ans et classe ouverte `>70`.
- 648 346 liquidations F+H ; 15 581 dans la classe ouverte (`F=9 083`, `H=6 498`), 632 765 dans les âges fermés.
- Classe `>70` : **jamais remplacée arbitrairement par 71 ans**, mais conservée dans les totaux et exclue des calibrations nécessitant un âge numérique.
- `src/cnav_crossed.py` : contrôles d'intégrité, rapprochement des âges, comparaison avec le mécanisme d'indépendance conditionnelle au sexe.
- `scripts/compare_cnav_methods.py` : rapports chiffrés descriptifs, sans modifier les sorties du moteur. Pour chaque sexe et âge, le contre-factuel *indépendance* est âge total × part du groupe dans le total du sexe, en incluant la classe ouverte dans le dénominateur.

## Points méthodologiques à arbitrer avant une substitution active

1. **Calendrier juridique** : le 1er septembre 2026 indiqué par la source COR Tab 1.4 doit s'appliquer au dispositif qu'elle décrit et ne peut être imposé à *tous* les scénarios. `baseline_eligibility_year/month` et `reform_eligibility_year/month` sont déjà suivis ; construire une date d'effet explicite par scénario et des cohortes éligibles, avec tests de bordure août/septembre 2026.
2. **Facteur de transition** : `build_reference_aod_transition()` calcule `(AOD_legal-744)/24`, agrégé par année d'éligibilité. Ce coefficient n'est pas une probabilité de report. Il ne faut pas multiplier la liquidation déplacée par un second effet juridique avant d'établir l'absence de double comptage.
3. **Distribution CNAV observée** : le croisement historique 2024 remplace l'hypothèse d'indépendance *pour les observations historiques*, pas automatiquement la reconstruction d'une liquidation de droit commun à 64 ans stabilisés.
4. **Périmètre** : la calibration CNAV n'est pas directement un total tous régimes.
5. **Statuts** : 60–64 ans Insee n'est pas la situation des futurs liquidants ; préserver l'étiquette de proxy.

## Contrôle de non-régression

Les nouveaux modules ne sont ni importés ni appelés dans `src/simulation.py`. Le modèle principal est donc inchangé par construction. Les trois nouveaux tests isolent le traitement des âges ouverts, les identités CNAV et les rapprochements de méthodes.
