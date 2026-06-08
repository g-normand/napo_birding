from bs4 import BeautifulSoup  
from datetime import datetime
import requests
import argparse
import csv
import re
    
parser = argparse.ArgumentParser(
    description="Compare guide species with eBird"
)

parser.add_argument(
    "--guide",
    type=str,
    required=True,
    help="Guide name (guango)"
)

def linkify(text):
    if not text or text == '—':
        return text
    return re.sub(
        r'(https?://\S+)',
        r'<a href="\1" target="_blank">\1</a>',
        text
    )

args = parser.parse_args()

guide = args.guide

def extract_observation_dates(list_urls):
    result = {}
    for url in list_urls:
        website = requests.get(f'{url}?hs_sortBy=taxon_order&hs_o=asc')   
        soup = BeautifulSoup(website.text, 'html.parser')
        hotspot = soup.find('div', class_='PlaceTitle-name').find('h1').get_text(strip=True)
        
        for li in soup.find_all('li', class_='BirdList-list-list-item'):
            time_tag = li.find('time')
            if time_tag and time_tag.has_attr('datetime'):
                is_exotic = li.find('svg', class_='Icon--exoticEscapee') is not None
                if is_exotic:
                    continue
                observer_div = li.find('div', class_='Obs-observer')
                name = li.find('span', class_='Species-common').get_text(strip=True)
                if 'sp.' in name:
                   continue
                birder_tag = observer_div.select_one('span:not(.is-visuallyHidden), a')  
                birder = birder_tag.get_text(strip=True) if birder_tag else None
                last_seen = datetime.strptime(time_tag['datetime'], '%Y-%m-%d %H:%M')
                checklist = li.find('div', class_='Obs-date').find('a').get('href')
                if name in result:
                    if last_seen > result[name]['last_seen']:
                        #Newest
                        result[name] = dict(
                            where=hotspot,
                            last_seen=last_seen,
                            checklist=checklist,
                            birder=birder)
                else:
                    result[name] = dict(
                        where=hotspot,
                        last_seen=last_seen,
                        checklist=checklist,
                        birder=birder)

    return result


if (guide == 'guango'):
    list_urls = [
     'https://ebird.org/hotspot/L489428/bird-list', #Guango
    ]
    page_title = 'Lista Guango vs eBird'
    file_guide = "files/guia_guango.csv"
    output_file = 'dist/lista_guango.html'
    description = 'Diferencia entre la guia de Guango y <a href="https://ebird.org/hotspot/L489428/bird-list">eBird</a> en Guango Lodge.'
else:
    raise Error('GUIA DESCONOCIDA')

ebird_data = extract_observation_dates(list_urls)

guia_data = {}
order = 1

with open(file_guide, newline='', encoding='utf-8') as fp:
    reader = csv.DictReader(fp, delimiter=';')

    for row in reader:
        species = row["especies"].strip()
        if not species:
            continue
        guia_data[species] = dict(order=order, comentarios=row['comentarios'], guia=row['guia'])
        order += 1

only_in_ebird = {k: ebird_data[k] for k in ebird_data.keys() - guia_data.keys()}
only_in_guide = {k: guia_data[k] for k in guia_data.keys() - ebird_data.keys()}

new_in_guide = {}
guide_and_ebird = {}
for species in ebird_data.keys() & guia_data.keys():
    if guia_data[species]['guia'] == 'ebird':
        new_in_guide[species] = ebird_data[species]
    else:
        guide_and_ebird[species] = ebird_data[species]

sorted_ebird = sorted(only_in_ebird.items(), key=lambda x: x[1]['last_seen'], reverse=True)
sorted_guide = sorted(only_in_guide.items(), key=lambda x: x[1]['order'])
sorted_new_guide = sorted(new_in_guide.items(), key=lambda x: x[1]['last_seen'], reverse=True)
sorted_guide_and_ebird = sorted(guide_and_ebird.items(), key=lambda x: x[1]['last_seen'], reverse=True)

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{page_title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 1200px; margin: auto; }}
    h1   {{ color: #2c5f2e; }}
    h2   {{ color: #3a7d44; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
    th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #eee; }}
    th {{ background: #f0f7f0; }}
    tr:hover {{ background: #f9fdf9; }}
    .badge {{ font-size: 0.85em; color: #666; margin-left: 6px; }}
  </style>
</head>
<body>
  <h1>{page_title}</h1>
  <div>{description}</div>

  <h2>Solo en eBird <span class="badge">({len(only_in_ebird)} especies)</span></h2>
  <table>
    <thead><tr><th>Especie</th><th>Último avistamiento</th><th>Hotspot</th><th>Observador</th></tr></thead>
    <tbody>
"""
for species, info in sorted_ebird:
    date_str = info['last_seen'].strftime('%d/%m/%Y')
    birder   = info.get('birder') or '—'
    where    = info.get('where') or '—'
    checklist = info.get('checklist')
    html += f"      <tr><td>{species}</td><td><a href='{checklist}'>{date_str}</a></td><td>{where}</td><td>{birder}</td></tr>\n"


if(len(only_in_guide)) > 0:
    html += f"""    </tbody>
    </table>

    <h2>Solo en la guía <span class="badge">({len(only_in_guide)} especies)</span></h2>
    <table>
        <thead><tr><th>Especie</th><th>Comentarios</th></tr></thead>
        <tbody>
    """
    for species, info in sorted_guide:
        comentarios = linkify(info.get('comentarios') or '—')
        html += f"      <tr><td>{species}</td><td>{comentarios}</td></tr>\n"

if(len(new_in_guide)) > 0:
    html += f"""    </tbody>
    </table>

    <h2>Nuevo para la guía <span class="badge">({len(new_in_guide)} especies)</span></h2>
    <table>
        <thead><tr><th>Especie</th><th>Último avistamiento</th><th>Hotspot</th><th>Observador</th></tr></thead>
        <tbody>
    """
    for species, info in sorted_new_guide:
        date_str = info['last_seen'].strftime('%d/%m/%Y')
        birder   = info.get('birder') or '—'
        where    = info.get('where') or '—'
        checklist = info.get('checklist')
        html += f"      <tr><td>{species}</td><td><a href='{checklist}'>{date_str}</a></td><td>{where}</td><td>{birder}</td></tr>\n"



html += f"""    </tbody>
</table>

<h2>En la guía y en eBird <span class="badge">({len(guide_and_ebird)} especies)</span></h2>
<table>
    <thead><tr><th>Especie</th><th>Último avistamiento</th><th>Hotspot</th><th>Observador</th></tr></thead>
    <tbody>
"""
for species, info in sorted_guide_and_ebird:
    date_str = info['last_seen'].strftime('%d/%m/%Y')
    birder   = info.get('birder') or '—'
    where    = info.get('where') or '—'
    checklist = info.get('checklist')
    html += f"      <tr><td>{species}</td><td><a href='{checklist}'>{date_str}</a></td><td>{where}</td><td>{birder}</td></tr>\n"


html += """    </tbody>
  </table>
</body>
</html>
"""

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'{output_file.upper()} : DONE!')