import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'capabilities' / 'catalog.json'
items=[]

def add(id, provider, group, description, url, params=None, fixed=None, keywords=None, response='json', cache=300, min_interval=0.25, headers=None, accept=None, extra=None):
    item={
        'id':id,'provider':provider,'group':group,'description':description,
        'url':url,'method':'GET','auth':'none','risk':'read_only','response':response,
        'params':params or {},'fixed_query':fixed or {},'keywords':keywords or [],
        'cache_ttl':cache,'min_interval':min_interval
    }
    if headers: item['headers']=headers
    if accept: item['accept']=accept
    if extra: item['allow_extra_query']=extra
    items.append(item)

def q(required=False, default=None, name=None):
    d={'in':'query','required':required}
    if default is not None: d['default']=default
    if name: d['name']=name
    return d

def p(required=True): return {'in':'path','required':required}

# Wikimedia / Wikidata (20)
wiki_api='https://pt.wikipedia.org/w/api.php'
wiki_en='https://en.wikipedia.org/w/api.php'
base_fixed={'format':'json','origin':'*'}
add('wikipedia.search.pt','Wikimedia','knowledge','Pesquisar artigos na Wikipédia em português.',wiki_api,{'query':q(True)}, {'action':'query','list':'search','srsearch':'{unused}','format':'json'}, ['wikipedia','pesquisa','enciclopedia'])
# Override mapping by using param names directly for APIs expecting special names
items[-1]['params']={'query':{'in':'query','required':True,'name':'srsearch'}}; items[-1]['fixed_query']={'action':'query','list':'search','format':'json','srlimit':10}
add('wikipedia.search.en','Wikimedia','knowledge','Pesquisar artigos na Wikipédia em inglês.',wiki_en,{'query':{'in':'query','required':True,'name':'srsearch'}},{'action':'query','list':'search','format':'json','srlimit':10},['wikipedia','english','search'])
add('wikipedia.page.extract.pt','Wikimedia','knowledge','Obter resumo/extrato de uma página da Wikipédia em português.',wiki_api,{'title':{'in':'query','required':True,'name':'titles'}},{'action':'query','prop':'extracts','explaintext':1,'format':'json'},['resumo','artigo','wikipedia'])
add('wikipedia.page.extract.en','Wikimedia','knowledge','Obter resumo/extrato de uma página da Wikipédia em inglês.',wiki_en,{'title':{'in':'query','required':True,'name':'titles'}},{'action':'query','prop':'extracts','explaintext':1,'format':'json'},['summary','article'])
add('wikipedia.page.categories.pt','Wikimedia','knowledge','Listar categorias de um artigo da Wikipédia.',wiki_api,{'title':{'in':'query','required':True,'name':'titles'}},{'action':'query','prop':'categories','cllimit':50,'format':'json'},['categorias'])
add('wikipedia.page.links.pt','Wikimedia','knowledge','Listar links internos de um artigo da Wikipédia.',wiki_api,{'title':{'in':'query','required':True,'name':'titles'}},{'action':'query','prop':'links','pllimit':50,'format':'json'},['links','referencias'])
add('wikipedia.page.images.pt','Wikimedia','knowledge','Listar imagens associadas a um artigo da Wikipédia.',wiki_api,{'title':{'in':'query','required':True,'name':'titles'}},{'action':'query','prop':'images','imlimit':50,'format':'json'},['imagens'])
add('wikipedia.page.info.pt','Wikimedia','knowledge','Obter metadados e informações básicas de uma página.',wiki_api,{'title':{'in':'query','required':True,'name':'titles'}},{'action':'query','prop':'info','inprop':'url','format':'json'},['metadata','url'])
add('wikipedia.random.pt','Wikimedia','knowledge','Obter páginas aleatórias da Wikipédia em português.',wiki_api,{'limit':{'in':'query','required':False,'name':'rnlimit','default':5}},{'action':'query','list':'random','rnnamespace':0,'format':'json'},['aleatorio'])
add('wikipedia.opensearch.pt','Wikimedia','knowledge','Autocompletar títulos da Wikipédia em português.',wiki_api,{'query':{'in':'query','required':True,'name':'search'}},{'action':'opensearch','limit':10,'namespace':0,'format':'json'},['autocomplete'])
wd='https://www.wikidata.org/w/api.php'
add('wikidata.search.pt','Wikidata','knowledge','Pesquisar entidades estruturadas no Wikidata em português.',wd,{'query':{'in':'query','required':True,'name':'search'}},{'action':'wbsearchentities','language':'pt','format':'json','limit':10},['wikidata','entidades'])
add('wikidata.search.en','Wikidata','knowledge','Pesquisar entidades do Wikidata em inglês.',wd,{'query':{'in':'query','required':True,'name':'search'}},{'action':'wbsearchentities','language':'en','format':'json','limit':10},['wikidata'])
add('wikidata.entity.get','Wikidata','knowledge','Obter uma entidade do Wikidata por QID.',wd,{'id':{'in':'query','required':True,'name':'ids'}},{'action':'wbgetentities','props':'labels|descriptions|claims|sitelinks','languages':'pt|en','format':'json'},['qid','dados estruturados'])
add('wikidata.entity.labels','Wikidata','knowledge','Obter rótulos e descrições de uma entidade do Wikidata.',wd,{'id':{'in':'query','required':True,'name':'ids'}},{'action':'wbgetentities','props':'labels|descriptions','languages':'pt|en','format':'json'},['labels'])
add('wikidata.entity.sitelinks','Wikidata','knowledge','Obter links de uma entidade para projetos Wikimedia.',wd,{'id':{'in':'query','required':True,'name':'ids'}},{'action':'wbgetentities','props':'sitelinks','format':'json'},['sitelinks'])
add('wikidata.sparql','Wikidata','knowledge','Executar consulta SPARQL pública no Wikidata.', 'https://query.wikidata.org/sparql', {'query':{'in':'query','required':True,'name':'query'}},{'format':'json'},['sparql','grafo'],min_interval=1.0,headers={'Accept':'application/sparql-results+json'})
commons='https://commons.wikimedia.org/w/api.php'
add('commons.search.images','Wikimedia Commons','media','Pesquisar arquivos de mídia no Wikimedia Commons.',commons,{'query':{'in':'query','required':True,'name':'gsrsearch'}},{'action':'query','generator':'search','gsrnamespace':6,'gsrlimit':12,'prop':'imageinfo','iiprop':'url|mime|size','format':'json'},['imagens','commons','media'])
add('commons.file.info','Wikimedia Commons','media','Obter informações de um arquivo do Wikimedia Commons.',commons,{'title':{'in':'query','required':True,'name':'titles'}},{'action':'query','prop':'imageinfo','iiprop':'url|mime|size|extmetadata','format':'json'},['arquivo','licenca','metadata'])
add('commons.search.categories','Wikimedia Commons','media','Pesquisar categorias no Wikimedia Commons.',commons,{'query':{'in':'query','required':True,'name':'gsrsearch'}},{'action':'query','generator':'search','gsrnamespace':14,'gsrlimit':12,'format':'json'},['categorias','commons'])
add('commons.category.members','Wikimedia Commons','media','Listar membros de uma categoria do Wikimedia Commons.',commons,{'category':{'in':'query','required':True,'name':'cmtitle'}},{'action':'query','list':'categorymembers','cmlimit':25,'format':'json'},['categoria','arquivos'])

# BrasilAPI (34) - public, no auth
b='https://brasilapi.com.br/api'
add('brasil.cep.v1','BrasilAPI','brazil','Consultar endereço por CEP.',b+'/cep/v1/{cep}',{'cep':p()},keywords=['cep','endereco'])
add('brasil.cep.v2','BrasilAPI','brazil','Consultar CEP com dados v2 e possível geolocalização.',b+'/cep/v2/{cep}',{'cep':p()},keywords=['cep','coordenadas'])
add('brasil.cnpj','BrasilAPI','brazil','Consultar dados cadastrais públicos de CNPJ.',b+'/cnpj/v1/{cnpj}',{'cnpj':p()},keywords=['cnpj','empresa'])
add('brasil.ddd','BrasilAPI','brazil','Consultar estado e cidades por DDD.',b+'/ddd/v1/{ddd}',{'ddd':p()},keywords=['ddd','telefone'])
add('brasil.banks.list','BrasilAPI','brazil','Listar bancos brasileiros.',b+'/banks/v1',keywords=['bancos'])
add('brasil.banks.get','BrasilAPI','brazil','Consultar banco por código.',b+'/banks/v1/{code}',{'code':p()},keywords=['banco','codigo'])
add('brasil.holidays','BrasilAPI','brazil','Listar feriados nacionais por ano.',b+'/feriados/v1/{year}',{'year':p()},keywords=['feriados','calendario'])
add('brasil.ibge.states.list','BrasilAPI','brazil','Listar UFs brasileiras.',b+'/ibge/uf/v1',keywords=['ibge','estados','uf'])
add('brasil.ibge.state.get','BrasilAPI','brazil','Consultar UF por sigla ou código.',b+'/ibge/uf/v1/{code}',{'code':p()},keywords=['ibge','uf'])
add('brasil.ibge.cities','BrasilAPI','brazil','Listar municípios de uma UF.',b+'/ibge/municipios/v1/{uf}',{'uf':p()},keywords=['municipios','cidades'])
add('brasil.pix.participants','BrasilAPI','brazil','Listar participantes do PIX.',b+'/pix/v1/participants',keywords=['pix','bancos'])
add('brasil.fipe.tables','BrasilAPI','brazil','Listar tabelas de referência FIPE.',b+'/fipe/tabelas/v1',keywords=['fipe','veiculos'])
add('brasil.fipe.brands','BrasilAPI','brazil','Listar marcas FIPE por tipo de veículo.',b+'/fipe/marcas/v1/{vehicle_type}',{'vehicle_type':p()},keywords=['fipe','marcas'])
add('brasil.fipe.vehicles','BrasilAPI','brazil','Pesquisar veículos FIPE.',b+'/fipe/veiculos/v1/{vehicle_type}',{'vehicle_type':p(),'brand':q(False),'search':q(False)},keywords=['fipe','veiculos'],extra=['brand','search'])
add('brasil.fipe.price','BrasilAPI','brazil','Consultar preço FIPE por código.',b+'/fipe/preco/v1/{fipe_code}',{'fipe_code':p()},keywords=['fipe','preco'])
add('brasil.isbn','BrasilAPI','brazil','Consultar livro por ISBN.',b+'/isbn/v1/{isbn}',{'isbn':p()},keywords=['isbn','livro'])
add('brasil.ncm.list','BrasilAPI','brazil','Listar códigos NCM.',b+'/ncm/v1',keywords=['ncm','mercosul'],cache=3600)
add('brasil.ncm.get','BrasilAPI','brazil','Consultar NCM por código.',b+'/ncm/v1/{code}',{'code':p()},keywords=['ncm'])
add('brasil.ncm.search','BrasilAPI','brazil','Pesquisar NCM por descrição ou código.',b+'/ncm/v1',{'search':q(True)},keywords=['ncm','pesquisa'])
add('brasil.rates.list','BrasilAPI','brazil','Listar taxas e índices oficiais disponíveis.',b+'/taxas/v1',keywords=['selic','cdi','ipca','taxas'])
add('brasil.rates.get','BrasilAPI','brazil','Consultar uma taxa oficial por nome.',b+'/taxas/v1/{name}',{'name':p()},keywords=['selic','cdi','ipca'])
add('brasil.registrobr.domain','BrasilAPI','brazil','Consultar situação de domínio .br.',b+'/registrobr/v1/{domain}',{'domain':p()},keywords=['dominio','registro.br'])
add('brasil.cptec.cities.search','BrasilAPI','brazil','Pesquisar cidades no CPTEC.',b+'/cptec/v1/cidade/{city}',{'city':p()},keywords=['cptec','cidade','clima'])
add('brasil.cptec.capitals','BrasilAPI','brazil','Consultar clima atual de capitais pelo CPTEC.',b+'/cptec/v1/clima/capital',keywords=['clima','capitais'])
add('brasil.cptec.airport','BrasilAPI','brazil','Consultar clima em aeroporto por código ICAO.',b+'/cptec/v1/clima/aeroporto/{icao}',{'icao':p()},keywords=['aeroporto','clima'])
add('brasil.cptec.forecast','BrasilAPI','brazil','Consultar previsão CPTEC por cidade e dias.',b+'/cptec/v1/clima/previsao/{city_code}/{days}',{'city_code':p(),'days':p()},keywords=['previsao','clima'])
add('brasil.cptec.ocean','BrasilAPI','brazil','Consultar previsão de ondas por cidade.',b+'/cptec/v1/ondas/{city_code}/{days}',{'city_code':p(),'days':p()},keywords=['ondas','mar'])
add('brasil.cvm.brokers.list','BrasilAPI','brazil','Listar corretoras registradas na CVM.',b+'/cvm/corretoras/v1',keywords=['cvm','corretoras'])
add('brasil.cvm.broker.get','BrasilAPI','brazil','Consultar corretora CVM por CNPJ.',b+'/cvm/corretoras/v1/{cnpj}',{'cnpj':p()},keywords=['cvm','corretora'])
add('brasil.cvm.funds.list','BrasilAPI','brazil','Listar fundos registrados na CVM.',b+'/cvm/fundos/v1',keywords=['cvm','fundos'])
add('brasil.cvm.fund.get','BrasilAPI','brazil','Consultar fundo CVM por CNPJ.',b+'/cvm/fundos/v1/{cnpj}',{'cnpj':p()},keywords=['cvm','fundo'])
add('brasil.b3.stocks','BrasilAPI','brazil','Listar tickers de ações B3 quando disponível.',b+'/b3/v1/acoes',keywords=['b3','acoes','ticker'])
add('brasil.b3.funds','BrasilAPI','brazil','Listar tickers de fundos B3 quando disponível.',b+'/b3/v1/fundos',keywords=['b3','fundos','ticker'])
add('brasil.tuss.search','BrasilAPI','brazil','Pesquisar termos TUSS quando disponível.',b+'/tuss/v1',{'search':q(True)},keywords=['tuss','saude'])

# Open-Meteo (18)
om='https://api.open-meteo.com/v1/forecast'
geo='https://geocoding-api.open-meteo.com/v1/search'
add('weather.geocode','Open-Meteo','weather','Pesquisar localidade e coordenadas.',geo,{'name':q(True),'count':q(False,10),'language':q(False,'pt'),'countryCode':q(False)},keywords=['cidade','coordenadas','geocode'])
common={'latitude':q(True),'longitude':q(True),'timezone':q(False,'auto')}
add('weather.current','Open-Meteo','weather','Condições meteorológicas atuais.',om,common,{'current':'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m','forecast_days':1},['tempo','agora'])
add('weather.daily.basic','Open-Meteo','weather','Previsão diária de temperatura, chuva e vento.',om,common,{'daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset','forecast_days':7},['previsao','7 dias'])
add('weather.hourly.basic','Open-Meteo','weather','Previsão horária básica.',om,common,{'hourly':'temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,wind_speed_10m','forecast_days':3},['hora','previsao'])
add('weather.precipitation','Open-Meteo','weather','Previsão detalhada de precipitação.',om,common,{'hourly':'precipitation_probability,precipitation,rain,showers','forecast_days':5},['chuva'])
add('weather.wind','Open-Meteo','weather','Previsão detalhada de vento.',om,common,{'hourly':'wind_speed_10m,wind_gusts_10m,wind_direction_10m','forecast_days':5},['vento'])
add('weather.sun','Open-Meteo','weather','Nascer/pôr do sol e duração do dia.',om,common,{'daily':'sunrise,sunset,daylight_duration,sunshine_duration','forecast_days':7},['sol'])
add('weather.humidity','Open-Meteo','weather','Umidade e ponto de orvalho por hora.',om,common,{'hourly':'relative_humidity_2m,dew_point_2m','forecast_days':3},['umidade'])
add('weather.uv','Open-Meteo','weather','Índice UV diário.',om,common,{'daily':'uv_index_max,uv_index_clear_sky_max','forecast_days':7},['uv'])
add('weather.air_quality','Open-Meteo','weather','Qualidade do ar e poluentes.', 'https://air-quality-api.open-meteo.com/v1/air-quality', common, {'hourly':'pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,european_aqi,us_aqi','forecast_days':3},['ar','poluicao'])
add('weather.pollen','Open-Meteo','weather','Previsão de pólen quando disponível.', 'https://air-quality-api.open-meteo.com/v1/air-quality', common, {'hourly':'alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,ragweed_pollen','forecast_days':3},['polen','alergia'])
add('weather.marine','Open-Meteo','weather','Condições marítimas e ondas.', 'https://marine-api.open-meteo.com/v1/marine', {'latitude':q(True),'longitude':q(True),'timezone':q(False,'auto')}, {'hourly':'wave_height,wave_direction,wave_period,wind_wave_height,swell_wave_height','forecast_days':5},['mar','ondas'])
add('weather.flood','Open-Meteo','weather','Previsão de vazão de rios/enchentes.', 'https://flood-api.open-meteo.com/v1/flood', {'latitude':q(True),'longitude':q(True)}, {'daily':'river_discharge,river_discharge_mean,river_discharge_max','forecast_days':7},['enchente','rio'])
add('weather.history','Open-Meteo','weather','Consultar histórico meteorológico por período.', 'https://archive-api.open-meteo.com/v1/archive', {'latitude':q(True),'longitude':q(True),'start_date':q(True),'end_date':q(True),'timezone':q(False,'auto')}, {'daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max'},['historico','clima'])
add('weather.elevation','Open-Meteo','geography','Consultar elevação por coordenadas.', 'https://api.open-meteo.com/v1/elevation', {'latitude':q(True),'longitude':q(True)},keywords=['altitude','elevacao'])
add('weather.soil','Open-Meteo','weather','Consultar temperatura e umidade do solo.',om,common,{'hourly':'soil_temperature_0cm,soil_temperature_6cm,soil_moisture_0_to_1cm,soil_moisture_3_to_9cm','forecast_days':3},['solo'])
add('weather.pressure','Open-Meteo','weather','Consultar pressão atmosférica.',om,common,{'hourly':'surface_pressure,pressure_msl','forecast_days':3},['pressao'])
add('weather.visibility','Open-Meteo','weather','Consultar visibilidade e cobertura de nuvens.',om,common,{'hourly':'visibility,cloud_cover,cloud_cover_low,cloud_cover_mid,cloud_cover_high','forecast_days':3},['visibilidade','nuvens'])

# Crossref (18)
cr='https://api.crossref.org'
add('crossref.works.search','Crossref','research','Pesquisar trabalhos acadêmicos por texto.',cr+'/works',{'query':{'in':'query','required':True,'name':'query.bibliographic'},'rows':q(False,10)},keywords=['doi','artigos','pesquisa'],min_interval=0.5)
add('crossref.works.title','Crossref','research','Pesquisar trabalhos por título.',cr+'/works',{'title':{'in':'query','required':True,'name':'query.title'},'rows':q(False,10)},keywords=['titulo','doi'])
add('crossref.works.author','Crossref','research','Pesquisar trabalhos por autor.',cr+'/works',{'author':{'in':'query','required':True,'name':'query.author'},'rows':q(False,10)},keywords=['autor'])
add('crossref.works.doi','Crossref','research','Consultar metadados de DOI.',cr+'/works/{doi}',{'doi':p()},keywords=['doi','metadata'])
add('crossref.journals.list','Crossref','research','Listar periódicos no Crossref.',cr+'/journals',{'rows':q(False,20)},keywords=['periodicos','journals'])
add('crossref.journals.get','Crossref','research','Consultar periódico por ISSN.',cr+'/journals/{issn}',{'issn':p()},keywords=['issn'])
add('crossref.journals.works','Crossref','research','Listar trabalhos de um periódico por ISSN.',cr+'/journals/{issn}/works',{'issn':p(),'rows':q(False,10)},keywords=['issn','artigos'])
add('crossref.members.list','Crossref','research','Listar membros/publicadores Crossref.',cr+'/members',{'rows':q(False,20)},keywords=['publishers','membros'])
add('crossref.members.get','Crossref','research','Consultar membro Crossref por ID.',cr+'/members/{id}',{'id':p()},keywords=['publisher'])
add('crossref.members.works','Crossref','research','Listar trabalhos de um membro Crossref.',cr+'/members/{id}/works',{'id':p(),'rows':q(False,10)},keywords=['publisher','works'])
add('crossref.funders.search','Crossref','research','Pesquisar financiadores.',cr+'/funders',{'query':q(True),'rows':q(False,10)},keywords=['funder','financiador'])
add('crossref.funders.get','Crossref','research','Consultar financiador por DOI/ID.',cr+'/funders/{id}',{'id':p()},keywords=['funder'])
add('crossref.funders.works','Crossref','research','Listar trabalhos associados a financiador.',cr+'/funders/{id}/works',{'id':p(),'rows':q(False,10)},keywords=['funder','works'])
add('crossref.prefixes.get','Crossref','research','Consultar prefixo DOI.',cr+'/prefixes/{prefix}',{'prefix':p()},keywords=['doi','prefixo'])
add('crossref.prefixes.works','Crossref','research','Listar trabalhos por prefixo DOI.',cr+'/prefixes/{prefix}/works',{'prefix':p(),'rows':q(False,10)},keywords=['doi','prefixo'])
add('crossref.types.list','Crossref','research','Listar tipos de obra do Crossref.',cr+'/types',keywords=['tipos','works'])
add('crossref.types.works','Crossref','research','Listar trabalhos por tipo Crossref.',cr+'/types/{type}/works',{'type':p(),'rows':q(False,10)},keywords=['tipo','artigo'])
add('crossref.agency','Crossref','research','Identificar agência responsável por um DOI.',cr+'/works/{doi}/agency',{'doi':p()},keywords=['doi','agency'])

# OpenAlex (24)
oa='https://api.openalex.org'
entities=['works','authors','sources','institutions','topics','publishers','funders','keywords']
for ent in entities:
    add(f'openalex.{ent}.search','OpenAlex','research',f'Pesquisar {ent} no OpenAlex.',oa+f'/{ent}',{'search':q(True),'per-page':q(False,10)},keywords=['openalex',ent],min_interval=0.2)
    add(f'openalex.{ent}.get','OpenAlex','research',f'Consultar {ent} por ID OpenAlex.',oa+f'/{ent}/{{id}}',{'id':p()},keywords=['openalex',ent,'id'],min_interval=0.2)
# 16 above
add('openalex.works.group.year','OpenAlex','research','Contar trabalhos por ano de publicação.',oa+'/works',{'search':q(True)},{'group_by':'publication_year','per-page':50},['tendencia','ano'])
add('openalex.works.filter.year','OpenAlex','research','Pesquisar trabalhos filtrados por ano.',oa+'/works',{'search':q(True),'year':{'in':'query','required':True,'name':'filter'}},{},['ano','filtro'])
# fix filter requires composed expression impossible generic; use direct alias query param called filter
items[-1]['params']={'search':q(True),'filter':q(True),'per-page':q(False,10)}
add('openalex.works.sort.cited','OpenAlex','research','Pesquisar trabalhos ordenados por citações.',oa+'/works',{'search':q(True),'per-page':q(False,10)},{'sort':'cited_by_count:desc'},['citacoes'])
add('openalex.works.open_access','OpenAlex','research','Pesquisar trabalhos e filtrar por acesso aberto.',oa+'/works',{'search':q(True),'filter':q(False,'open_access.is_oa:true'),'per-page':q(False,10)},keywords=['open access','oa'])
add('openalex.works.doi','OpenAlex','research','Consultar trabalho por DOI via filtro OpenAlex.',oa+'/works',{'doi':{'in':'query','required':True,'name':'filter'}},{'per-page':5},['doi'])
# caller passes works.doi filter e.g. doi:https://doi.org/...
add('openalex.authors.group.country','OpenAlex','research','Agrupar autores por país quando disponível.',oa+'/authors',{'search':q(True)},{'group_by':'last_known_institutions.country_code','per-page':50},['autores','pais'])
add('openalex.institutions.country','OpenAlex','research','Pesquisar instituições com filtro opcional de país.',oa+'/institutions',{'search':q(True),'filter':q(False),'per-page':q(False,10)},keywords=['universidade','instituicao'])
add('openalex.sources.issn','OpenAlex','research','Consultar fontes/periódicos por filtro ISSN.',oa+'/sources',{'filter':q(True),'per-page':q(False,10)},keywords=['issn','journals'])
add('openalex.topics.group.domain','OpenAlex','research','Agrupar tópicos por domínio.',oa+'/topics',{'search':q(False)},{'group_by':'domain.id','per-page':50},['topicos','dominio'])

# World Bank (20)
wb='https://api.worldbank.org/v2'
jsonfix={'format':'json','per_page':100}
add('worldbank.countries.list','World Bank','economy','Listar países e economias do Banco Mundial.',wb+'/country',fixed=jsonfix,keywords=['paises','economia'])
add('worldbank.country.get','World Bank','economy','Consultar país/economia por código.',wb+'/country/{code}',{'code':p()},jsonfix,['pais'])
add('worldbank.regions.list','World Bank','economy','Listar regiões do Banco Mundial.',wb+'/region',fixed=jsonfix,keywords=['regioes'])
add('worldbank.region.get','World Bank','economy','Consultar região por código.',wb+'/region/{code}',{'code':p()},jsonfix,['regiao'])
add('worldbank.income_levels','World Bank','economy','Listar níveis de renda.',wb+'/incomeLevel',fixed=jsonfix,keywords=['renda'])
add('worldbank.income_level.get','World Bank','economy','Consultar nível de renda por código.',wb+'/incomeLevel/{code}',{'code':p()},jsonfix,['renda'])
add('worldbank.lending_types','World Bank','economy','Listar tipos de empréstimo/classificação.',wb+'/lendingType',fixed=jsonfix,keywords=['lending'])
add('worldbank.sources','World Bank','economy','Listar fontes de dados.',wb+'/source',fixed=jsonfix,keywords=['fontes'])
add('worldbank.topics','World Bank','economy','Listar tópicos de indicadores.',wb+'/topic',fixed=jsonfix,keywords=['topicos'])
add('worldbank.indicators.list','World Bank','economy','Listar indicadores do Banco Mundial.',wb+'/indicator',{'page':q(False,1)},jsonfix,['indicadores'])
add('worldbank.indicator.get','World Bank','economy','Consultar metadados de indicador.',wb+'/indicator/{indicator}',{'indicator':p()},jsonfix,['indicador'])
for cid,code,desc in [
('population','SP.POP.TOTL','População total'),('gdp','NY.GDP.MKTP.CD','PIB em US$ correntes'),
('gdp.percapita','NY.GDP.PCAP.CD','PIB per capita'),('inflation','FP.CPI.TOTL.ZG','Inflação ao consumidor'),
('unemployment','SL.UEM.TOTL.ZS','Desemprego'),('life_expectancy','SP.DYN.LE00.IN','Expectativa de vida'),
('urban_population','SP.URB.TOTL.IN.ZS','Percentual de população urbana'),('internet_users','IT.NET.USER.ZS','Usuários de internet'),
('co2','EN.ATM.CO2E.PC','Emissões de CO2 per capita')]:
    add(f'worldbank.data.{cid}','World Bank','economy',f'Consultar {desc} por país.',wb+f'/country/{{country}}/indicator/{code}',{'country':p(),'date':q(False)},jsonfix,[desc.lower(),'dados'])

# GitHub public (20)
gh='https://api.github.com'
gheaders={'Accept':'application/vnd.github+json'}
add('github.repo.get','GitHub','software','Consultar repositório público.',gh+'/repos/{owner}/{repo}',{'owner':p(),'repo':p()},keywords=['repositorio','github'],min_interval=1.1,headers=gheaders)
for cid,path,desc in [
('releases','releases','Listar releases'),('release.latest','releases/latest','Obter release mais recente'),('tags','tags','Listar tags'),('branches','branches','Listar branches'),('commits','commits','Listar commits'),('contributors','contributors','Listar contribuidores'),('languages','languages','Listar linguagens'),('issues','issues','Listar issues públicas'),('pulls','pulls','Listar pull requests'),('readme','readme','Obter README'),('forks','forks','Listar forks'),('stargazers','stargazers','Listar estrelas/usuários'),('topics','topics','Obter tópicos')]:
    add(f'github.repo.{cid}','GitHub','software',f'{desc} de um repositório público.',gh+f'/repos/{{owner}}/{{repo}}/{path}',{'owner':p(),'repo':p(),'per_page':q(False,20)},keywords=['github',cid],min_interval=1.1,headers=gheaders)
add('github.repo.contents','GitHub','software','Ler conteúdo de arquivo/diretório público no GitHub.',gh+'/repos/{owner}/{repo}/contents/{path}',{'owner':p(),'repo':p(),'path':p(),'ref':q(False)},keywords=['arquivo','codigo'],min_interval=1.1,headers=gheaders)
add('github.user.get','GitHub','software','Consultar perfil público de usuário GitHub.',gh+'/users/{username}',{'username':p()},keywords=['usuario'],min_interval=1.1,headers=gheaders)
add('github.user.repos','GitHub','software','Listar repositórios públicos de usuário GitHub.',gh+'/users/{username}/repos',{'username':p(),'per_page':q(False,30)},keywords=['repositorios'],min_interval=1.1,headers=gheaders)
add('github.org.get','GitHub','software','Consultar organização GitHub.',gh+'/orgs/{org}',{'org':p()},keywords=['organizacao'],min_interval=1.1,headers=gheaders)
add('github.org.repos','GitHub','software','Listar repositórios de organização GitHub.',gh+'/orgs/{org}/repos',{'org':p(),'per_page':q(False,30)},keywords=['organizacao','repositorios'],min_interval=1.1,headers=gheaders)
add('github.search.repositories','GitHub','software','Pesquisar repositórios públicos no GitHub.',gh+'/search/repositories',{'q':q(True),'per_page':q(False,10)},keywords=['search','repositorio'],min_interval=2.0,headers=gheaders)

# Open Library (10)
ol='https://openlibrary.org'
add('openlibrary.search.books','Open Library','books','Pesquisar livros por texto.',ol+'/search.json',{'q':q(True),'limit':q(False,10)},keywords=['livros','books'],min_interval=1.0)
add('openlibrary.search.title','Open Library','books','Pesquisar livros por título.',ol+'/search.json',{'title':q(True),'limit':q(False,10)},keywords=['titulo'])
add('openlibrary.search.author','Open Library','books','Pesquisar livros por autor.',ol+'/search.json',{'author':q(True),'limit':q(False,10)},keywords=['autor'])
add('openlibrary.search.isbn','Open Library','books','Pesquisar livro por ISBN.',ol+'/search.json',{'isbn':q(True),'limit':q(False,5)},keywords=['isbn'])
add('openlibrary.work.get','Open Library','books','Consultar obra por chave Open Library.',ol+'/works/{key}.json',{'key':p()},keywords=['obra'])
add('openlibrary.author.get','Open Library','books','Consultar autor por chave Open Library.',ol+'/authors/{key}.json',{'key':p()},keywords=['autor'])
add('openlibrary.author.works','Open Library','books','Listar obras de autor Open Library.',ol+'/authors/{key}/works.json',{'key':p(),'limit':q(False,20)},keywords=['autor','obras'])
add('openlibrary.subject','Open Library','books','Listar livros por assunto.',ol+'/subjects/{subject}.json',{'subject':p(),'limit':q(False,20)},keywords=['assunto','tema'])
add('openlibrary.edition.get','Open Library','books','Consultar edição por chave.',ol+'/books/{key}.json',{'key':p()},keywords=['edicao'])
add('openlibrary.recent.changes','Open Library','books','Consultar mudanças recentes no catálogo.',ol+'/recentchanges.json',{'limit':q(False,20)},keywords=['recentes'],min_interval=1.0)

# Frankfurter (8)
fr='https://api.frankfurter.dev/v2'
add('fx.currencies','Frankfurter','finance','Listar moedas suportadas.',fr+'/currencies',keywords=['moedas','cambio'])
add('fx.rates.latest','Frankfurter','finance','Obter cotações mais recentes.',fr+'/rates',{'base':q(False),'quotes':q(False)},keywords=['cambio','cotacao'])
add('fx.rate.pair','Frankfurter','finance','Obter cotação direta entre duas moedas.',fr+'/rate/{base}/{quote}',{'base':p(),'quote':p()},keywords=['par','moeda'])
add('fx.rates.date','Frankfurter','finance','Obter cotações de uma data.',fr+'/rates',{'date':q(True),'base':q(False),'quotes':q(False)},keywords=['historico','data'])
add('fx.rates.period','Frankfurter','finance','Obter série de cotações por período.',fr+'/rates',{'from':q(True),'to':q(True),'base':q(False),'quotes':q(False)},keywords=['serie temporal'])
add('fx.providers','Frankfurter','finance','Listar provedores de cotações oficiais.',fr+'/providers',keywords=['bancos centrais'])
add('fx.rates.usd','Frankfurter','finance','Cotações atuais com USD como base.',fr+'/rates',{'quotes':q(False)},{'base':'USD'},['dolar'])
add('fx.rates.brl','Frankfurter','finance','Cotações atuais com BRL como base.',fr+'/rates',{'quotes':q(False)},{'base':'BRL'},['real','brl'])

# APIs.guru (4)
ag='https://api.apis.guru/v2'
add('apiguru.list','APIs.guru','capability_discovery','Listar catálogo público de especificações OpenAPI.',ag+'/list.json',keywords=['openapi','apis','discovery'],cache=3600)
add('apiguru.metrics','APIs.guru','capability_discovery','Obter métricas do catálogo APIs.guru.',ag+'/metrics.json',keywords=['openapi','metricas'],cache=3600)
add('apiguru.providers','APIs.guru','capability_discovery','Listar provedores no diretório APIs.guru.',ag+'/providers.json',keywords=['provedores','openapi'],cache=3600)
add('apiguru.provider.apis','APIs.guru','capability_discovery','Listar APIs conhecidas de um provedor.',ag+'/{provider}.json',{'provider':p()},keywords=['provider','openapi'],cache=3600)

# Hacker News (9)
hn='https://hacker-news.firebaseio.com/v0'
for cid,path,desc in [
('top','topstories','IDs das principais histórias'),('new','newstories','IDs das histórias novas'),('best','beststories','IDs das melhores histórias'),('ask','askstories','IDs de Ask HN'),('show','showstories','IDs de Show HN'),('jobs','jobstories','IDs de vagas')]:
    add(f'hn.{cid}','Hacker News','news',desc+' do Hacker News.',hn+f'/{path}.json',keywords=['hacker news','tech'],cache=60)
add('hn.item','Hacker News','news','Obter item/história/comentário por ID.',hn+'/item/{id}.json',{'id':p()},keywords=['item','noticia'])
add('hn.user','Hacker News','news','Consultar usuário Hacker News.',hn+'/user/{id}.json',{'id':p()},keywords=['usuario'])
add('hn.updates','Hacker News','news','Consultar itens e perfis atualizados recentemente.',hn+'/updates.json',keywords=['updates'],cache=60)

# USGS (8)
usgs='https://earthquake.usgs.gov'
add('usgs.earthquake.hour','USGS','geoscience','Terremotos da última hora (M1+).',usgs+'/earthquakes/feed/v1.0/summary/1.0_hour.geojson',keywords=['terremoto','earthquake'],cache=60)
add('usgs.earthquake.day','USGS','geoscience','Terremotos do último dia (M1+).',usgs+'/earthquakes/feed/v1.0/summary/1.0_day.geojson',keywords=['terremoto'],cache=120)
add('usgs.earthquake.week','USGS','geoscience','Terremotos da última semana (M2.5+).',usgs+'/earthquakes/feed/v1.0/summary/2.5_week.geojson',keywords=['terremoto'],cache=600)
add('usgs.earthquake.month','USGS','geoscience','Terremotos do último mês (M4.5+).',usgs+'/earthquakes/feed/v1.0/summary/4.5_month.geojson',keywords=['terremoto'],cache=1800)
qurl=usgs+'/fdsnws/event/1/query'
add('usgs.earthquake.search','USGS','geoscience','Pesquisar terremotos por período e magnitude.',qurl,{'starttime':q(True),'endtime':q(True),'minmagnitude':q(False,2.5),'limit':q(False,50)},{'format':'geojson'},['terremoto','periodo'])
add('usgs.earthquake.near','USGS','geoscience','Pesquisar terremotos próximos a coordenadas.',qurl,{'latitude':q(True),'longitude':q(True),'maxradiuskm':q(False,200),'minmagnitude':q(False,2.5),'limit':q(False,50)},{'format':'geojson','orderby':'time'},['proximidade'])
add('usgs.earthquake.significant','USGS','geoscience','Terremotos significativos do último mês.',usgs+'/earthquakes/feed/v1.0/summary/significant_month.geojson',keywords=['significativo'],cache=600)
add('usgs.earthquake.all.day','USGS','geoscience','Todos os terremotos do último dia.',usgs+'/earthquakes/feed/v1.0/summary/all_day.geojson',keywords=['todos','terremotos'],cache=120)

# PyPI + npm (8)
add('pypi.project','PyPI','software','Consultar metadados de pacote Python.', 'https://pypi.org/pypi/{project}/json', {'project':p()}, keywords=['python','pacote','pypi'],cache=600)
add('pypi.release','PyPI','software','Consultar uma versão específica de pacote Python.', 'https://pypi.org/pypi/{project}/{version}/json', {'project':p(),'version':p()}, keywords=['python','versao'],cache=600)
add('pypi.simple.project','PyPI','software','Listar arquivos/versionamento pelo Simple JSON API.', 'https://pypi.org/simple/{project}/', {'project':p()}, keywords=['python','simple'],headers={'Accept':'application/vnd.pypi.simple.v1+json'},cache=600)
add('npm.package','npm','software','Consultar metadados de pacote npm.', 'https://registry.npmjs.org/{package}', {'package':p()}, keywords=['javascript','npm'],cache=600)
add('npm.package.version','npm','software','Consultar versão específica de pacote npm.', 'https://registry.npmjs.org/{package}/{version}', {'package':p(),'version':p()}, keywords=['npm','versao'],cache=600)
add('npm.search','npm','software','Pesquisar pacotes npm.', 'https://registry.npmjs.org/-/v1/search', {'text':q(True),'size':q(False,10),'from':q(False,0)}, keywords=['npm','search'],cache=300)
add('npm.search.quality','npm','software','Pesquisar npm priorizando qualidade.', 'https://registry.npmjs.org/-/v1/search', {'text':q(True),'size':q(False,10)}, {'quality':1.0,'popularity':0.0,'maintenance':0.0}, ['npm','qualidade'])
add('npm.search.popular','npm','software','Pesquisar npm priorizando popularidade.', 'https://registry.npmjs.org/-/v1/search', {'text':q(True),'size':q(False,10)}, {'quality':0.0,'popularity':1.0,'maintenance':0.0}, ['npm','popularidade'])

# arXiv (6)
ar='https://export.arxiv.org/api/query'
add('arxiv.search.all','arXiv','research','Pesquisar artigos no arXiv por qualquer campo.',ar,{'query':{'in':'query','required':True,'name':'search_query'},'max_results':q(False,10)},{'sortBy':'relevance','sortOrder':'descending'},['arxiv','preprint'],response='text',min_interval=3.0)
add('arxiv.search.title','arXiv','research','Pesquisar arXiv por título (use ti:termo).',ar,{'query':{'in':'query','required':True,'name':'search_query'},'max_results':q(False,10)},{'sortBy':'relevance'},['titulo'],response='text',min_interval=3.0)
add('arxiv.search.author','arXiv','research','Pesquisar arXiv por autor (use au:nome).',ar,{'query':{'in':'query','required':True,'name':'search_query'},'max_results':q(False,10)},{'sortBy':'submittedDate','sortOrder':'descending'},['autor'],response='text',min_interval=3.0)
add('arxiv.search.category','arXiv','research','Pesquisar arXiv por categoria (use cat:codigo).',ar,{'query':{'in':'query','required':True,'name':'search_query'},'max_results':q(False,10)},{'sortBy':'submittedDate','sortOrder':'descending'},['categoria'],response='text',min_interval=3.0)
add('arxiv.latest','arXiv','research','Listar artigos recentes para uma consulta.',ar,{'query':{'in':'query','required':True,'name':'search_query'},'max_results':q(False,10)},{'sortBy':'submittedDate','sortOrder':'descending'},['recentes'],response='text',min_interval=3.0)
add('arxiv.id.list','arXiv','research','Consultar artigos arXiv por lista de IDs.',ar,{'id_list':q(True),'max_results':q(False,10)},keywords=['id','arxiv'],response='text',min_interval=3.0)

# Extra public developer/data capabilities to exceed 200 with meaningful distinct use cases
# GitHub raw endpoints/metadata
add('github.repo.events','GitHub','software','Listar eventos recentes de repositório público.',gh+'/repos/{owner}/{repo}/events',{'owner':p(),'repo':p(),'per_page':q(False,20)},keywords=['eventos'],min_interval=1.1,headers=gheaders)
add('github.repo.community','GitHub','software','Consultar perfil de comunidade/saúde do repositório.',gh+'/repos/{owner}/{repo}/community/profile',{'owner':p(),'repo':p()},keywords=['community','license'],min_interval=1.1,headers=gheaders)
add('github.repo.license','GitHub','software','Consultar licença de repositório público.',gh+'/repos/{owner}/{repo}/license',{'owner':p(),'repo':p()},keywords=['license','licenca'],min_interval=1.1,headers=gheaders)
add('github.repo.compare','GitHub','software','Comparar duas refs/commits de repositório.',gh+'/repos/{owner}/{repo}/compare/{basehead}',{'owner':p(),'repo':p(),'basehead':p()},keywords=['diff','compare'],min_interval=1.1,headers=gheaders)

# Google public DNS-over-HTTPS (4)
doh='https://dns.google/resolve'
for cid,typ,desc in [('a','A','Resolver IPv4'),('aaaa','AAAA','Resolver IPv6'),('mx','MX','Consultar servidores de email'),('txt','TXT','Consultar registros TXT')]:
    add(f'dns.{cid}','Google DNS','network',f'{desc} via DNS-over-HTTPS.',doh,{'name':q(True)},{'type':typ},['dns',typ.lower()],cache=300)

# ipify (1)
add('network.public_ip','ipify','network','Descobrir IP público atual.', 'https://api.ipify.org', fixed={'format':'json'}, keywords=['ip','internet'],cache=60)

# JSONPlaceholder (read-only test capabilities for development, 5)
jp='https://jsonplaceholder.typicode.com'
add('dev.sample.posts','JSONPlaceholder','developer','Obter posts de exemplo para testar pipelines.',jp+'/posts',keywords=['teste','json'])
add('dev.sample.post','JSONPlaceholder','developer','Obter post de exemplo por ID.',jp+'/posts/{id}',{'id':p()},keywords=['teste'])
add('dev.sample.users','JSONPlaceholder','developer','Obter usuários de exemplo.',jp+'/users',keywords=['teste'])
add('dev.sample.todos','JSONPlaceholder','developer','Obter tarefas de exemplo.',jp+'/todos',keywords=['teste'])
add('dev.sample.comments','JSONPlaceholder','developer','Obter comentários de exemplo.',jp+'/comments',keywords=['teste'])

# Deduplicate check
seen=set(); dup=[]
for x in items:
    if x['id'] in seen: dup.append(x['id'])
    seen.add(x['id'])
if dup: raise SystemExit(f'Duplicate IDs: {dup}')

OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
print('count', len(items))
from collections import Counter
print('providers', Counter(x['provider'] for x in items))
print('groups', Counter(x['group'] for x in items))
