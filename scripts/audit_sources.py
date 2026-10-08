"""Audit reproductible MASTER / Parquet / classeurs institutionnels locaux.
Ne modifie ni le MASTER, ni les Parquet, ni les classeurs sources.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.xlsx_audit import XlsxValues
from src.source_audit import Audit, GROUPS, SEX, TABLES, equivalent, missing, parse_range


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8-sig')
        return
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=';')
        writer.writeheader(); writer.writerows(rows)


def column_letter(number):
    letters = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def year_values(book, sheet, header_row, data_row):
    cells=book.cells(sheet, end=max(header_row, data_row))
    out={}
    for address, year in cells.items():
        if int(re.search(r'\d+',address).group())!=header_row: continue
        if not isinstance(year, int) or not 1900<=year<=2100: continue
        col=re.sub(r'\d+', '', address); ref=f'{col}{data_row}'
        out[year]=(cells.get(ref), ref)
    return out


def eec_rows(book, sheet):
    out={}
    for rn,row in book.rows(sheet):
        label=row.get(f'A{rn}', '')
        ages=re.search(r'De (\d+) \u00e0 (\d+) ans',str(label))
        if not ages or int(ages[2])-int(ages[1])!=4: continue
        group=f'{ages[1]}-{ages[2]}'
        for sex, nc, rc in [('F','B','C'),('H','D','E'),('T','F','G')]:
            out[group,sex]=(row.get(f'{nc}{rn}'), row.get(f'{rc}{rn}'),f'{nc}{rn}',f'{rc}{rn}')
    return out


def audit_project(root, output, parquet_reader=None):
    if parquet_reader is None:
        import pandas as pd
        parquet_reader=pd.read_parquet
    output.mkdir(parents=True, exist_ok=True)
    audit=Audit(); inventory=[]
    master_path=root/'data/MASTER_DATA_RETRAITES_V1.xlsx'
    master=XlsxValues(master_path)
    tables={sheet:master.table(sheet)[1] for sheet in TABLES}
    # Niveau 1 : egalite de toutes les cellules, y compris NaN et textes.
    for sheet,name in TABLES.items():
        columns, records=master.table(sheet)
        frame=parquet_reader(root/'data/processed'/name)
        if list(frame.columns)!=columns or len(frame)!=len(records):
            audit.notice(f'MP_{sheet}',name,'ECART','Dimensions ou colonnes differentes du MASTER.')
            continue
        pairs=[]
        for i,(source,row) in enumerate(zip(records,frame.to_dict('records')),2):
            for column_index, col in enumerate(columns, 1):
                pairs.append((f'ligne={i};col={col}',row[col],source[col],f'{column_letter(column_index)}{i}'))
        audit.compare(f'MP_{sheet}', name, 'toutes les colonnes', pairs,
                      'data/MASTER_DATA_RETRAITES_V1.xlsx',sheet,
                      note='Valeurs comparees en ordre identique; types physiques non imposes; NaN controles.')
    paths=sorted((root/'data/sources').rglob('*.xlsx'))
    books={}
    for p in [master_path]+paths:
        b=master if p==master_path else XlsxValues(p)
        books[p.name]=b
        inventory.append({'fichier':p.relative_to(root).as_posix(),'octets':p.stat().st_size,
                          'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                          'nb_feuilles':len(b.sheets),'feuilles':' | '.join(b.sheets)})
    source_path=lambda b:b.path.relative_to(root).as_posix()
    central=books['00_central.xlsx']
    cor1=next(b for name,b in books.items() if name.endswith('P1.xlsx'))
    cor2=next(b for name,b in books.items() if name.endswith('P2.xlsx'))
    # Niveau 2 : demographie complete du perimetre 15-100 ans, F/H, 2025-2070.
    for sex in ['F','H']:
        sheet='population'+sex
        cells=central.cells(sheet,end=108)
        years={year:re.sub(r'\d+','',c) for c,year in cells.items() if c.endswith('2') and re.search(r'\d+',c)[0]=='2' and isinstance(year,int) and 2025<=year<=2070}
        ages={v:int(re.search(r'\d+',c)[0]) for c,v in cells.items() if re.fullmatch(r'A\d+',c) and isinstance(v,int) and 0<=v<=105}
        pairs=[]
        for row in tables['DEMOGRAPHIE']:
            if row['sex']!=sex:continue
            ref=f"{years[row['year']]}{ages[row['age']]}"
            pairs.append(((row['year'],row['age'],sex),row['population'],cells.get(ref),ref))
        audit.compare('SRC_DEMOG_'+sex,'demography.parquet','population',pairs,source_path(central),sheet,
                      note='Controle du perimetre present seulement; les 0-14 et 101+ ans ne figurent pas dans le MASTER.')
    ev={}
    for sex in ['F','H']:
        s='hyp_mortalite'+sex; vals=year_values(central,s,2,376)
        pairs=[]
        for row in tables['EV65']:
            if row['sex']!=sex:continue
            official,cell=vals[row['year']];ev[row['year'],sex]=official
            pairs.append(((row['year'],sex),row['life_expectancy_65'],official,cell))
        audit.compare('SRC_EV65_'+sex,'life_expectancy_65.parquet','life_expectancy_65',pairs,source_path(central),s,
                      note='Esperance de vie de periode; pas esperance de vie par generation observee.')
    pop={(r['year'],r['sex']):r['population'] for r in tables['DEMOGRAPHIE'] if r['age']==65}
    pairs=[]
    for row in tables['EV65']:
        if row['sex']!='T':continue
        y=row['year'];vf=pop[y,'F'];vh=pop[y,'H']
        val=(vf*ev[y,'F']+vh*ev[y,'H'])/(vf+vh)
        pairs.append(((y,'T'),row['life_expectancy_65'],val,'EV65 F/H + population age 65'))
    audit.compare('DER_EV65_T','life_expectancy_65.parquet','life_expectancy_65',pairs,
                  source_path(central),'populationF/H; hyp_mortaliteF/H','moyenne ponderee par population a 65 ans')
    # Macro : source horizontale en ratios, pas de division supplementaire par 100.
    macro_specs={
      'productivity_growth_high':('Fig 1.10',4,6),'productivity_growth_ref':('Fig 1.10',4,7),
      'productivity_growth_low':('Fig 1.10',4,8),'unemployment_rate_ref':('Fig 1.11',4,6),
      'unemployment_rate_low':('Fig 1.11',4,7),'unemployment_rate_high':('Fig 1.11',4,8),
      'employment_rate_ref':('Fig 1.12',4,6),'employment_rate_u5':('Fig 1.12',4,7),
      'employment_rate_u10':('Fig 1.12',4,8),'active_population_growth_ref':('Fig 1.6',4,6),
      'real_gdp_growth_raa':('Tab 1.1',4,6),
    }
    retirement_specs={
      'pension_expenditure_pct_gdp':('Fig 2.2',4,6), 'pension_resources_pct_gdp':('Fig 2.8',4,6),
      'pension_balance_pct_gdp':('Fig 2.14',4,6),'pension_relative_to_labour_income':('Fig 2.3',4,6),
      'contributors_per_retiree':('Fig 2.3',4,8),'average_net_pension_eur2023':('Fig 2.4',4,6),
      'average_net_contributor_income_eur2023':('Fig 2.4',4,8),'retirement_age_conj':('Fig 2.5',4,6),
    }
    sensitivity_specs={
      'COR_SENSI_CHOM': {'expenditure_ref':(4,6),'expenditure_u5':(4,7),'expenditure_u10':(4,8),
                        'balance_ref':(9,11),'balance_u5':(9,12),'balance_u10':(9,13)},
      'COR_SENSI_PROD': {'expenditure_ref':(4,7),'expenditure_p04':(4,8),'expenditure_p10':(4,6),
                        'balance_ref':(9,12),'balance_p04':(9,13),'balance_p10':(9,11)},
    }
    for table,book,specs in [('COR_MACRO',cor1,macro_specs),('COR_RETRAITE',cor2,retirement_specs)]:
        for col,(sheet,yr,dr) in specs.items():
            vals=year_values(book,sheet,yr,dr)
            pairs=[(r['year'],r[col],vals.get(r['year'],(None,''))[0], vals.get(r['year'],(None,''))[1]) for r in tables[table]]
            audit.compare('SRC_'+table+'_'+col,TABLES[table],col,pairs,source_path(book),sheet,
                          note='La concordance de copie ne vaut pas validation des metadonnees; valeurs sources manquantes conservees.')
    for table,specs in sensitivity_specs.items():
        sheet='Fig 2.21' if table=='COR_SENSI_CHOM' else 'Fig 2.22'
        for col,(yr,dr) in specs.items():
            vals=year_values(cor2,sheet,yr,dr)
            audit.compare('SRC_'+table+'_'+col,TABLES[table],col,[(r['year'],r[col],vals[r['year']][0],vals[r['year']][1]) for r in tables[table]],source_path(cor2),sheet)
    anchors=cor1.cells('Fig 1.8',end=30);pairs=[]
    anchor_rows={('55-59','F'):12,('60-64','F'):13,('65-69','F'):14,('55-59','H'):25,('60-64','H'):26,('65-69','H'):27}
    for r in tables['ACTIVITE_SENIORS']:
        if missing(r['activity_rate_cor2026_anchor']):continue
        cell=f"{ {2025:'D',2050:'E',2070:'F'}[r['year']]}{anchor_rows[r['age_group'],r['sex']]}"
        pairs.append(((r['year'],r['age_group'],r['sex']),r['activity_rate_cor2026_anchor'],anchors[cell]/100,cell))
    audit.compare('SRC_ACTIVITY_ANCHORS','activity_rates.parquet','activity_rate_cor2026_anchor',pairs,source_path(cor1),'Fig 1.8','pourcentage / 100')
    audit.notice('SOURCE_ACTIVITY_MISSING','activity_rates.parquet','PARTIEL',
                 'Les 414 taux activity_rate_insee2023 sont egaux au MASTER mais non confrontes a ECRT2023-E2.xlsx, absent du ZIP. Les 18 ancrages COR sont verifies.',source='ECRT2023-E2.xlsx')
    # Travail : 4 grandeurs directes, 4 derives; controle independant CHOM01 arrondi.
    a=eec_rows(books['EEC_PACT00.xlsx'],'PACT00');e=eec_rows(books['EEC_PEMP01.xlsx'],'PEMP01');u=eec_rows(books['EEC_CHOM01.xlsx'],'CHOM01')
    for col,bookname,sheet,index,factor,data in [
        ('active_population','EEC_PACT00.xlsx','PACT00',0,1000,a),('activity_rate','EEC_PACT00.xlsx','PACT00',1,.01,a),
        ('employed_population','EEC_PEMP01.xlsx','PEMP01',0,1000,e),('employment_rate','EEC_PEMP01.xlsx','PEMP01',1,.01,e)]:
        pairs=[((r['age_group'],r['sex']),r[col],data[r['age_group'],r['sex']][index]*factor,data[r['age_group'],r['sex']][index+2]) for r in tables['TRAVAIL_2025']]
        audit.compare('SRC_WORK_'+col,'labour_status_rates.parquet',col,pairs,source_path(books[bookname]),sheet,f'x {factor}')
    for col in ['unemployed_population','unemployment_rate','unemployed_share_population','inactive_share_population']:
        pairs=[]
        for r in tables['TRAVAIL_2025']:
            key=r['age_group'],r['sex']; act,ar,ac,arc=a[key];emp,er,ec,erc=e[key]
            val={'unemployed_population':(act-emp)*1000,'unemployment_rate':(act-emp)/act,'unemployed_share_population':(ar-er)/100,'inactive_share_population':1-ar/100}[col]
            pairs.append((key,r[col],val,f'PACT00!{ac}/{arc}; PEMP01!{ec}/{erc}'))
        audit.compare('DER_WORK_'+col,'labour_status_rates.parquet',col,pairs,'EEC_PACT00.xlsx + EEC_PEMP01.xlsx','PACT00 / PEMP01',
                      {'unemployed_population':'(actifs - emplois) * 1000','unemployment_rate':'(actifs - emplois) / actifs','unemployed_share_population':'(taux activite - taux emploi) / 100','inactive_share_population':'1 - taux activite / 100'}[col],atol=1e-7)
    for col,index,factor,tolerance in [('unemployed_population',0,1000,151.0),('unemployment_rate',1,.01,.000501)]:
        pairs=[((r['age_group'],r['sex']),r[col],u[r['age_group'],r['sex']][index]*factor,u[r['age_group'],r['sex']][index+2]) for r in tables['TRAVAIL_2025']]
        audit.compare('CHECK_CHOM01_'+col,'labour_status_rates.parquet',col,pairs,source_path(books['EEC_CHOM01.xlsx']),'CHOM01',f'x {factor}',
                      note='Controle avec tolerance d arrondi; effectifs publies en milliers a une decimale, tolerance 151 personnes (trois arrondis possibles de 50, plus marge numerique); taux publies a 0,1 point, tolerance 0,0501 point. Il ne s agit pas d une egalite exacte des sources arrondies.',atol=tolerance,rtol=0)
    # Regles par generation : tables COR, pas validation juridique actualisee.
    def bounds(label):
        if isinstance(label,int):return (label,1),(label,12)
        dates=re.findall(r'(\d{2})/(\d{2})/(\d{4})',str(label))
        if len(dates)!=2:raise ValueError(label)
        return (int(dates[0][2]),int(dates[0][1])),(int(dates[1][2]),int(dates[1][1]))
    for table,sheet,first,last,labelcol,aodcol,darcol in [('LEGAL_AOD_DAR','Tab 1.4',6,21,'D','G','J'),('LEGAL_RACL20','Tab 1.5',5,13,'E','G','J')]:
        rules=[]
        for rn,row in cor1.rows(sheet,first,last):
            start,end=bounds(row[f'{labelcol}{rn}']);v=row[f'{aodcol}{rn}'];dar=row[f'{darcol}{rn}']
            if isinstance(v,str):
                match=re.search(r'(\d+) ans(?: et (\d+) mois)?',v);months=int(match[1])*12+int(match[2] or 0)
            else: months=round(float(v)*12)
            dar=int(re.search(r'\d+',str(dar))[0]);rules.append((start,end,months,dar,rn))
        for key_col,pos in [('aod_months' if table=='LEGAL_AOD_DAR' else 'racl20_aod_months',2),('dar_quarters',3)]:
            pairs=[]
            for r in tables[table]:
                key=r['birth_year'],r['birth_month'];match=next((v for v in rules if v[0]<=key<=v[1]),None)
                if match is None and key>rules[-1][1]:match=rules[-1]
                if match is None:raise ValueError(f'Regle absente {key}')
                pairs.append((key,r[key_col],match[pos],f'{aodcol if pos==2 else darcol}{match[4]}'))
            audit.compare('SRC_'+table+'_'+key_col,TABLES[table],key_col,pairs,source_path(cor1),sheet,
                          'expansion mensuelle; derniere regle prolongee aux generations suivantes',note='Concordance avec le tableau fourni, pas verification Legifrance de la date d effet. AAD=67 ans non present dans ces tableaux.')
    # Benchmarks : lecture des 9 cellules publiees sous forme de fourchettes.
    cells=cor2.cells('Tab 2.10',end=29)
    metricrows={'gdp_pct':25,'employment_thousands':26,'primary_balance_pts_gdp':27}
    for col,pos in [('min_value',0),('max_value',1)]:
        pairs=[]
        for r in tables['BENCH_COR_AOD1']:
            cell=f"{ {2:'D',10:'E',20:'F'}[r['horizon_years']]}{metricrows[r['metric']]}"
            pairs.append(((r['metric'],r['horizon_years']),r[col],parse_range(cells[cell])[pos],cell))
        audit.compare('SRC_BENCH_'+col,'institutional_benchmarks.parquet',col,pairs,source_path(cor2),'Tab 2.10','lecture de bornes; unites source conservees')
    # DREES : extraction ciblee des lignes CNAV, flux 2024; pas de somme entre regimes.
    drees_extracts={}
    for part,sheet in [(1,'B-Liquidants'),(2,'H-Conditions_liq')]:
        book=next(b for name,b in books.items() if f'Part {part} -' in name)
        selected=[]
        for rn,row in book.rows(sheet):
            v=lambda c:row.get(f'{c}{rn}')
            if v('A')==2024 and v('C')=='CNAV' and v('D')=='0015' and v('F')=='Flux':
                selected.append({'excel_row':rn,**{re.sub(r'\d+','',c):val for c,val in row.items()}})
        drees_extracts[part]=(book,selected)
    b1,rows1=drees_extracts[1]
    ages={(SEX[r['E']],r['H']):r for r in rows1 if r.get('G')=='Ensemble' and r.get('I')=='Ensemble'}
    pairs=[]
    for r in tables['CNAV_LIQ_AGE']:
        q=ages[r['sex'],r['age_label']]
        pairs.append(((r['sex'],r['age_label']),r['effectifs'],q['J'],f"J{q['excel_row']}"))
    audit.compare('SRC_CNAV_AGE','liquidation_age_counts.parquet','effectifs',pairs,source_path(b1),'B-Liquidants','Filtres : 2024, CNAV, CC=0015, Flux, Nb_trim=Ensemble, Type_depart=Ensemble; ages hors total')
    b2,rows2=drees_extracts[2]
    motives=[r for r in rows2 if r.get('H')=='Ensemble' and r.get('I')=='Ensemble' and r.get('G') in GROUPS]
    for col in ['effectifs','share_total','avg_monthly_pension_eur']:
        pairs=[]
        for r in tables['CNAV_LIQ_GROUP']:
            chosen=[v for v in motives if SEX[v['E']]==r['sex'] and GROUPS[v['G']]==r['group_code']]
            count=sum(v['J'] for v in chosen)
            total=sum(v['J'] for v in motives if SEX[v['E']]==r['sex'])
            val={'effectifs':count,'share_total':count/total,'avg_monthly_pension_eur':sum(v['J']*v['K'] for v in chosen)/count}[col]
            pairs.append(((r['sex'],r['group_code']),r[col],val,';'.join(f"J{v['excel_row']}:K{v['excel_row']}" for v in chosen)))
        audit.compare('SRC_CNAV_GROUP_'+col,'liquidation_groups.parquet',col,pairs,source_path(b2),'H-Conditions_liq','regroupement de 9 motifs exclusifs; pension ponderee par effectifs')
    jointrows=[r for r in rows2 if r.get('H')=='Ensemble' and r.get('I')!='Ensemble' and r.get('G') in GROUPS]
    joint=defaultdict(lambda:{'effectifs':0,'source_rows':[],'pension_weighted_sum':0.0,'pension_known_n':0})
    for r in jointrows:
        age='>70' if r['I']=='plus de 70' else r['I']
        key=SEX[r['E']],age,GROUPS[r['G']]
        joint[key]['effectifs']+=r['J'];joint[key]['source_rows'].append(r['excel_row'])
        if r.get('K') is not None:
            joint[key]['pension_weighted_sum']+=r['J']*r['K'];joint[key]['pension_known_n']+=r['J']
    joint_export=[]
    for (sex,age,group),r in sorted(joint.items()):
        joint_export.append({'year':2024,'sex':sex,'age_label':age,'group_code':group,
                             'effectifs':r['effectifs'],'source_file':source_path(b2),'source_sheet':'H-Conditions_liq',
                             'source_rows':'|'.join(map(str,r['source_rows'])),'source_filter':'CNAV;0015;Flux;Taux=Ensemble;hors totaux;hors mico/C2P',
                             'method_status':'observed_grouped_not_active'})
    byage=defaultdict(float);bygroup=defaultdict(float)
    for r in joint_export:
        byage[r['sex'],r['age_label']]+=r['effectifs'];bygroup[r['sex'],r['group_code']]+=r['effectifs']
    audit.compare('JOINT_AGE_MARGIN','cnav_age_group_2024.csv','effectifs',[(k,val,ages[k]['J'],f"J{ages[k]['excel_row']}") for k,val in byage.items()],source_path(b1),'B-Liquidants','somme des motifs exclusifs par age et sexe')
    audit.compare('JOINT_GROUP_MARGIN','cnav_age_group_2024.csv','effectifs',[( (r['sex'],r['group_code']),bygroup[r['sex'],r['group_code']],r['effectifs'],f'D{row_index}') for row_index, r in enumerate(tables['CNAV_LIQ_GROUP'], 2)],
                  'data/MASTER_DATA_RETRAITES_V1.xlsx','CNAV_LIQ_GROUP','somme des ages, y compris >70')
    write_csv(root/'data/derived/cnav_age_group_2024.csv',joint_export)
    # Notes : aucune correction economique silencieuse.
    audit.notice('META_FIG24','retirement_baseline.parquet','ALERTE','Fig 2.4!B10 mentionne fecondite 1,8, solde migratoire 70000 et chomage 7% des 2032; Fig 2.2!B8 mentionne 1,45, 150000 et 2040. Copie des valeurs conforme, validite economique non etablie.',source_path(cor2),'Fig 2.4!B10 / Fig 2.2!B8')
    audit.notice('CNAV_OPEN_AGE','liquidation_age_counts.parquet','ALERTE','La source contient >70 (F=9083, H=6498). Le groupby(age_numeric) du modele elimine cette classe NaN: 632765 au lieu de 648346 au total F+H. Les effectifs 64 ans ne changent pas, les parts normalisees changent.')
    audit.notice('JOINT_DISCOVERED','cnav_age_group_2024.csv','INFO','Croisement observe age x sexe x motif disponible dans H-Conditions_liq. Export annexe fourni, non branche dans la simulation. Cela ne fournit ni statut juste avant liquidation ni hazard conditionnel.',source_path(b2),'H-Conditions_liq')
    audit.notice('STATUS_PROXY','labour_status_rates.parquet','ALERTE','Le groupe 60-64 ans porte sur toute la population en logement ordinaire, dont des retraites; il ne mesure pas le statut des liquidants avant leur depart.')
    audit.notice('MODEL_TRANSITION','reference_transition.py','ALERTE','Facteur lineaire (AOD-744)/24 ajoute au calendrier; hypothese propre au prototype, pas equation institutionnelle; pas de validation independante.')
    audit.notice('SOURCE_CONTEXT','all','INFO','Comparaison des fichiers fournis; authenticite, mise a jour externe et validation Legifrance non verifiees dans ce lot.')
    audit.notice('LEGAL_EFFECTIVE_DATE','legal_aod_dar.parquet','ALERTE','Tab 1.4 indique une application aux liquidations a partir du 1er septembre 2026; le moteur applique sa table a toutes les dates et simule un benchmark des 2022. Date d effet a modeliser; aucun lissage ajoute.')
    write_csv(output/'controles.csv',audit.checks)
    write_csv(output/'cellules.csv',audit.cells)
    write_csv(output/'inventaire.csv',inventory)
    result={'source':'modelisation_retraite.zip','sources_non_modifiees':True,'controles':audit.checks,
            'nb_controles':len(audit.checks),'nb_cellules_comparees':len(audit.cells),
            'nb_ecarts':sum(r['ecarts'] for r in audit.checks),'nb_joint_rows':len(joint_export)}
    (output/'synthese.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for b in set(books.values()):b.close()
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=audit_project(args.root,args.output or args.root/'data/audit')
    print(f"Controles : {report['nb_controles']} | Cellules : {report['nb_cellules_comparees']} | Ecarts : {report['nb_ecarts']}")
    for c in report['controles']:
        if c['statut'] not in ('CONFORME','INFO'):
            print(c['statut'],c['controle'],c['note'])
    raise SystemExit(1 if report['nb_ecarts'] or any(r['statut']=='ECART' for r in report['controles']) else 0)
