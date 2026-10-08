# Audit des sources et correction du scenario sans reforme

- **Verification :** les 13 Parquet concordent avec le MASTER; les valeurs sourcables sont rapprochees des classeurs fournis, avec tolerances explicites.
- **Correction :** le vrai scenario `statu_quo` produit des effets nuls sur 2026-2070; un preset +1 an avec des ages identiques est refuse.
- **Nouvelle information :** la DREES fournit bien le croisement CNAV 2024 age x sexe x groupe. L'extraction est disponible, mais n'est pas encore utilisee par le moteur.
- **Inchange :** sources originales, MASTER, Parquet, hypothese de reconstruction, facteur de maturite et resultats du benchmark positif.
- **Limites restantes :** ECRT2023-E2 absent, classe >70, statut avant liquidation, metadonnees COR et date d'effet de la reforme.
- **Tests :** 47 ajoutes. Rejeu local de 164 tests avec lecteur Parquet de controle; validation native finale requise sur la VM.
