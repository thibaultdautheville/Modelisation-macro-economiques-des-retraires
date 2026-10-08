# Integration des sources retraite dans le depot existant

Ce paquet contient neuf fichiers XLSX originaux, verifies comme archives XLSX, dont le MASTER de 17 feuilles. Il ne contient pas le code Python ni les tables Parquet deja presentes dans le depot.

1. Verifier les droits de redistribution et la visibilite du depot GitHub avant de publier les classeurs sources.
2. Depuis PowerShell, se placer a la racine du projet : `cd "C:\Projets\Modélisation retraite"`.
3. Extraire le ZIP dans un dossier local de confiance puis copier le contenu de son sous-dossier `data` dans le dossier `data` du projet, en fusionnant les dossiers (ne pas supprimer `data/processed`).
4. Verifier le MASTER : `python -c "from zipfile import is_zipfile; print(is_zipfile('data/MASTER_DATA_RETRAITES_V1.xlsx'))"`. Resultat attendu : `True`.
5. Verifier les sources : `Get-ChildItem data\sources -Recurse -File`.
6. Examiner les modifications : `git status --short` et `git diff --stat`.
7. Si les donnees sont autorisees : `git add data/MASTER_DATA_RETRAITES_V1.xlsx data/sources` puis `git commit -m "Restore master workbook and add institutional source files"` et `git push origin main`.
8. Relancer `python -m pytest -q`.

Important : ne pas reconstruire automatiquement les Parquet a partir du MASTER sans verifier les scripts ETL et leur correspondance au millesime des sources. Les anciens fichiers Parquet restent inchanges par ce paquet.

Le classeur ECRT2023-E2.xlsx n'a pas ete fourni dans ce lot.
