# Franchise Scout

Scraper de franquicias españolas que extrae información de directorios públicos, busca la web oficial de cada franquicia y analiza si tienen sección de franquiciados, emails de contacto, formularios de captación y material descargable.

## Fuentes

- **mundofranquicia.com** — directorio de franquicias en España
- **franquiciashoy.es** — directorio de franquicias en España

## Datos extraídos

| Campo | Descripción |
|-------|-------------|
| Nombre | Nombre de la franquicia |
| Sector | Categoría/sector |
| Fuente directorio | De qué directorio se extrajo (mundofranquicia / franquiciashoy) |
| URL directorio | Enlace a la ficha en el directorio |
| Web oficial | URL de la web oficial (buscada automáticamente) |
| Sección franquiciados | Si la web tiene apartado para franquiciados |
| URL sección | Enlace directo a la sección |
| Email | Email de contacto encontrado |
| Tipo email | genérico / franquicias / personal |
| LinkedIn | URL del perfil de LinkedIn |
| Formulario franquicia | Si tiene formulario de captación |
| Material descargable | Si ofrece dossier/PDF descargable |
| URL material | Enlace al material |
| Notas | Observaciones adicionales |

## Instalación

```bash
git clone https://github.com/TU_USUARIO/franchise-scout.git
cd franchise-scout
pip install -r requirements.txt
```

## Uso

```bash
# Pipeline completo — 250 franquicias (125 por fuente), exportar a CSV
python scraper.py --max 125 --csv output/franquicias.csv

# Test rápido — 5 por fuente
python scraper.py --max 5 --csv output/test.csv

# Solo una fuente
python scraper.py --source mundo --max 50 --csv output/franquicias.csv
python scraper.py --source franquiciashoy --max 50 --csv output/franquicias.csv

# Solo scraping (sin analizar webs)
python scraper.py --max 125 --skip-analysis --csv output/franquicias.csv

# Exportar a Google Sheets (requiere credentials.json)
python scraper.py --max 125
```

## Opciones

| Flag | Descripción |
|------|-------------|
| `--max N` | Máximo de franquicias por fuente |
| `--csv [FILE]` | Exportar a CSV (default: `output/franquicias.csv`) |
| `--source {all,mundo,franquiciashoy}` | Fuente a scrapear |
| `--skip-analysis` | Solo extraer nombres, sin analizar webs |
| `--no-sheets` | No escribir a Google Sheets |

## Estructura

```
franchise-scout/
├── scraper.py              # CLI principal
├── scrapers/
│   ├── mundofranquicia.py  # Scraper de mundofranquicia.com
│   └── franquiciashoy.py   # Scraper de franquiciashoy.es
├── analysis/
│   ├── search.py           # Búsqueda de web oficial (Google)
│   └── web_analyzer.py     # Análisis de webs de franquicias
├── output/
│   ├── csv_export.py       # Exportación a CSV
│   └── sheets.py           # Exportación a Google Sheets
└── requirements.txt
```

## Notas

- El scraper incluye delays entre peticiones para evitar bloqueos.
- La búsqueda de webs oficiales usa Google Search, que tiene límites de uso.
- Para Google Sheets necesitas un archivo `credentials.json` de Google Cloud.
