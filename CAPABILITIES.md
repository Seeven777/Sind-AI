# Public Capability Catalog — usado pela Jarvis Autonomy Expansion 0.7

Este catálogo público/read-only foi introduzido na Expansion 0.6 e permanece ativo na 0.7 ao lado do novo Action Hub.

Total: **237** capacidades • **21** provedores • **15** grupos.

Todas as capacidades embutidas são configuradas como `GET`, `auth=none` e `risk=read_only`.

## APIs.guru (4)

- `apiguru.list` — Listar catálogo público de especificações OpenAPI.
- `apiguru.metrics` — Obter métricas do catálogo APIs.guru.
- `apiguru.provider.apis` — Listar APIs conhecidas de um provedor. — parâmetros obrigatórios: provider
- `apiguru.providers` — Listar provedores no diretório APIs.guru.

## BrasilAPI (43)

- `brasil.b3.funds` — Listar tickers de fundos B3 por tipo de fundo. — parâmetros obrigatórios: type_fund
- `brasil.b3.stocks` — Listar tickers de ações negociadas na B3.
- `brasil.banks.get` — Consultar banco por código. — parâmetros obrigatórios: code
- `brasil.banks.list` — Listar bancos brasileiros.
- `brasil.cep.v1` — Consultar endereço por CEP. — parâmetros obrigatórios: cep
- `brasil.cep.v2` — Consultar CEP com dados v2 e possível geolocalização. — parâmetros obrigatórios: cep
- `brasil.cnpj` — Consultar dados cadastrais públicos de CNPJ. — parâmetros obrigatórios: cnpj
- `brasil.cptec.airport` — Consultar clima em aeroporto por código ICAO. — parâmetros obrigatórios: icao
- `brasil.cptec.capitals` — Consultar clima atual de capitais pelo CPTEC.
- `brasil.cptec.cities.list` — Listar cidades disponíveis no serviço CPTEC.
- `brasil.cptec.cities.search` — Pesquisar cidades no CPTEC. — parâmetros obrigatórios: city
- `brasil.cptec.forecast` — Consultar previsão CPTEC por cidade e dias. — parâmetros obrigatórios: city_code, days
- `brasil.cptec.forecast.coordinates` — Consultar previsão semanal CPTEC por latitude e longitude. — parâmetros obrigatórios: latitude, longitude
- `brasil.cptec.forecast.default` — Consultar previsão CPTEC padrão por código da cidade. — parâmetros obrigatórios: city_code
- `brasil.cptec.ocean` — Consultar previsão de ondas por cidade. — parâmetros obrigatórios: city_code, days
- `brasil.cptec.ocean.default` — Consultar previsão de ondas CPTEC padrão por cidade. — parâmetros obrigatórios: city_code
- `brasil.currency.list` — Listar moedas disponíveis para consulta de câmbio.
- `brasil.currency.quote` — Consultar cotação de moeda em uma data. — parâmetros obrigatórios: currency, date
- `brasil.cvm.broker.get` — Consultar corretora CVM por CNPJ. — parâmetros obrigatórios: cnpj
- `brasil.cvm.brokers.list` — Listar corretoras registradas na CVM.
- `brasil.cvm.fund.get` — Consultar fundo CVM por CNPJ. — parâmetros obrigatórios: cnpj
- `brasil.cvm.funds.list` — Listar fundos registrados na CVM.
- `brasil.ddd` — Consultar estado e cidades por DDD. — parâmetros obrigatórios: ddd
- `brasil.fipe.brands` — Listar marcas FIPE por tipo de veículo. — parâmetros obrigatórios: vehicle_type
- `brasil.fipe.price` — Consultar preço FIPE por código. — parâmetros obrigatórios: fipe_code
- `brasil.fipe.tables` — Listar tabelas de referência FIPE.
- `brasil.fipe.vehicles` — Listar veículos FIPE por tipo e código da marca. — parâmetros obrigatórios: vehicle_type, brand_code
- `brasil.holidays` — Listar feriados nacionais por ano. — parâmetros obrigatórios: year
- `brasil.ibge.cities` — Listar municípios de uma UF. — parâmetros obrigatórios: uf
- `brasil.ibge.state.get` — Consultar UF por sigla ou código. — parâmetros obrigatórios: code
- `brasil.ibge.states.list` — Listar UFs brasileiras.
- `brasil.isbn` — Consultar livro por ISBN. — parâmetros obrigatórios: isbn
- `brasil.ncm.get` — Consultar NCM por código. — parâmetros obrigatórios: code
- `brasil.ncm.list` — Listar códigos NCM.
- `brasil.ncm.search` — Pesquisar NCM por descrição ou código. — parâmetros obrigatórios: search
- `brasil.pix.participants` — Listar participantes do PIX.
- `brasil.rates.get` — Consultar uma taxa oficial por nome. — parâmetros obrigatórios: name
- `brasil.rates.list` — Listar taxas e índices oficiais disponíveis.
- `brasil.registrobr.domain` — Consultar situação de domínio .br. — parâmetros obrigatórios: domain
- `brasil.tuss.autocomplete` — Obter sugestões autocomplete TUSS. — parâmetros obrigatórios: search
- `brasil.tuss.get` — Buscar registro TUSS pelo código. — parâmetros obrigatórios: tuss
- `brasil.tuss.list` — Listar registros TUSS.
- `brasil.tuss.search` — Pesquisar procedimentos TUSS por termo. — parâmetros obrigatórios: search

## Crossref (18)

- `crossref.agency` — Identificar agência responsável por um DOI. — parâmetros obrigatórios: doi
- `crossref.funders.get` — Consultar financiador por DOI/ID. — parâmetros obrigatórios: id
- `crossref.funders.search` — Pesquisar financiadores. — parâmetros obrigatórios: query
- `crossref.funders.works` — Listar trabalhos associados a financiador. — parâmetros obrigatórios: id
- `crossref.journals.get` — Consultar periódico por ISSN. — parâmetros obrigatórios: issn
- `crossref.journals.list` — Listar periódicos no Crossref.
- `crossref.journals.works` — Listar trabalhos de um periódico por ISSN. — parâmetros obrigatórios: issn
- `crossref.members.get` — Consultar membro Crossref por ID. — parâmetros obrigatórios: id
- `crossref.members.list` — Listar membros/publicadores Crossref.
- `crossref.members.works` — Listar trabalhos de um membro Crossref. — parâmetros obrigatórios: id
- `crossref.prefixes.get` — Consultar prefixo DOI. — parâmetros obrigatórios: prefix
- `crossref.prefixes.works` — Listar trabalhos por prefixo DOI. — parâmetros obrigatórios: prefix
- `crossref.types.list` — Listar tipos de obra do Crossref.
- `crossref.types.works` — Listar trabalhos por tipo Crossref. — parâmetros obrigatórios: type
- `crossref.works.author` — Pesquisar trabalhos por autor. — parâmetros obrigatórios: author
- `crossref.works.doi` — Consultar metadados de DOI. — parâmetros obrigatórios: doi
- `crossref.works.search` — Pesquisar trabalhos acadêmicos por texto. — parâmetros obrigatórios: query
- `crossref.works.title` — Pesquisar trabalhos por título. — parâmetros obrigatórios: title

## Frankfurter (8)

- `fx.currencies` — Listar moedas suportadas.
- `fx.providers` — Listar provedores de cotações oficiais.
- `fx.rate.pair` — Obter cotação direta entre duas moedas. — parâmetros obrigatórios: base, quote
- `fx.rates.brl` — Cotações atuais com BRL como base.
- `fx.rates.date` — Obter cotações de uma data. — parâmetros obrigatórios: date
- `fx.rates.latest` — Obter cotações mais recentes.
- `fx.rates.period` — Obter série de cotações por período. — parâmetros obrigatórios: from, to
- `fx.rates.usd` — Cotações atuais com USD como base.

## GDELT (6)

- `gdelt.news.search` — Pesquisar notícias globais recentes no GDELT. — parâmetros obrigatórios: query
- `gdelt.news.timeline.country` — Cobertura no GDELT separada por país da fonte. — parâmetros obrigatórios: query
- `gdelt.news.timeline.language` — Cobertura no GDELT separada por idioma. — parâmetros obrigatórios: query
- `gdelt.news.timeline.raw` — Linha do tempo com volume bruto de notícias no GDELT. — parâmetros obrigatórios: query
- `gdelt.news.timeline.tone` — Linha do tempo do tom médio da cobertura no GDELT. — parâmetros obrigatórios: query
- `gdelt.news.timeline.volume` — Linha do tempo do volume relativo de cobertura no GDELT. — parâmetros obrigatórios: query

## GitHub (24)

- `github.org.get` — Consultar organização GitHub. — parâmetros obrigatórios: org
- `github.org.repos` — Listar repositórios de organização GitHub. — parâmetros obrigatórios: org
- `github.repo.branches` — Listar branches de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.commits` — Listar commits de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.community` — Consultar perfil de comunidade/saúde do repositório. — parâmetros obrigatórios: owner, repo
- `github.repo.compare` — Comparar duas refs/commits de repositório. — parâmetros obrigatórios: owner, repo, basehead
- `github.repo.contents` — Ler conteúdo de arquivo/diretório público no GitHub. — parâmetros obrigatórios: owner, repo, path
- `github.repo.contributors` — Listar contribuidores de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.events` — Listar eventos recentes de repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.forks` — Listar forks de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.get` — Consultar repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.issues` — Listar issues públicas de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.languages` — Listar linguagens de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.license` — Consultar licença de repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.pulls` — Listar pull requests de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.readme` — Obter README de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.release.latest` — Obter release mais recente de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.releases` — Listar releases de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.stargazers` — Listar estrelas/usuários de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.tags` — Listar tags de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.repo.topics` — Obter tópicos de um repositório público. — parâmetros obrigatórios: owner, repo
- `github.search.repositories` — Pesquisar repositórios públicos no GitHub. — parâmetros obrigatórios: q
- `github.user.get` — Consultar perfil público de usuário GitHub. — parâmetros obrigatórios: username
- `github.user.repos` — Listar repositórios públicos de usuário GitHub. — parâmetros obrigatórios: username

## Google DNS (4)

- `dns.a` — Resolver IPv4 via DNS-over-HTTPS. — parâmetros obrigatórios: name
- `dns.aaaa` — Resolver IPv6 via DNS-over-HTTPS. — parâmetros obrigatórios: name
- `dns.mx` — Consultar servidores de email via DNS-over-HTTPS. — parâmetros obrigatórios: name
- `dns.txt` — Consultar registros TXT via DNS-over-HTTPS. — parâmetros obrigatórios: name

## Hacker News (9)

- `hn.ask` — IDs de Ask HN do Hacker News.
- `hn.best` — IDs das melhores histórias do Hacker News.
- `hn.item` — Obter item/história/comentário por ID. — parâmetros obrigatórios: id
- `hn.jobs` — IDs de vagas do Hacker News.
- `hn.new` — IDs das histórias novas do Hacker News.
- `hn.show` — IDs de Show HN do Hacker News.
- `hn.top` — IDs das principais histórias do Hacker News.
- `hn.updates` — Consultar itens e perfis atualizados recentemente.
- `hn.user` — Consultar usuário Hacker News. — parâmetros obrigatórios: id

## JSONPlaceholder (5)

- `dev.sample.comments` — Obter comentários de exemplo.
- `dev.sample.post` — Obter post de exemplo por ID. — parâmetros obrigatórios: id
- `dev.sample.posts` — Obter posts de exemplo para testar pipelines.
- `dev.sample.todos` — Obter tarefas de exemplo.
- `dev.sample.users` — Obter usuários de exemplo.

## Open Library (10)

- `openlibrary.author.get` — Consultar autor por chave Open Library. — parâmetros obrigatórios: key
- `openlibrary.author.works` — Listar obras de autor Open Library. — parâmetros obrigatórios: key
- `openlibrary.edition.get` — Consultar edição por chave. — parâmetros obrigatórios: key
- `openlibrary.recent.changes` — Consultar mudanças recentes no catálogo.
- `openlibrary.search.author` — Pesquisar livros por autor. — parâmetros obrigatórios: author
- `openlibrary.search.books` — Pesquisar livros por texto. — parâmetros obrigatórios: q
- `openlibrary.search.isbn` — Pesquisar livro por ISBN. — parâmetros obrigatórios: isbn
- `openlibrary.search.title` — Pesquisar livros por título. — parâmetros obrigatórios: title
- `openlibrary.subject` — Listar livros por assunto. — parâmetros obrigatórios: subject
- `openlibrary.work.get` — Consultar obra por chave Open Library. — parâmetros obrigatórios: key

## Open-Meteo (18)

- `weather.air_quality` — Qualidade do ar e poluentes. — parâmetros obrigatórios: latitude, longitude
- `weather.current` — Condições meteorológicas atuais. — parâmetros obrigatórios: latitude, longitude
- `weather.daily.basic` — Previsão diária de temperatura, chuva e vento. — parâmetros obrigatórios: latitude, longitude
- `weather.elevation` — Consultar elevação por coordenadas. — parâmetros obrigatórios: latitude, longitude
- `weather.flood` — Previsão de vazão de rios/enchentes. — parâmetros obrigatórios: latitude, longitude
- `weather.geocode` — Pesquisar localidade e coordenadas. — parâmetros obrigatórios: name
- `weather.history` — Consultar histórico meteorológico por período. — parâmetros obrigatórios: latitude, longitude, start_date, end_date
- `weather.hourly.basic` — Previsão horária básica. — parâmetros obrigatórios: latitude, longitude
- `weather.humidity` — Umidade e ponto de orvalho por hora. — parâmetros obrigatórios: latitude, longitude
- `weather.marine` — Condições marítimas e ondas. — parâmetros obrigatórios: latitude, longitude
- `weather.pollen` — Previsão de pólen quando disponível. — parâmetros obrigatórios: latitude, longitude
- `weather.precipitation` — Previsão detalhada de precipitação. — parâmetros obrigatórios: latitude, longitude
- `weather.pressure` — Consultar pressão atmosférica. — parâmetros obrigatórios: latitude, longitude
- `weather.soil` — Consultar temperatura e umidade do solo. — parâmetros obrigatórios: latitude, longitude
- `weather.sun` — Nascer/pôr do sol e duração do dia. — parâmetros obrigatórios: latitude, longitude
- `weather.uv` — Índice UV diário. — parâmetros obrigatórios: latitude, longitude
- `weather.visibility` — Consultar visibilidade e cobertura de nuvens. — parâmetros obrigatórios: latitude, longitude
- `weather.wind` — Previsão detalhada de vento. — parâmetros obrigatórios: latitude, longitude

## OpenAlex (25)

- `openalex.authors.get` — Consultar authors por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.authors.group.country` — Agrupar autores por país quando disponível. — parâmetros obrigatórios: search
- `openalex.authors.search` — Pesquisar authors no OpenAlex. — parâmetros obrigatórios: search
- `openalex.funders.get` — Consultar funders por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.funders.search` — Pesquisar funders no OpenAlex. — parâmetros obrigatórios: search
- `openalex.institutions.country` — Pesquisar instituições com filtro opcional de país. — parâmetros obrigatórios: search
- `openalex.institutions.get` — Consultar institutions por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.institutions.search` — Pesquisar institutions no OpenAlex. — parâmetros obrigatórios: search
- `openalex.keywords.get` — Consultar keywords por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.keywords.search` — Pesquisar keywords no OpenAlex. — parâmetros obrigatórios: search
- `openalex.publishers.get` — Consultar publishers por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.publishers.search` — Pesquisar publishers no OpenAlex. — parâmetros obrigatórios: search
- `openalex.sources.get` — Consultar sources por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.sources.issn` — Consultar fontes/periódicos por filtro ISSN. — parâmetros obrigatórios: filter
- `openalex.sources.search` — Pesquisar sources no OpenAlex. — parâmetros obrigatórios: search
- `openalex.topics.get` — Consultar topics por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.topics.group.domain` — Agrupar tópicos por domínio.
- `openalex.topics.search` — Pesquisar topics no OpenAlex. — parâmetros obrigatórios: search
- `openalex.works.doi` — Consultar trabalho por DOI via filtro OpenAlex. — parâmetros obrigatórios: doi
- `openalex.works.filter.year` — Pesquisar trabalhos filtrados por ano. — parâmetros obrigatórios: search, filter
- `openalex.works.get` — Consultar works por ID OpenAlex. — parâmetros obrigatórios: id
- `openalex.works.group.year` — Contar trabalhos por ano de publicação. — parâmetros obrigatórios: search
- `openalex.works.open_access` — Pesquisar trabalhos e filtrar por acesso aberto. — parâmetros obrigatórios: search
- `openalex.works.search` — Pesquisar works no OpenAlex. — parâmetros obrigatórios: search
- `openalex.works.sort.cited` — Pesquisar trabalhos ordenados por citações. — parâmetros obrigatórios: search

## PyPI (3)

- `pypi.project` — Consultar metadados de pacote Python. — parâmetros obrigatórios: project
- `pypi.release` — Consultar uma versão específica de pacote Python. — parâmetros obrigatórios: project, version
- `pypi.simple.project` — Listar arquivos/versionamento pelo Simple JSON API. — parâmetros obrigatórios: project

## USGS (8)

- `usgs.earthquake.all.day` — Todos os terremotos do último dia.
- `usgs.earthquake.day` — Terremotos do último dia (M1+).
- `usgs.earthquake.hour` — Terremotos da última hora (M1+).
- `usgs.earthquake.month` — Terremotos do último mês (M4.5+).
- `usgs.earthquake.near` — Pesquisar terremotos próximos a coordenadas. — parâmetros obrigatórios: latitude, longitude
- `usgs.earthquake.search` — Pesquisar terremotos por período e magnitude. — parâmetros obrigatórios: starttime, endtime
- `usgs.earthquake.significant` — Terremotos significativos do último mês.
- `usgs.earthquake.week` — Terremotos da última semana (M2.5+).

## Wikidata (6)

- `wikidata.entity.get` — Obter uma entidade do Wikidata por QID. — parâmetros obrigatórios: id
- `wikidata.entity.labels` — Obter rótulos e descrições de uma entidade do Wikidata. — parâmetros obrigatórios: id
- `wikidata.entity.sitelinks` — Obter links de uma entidade para projetos Wikimedia. — parâmetros obrigatórios: id
- `wikidata.search.en` — Pesquisar entidades do Wikidata em inglês. — parâmetros obrigatórios: query
- `wikidata.search.pt` — Pesquisar entidades estruturadas no Wikidata em português. — parâmetros obrigatórios: query
- `wikidata.sparql` — Executar consulta SPARQL pública no Wikidata. — parâmetros obrigatórios: query

## Wikimedia (10)

- `wikipedia.opensearch.pt` — Autocompletar títulos da Wikipédia em português. — parâmetros obrigatórios: query
- `wikipedia.page.categories.pt` — Listar categorias de um artigo da Wikipédia. — parâmetros obrigatórios: title
- `wikipedia.page.extract.en` — Obter resumo/extrato de uma página da Wikipédia em inglês. — parâmetros obrigatórios: title
- `wikipedia.page.extract.pt` — Obter resumo/extrato de uma página da Wikipédia em português. — parâmetros obrigatórios: title
- `wikipedia.page.images.pt` — Listar imagens associadas a um artigo da Wikipédia. — parâmetros obrigatórios: title
- `wikipedia.page.info.pt` — Obter metadados e informações básicas de uma página. — parâmetros obrigatórios: title
- `wikipedia.page.links.pt` — Listar links internos de um artigo da Wikipédia. — parâmetros obrigatórios: title
- `wikipedia.random.pt` — Obter páginas aleatórias da Wikipédia em português.
- `wikipedia.search.en` — Pesquisar artigos na Wikipédia em inglês. — parâmetros obrigatórios: query
- `wikipedia.search.pt` — Pesquisar artigos na Wikipédia em português. — parâmetros obrigatórios: query

## Wikimedia Commons (4)

- `commons.category.members` — Listar membros de uma categoria do Wikimedia Commons. — parâmetros obrigatórios: category
- `commons.file.info` — Obter informações de um arquivo do Wikimedia Commons. — parâmetros obrigatórios: title
- `commons.search.categories` — Pesquisar categorias no Wikimedia Commons. — parâmetros obrigatórios: query
- `commons.search.images` — Pesquisar arquivos de mídia no Wikimedia Commons. — parâmetros obrigatórios: query

## World Bank (20)

- `worldbank.countries.list` — Listar países e economias do Banco Mundial.
- `worldbank.country.get` — Consultar país/economia por código. — parâmetros obrigatórios: code
- `worldbank.data.co2` — Consultar Emissões de CO2 per capita por país. — parâmetros obrigatórios: country
- `worldbank.data.gdp` — Consultar PIB em US$ correntes por país. — parâmetros obrigatórios: country
- `worldbank.data.gdp.percapita` — Consultar PIB per capita por país. — parâmetros obrigatórios: country
- `worldbank.data.inflation` — Consultar Inflação ao consumidor por país. — parâmetros obrigatórios: country
- `worldbank.data.internet_users` — Consultar Usuários de internet por país. — parâmetros obrigatórios: country
- `worldbank.data.life_expectancy` — Consultar Expectativa de vida por país. — parâmetros obrigatórios: country
- `worldbank.data.population` — Consultar População total por país. — parâmetros obrigatórios: country
- `worldbank.data.unemployment` — Consultar Desemprego por país. — parâmetros obrigatórios: country
- `worldbank.data.urban_population` — Consultar Percentual de população urbana por país. — parâmetros obrigatórios: country
- `worldbank.income_level.get` — Consultar nível de renda por código. — parâmetros obrigatórios: code
- `worldbank.income_levels` — Listar níveis de renda.
- `worldbank.indicator.get` — Consultar metadados de indicador. — parâmetros obrigatórios: indicator
- `worldbank.indicators.list` — Listar indicadores do Banco Mundial.
- `worldbank.lending_types` — Listar tipos de empréstimo/classificação.
- `worldbank.region.get` — Consultar região por código. — parâmetros obrigatórios: code
- `worldbank.regions.list` — Listar regiões do Banco Mundial.
- `worldbank.sources` — Listar fontes de dados.
- `worldbank.topics` — Listar tópicos de indicadores.

## arXiv (6)

- `arxiv.id.list` — Consultar artigos arXiv por lista de IDs. — parâmetros obrigatórios: id_list
- `arxiv.latest` — Listar artigos recentes para uma consulta. — parâmetros obrigatórios: query
- `arxiv.search.all` — Pesquisar artigos no arXiv por qualquer campo. — parâmetros obrigatórios: query
- `arxiv.search.author` — Pesquisar arXiv por autor (use au:nome). — parâmetros obrigatórios: query
- `arxiv.search.category` — Pesquisar arXiv por categoria (use cat:codigo). — parâmetros obrigatórios: query
- `arxiv.search.title` — Pesquisar arXiv por título (use ti:termo). — parâmetros obrigatórios: query

## ipify (1)

- `network.public_ip` — Descobrir IP público atual.

## npm (5)

- `npm.package` — Consultar metadados de pacote npm. — parâmetros obrigatórios: package
- `npm.package.version` — Consultar versão específica de pacote npm. — parâmetros obrigatórios: package, version
- `npm.search` — Pesquisar pacotes npm. — parâmetros obrigatórios: text
- `npm.search.popular` — Pesquisar npm priorizando popularidade. — parâmetros obrigatórios: text
- `npm.search.quality` — Pesquisar npm priorizando qualidade. — parâmetros obrigatórios: text
