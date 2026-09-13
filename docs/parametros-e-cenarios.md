# Estratégia de geração — parâmetros e cenários

**Este documento é a especificação da etapa 1.5.** Ele define *o quê* será
gerado e *por quê*. O `dados_sinteticos/parametros.py` e o `cenarios.py` são a
transcrição dele em Python — escritos por Luiz, não por Claude.

> **Nota de autoria:** a estrutura de negócio e as faixas abaixo foram definidas
> por Claude a pedido de Luiz, por se tratar de projeto de estudo/portfólio.
> As decisões de método (o que é cenário, o que é armadilha, onde fica a
> fronteira gerador × motor) valem como parte do projeto e devem ser defendidas.

---

## 1. As duas regras que governam tudo aqui

**Regra 1 — nenhum número mágico.** Todo valor tem nome, mora em
`parametros.py`, e é importado. Um `0.35` solto dentro da lógica de geração é
bug, mesmo que o resultado esteja certo: parâmetro sem nome não é ajustável nem
auditável.

**Regra 2 — o gerador não pode conhecer os limiares do motor.** Ele sabe **qual**
problema plantou (e grava isso no gabarito); ele **não** pode saber com que corte
o motor procura. As faixas de perturbação abaixo são escolhidas por
plausibilidade de negócio e, deliberadamente, **atravessam** o limiar que o motor
vier a usar — parte dos casos fica acima, parte abaixo. É isso que permite medir
recall em vez de encená-lo. No dia em que uma faixa for ajustada para o motor
acertar, o número de precisão vira ficção.

## 2. De onde vêm estas faixas — declaração honesta

**Elas são arbitradas.** Não há base real neste projeto (`CLAUDE.md` seção 3), e
não vou fingir benchmark de mercado que não medi. As faixas foram escolhidas para
serem *plausíveis* dentro de cada segmento e para produzir volumes que permitam
teste estatístico.

**Por que isso não invalida a medição:** a precisão do motor é medida contra o
**gabarito**, não contra a realidade. O que precisa ser verdadeiro é a *relação*
entre o problema plantado e o sinal observável — e essa relação é construída, não
estimada. O que fica comprometido é a **validade externa**: não se pode afirmar
que "no mercado brasileiro o CPL médio é X". O projeto não afirma isso em lugar
nenhum, e a seção "Limitações" do README (etapa 4.4) precisa dizer exatamente
este parágrafo.

---

## 3. Estrutura de negócio — a agência e as 12 contas

Agência de performance, **12 contas ativas**, **um canal de mídia por conta**
(Meta Ads), CRM no formato RD Station.

| # | Conta | Segmento | Ticket base (R$) | Leads/dia | CPL base (R$) | Margem base | Lag mediano |
|---|---|---|---|---|---|---|---|
| 01 | `acme_odonto` | Saúde / odontologia | 3.500 | 22 | 38 | 0,42 | 12 d |
| 02 | `belaforma_estetica` | Estética | 4.200 | 18 | 45 | 0,45 | 10 d |
| 03 | `construtora_horizonte` | Imobiliário | 14.000 | 9 | 130 | 0,26 | 38 d |
| 04 | `imob_costa_verde` | Imobiliário | 11.000 | 12 | 110 | 0,28 | 34 d |
| 05 | `edu_prime_cursos` | Educação | 3.200 | 25 | 28 | 0,50 | 8 d |
| 06 | `edu_carreira_tech` | Educação | 5.800 | 20 | 42 | 0,47 | 14 d |
| 07 | `contabil_nexus` | Serviços B2B | 6.500 | 11 | 85 | 0,38 | 26 d |
| 08 | `juridico_menezes` | Serviços B2B | 9.000 | 8 | 120 | 0,40 | 30 d |
| 09 | `saas_gestor_pro` | Software B2B | 7.400 | 14 | 95 | 0,55 | 24 d |
| 10 | `saas_fluxo` | Software B2B | 4.900 | 16 | 70 | 0,58 | 20 d |
| 11 | `clinica_vitalis` | Saúde | 8.200 | 10 | 105 | 0,35 | 22 d |
| 12 | `solar_energia_ma` | Energia solar | 12.500 | 13 | 115 | 0,24 | 42 d 

**Por que a variedade importa:** se as 12 contas fossem parecidas, um limiar
único funcionaria e o projeto não provaria nada. A dispersão de ticket (4x), de
lag (5x) e de margem (2,4x) é o que obriga o motor a comparar cada conta consigo
mesma, e não com uma média de mercado.

**Cada conta tem 3 a 6 campanhas ativas** — necessário para a ADR 0003 (avaliação
por campanha) e para o paradoxo de Simpson poder existir.

## 4. Parâmetros base do funil

| Parâmetro | Valor base | Observação |
|---|---|---|
| `taxa_lead_qualificado` | 0,35 | lead a qualificado |
| `taxa_qualificado_proposta` | 0,45 | qualificado a proposta |
| `taxa_proposta_ganho` | 0,30 | proposta a ganho |
| **conversão ponta a ponta** | **≈ 0,047** | produto das três |
| `distribuicao_lag` | lognormal | mediana por conta (tabela acima); p90 ≈ 2,2 x mediana; cauda truncada em **120 dias** |
| `sla_primeiro_contato` | 60 min (`score_fit` ≥ 70) · 4 h (40 a 69) · 24 h (< 40) | usado pela R3 |
| `sla_por_estagio` | 3 d `novo` · 5 d `contato_feito` · 7 d `qualificado` · 10 d `proposta` · 14 d `negociacao` | usado pela R6 |
| `toques_ate_perda` | mediana 4, mínimo 0 | usado pela R7 |
| `distribuicao_score_fit` | 0 a 100, mediana 55 | 25% dos leads com score ≥ 70 |
| `completude_utm` | 0,88 | fração de leads com UTM válida |
| `taxa_campaign_source_nulo` | 0,08 | base — sobe no cenário 9 |
| `taxa_contato_duplicado` | 0,03 | e-mail igual, `contact_id` diferente |
| `variacao_diaria` | ±18% | ruído dia a dia, para nada sair liso demais |
| `queda_fim_de_semana` | −45% | sazonalidade semanal — é armadilha, não problema |

**Janela temporal**

```
|---- baseline: 60 dias ----|---- período analisado: 30 dias ----|---- maturação: +30 dias ----|
```

Os 30 dias finais **não geram leads novos** — existem apenas para os leads do
período analisado terem tempo de fechar. Sem eles, a coorte final nunca amadurece
e o período analisado nasce vazio (ADR 0001).

> **Tensão declarada, encontrada pelo teste `test_lag_cabe_dentro_do_corte`:**
> a maturação da ADR 0001 é de 30 dias, mas três contas têm lag mediano acima
> disso — `construtora_horizonte` (38 d), `imob_costa_verde` (34 d) e
> `solar_energia_ma` (42 d). Nelas, a maior parte da receita de uma coorte ainda
> não fechou quando a coorte é declarada madura.
>
> **Isso não é bug e não reabre a ADR 0001.** É o comportamento correto: ciclo
> longo com janela de 30 dias genuinamente não permite afirmar nada, e o produto
> deve **dizer isso** em vez de responder. Essas contas devem cair na R99 e na
> flag de imaturidade da etapa 2.3 com mais frequência que as demais — e isso é
> um resultado a verificar na fase 3, não um defeito a corrigir na fase 1.
>
> A truncagem foi movida de 90 para 120 dias porque o p90 da conta solar é 92 d:
> cortar em 90 amputava a cauda abaixo do próprio p90. Negócio que não fecha
> dentro da janela permanece `aberto`, e é insumo legítimo da R6.

---

## 5. Os 10 cenários

Um cenário é uma **perturbação nomeada** aplicada sobre a base. Cada conta recebe
um cenário; o gabarito registra qual.

| # | Cenário | Perturbação | Regra que deve pegar |
|---|---|---|---|
| 1 | `cpl_alto` | CPL **+30% a +70%**; todo o resto constante | **R1** — efeito-CPL |
| 2 | `conversao_caiu` | `taxa_proposta_ganho` **−25% a −50%**; CPL constante | **R1** — efeito-conversão |
| 3 | `volume_barato_sem_venda` | CPL **−25% a −45%**, leads **+40% a +90%**, `taxa_lead_qualificado` **−40% a −60%** | **R2** |
| 4 | `sla_estourado` | **45% a 80%** dos leads com `score_fit` ≥ 70 sem contato dentro do SLA | **R3** |
| 5 | `caro_porem_saudavel` | CPL **+25% a +50%**, ticket **+40% a +90%**, margem **+5 a +12 p.p.** | **R4** — não pausar |
| 6 | `barato_porem_destrutivo` | CPL **−20% a −40%**, ticket **−30% a −55%**, margem **−10 a −20 p.p.** | **R5** |
| 7 | `pipeline_parado` | **35% a 70%** dos negócios abertos sem movimento além do SLA do estágio | **R6** |
| 8 | `follow_up_insuficiente` | fração de perdidos com 0 a 2 toques sobe de 15% para **55% a 85%** | **R7** |
| 9 | `origem_perdida` | `campaign_source` nulo sobe de 8% para **30% a 60%** | **R8** |
| 10 | `mudanca_de_mix` | verba migra **50 a 75 p.p.** entre campanhas; **nenhuma campanha piora** | **R10** |

Mais o controle:

| | Cenário | Perturbação | Resposta correta |
|---|---|---|---|
| 0 | `normal` | nenhuma | **silêncio** — qualquer achado aqui é falso positivo |

**Repare nos cenários 5 e 10:** a resposta certa não é "alerta". É "não pause" e
"isto é mix, não vazamento". São as duas regras que impedem uma ação errada, e
são o motivo de o motor existir — um detector trivial mata a campanha mais
lucrativa da conta nos dois casos.

## 6. Condições transversais

Não são cenários: são **estados do dado** que podem se sobrepor a qualquer
cenário. É o que produz os "cenários triplos" da etapa 3.6.

| Condição | Perturbação | Efeito esperado |
|---|---|---|
| `dados_incompletos` | UTM válida cai para **60% a 78%**, ou leads sem campanha sobem para **18% a 35%** | **R0** bloqueia a conta antes de qualquer regra econômica |
| `amostra_pequena` | volume de leads reduzido a **15% a 35%** do base | **R99** silencia as regras econômicas; a diferença deixa de ser distinguível de ruído |

## 7. As sete armadilhas

Armadilha é dado que **parece problema e não é**. O critério de saída da fase 3 é
alarme falso abaixo de 5% aqui — contra 41,4% do detector trivial.

| # | Armadilha | O que o dado mostra | Por que não é problema |
|---|---|---|---|
| 1 | `mix_de_campanha` | CAC agregado sobe forte | Nenhuma campanha piorou; a verba migrou (ADR 0003) |
| 2 | `caro_porem_saudavel` | CAC sobe 40% | A margem subiu mais; o payback melhorou |
| 3 | `outlier_de_ticket` | ticket médio salta | Um único negócio muito grande desloca a média; a mediana não se move |
| 4 | `sazonalidade_semanal` | queda de 45% em leads e custo | É fim de semana. Acontece toda semana, inclusive no baseline |
| 5 | `campanha_sem_historico` **(nova)** | campanha com CAC "muito acima" | Ela nasceu no período analisado. Não há baseline — comparar é inventar |
| 6 | `janela_com_feriado` **(nova)** | 3 a 5 dias com queda de 60% a 80% | Feriado. O período tem menos dias úteis, não menos eficiência |
| 7 | `reposicionamento_de_ticket` **(nova)** | ticket sobe 60% a 120% e volume cai | Decisão comercial deliberada do cliente. CAC sobe por desenho, não por falha |

As armadilhas 1 e 2 coincidem com os cenários 10 e 5 — de propósito. Elas são, ao
mesmo tempo, o que o motor deve **explicar** e o que ele não deve **alarmar**.

---

## 8. Semente e reprodutibilidade

`gerar("normal", 42)` tem que produzir bytes idênticos em qualquer máquina. Três
coisas precisam estar versionadas para isso valer:

1. **O código do gerador** — em `dados_sinteticos/`.
2. **A semente e os parâmetros** — em `parametros.py` e `cenarios.py`. Toda
   aleatoriedade passa por um gerador semeado explicitamente; nenhuma chamada usa
   o estado global do `random` ou do `numpy`.
3. **As versões das bibliotecas** — no `pyproject.toml`, que já existe. Mudança
   de versão do `numpy` pode alterar o fluxo do gerador de números
   pseudoaleatórios, e o `raw/` sai diferente sem ninguém ter tocado no código.

## 9. Gabarito

`avaliacao/gabarito_contas.json`. **Nunca em `raw/`.**

Uma entrada por conta, registrando: cenário aplicado, magnitude sorteada dentro
da faixa, condições transversais ativas, armadilhas plantadas, semente usada, e
quais regras deveriam disparar.

O campo de magnitude é o que permite a análise mais útil da fase 3: **onde,
dentro da faixa, o motor começa a acertar.** Um motor que só pega perturbações de
+70% tem precisão alta e serventia baixa.

## 10. O que `parametros.py` e `cenarios.py` precisam expor

Estrutura, não código — a transcrição é sua.

**`parametros.py`**
`FUNIL_BASE` · `CONTAS` · `JANELA` · `DISTRIBUICAO_LAG` · `SLA_PRIMEIRO_CONTATO` ·
`SLA_POR_ESTAGIO` · `COMPLETUDE` · `RUIDO`

**`cenarios.py`**
`CENARIOS` · `CONDICOES_TRANSVERSAIS` · `ARMADILHAS`

Cada constante leva **docstring dizendo de onde veio a faixa** — e, quando a
resposta for "arbitrada", a docstring diz "arbitrada", não inventa fonte.
