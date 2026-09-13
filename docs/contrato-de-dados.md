# Contrato de dados

> **Nota de autoria — divergência registrada (`CLAUDE.md`, regra 7).**
> A etapa 1.3 previa que este documento fosse escrito por Luiz, com Claude
> apenas entrevistando. A pedido explícito dele ("eu exijo"), Claude redigiu as
> cinco fontes e decidiu os três pontos que estavam em aberto na entrevista da
> `meta_ads_insights` (chave composta, buraco de dia, duplicata). O que veio da
> entrevista original está marcado com **[LG]**; o resto é decisão de Claude.
> Isto fica registrado para que, na revisão, se saiba qual parte não foi julgada
> pelo autor do projeto.

---

## 1. Para que serve este documento

Sem contrato, "dado ruim" é o que alguém acha que é ruim no dia em que olhou.
Com contrato, é **violação verificável** — e um teste reprova o build sozinho,
sem ninguém na sala.

Este arquivo é escrito **antes** de existir código de ingestão. Contrato escrito
depois do pipeline descreve o que o código já faz, em vez de julgá-lo — e nunca
reprova nada.

**O que este documento não é:** não é dicionário de dados do warehouse (isso são
as marts), nem documentação de API. Ele descreve o dado **como a origem entrega**,
inclusive quando a origem entrega errado.

## 2. Como ele é aplicado

Todo limite deste documento cai em um de três níveis. O nível determina a ação.

| Nível | O que caracteriza | Ação | Onde é verificado |
|---|---|---|---|
| **Estrutural** | o pipeline não sabe o que está lendo: campo ausente, chave nula, grão diferente do declarado | **build reprova** | teste dbt em `staging` (`not_null`, `unique`, `relationships`) |
| **Contraditório** | a fonte afirmou duas coisas incompatíveis: mesma chave com valores diferentes, clique sem impressão, fechamento anterior à criação | **build reprova** | teste singular dbt em `staging`/`intermediate` |
| **Degradante** | o dado é utilizável, mas incompleto: buraco de dia, origem ausente, negócio ganho ainda sem linha no financeiro | **passa, e é contado** | métrica de completude em `marts`, lida pela regra **R0** |

**A regra que vale para os três níveis: nada é descartado em silêncio.**
Descartar linha ruim sem avisar é produzir resposta a partir de um conjunto que
foi encolhido escondido. Este produto se define por *recusar-se a responder
quando os dados não permitem afirmar* — descarte silencioso é o oposto exato
disso. Ou falha, ou mantém e conta.

## 3. Como ler as tabelas de campo

- **Tipo na origem** é o tipo que a fonte **entrega**, não o que gostaríamos.
  `string` aqui significa que chega como texto, mesmo sendo número.
- **Obrigatório** = o campo tem que existir na linha. Diferente de não-nulo.
- **Nulo permitido** = pode vir vazio **sem violar o contrato**. Esta coluna é a
  mais importante do documento: ver seção 7.
- **Formato** é parte do contrato. Declarar só o tipo não protege contra nada —
  `"1234.56"` e `"1.234,56"` são ambos `string`, e confundir os dois produz
  custo mil vezes menor, sem exceção e sem log.

## 4. Convenções válidas para todas as fontes

| Assunto | Regra |
|---|---|
| Fuso horário | Timestamps do CRM chegam em ISO 8601 com deslocamento `-03:00`. A conversão para UTC é `staging`. Timestamp sem fuso é violação **estrutural** |
| Caixa de texto | UTM chega em caixas inconsistentes (`FaceBook_Ads`, `facebook_ads`, `FACEBOOK ADS`). **Não é violação** — normalizar é tipagem, e acontece em `staging` |
| Números como texto | Fato da origem, não violação. Conversão em `staging` |
| Chaves | Sempre `string`, mesmo quando parecem inteiros. Id numérico convertido para inteiro perde zero à esquerda e estoura precisão |
| Encoding | UTF-8. Outro encoding é violação **estrutural** |

---

## 5.1 Fonte: `meta_ads_insights`

**Origem:** Graph API da Meta, endpoint `/insights`
**Formato:** JSON, **paginado com cursor** (`paging.cursors.after`). Todas as
páginas de uma conta compõem uma única fonte lógica
**Grão:** uma campanha, num dia **[LG]**
**Chave:** `account_id` + `campaign_id` + `date_start`

> **Decisão sobre a chave:** `campaign_id` já é único no ecossistema da Meta, o
> que torna `account_id` tecnicamente redundante. Foi incluído mesmo assim: as 12
> contas são unidas numa tabela só, e a chave composta deixa isso explícito além
> de pegar um bug de gerador que atribua a mesma campanha a duas contas. Custo:
> uma coluna a mais em todo teste de unicidade.

| Campo | Tipo na origem | Obrigatório | Nulo permitido | Formato |
|---|---|---|---|---|
| `account_id` | string | sim | não | `act_` + dígitos |
| `campaign_id` | string | sim | não | só dígitos |
| `campaign_name` | string | sim | não | texto livre |
| `date_start` | string | sim | não | `YYYY-MM-DD` |
| `date_stop` | string | sim | não | `YYYY-MM-DD` |
| `spend` | **string** | sim | não | `^\d+(\.\d{1,2})?$` — ponto decimal, sem separador de milhar |
| `impressions` | **string** | sim | não | só dígitos |
| `clicks` | **string** | sim | não | só dígitos |

**Limites de aceitação**

| Limite | Nível | Por que existe |
|---|---|---|
| `date_start = date_stop` | estrutural | o recorte é diário. Se a API mudar para semanal, o pipeline soma semanas achando que são dias — sem erro nenhum aparecer |
| `campaign_id` não nulo | estrutural | sem chave não há linha |
| `spend` casa o formato declarado | estrutural | fixa o formato, não só o tipo |
| `spend >= 0`, `impressions >= 0`, `clicks >= 0` | contraditório | negativo é impossível |
| `clicks <= impressions` | contraditório | clique sem impressão é contradição |
| chave única, após deduplicar linhas idênticas | ver abaixo | |
| sem buraco de dia dentro da janela ativa da campanha | degradante | ver abaixo |

**Duplicatas — as duas são coisas diferentes**

| Caso | O que é | Ação | Nível |
|---|---|---|---|
| Duplicata **exata** (todos os campos iguais) | reentrega da API, fenômeno conhecido e recorrente. Descartar uma cópia é provadamente sem perda | deduplicar em `staging`, **contando** quantas foram | degradante |
| Duplicata **de chave** (mesma campanha e dia, `spend` diferente) | contradição. Escolher entre `800` e `1200` é chutar, e chutar aqui dobra ou corta o CAC pela metade | build reprova | contraditório |

> **Decisão:** "reprova sempre que houver duplicata" foi descartado. A agência
> roda isto semanalmente; um build que morre toda vez que a Meta reentrega deixa
> a ferramenta quebrada metade das semanas.

**Buraco de dia**

O contrato **não** exige linha para toda campanha em todos os 90 dias — uma
campanha encerrada no dia 10 não precisa de 80 linhas de zero. Exige linha para
todo dia **entre o primeiro e o último em que a campanha aparece**.

> **Decisão:** classificado como **degradante**, não estrutural. Buraco somado
> como zero **abaixa** o custo → CAC menor → a R1 não dispara → o problema passa
> em silêncio. Falso negativo é o pior erro deste produto, porque um alarme que
> não toca não deixa rastro. Mas reprovar o build por um dia faltante travaria a
> conta inteira; a R0 já existe para bloquear a análise quando a completude cai.

**O que NÃO é violação**

- Número entregue como string. É o comportamento real da API.
- `campaign_name` diferente para o mesmo `campaign_id` ao longo do período.
  Renomear campanha é rotina de gestor de tráfego. **`campaign_id` é a chave;
  `campaign_name` é atributo descritivo e nunca serve para agrupar.** Agrupar por
  nome parte uma campanha renomeada em duas — uma "sem histórico" e outra que
  "parou de gastar", ambas falso positivo, e quebra a ADR 0003. O nome mais
  recente vira coluna de `dim_campanha` (etapa 2.4), para apresentação ao humano.
- Resposta paginada. Montar as páginas é trabalho de ingestão.

---

## 5.2 Fonte: `crm_negocios`

**Origem:** export manual do CRM (formato RD Station)
**Formato:** CSV, separador vírgula, campos com aspas, **decimal com ponto**
**Grão:** um negócio (deal)
**Chave:** `deal_id`

| Campo | Tipo na origem | Obrigatório | Nulo permitido | Formato |
|---|---|---|---|---|
| `deal_id` | string | sim | não | dígitos |
| `contact_id` | string | sim | não | dígitos — referencia `crm_contatos` |
| `nome_negocio` | string | sim | não | texto livre |
| `estagio` | string | sim | não | ver valores aceitos |
| `status` | string | sim | não | `aberto` / `ganho` / `perdido` |
| `valor` | **string** | sim | não | `^\d+(\.\d{1,2})?$` |
| `data_criacao` | string | sim | não | ISO 8601 com `-03:00` |
| `data_fechamento` | string | sim | **sim** | ISO 8601 com `-03:00` |
| `campaign_source` | string | sim | **sim** | texto livre, caixa inconsistente |
| `utm_campaign` | string | sim | **sim** | texto livre, caixa inconsistente |
| `motivo_perda` | string | sim | **sim** | texto livre |
| `proprietario` | string | sim | não | nome do vendedor |

**Valores aceitos em `estagio`**
`novo` · `contato_feito` · `qualificado` · `proposta` · `negociacao` · `ganho` ·
`perdido`

O SLA de cada estágio **não** vive aqui — vive em `dim_estagio` (etapa 2.4).
Contrato descreve o dado; SLA é regra de negócio.

**Limites de aceitação**

| Limite | Nível |
|---|---|
| `deal_id` único | estrutural |
| `contact_id` existe em `crm_contatos` | estrutural |
| `estagio` na lista de valores aceitos | estrutural |
| `data_criacao` com fuso explícito | estrutural |
| `data_fechamento >= data_criacao` | **contraditório** — negócio fechado antes de existir. É o teste singular exigido pela etapa 2.5 |
| `status = ganho` ⇒ `valor > 0` **e** `data_fechamento` não nulo | contraditório |
| `status = aberto` ⇒ `data_fechamento` nulo | contraditório |
| `status = perdido` ⇒ `motivo_perda` não nulo | degradante |
| `valor >= 0` | contraditório |

**O que NÃO é violação — e esta é a linha mais importante do documento**

- **`campaign_source` nulo.** Não é erro de export: é o fenômeno que a regra
  **R8** (receita sem origem rastreável) existe para medir. Se o contrato o
  tratasse como violação, o build reprovaria exatamente nos casos em que o
  produto tem algo a dizer, e a R8 nunca rodaria.
- `data_fechamento` nulo quando `status = aberto`. É o estado normal de um
  negócio em andamento.
- `motivo_perda` nulo quando o negócio não foi perdido.
- UTM em caixa inconsistente.

---

## 5.3 Fonte: `crm_contatos`

**Origem:** export manual do CRM (formato RD Station)
**Formato:** CSV, separador vírgula, campos com aspas
**Grão:** um contato
**Chave:** `contact_id`

| Campo | Tipo na origem | Obrigatório | Nulo permitido | Formato |
|---|---|---|---|---|
| `contact_id` | string | sim | não | dígitos |
| `email` | string | sim | não | `local@dominio` |
| `nome` | string | sim | não | texto livre |
| `telefone` | string | sim | **sim** | texto livre, sem máscara garantida |
| `data_criacao` | string | sim | não | ISO 8601 com `-03:00` |
| `score_fit` | **string** | sim | não | inteiro de `0` a `100` |
| `utm_source` | string | sim | **sim** | texto livre, caixa inconsistente |
| `utm_medium` | string | sim | **sim** | texto livre, caixa inconsistente |
| `utm_campaign` | string | sim | **sim** | texto livre, caixa inconsistente |

**Limites de aceitação**

| Limite | Nível |
|---|---|
| `contact_id` único | estrutural |
| `email` não nulo e com `@` | estrutural |
| `score_fit` entre 0 e 100 | contraditório |
| `data_criacao` com fuso explícito | estrutural |
| taxa de UTM válida na conta | degradante — alimenta a **R0** (bloqueia se < 80%) |

**O que NÃO é violação**

- **E-mail repetido em `contact_id` diferentes.** Cerca de 3% dos contatos são
  duplicados assim, e isso é o comportamento real de um CRM onde a mesma pessoa
  preenche dois formulários. **Se isto fosse violação, o build reprovaria em toda
  conta** e a deduplicação por hash da etapa 2.3 não teria o que deduplicar.
  A unicidade que o contrato exige é de `contact_id`, não de `email`.
- Telefone nulo ou sem máscara.
- UTM nula. Alimenta a R0; não reprova nada sozinha.

> **Atenção ao efeito da deduplicação, porque ele não é intuitivo:** duplicata de
> contato **infla o número de leads**. Leads inflados → CPL aparente **menor** e
> taxa de conversão aparente **menor**. Os dois se movem para lados opostos do
> diagnóstico: o CPL parece bom e a conversão parece ruim. Deduplicar não é
> higiene — é o que impede o motor de apontar "problema de conversão" onde havia
> só contagem dobrada.

---

## 5.4 Fonte: `crm_atividades`

**Origem:** export manual do CRM (formato RD Station)
**Formato:** CSV, separador vírgula, campos com aspas
**Grão:** um toque registrado — uma interação entre vendedor e contato
**Chave:** `atividade_id`

| Campo | Tipo na origem | Obrigatório | Nulo permitido | Formato |
|---|---|---|---|---|
| `atividade_id` | string | sim | não | dígitos |
| `deal_id` | string | sim | **sim** | dígitos — nulo quando a atividade é do contato, antes de virar negócio |
| `contact_id` | string | sim | não | dígitos |
| `tipo` | string | sim | não | `ligacao` / `email` / `whatsapp` / `reuniao` / `nota` |
| `direcao` | string | sim | não | `saida` / `entrada` |
| `resultado` | string | sim | **sim** | `atendeu` / `nao_atendeu` / `sem_resposta` / `respondeu` |
| `data_hora` | string | sim | não | ISO 8601 com `-03:00` |

**Por que `direcao` e `resultado` são obrigatórios**

A etapa 3.4 exige distinguir **"sem follow-up"** de **"sem resposta"**. São
diagnósticos opostos e acionam pessoas diferentes: no primeiro, o vendedor não
ligou; no segundo, ligou e o lead sumiu. Sem `direcao`, não dá para saber quem
iniciou; sem `resultado`, não dá para saber o que aconteceu. Um contrato que
omitisse esses dois campos tornaria a R7 impossível de calcular corretamente — e
ela apontaria o vendedor errado.

O que conta como "toque" para a R7 (`direcao = saida` e `tipo` entre ligação,
e-mail e WhatsApp; `nota` não é toque) é **regra de negócio e vive em `motor/`**.
O contrato só garante que os campos existem para a regra poder decidir.

**Limites de aceitação**

| Limite | Nível |
|---|---|
| `atividade_id` único | estrutural |
| `contact_id` existe em `crm_contatos` | estrutural |
| `deal_id`, quando não nulo, existe em `crm_negocios` | estrutural |
| `tipo` e `direcao` na lista de valores aceitos | estrutural |
| `data_hora >= data_criacao` do contato referenciado | **contraditório** — atividade anterior à existência do contato |
| `data_hora` com fuso explícito | estrutural |

**O que NÃO é violação**

- **Negócio com zero atividades.** É precisamente o sinal que a **R7**
  (follow-up insuficiente) e a **R3** (lead não contatado dentro do SLA) medem.
  Exigir ao menos uma atividade por negócio apagaria o problema mais caro que
  este produto detecta.
- `deal_id` nulo: atividade feita antes de o contato virar negócio.
- `resultado` nulo em `tipo = nota`.

---

## 5.5 Fonte: `financeiro_margens`

**Origem:** planilha do financeiro, exportada
**Formato:** CSV, **separador ponto e vírgula**, **decimal com vírgula**,
milhar com ponto. Este é o único arquivo do projeto com essa convenção
**Grão:** um negócio ganho, num mês de competência
**Chave:** `deal_id` + `mes_competencia`

| Campo | Tipo na origem | Obrigatório | Nulo permitido | Formato |
|---|---|---|---|---|
| `deal_id` | string | sim | não | dígitos |
| `mes_competencia` | string | sim | não | `YYYY-MM` |
| `receita_bruta` | **string** | sim | não | `^\d{1,3}(\.\d{3})*,\d{2}$` — ex.: `3.450,00` |
| `custo_direto` | **string** | sim | não | mesmo formato |
| `margem_percentual` | **string** | sim | não | `^0,\d{1,4}$` ou `^1,0+$` — ex.: `0,32` |
| `valor_estorno` | **string** | sim | **sim** | mesmo formato de `receita_bruta` |

> **O formato importa mais aqui do que em qualquer outra fonte.** `3.450,00` lido
> por um parser de ponto decimal vira `3.450` — mil vezes menor — sem lançar
> exceção. Receita mil vezes menor faz a margem não pagar a aquisição, e a **R5**
> ("barato porém destrutivo") dispara em toda conta. O contrato fixa o formato
> justamente para que a etapa 2.5 tenha contra o que testar.

**Limites de aceitação**

| Limite | Nível |
|---|---|
| chave `deal_id` + `mes_competencia` única | estrutural |
| formato decimal com vírgula respeitado | estrutural |
| `deal_id` existe em `crm_negocios` **com `status = ganho`** | contraditório — margem de negócio não ganho |
| `receita_bruta >= 0`, `custo_direto >= 0` | contraditório |
| `margem_percentual` entre `-1` e `1` | contraditório |
| `receita_bruta - custo_direto` coerente com `margem_percentual` (tolerância de arredondamento) | contraditório |

**O que NÃO é violação**

- **Negócio ganho sem linha no financeiro.** O fechamento contábil tem atraso em
  relação ao comercial. É **degradante**: a cobertura de margem é contada e lida
  pela R0, e as regras que dependem de margem (R4, R5) se calam quando a
  cobertura é baixa — em vez de responder com dado pela metade.
- `valor_estorno` nulo. A maioria dos negócios não tem estorno.

> **Limitação declarada (etapa 4.3, red team):** `receita_bruta` não é líquida de
> estorno. `valor_estorno` existe no contrato, mas enquanto o motor não o
> subtrair, a margem é otimista. Isto está registrado como falha aberta, não
> como resolvido.

---

## 6. Limites entre fontes

Nem toda violação vive dentro de um arquivo. Estas são verificadas depois do
`staging`, quando as fontes já podem se enxergar.

| Limite | Nível | Observação |
|---|---|---|
| `crm_negocios.contact_id` existe em `crm_contatos` | estrutural | teste `relationships` do dbt |
| `crm_atividades.contact_id` existe em `crm_contatos` | estrutural | idem |
| `financeiro_margens.deal_id` existe em `crm_negocios` | estrutural | idem |
| `crm_negocios.utm_campaign` sem campanha correspondente em `meta_ads_insights` | **degradante** | campanha que existe no CRM e não nos insights. Alimenta a R0 e a R8 — é uma das sujeiras plantadas de propósito na etapa 1.7 |
| negócio `ganho` sem linha em `financeiro_margens` | degradante | atraso do fechamento contábil |
| dia com custo em `meta_ads_insights` e nenhum lead em `crm_contatos` | degradante | pode ser real (campanha de alcance) ou quebra de rastreamento |

## 7. Resumo — o que parece erro e é sinal

Esta é a tabela que separa este projeto de um validador genérico. Cada linha
aqui é um caso em que reprovar o build **apagaria** justamente o que o produto
existe para detectar.

| Fenômeno | Regra que depende dele |
|---|---|
| `campaign_source` nulo em parte dos negócios | **R8** — receita sem origem rastreável |
| E-mail repetido em `contact_id` diferentes | **R0/R1** — deduplicação da etapa 2.3 |
| Negócio com zero atividades | **R3, R7** — SLA e follow-up insuficiente |
| Negócio parado há muitos dias no mesmo estágio | **R6** — pipeline parado |
| Negócio ganho sem margem lançada | **R4, R5** — silenciadas por cobertura baixa |
| Campanha no CRM sem correspondente nos insights | **R0, R8** |
| Amostra pequena demais para afirmar | **R99** — silencia as regras econômicas |

**A diferença prática entre "pode ser nulo" e "nulidade viola o contrato":**
a primeira é medida e vira entrada de uma regra; a segunda reprova o build.
Confundir as duas custa nos dois sentidos — tratar sinal como erro apaga o
diagnóstico, e tratar erro como sinal faz o motor diagnosticar ruído.
