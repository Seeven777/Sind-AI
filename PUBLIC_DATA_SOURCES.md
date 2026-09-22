# Catálogo inicial de dados públicos — Cognitive Foundation 1.0a

Fontes catalogadas: **28**.

Este arquivo descreve o ponto de partida. O catálogo pode crescer por descoberta de OpenAPI, feeds, sitemaps e novos adaptadores aprovados.

| ID | Fonte | Autoridade | Acesso | Adapter |
|---|---|---|---|---|
| `dados_gov_br` | Portal Brasileiro de Dados Abertos | official | REST/OpenAPI | direct |
| `ibge` | IBGE APIs | official | REST/JSON | direct |
| `camara` | Dados Abertos da Câmara dos Deputados | official | REST/JSON/XML/OpenAPI | direct |
| `senado` | Dados Abertos do Senado Federal | official | Web Service/JSON/XML/CSV | direct |
| `datajud` | CNJ DataJud API Pública | official | REST/JSON | direct |
| `receita_federal` | Receita Federal — Dados Abertos | official | bulk files/catalog | direct |
| `mte_pdet` | MTE — Microdados RAIS/CAGED | official | bulk files/catalog | direct |
| `crossref` | Crossref REST API | primary_metadata | REST/JSON | direct |
| `wikidata` | Wikidata Query Service | platform | SPARQL/JSON | direct |
| `github` | GitHub REST API pública | platform | REST/JSON | direct |
| `open_meteo` | Open-Meteo | platform | REST/JSON | direct |
| `nominatim` | OpenStreetMap Nominatim | platform | REST/JSON | direct |
| `overpass` | OpenStreetMap Overpass API | platform | Overpass QL/JSON | direct |
| `brasilapi` | BrasilAPI | community | REST/JSON | direct |
| `worldbank` | World Bank Open Data API | official_international | REST/JSON | capability |
| `openalex` | OpenAlex | primary_metadata | REST/snapshot | capability |
| `wikipedia_wikimedia` | Wikimedia APIs | platform | REST/MediaWiki | discover |
| `gdelt` | GDELT | platform | API/bulk | discover |
| `bcb_dados_abertos` | Banco Central do Brasil — Dados Abertos | official | API/OData/JSON/CSV | discover |
| `portal_transparencia` | Portal da Transparência do Governo Federal | official | REST + downloads abertos | discover |
| `compras_gov` | Compras.gov.br — API de Dados Abertos | official | REST/OpenAPI + CSV | discover |
| `pncp` | Portal Nacional de Contratações Públicas — Dados Abertos | official | REST/JSON | discover |
| `inep` | INEP — Dados Abertos e Microdados | official | downloads/microdados/painéis | catalog |
| `stf_corte_aberta` | STF — Corte Aberta | official | downloads CSV/XLSX + painéis | discover |
| `dados_abertos_sp` | Portal de Dados Abertos do Estado de São Paulo | official | CKAN REST + downloads | direct |
| `alesp_dados_abertos` | ALESP — Dados Abertos | official | structured downloads + documented interfaces | discover |
| `observasampa` | ObservaSampa — Dados Abertos | official | CSV/XLSX/JSON/XML downloads | discover |
| `geosampa` | GeoSampa — Dados Abertos Geoespaciais | official | geospatial downloads/web GIS | discover |

## Prioridade por domínio

- Trabalho/emprego: MTE PDET, RAIS/CAGED; IBGE e Dados Abertos SP como complemento estatístico.
- Empresas: Receita Federal/CNPJ; BrasilAPI apenas como conveniência quando adequado.
- Justiça: CNJ/DataJud e fontes oficiais de tribunais.
- Legislação/processo legislativo: Câmara, Senado e ALESP para o âmbito estadual.
- Economia/finanças: Banco Central, IBGE e World Bank.
- Contratações públicas: Compras.gov.br, PNCP e Portal da Transparência.
- São Paulo: Dados Abertos SP, ObservaSampa, GeoSampa e ALESP.
- Educação: INEP.
- Ciência/metadados: Crossref/OpenAlex.
- Entidades e relações: Wikidata.
- Software/documentação: GitHub.
- Geodados: OpenStreetMap/Nominatim/Overpass e GeoSampa.

## Tipos de integração

1. **direct** — existe um adapter de leitura implementado no Jarvis.
2. **discover** — o Jarvis conhece a fonte e tenta descobrir OpenAPI/Swagger, feed, sitemap ou outra interface antes de propor um adapter.
3. **catalog/bulk** — o Jarvis descobre/downloads e processa localmente somente quando necessário.

Nenhuma fonte pública externa recebe automaticamente documentos internos ou segredos.
