# Estratégia de dados públicos — Jarvis Cognitive Foundation 1.0a

O objetivo não é transformar o Jarvis em um menu de APIs. Dados públicos são uma extensão do raciocínio: o usuário pergunta normalmente, o Jarvis identifica o domínio, escolhe uma fonte adequada, consulta/descobre a interface, cruza evidências e responde.

## Quatro formas de aquisição

### 1. APIs estruturadas
Preferência quando existem endpoints oficiais e adequados ao pedido.

Exemplos catalogados: IBGE, Câmara, Senado, Dados.gov.br, CNJ/DataJud, Banco Central, Compras.gov.br/PNCP, Receita Federal, MTE, INEP, Dados Abertos SP, ALESP, ObservaSampa, GeoSampa, Crossref, Wikidata, World Bank e outros.

Vantagens: campos estruturados, menor contexto, fácil cache e melhor verificabilidade.

### 2. Descoberta automática de interfaces
Quando um site ainda não tem adaptador, `discover_public_interfaces` verifica, de forma controlada:

- OpenAPI/Swagger;
- RSS/Atom;
- sitemap.xml;
- robots.txt.

A descoberta é salva como proposta. Ela não instala silenciosamente uma integração de escrita.

### 3. Pesquisa web + leitura de páginas
Para temas não cobertos por API. O Research Engine continua responsável por:

- encontrar fontes;
- resolver redirecionamentos;
- preferir fontes oficiais/primárias;
- extrair evidências;
- reduzir o material antes de enviar ao modelo local.

### 4. Grandes conjuntos para processamento local
Arquivos massivos não devem ser baixados em toda pergunta.

Exemplos: CNPJ da Receita, RAIS/CAGED, microdados do INEP, bases CSV/XLSX de tribunais e portais públicos.

Fluxo recomendado:

`catálogo → usuário/tarefa decide baixar → download → Document/Data Engine → SQLite/FTS → consulta local`

Isso transforma um conjunto grande em conhecimento reutilizável sem repetir tráfego ou processamento.

---

## Fonte certa para o domínio certo

O broker usa autoridade + aderência ao tema. Uma fonte oficial brasileira recebe prioridade quando o pedido é sobre dados governamentais brasileiros. Plataformas comunitárias continuam úteis como conveniência, mas não substituem uma fonte oficial disponível.

Categorias importantes:

- território/população/economia: IBGE;
- legislação e processo legislativo: Câmara/Senado;
- Justiça: CNJ DataJud + bases abertas dos tribunais;
- trabalho e emprego: MTE/RAIS/CAGED;
- empresas: Receita Federal/CNPJ;
- sistema financeiro: Banco Central;
- compras/contratações: Compras.gov.br, PNCP e Portal da Transparência;
- educação: INEP;
- produção científica: Crossref/OpenAlex;
- entidades/relações: Wikidata;
- software/documentação: GitHub;
- geodados: OpenStreetMap/Nominatim/Overpass;
- contexto geral: Wikimedia, sempre subordinada a fontes primárias quando necessário.

---

## Camada regional de São Paulo

Para uso do SindPetshop-SP, o broker também prioriza fontes do território quando a pergunta é estadual/municipal:

- Dados Abertos SP — catálogo CKAN/API do Governo do Estado;
- ALESP — processo legislativo, legislação e bases estruturadas;
- ObservaSampa — indicadores e séries históricas municipais;
- GeoSampa — camadas geográficas e dados territoriais.

Essas fontes continuam invisíveis como “menus”: o agente deve selecioná-las quando o contexto pedir São Paulo.

## Expansão contínua

A meta é permitir este ciclo:

`necessidade nova → pesquisar fontes → descobrir API/feed/OpenAPI → criar proposta → testar → aprovação → Capability/Adapter → cache → reutilização`

Assim o Jarvis pode ampliar seu alcance sem carregar milhares de schemas no Qwen e sem exigir que cada nova fonte vire uma aba na interface.

## Regras de custo

O núcleo continua sem API paga obrigatória.

Uma fonte pode ser:

- pública e sem autenticação;
- pública com token gratuito;
- download aberto;
- open source/self-hostable;
- opcional, com termos próprios.

Serviços pagos nunca devem ser requisito do funcionamento central. Uma organização pode conectar futuramente um serviço já contratado, mas isso permanece opcional.

## Rate limits e etiqueta de uso

O Jarvis deve aplicar cache e limitação local. Em particular, serviços públicos compartilhados como Nominatim, Overpass e GitHub não autenticado não devem ser usados como mecanismos de varredura massiva.

Para grandes volumes, preferir snapshots/downloads oficiais e análise local.

## Privacidade

Dados públicos externos e dados institucionais internos são camadas diferentes.

O Jarvis não deve enviar documentos internos para serviços públicos para “enriquecimento”. Consultas externas devem conter apenas os parâmetros necessários. Segredos permanecem no keyring e conteúdo institucional permanece local salvo ação explicitamente autorizada.
