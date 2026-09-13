# ETAPAS.md

Ordem de construção. Uma etapa por vez, na ordem.

Cada etapa tem **objetivo**, **o que construir**, **pergunta de verificação** e
**critério de saída**. A pergunta de verificação não é formalidade: se eu errar,
paramos e revisamos antes de seguir.

Legenda: `[EU]` eu digito · `[VC]` você escreve · `[JUNTOS]` você me dita a
estrutura, eu escrevo, você critica.

---

## Fase 1 — Fundação e fontes

**Foco da fase: a sujeira.** Esta fase existe para que o dado seja difícil de
tratar. Se ao final o `raw/` estiver fácil de ler, a fase falhou.

### 1.1 — Ambiente e higiene

`[VC]` `.gitignore`, `pyproject.toml` com ruff e pytest configurados, venv.

Antes de escrever, me explique por que `.gitignore` vem **antes** do primeiro
commit e não depois.

> **Verificação:** o `raw/` vai ter ~29 MB de dado gerado. Por que ele não entra
> no Git, se é o insumo do projeto inteiro? O que entra no lugar?

**Saída:** `ruff check .` roda sem erro numa pasta praticamente vazia.

### 1.2 — Estrutura de pastas

`[JUNTOS]` Antes de criar qualquer diretório, me faça desenhar a estrutura e
explicar o que vive em cada pasta. Só depois corrija o que estiver errado.

Camadas previstas: `dados_sinteticos/`, `raw/`, `transform/`, `motor/`,
`avaliacao/`, `app/`, `tests/`, `docs/`.

> **Verificação:** por que `avaliacao/` é uma pasta separada de `tests/`, se
> ambas testam coisas?

**Saída:** estrutura criada, cada pasta com um `README.md` de uma linha dizendo
o que vive ali.

### 1.3 — Contrato de dados, antes de qualquer código

`[EU]` `docs/contrato-de-dados.md`. Você me entrevista campo a campo; eu escrevo.

Fontes: `meta_ads_insights`, `crm_negocios`, `crm_contatos`, `crm_atividades`,
`financeiro_margens`. Para cada uma: campos, tipo **na origem** (não o tipo que
eu queria), obrigatoriedade, chave, e limites de aceitação.

Atenção ao campo `campaign_source`: ele **pode** ser nulo. Isso não é violação de
contrato — é o fenômeno que a regra R8 mede. Preciso saber distinguir os dois.

> **Verificação:** qual a diferença prática entre "campo que pode ser nulo" e
> "campo cuja nulidade viola o contrato"? Dê um exemplo de cada nas nossas fontes.

**Saída:** contrato escrito antes de existir uma linha de código de ingestão.

### 1.4 — ADRs 0001 a 0004

`[EU]` Quatro registros de decisão. Você me entrevista; eu escrevo cada um no
formato Contexto / Decisão / Consequências.

O conteúdo está em `CLAUDE.md` seção 4 — mas **não copie de lá**. Me faça
reconstruir o raciocínio, porque é isso que vou ter que explicar em vídeo.

> **Verificação:** a ADR 0002 trocou recall por precisão. Quanto de cada, e por
> que essa troca é certa para este destinatário e errada para outro?

**Saída:** quatro arquivos em `docs/adr/`, escritos por mim.

### 1.5 — Gerador: parâmetros e cenários

`[EU]` `dados_sinteticos/parametros.py` e `cenarios.py`.

Parâmetros base do funil (leads/dia, CPL, conversão, ticket, margem, lag de
fechamento, SLA, toques, completude de origem) e as perturbações de cada um dos
10 cenários.

Regra: todo parâmetro fica **explícito e nomeado**. Nada de número mágico dentro
da lógica.

> **Verificação:** o cenário "caro porém saudável" sobe o CPL e sobe o ticket.
> Por que ele existe no conjunto de testes, se não é um problema?

**Saída:** parâmetros importáveis, com docstring dizendo de onde veio cada faixa.

### 1.6 — Gerador: simulação

`[JUNTOS]` `dados_sinteticos/gerador.py`. Gera leads, custo, atendimento e
negócios para baseline (60 dias) e período analisado (30 dias).

Ponto crítico: o lead fecha com atraso. A geração precisa produzir
`dia_fechamento = dia_lead + lag`, e o lag vem de distribuição, não de constante.

> **Verificação:** por que simulamos 30 dias **além** do último lead do período?
> O que acontece com o CAC se não fizermos isso?

**Saída:** `gerar("normal", 42)` reproduz o mesmo resultado duas vezes seguidas.

### 1.7 — Exportador: o formato cru

`[JUNTOS]` `dados_sinteticos/exportar.py`. Grava em `raw/` no formato das APIs.

Sujeira obrigatória, uma de cada vez, e eu escrevo cada injeção:
número como string · timestamp com fuso · UTM em cinco caixas · 3% de contatos
duplicados · `campaign_source` nulo · paginação com cursor · CSV com decimal em
vírgula.

Duas sujeiras extras que o protótipo ainda não tinha: campanha que aparece no CRM
e não nos insights, e um dia com custo duplicado por reentrega da API.

O gabarito vai para `avaliacao/gabarito_contas.json`. Nunca para `raw/`.

> **Verificação:** se eu esquecer a deduplicação de contatos lá na fase 2, o que
> acontece com o CPL e com a taxa de conversão? Os dois vão para o mesmo lado?

**Saída:** `make dados` gera 12 contas do zero em máquina limpa.

### 1.8 — Fechamento da fase

`[VC]` Teste de fumaça, `Makefile`, workflow de CI, `.vscode/extensions.json`.
`[EU]` Descrição do PR #1.

> **Verificação:** o CI roda `dbt build` numa fase em que ainda não existe nenhum
> modelo dbt. Isso é erro ou é proposital?

**Saída:** PR #1 aberto, CI verde, e eu consigo explicar cada arquivo do repo.

---

## Fase 2 — Camada de dados

**Foco da fase: o build tem que quebrar.** O valor não são os modelos — é a
capacidade de recusar dado ruim. Pipeline que nunca falha é pipeline que não está
olhando.

### 2.1 — dbt sobre DuckDB, mínimo viável
`[VC]` `dbt_project.yml`, `profiles.yml`, leitura de `raw/` como source.
Escopo travado: sem macro, sem snapshot, sem incremental, sem `dbt docs`.

### 2.2 — Staging
`[JUNTOS]` Quatro modelos `stg_*`. Só tipagem e renomeação. **Zero regra de
negócio** — me impeça se eu tentar colocar.
> **Verificação:** normalizar UTM é tipagem ou regra de negócio? Onde fica?

### 2.3 — Intermediate
`[EU]` Deduplicação por hash, coorte de lead com flag de maturidade, custo por
campanha e dia, negócios atribuídos. **É a camada mais difícil do projeto.**
> **Verificação:** dois contatos com o mesmo e-mail e negócios diferentes. Um
> lead ou dois? E se os negócios tiverem valores diferentes?

### 2.4 — Marts
`[JUNTOS]` `fct_coorte_semanal`, `fct_funil_diario`, `mart_metricas_periodo`,
`dim_campanha`, `dim_estagio` com SLA.
> **Verificação:** qual o grão de cada mart? Diga em uma frase por tabela.

### 2.5 — Os trinta testes
`[EU]` Chaves, relacionamentos, valores aceitos, o teste singular de fechamento
anterior ao lead, e o teste de maturidade de coorte.

### 2.6 — O teste do papel
`[EU]` Caso mínimo: 10 leads, 2 vendas, 1 campanha. Calculo CAC, CPL, conversão e
margem **no papel**, gravo o esperado num seed, e o teste compara contra o SQL.
> **Verificação:** se o SQL e o papel divergirem, qual dos dois está errado? Como
> você decide?

**Saída da fase:** injeto uma duplicata no seed, `dbt build` falha, CI reprova o
PR sozinho.

---

## Fase 3 — Motor e avaliação

**Foco: precisão medida, não regra escrita.** Toda alteração no motor termina com
a matriz de confusão rodando. Sem exceção.

### 3.1 — Camada de métricas em Python, lendo das marts
### 3.2 — R0, R99 e a guarda de qualidade — as que sabem calar
### 3.3 — Regras econômicas: R1, R2, R4, R5
Decomposição logarítmica exata do CAC (os efeitos precisam **somar** a variação
total), payback no lugar de margem, conversão por etapa, campo de impacto em reais.
### 3.4 — Regras operacionais: R3, R6, R7
SLA por faixa de score e por estágio; fila nominal; distinguir "sem follow-up" de
"sem resposta".
### 3.5 — R10 e a avaliação por campanha
### 3.6 — Conjunto cego ampliado
Três armadilhas novas (campanha sem histórico; janela com feriado; cliente que
mudou de ticket por reposicionamento), cenários triplos, 300 execuções por cenário.
### 3.7 — O detector trivial, como concorrente
Três linhas: "alerte se o CAC subiu mais de 25%". Rodar em todo commit. Se o
motor não ganhar com folga, a complexidade não se paga.

**Saída da fase:** alarme falso abaixo de 5% com sete armadilhas; nenhuma regra
abaixo de 0,95 de precisão no cego.

**Regra da fase:** nenhuma tela. Nem uma.

---

## Fase 4 — Narrativa, interface e case

**Foco: legibilidade.**

### 4.1 — Narrativa determinística
Situação, evidência, impacto em reais, ação, dono, prazo. Template, não LLM —
o texto pode ser gerado, o número nunca.
### 4.2 — Streamlit
Seletor de conta, CAC com faixa de controle, achados ordenados por dinheiro em
risco, painel de cobertura de atribuição.
### 4.3 — Red team
As seis falhas abertas: comparações múltiplas, receita não líquida de estorno,
restatement retroativo de API, regressão à média, Goodhart, último clique.
Fechar o que der, **declarar o que não der**.
### 4.4 — README como investigação
O problema, as quatro falhas encontradas, como cada uma foi corrigida, a matriz
nos dois conjuntos. Seção "Limitações" logo abaixo dos resultados.
### 4.5 — Artigo e vídeo
Um número só no artigo: 1,4% contra 41,4%. Vídeo de 90 segundos, tomada única.

**Saída da fase:** duas pessoas que não conhecem o projeto olham a tela e dizem o
que fariam, sem eu explicar nada.

---

## Se o prazo apertar

Corte interface e narrativa. **Nunca corte avaliação** — é ela que transforma o
projeto de demonstração em evidência.
