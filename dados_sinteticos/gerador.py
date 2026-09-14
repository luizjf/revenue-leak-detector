"""Simulação do funil. Produz estruturas limpas em memória.

FRONTEIRA COM A ETAPA 1.7: este módulo não conhece JSON, CSV nem `raw/`.
Um `open()` ou `json.dumps` aqui é responsabilidade vazada do exportador.
É essa separação que torna a sujeira testável: dá para comparar o objeto
limpo daqui com o arquivo sujo de lá.

ALEATORIEDADE: todo sorteio passa por um `np.random.Generator` recebido como
argumento. Nenhuma chamada a `np.random.seed()` ou ao módulo `random` — os
dois usam estado global, e estado global mata a reprodutibilidade em silêncio.
"""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import count

import numpy as np

from dados_sinteticos.cenarios import CENARIOS, Cenario, NomeCenario, Perturbacao
from dados_sinteticos.parametros import (
    COMPLETUDE_BASE,
    CONTAS_PADRAO,
    DATA_INICIO_BASELINE,
    DISTRIBUICAO_LAG,
    FUNIL_BASE,
    FUSO_BRASILIA,
    JANELA_PADRAO,
    MIDIA_BASE,
    OPERACAO_BASE,
    RUIDO,
    SEMENTE_PADRAO,
    SLA_PRIMEIRO_CONTATO,
    Conta,
    Estagio,
)

# z do percentil 90 da normal padrão. Converte a razão p90/mediana em sigma
# da lognormal — ver `_sortear_lag`.
Z90 = 1.2816

# Leads chegam em horário comercial estendido. Arbitrado.
HORA_MIN, HORA_MAX = 8, 21

# Espalhamento do CPL entre as campanhas de uma conta. É isto que permite o
# paradoxo de Simpson existir: sem CPLs diferentes, migrar verba não mexe no
# agregado e a R10 não teria o que detectar (ADR 0003).
CPL_MIN_CAMPANHA, CPL_MAX_CAMPANHA = 0.70, 1.40

TIPOS_TOQUE = ("ligacao", "email", "whatsapp")
RESULTADOS_TOQUE = ("atendeu", "nao_atendeu", "sem_resposta", "respondeu")


# ===========================================================================
# O que o gerador devolve
# ===========================================================================
@dataclass(frozen=True)
class Lead:
    """Um lead que entrou no funil.

    `quando` é datetime, não date: o SLA de primeiro contato da R3 é medido em
    MINUTOS (60 min para score alto). Com granularidade de dia, a R3 não teria
    o que medir.

    `utm_valida=False` é lead cuja origem não foi rastreada — insumo da R0.
    Não é sujeira de formato (isso é da 1.7): é o fenômeno em si.
    """

    id: str
    conta_id: str
    campanha_id: str
    quando: datetime
    score_fit: int
    utm_valida: bool


@dataclass(frozen=True)
class Custo:
    """Gasto de mídia de uma campanha num dia. Grão diário: é o que a Graph API
    entrega (docs/contrato-de-dados.md, 5.1).

    Há linha para toda campanha em todo dia da janela, inclusive com valor 0 —
    o contrato proíbe buraco de dia dentro da janela ativa.
    """

    conta_id: str
    campanha_id: str
    dia: date
    valor: float
    impressoes: int
    cliques: int


@dataclass(frozen=True)
class Atividade:
    """Um toque: interação registrada entre vendedor e lead.

    `direcao` e `resultado` existem para a R7 distinguir "não ligou" de
    "ligou e o lead sumiu" — diagnósticos opostos.
    """

    id: str
    lead_id: str
    negocio_id: str | None
    tipo: str
    direcao: str
    resultado: str | None
    quando: datetime


@dataclass(frozen=True)
class Negocio:
    """Um negócio. `fechado_em is None` significa ainda aberto — estado normal
    de quem está em andamento, não dado faltando.

    `campaign_source is None` é receita sem origem rastreável: o fenômeno que a
    R8 mede, não violação de contrato (docs/contrato-de-dados.md, seção 7).
    """

    id: str
    lead_id: str
    conta_id: str
    campaign_source: str | None
    estagio: Estagio
    status: str  # aberto | ganho | perdido
    valor: float
    margem: float
    criado_em: datetime
    fechado_em: datetime | None


@dataclass(frozen=True)
class DadosConta:
    conta_id: str
    leads: tuple[Lead, ...]
    custos: tuple[Custo, ...]
    atividades: tuple[Atividade, ...]
    negocios: tuple[Negocio, ...]


@dataclass(frozen=True)
class Resultado:
    """Saída do gerador: os dados de todas as contas mais o gabarito.

    O gabarito viaja junto aqui dentro, mas quem grava decide onde: dados vão
    para `raw/`, gabarito vai para `avaliacao/`. Nunca o contrário.
    """

    dados: tuple[DadosConta, ...]
    gabarito: dict


# ===========================================================================
# Calendário — derivado da âncora, sem `date.today()`
# ===========================================================================
def dias_de_captacao() -> list[date]:
    """Os 90 dias em que entram leads e há gasto: baseline + período analisado."""
    total = JANELA_PADRAO.baseline + JANELA_PADRAO.analisado
    return [DATA_INICIO_BASELINE + timedelta(days=i) for i in range(total)]


def fim_da_simulacao() -> date:
    """Último dia simulado, já incluindo a maturação. Depois dele, nada fecha."""
    total = JANELA_PADRAO.baseline + JANELA_PADRAO.analisado + JANELA_PADRAO.maturacao
    return DATA_INICIO_BASELINE + timedelta(days=total - 1)


def e_fim_de_semana(dia: date) -> bool:
    return dia.weekday() >= 5


def e_periodo_analisado(dia: date) -> bool:
    """Os 30 dias comparados contra o baseline. A migração de verba do cenário
    `mudanca_de_mix` só acontece aqui."""
    return dia >= DATA_INICIO_BASELINE + timedelta(days=JANELA_PADRAO.baseline)


# ===========================================================================
# Blocos de simulação
# ===========================================================================
def _campanhas_da_conta(conta: Conta, indice: int) -> tuple[str, ...]:
    """Ids numéricos e estáveis, no formato que a Graph API entrega."""
    return tuple(f"238{indice:02d}{i:03d}" for i in range(1, conta.n_campanhas + 1))


def _cpl_por_campanha(n: int) -> np.ndarray:
    """Fator de CPL de cada campanha, espalhado de 0,70 a 1,40 do CPL da conta.

    Determinístico, sem rng: é característica da conta, não sorteio.
    Sem esse espalhamento, todas as campanhas teriam o mesmo CAC e migrar
    verba entre elas não moveria o agregado — o paradoxo de Simpson não
    existiria e a R10 não teria o que detectar.
    """
    if n == 1:
        return np.array([1.0])
    return np.linspace(CPL_MIN_CAMPANHA, CPL_MAX_CAMPANHA, n)


def _pesos_de_verba(n: int, migracao: float, analisado: bool) -> np.ndarray:
    """Como a verba se reparte entre as campanhas num dia.

    Sem migração, uniforme. No período analisado do cenário `mudanca_de_mix`,
    a distribuição é interpolada em direção à campanha mais cara: `migracao`
    é o peso do alvo concentrado. Nenhuma campanha piora — só muda o peso de
    cada uma, que é exatamente o paradoxo de Simpson.

    A primeira versão tirava `migracao` da fatia de UMA campanha, e com quatro
    campanhas isso movia só 12 p.p. em vez dos 50 a 75 declarados no cenário:
    o agregado subia 3% e a armadilha não tentava ninguém. Interpolar move a
    verba de todas as baratas de uma vez.
    """
    uniforme = np.full(n, 1.0 / n)
    if migracao <= 0 or not analisado or n < 2:
        return uniforme
    alvo = np.zeros(n)
    alvo[-1] = 1.0
    peso = min(migracao, 1.0)
    pesos = (1 - peso) * uniforme + peso * alvo
    return pesos / pesos.sum()


def _sortear_lag(mediana_dias: int, rng: np.random.Generator) -> int:
    """Dias entre a entrada do lead e a resolução do negócio.

    Lognormal, truncada em `DISTRIBUICAO_LAG.corte_dias`:

        mediana = exp(mu)                =>  mu    = log(mediana_dias)
        p90     = exp(mu + Z90 * sigma)  =>  sigma = log(razao_p90) / Z90

    Lognormal e não normal porque o atraso é sempre positivo e tem cauda longa
    à direita — e é essa cauda que a ADR 0001 existe para tratar. Constante
    aqui seria o erro que o `ETAPAS.md` chama de ponto crítico da etapa.
    """
    mu = math.log(mediana_dias)
    sigma = math.log(DISTRIBUICAO_LAG.razao_p90_mediana) / Z90
    lag = float(rng.lognormal(mu, sigma))
    return int(min(round(lag), DISTRIBUICAO_LAG.corte_dias))


# Campo da Perturbacao -> parâmetro efetivo que ele altera.
_DESTINO = {
    "cpl_mult": "cpl",
    "leads_mult": "leads_dia",
    "ticket_mult": "ticket",
    "taxa_lead_qualificado_mult": "taxa_lead_qualificado",
    "taxa_proposta_ganho_mult": "taxa_proposta_ganho",
    "margem_delta_pp": "margem",
    "migracao_verba_delta_pp": "migracao_verba",
    "alto_fit_fora_sla_frac": "alto_fit_fora_sla",
    "negocios_parados_frac": "negocios_parados",
    "perdidos_ate_2_toques_frac": "perdidos_ate_2_toques",
    "campaign_source_nulo_frac": "campaign_source_nulo",
    "utm_valida_frac": "utm_valida",
}

# Parâmetros que são probabilidade: têm que continuar em [0, 1] depois da
# perturbação. `ticket`, `cpl` e `leads_dia` ficam de fora de propósito.
_PROBABILIDADES = (
    "margem",
    "taxa_lead_qualificado",
    "taxa_qualificado_proposta",
    "taxa_proposta_ganho",
    "alto_fit_fora_sla",
    "negocios_parados",
    "perdidos_ate_2_toques",
    "campaign_source_nulo",
    "utm_valida",
)


def _parametros_efetivos(
    conta: Conta, perturbacao: Perturbacao, rng: np.random.Generator
) -> tuple[dict[str, float], dict[str, float]]:
    """Aplica a perturbação sobre a base. Devolve (parâmetros, magnitudes).

    ESTA É A ÚNICA FUNÇÃO QUE INTERPRETA OS SUFIXOS. Se `_mult`, `_delta_pp` e
    `_frac` fossem aplicados em mais de um lugar, a convenção não protegeria
    nada:

        *_mult      valor = base * fator     (1.30 = +30%)
        *_delta_pp  valor = base + delta     (0.05 = +5 p.p.)
        *_frac      valor = fracao           (substitui a base)

    As magnitudes sorteadas voltam para o gabarito: é o que permite responder,
    na fase 3, a partir de que intensidade o motor começa a acertar.
    """
    params: dict[str, float] = {
        "leads_dia": float(conta.leads_dia),
        "cpl": float(conta.cpl_base),
        "ticket": float(conta.ticket_base),
        "margem": conta.margem_base,
        "taxa_lead_qualificado": FUNIL_BASE.taxa_lead_qualificado,
        "taxa_qualificado_proposta": FUNIL_BASE.taxa_qualificado_proposta,
        "taxa_proposta_ganho": FUNIL_BASE.taxa_proposta_ganho,
        "alto_fit_fora_sla": OPERACAO_BASE.alto_fit_fora_sla,
        "negocios_parados": OPERACAO_BASE.negocios_parados,
        "perdidos_ate_2_toques": OPERACAO_BASE.perdidos_ate_2_toques,
        "campaign_source_nulo": COMPLETUDE_BASE.campaign_source_nulo,
        "utm_valida": COMPLETUDE_BASE.utm_valida,
        "migracao_verba": 0.0,
    }
    magnitudes: dict[str, float] = {}

    for campo, faixa in vars(perturbacao).items():
        if faixa is None:
            continue
        fator = float(rng.uniform(faixa.minimo, faixa.maximo))
        magnitudes[campo] = fator
        chave = _DESTINO[campo]
        if campo.endswith("_mult"):
            params[chave] *= fator
        elif campo.endswith("_delta_pp"):
            params[chave] += fator
        elif campo.endswith("_frac"):
            params[chave] = fator
        else:  # pragma: no cover - só acontece se alguém criar sufixo novo
            raise ValueError(f"sufixo desconhecido em Perturbacao: {campo}")

    for chave in _PROBABILIDADES:
        params[chave] = min(max(params[chave], 0.0), 1.0)

    return params, magnitudes


def _sortear_score_fit(rng: np.random.Generator) -> int:
    """Score 0-100 respeitando as proporções de `SLA_PRIMEIRO_CONTATO`.

    A faixa é sorteada pela proporção declarada; o score, uniforme dentro dela.
    Corte, proporção e SLA vêm da mesma estrutura justamente para não
    divergirem.
    """
    probabilidades = [f.proporcao_leads for f in SLA_PRIMEIRO_CONTATO]
    i = int(rng.choice(len(SLA_PRIMEIRO_CONTATO), p=probabilidades))
    piso = SLA_PRIMEIRO_CONTATO[i].score_min
    teto = 100 if i == 0 else SLA_PRIMEIRO_CONTATO[i - 1].score_min - 1
    return int(rng.integers(piso, teto + 1))


def _faixa_do_score(score: int):
    """A faixa de fit à qual o score pertence. As faixas estão em ordem
    decrescente, então a primeira que couber é a certa."""
    for faixa in SLA_PRIMEIRO_CONTATO:
        if score >= faixa.score_min:
            return faixa
    return SLA_PRIMEIRO_CONTATO[-1]


def _leads_do_dia(
    conta: Conta,
    dia: date,
    campanhas: tuple[str, ...],
    params: dict[str, float],
    rng: np.random.Generator,
    ids: Iterator[int],
) -> list[Lead]:
    """Leads que entram num dia.

        volume = leads_dia * (1 ± variacao_diaria) * (fim de semana ? mult : 1)

    A campanha sai dos pesos de verba do dia — é por aí que a migração do
    cenário `mudanca_de_mix` entra. O datetime nasce com fuso: datetime
    ingênuo que "por convenção" significa -03:00 é convenção que nenhum teste
    verifica.
    """
    fator = float(
        rng.uniform(1 - RUIDO.variacao_diaria_amplitude, 1 + RUIDO.variacao_diaria_amplitude)
    )
    if e_fim_de_semana(dia):
        fator *= RUIDO.fim_de_semana_mult

    volume = max(0, round(params["leads_dia"] * fator))
    pesos = _pesos_de_verba(len(campanhas), params["migracao_verba"], e_periodo_analisado(dia))

    leads: list[Lead] = []
    for _ in range(volume):
        indice_campanha = int(rng.choice(len(campanhas), p=pesos))
        quando = datetime(
            dia.year,
            dia.month,
            dia.day,
            int(rng.integers(HORA_MIN, HORA_MAX)),
            int(rng.integers(0, 60)),
            tzinfo=FUSO_BRASILIA,
        )
        leads.append(
            Lead(
                id=f"{next(ids)}",
                conta_id=conta.id,
                campanha_id=campanhas[indice_campanha],
                quando=quando,
                score_fit=_sortear_score_fit(rng),
                utm_valida=bool(rng.random() < params["utm_valida"]),
            )
        )
    return leads


def _custo_do_dia(
    conta: Conta,
    dia: date,
    campanhas: tuple[str, ...],
    leads: list[Lead],
    params: dict[str, float],
) -> list[Custo]:
    """Gasto por campanha no dia: `n leads da campanha * CPL da campanha`.

    DECISÃO: o CPL é causa, não consequência. A alternativa — orçamento fixo,
    CPL derivado — é mais fiel ao que um gestor de mídia faz, mas tornaria a
    magnitude plantada aproximada em vez de exata, e é a magnitude exata que
    o gabarito registra. O custo dessa escolha: o gasto da conta oscila com o
    volume de leads em vez de ser um orçamento estável.

    Emite linha para TODA campanha em TODO dia, inclusive com valor zero: o
    contrato proíbe buraco de dia dentro da janela ativa, e buraco somado como
    zero baixa o custo, derruba o CAC e silencia a R1.
    """
    fatores = _cpl_por_campanha(len(campanhas))
    contagem = dict.fromkeys(campanhas, 0)
    for lead in leads:
        contagem[lead.campanha_id] += 1

    linhas: list[Custo] = []
    for campanha, fator in zip(campanhas, fatores, strict=True):
        n_leads = contagem[campanha]
        # Derivadas do volume de leads, sem sorteio: um dia com mais leads teve
        # mais cliques. `ceil` garante cliques >= leads e impressoes >= cliques,
        # que é o limite de aceitação `clicks <= impressions` do contrato 5.1.
        cliques = math.ceil(n_leads / MIDIA_BASE.taxa_clique_para_lead)
        impressoes = math.ceil(cliques / MIDIA_BASE.ctr)
        linhas.append(
            Custo(
                conta_id=conta.id,
                campanha_id=campanha,
                dia=dia,
                valor=round(n_leads * params["cpl"] * float(fator), 2),
                impressoes=impressoes,
                cliques=cliques,
            )
        )
    return linhas


def _negocio_do_lead(
    lead: Lead,
    conta: Conta,
    params: dict[str, float],
    rng: np.random.Generator,
    ids: Iterator[int],
) -> Negocio | None:
    """Faz o lead atravessar o funil. `None` se ele nunca vira negócio.

        lead -> qualificado : só aqui nasce o negócio no CRM
        qualificado -> proposta -> ganho : cada passo com sua taxa

    A resolução acontece em `lead.quando + _sortear_lag(...)`. Se cair depois
    do fim da simulação, o negócio permanece ABERTO — e é justamente por isso
    que existem os 30 dias de maturação: sem eles, quase toda a coorte do
    período analisado ficaria aberta, o denominador do CAC esvaziaria e todo
    cenário pareceria "CAC explodiu".

    `negocios_parados` força uma fração a ficar aberta mesmo quando resolveria
    — é o insumo da R6.
    """
    if rng.random() >= params["taxa_lead_qualificado"]:
        return None

    estagio = Estagio.QUALIFICADO
    ganhou = False
    if rng.random() < params["taxa_qualificado_proposta"]:
        estagio = Estagio.PROPOSTA
        if rng.random() < params["taxa_proposta_ganho"]:
            ganhou = True

    lag = _sortear_lag(conta.lag_mediano_dias, rng)
    resolucao = lead.quando + timedelta(days=lag)
    travado = rng.random() < params["negocios_parados"]

    if travado or resolucao.date() > fim_da_simulacao():
        status, fechado_em = "aberto", None
    elif ganhou:
        status, fechado_em, estagio = "ganho", resolucao, Estagio.GANHO
    else:
        status, fechado_em, estagio = "perdido", resolucao, Estagio.PERDIDO

    tem_origem = rng.random() >= params["campaign_source_nulo"]
    return Negocio(
        id=f"9{next(ids)}",
        lead_id=lead.id,
        conta_id=conta.id,
        campaign_source=lead.campanha_id if tem_origem else None,
        estagio=estagio,
        status=status,
        valor=round(params["ticket"] * float(rng.uniform(0.85, 1.15)), 2),
        margem=round(params["margem"], 4),
        criado_em=lead.quando,
        fechado_em=fechado_em,
    )


def _atividades_do_lead(
    lead: Lead,
    negocio: Negocio | None,
    params: dict[str, float],
    rng: np.random.Generator,
    ids: Iterator[int],
) -> list[Atividade]:
    """Toques do vendedor sobre o lead.

    O PRIMEIRO toque define a R3: ele cai dentro do SLA da faixa de fit do
    lead, ou fora dela. A fração fora do SLA só é perturbada para a faixa de
    fit mais alta — é sobre esses leads que o cenário 4 fala.

    A QUANTIDADE de toques define a R7. Uma fração (`perdidos_ate_2_toques`)
    recebe de 0 a 2; o resto recebe em torno da mediana declarada. Constante
    aqui apagaria a regra: ou todos passariam, ou nenhum.
    """
    faixa = _faixa_do_score(lead.score_fit)
    e_alto_fit = faixa is SLA_PRIMEIRO_CONTATO[0]
    prob_fora = params["alto_fit_fora_sla"] if e_alto_fit else OPERACAO_BASE.alto_fit_fora_sla

    if rng.random() < prob_fora:
        atraso = int(rng.integers(faixa.sla_minutos * 2, faixa.sla_minutos * 8))
    else:
        atraso = int(rng.integers(1, max(2, faixa.sla_minutos)))

    poucos_toques = rng.random() < params["perdidos_ate_2_toques"]
    mediana = FUNIL_BASE.toques_ate_perda_mediana
    n_toques = (
        int(rng.integers(0, 3)) if poucos_toques else int(rng.integers(mediana - 1, mediana + 3))
    )

    limite = datetime.combine(fim_da_simulacao(), datetime.min.time(), tzinfo=FUSO_BRASILIA)
    atividades: list[Atividade] = []
    quando = lead.quando + timedelta(minutes=atraso)
    for _ in range(n_toques):
        if quando > limite:
            break
        atividades.append(
            Atividade(
                id=f"7{next(ids)}",
                lead_id=lead.id,
                negocio_id=negocio.id if negocio is not None else None,
                tipo=str(rng.choice(TIPOS_TOQUE)),
                direcao="saida",
                resultado=str(rng.choice(RESULTADOS_TOQUE)),
                quando=quando,
            )
        )
        quando = quando + timedelta(days=int(rng.integers(1, 8)))
    return atividades


def _gerar_conta(
    conta: Conta, indice: int, cenario: Cenario, rng: np.random.Generator
) -> tuple[DadosConta, dict]:
    """Uma conta inteira. Devolve os dados e a entrada dela no gabarito.

    Os 30 dias de maturação NÃO aparecem no laço: eles não geram lead nem
    custo. Existem só para os fechamentos caberem dentro da janela.
    """
    params, magnitudes = _parametros_efetivos(conta, cenario.perturbacao, rng)
    campanhas = _campanhas_da_conta(conta, indice)

    ids_lead = count(int(f"{indice:02d}100000"))
    ids_negocio = count(int(f"{indice:02d}200000"))
    ids_atividade = count(int(f"{indice:02d}300000"))

    leads: list[Lead] = []
    custos: list[Custo] = []
    for dia in dias_de_captacao():
        do_dia = _leads_do_dia(conta, dia, campanhas, params, rng, ids_lead)
        leads.extend(do_dia)
        custos.extend(_custo_do_dia(conta, dia, campanhas, do_dia, params))

    negocios: list[Negocio] = []
    atividades: list[Atividade] = []
    for lead in leads:
        negocio = _negocio_do_lead(lead, conta, params, rng, ids_negocio)
        if negocio is not None:
            negocios.append(negocio)
        atividades.extend(_atividades_do_lead(lead, negocio, params, rng, ids_atividade))

    entrada = {
        "cenario": str(cenario.nome),
        "regras_esperadas": list(cenario.regras_esperadas),
        "magnitudes": magnitudes,
        "n_leads": len(leads),
        "n_negocios": len(negocios),
        "n_ganhos": sum(1 for n in negocios if n.status == "ganho"),
    }
    dados = DadosConta(
        conta_id=conta.id,
        leads=tuple(leads),
        custos=tuple(custos),
        atividades=tuple(atividades),
        negocios=tuple(negocios),
    )
    return dados, entrada


# ===========================================================================
# Orquestração
# ===========================================================================
def gerar(nome_cenario: str, semente: int = SEMENTE_PADRAO) -> Resultado:
    """Gera as 12 contas sob um cenário.

    Duas chamadas com a mesma semente devolvem exatamente o mesmo resultado —
    é o critério de saída da etapa 1.6.

    `SeedSequence.spawn` dá a cada conta um fluxo independente. Com um único
    Generator compartilhado, inserir uma conta no meio da lista mudaria o dado
    de todas as seguintes, e todo gabarito anterior deixaria de corresponder.
    """
    cenario = CENARIOS[NomeCenario(nome_cenario)]
    sub_sementes = np.random.SeedSequence(semente).spawn(len(CONTAS_PADRAO))

    dados: list[DadosConta] = []
    gabarito: dict = {"semente": semente, "cenario": str(cenario.nome), "contas": {}}

    for indice, (conta, sub) in enumerate(zip(CONTAS_PADRAO, sub_sementes, strict=True)):
        dados_conta, entrada = _gerar_conta(conta, indice, cenario, np.random.default_rng(sub))
        dados.append(dados_conta)
        gabarito["contas"][conta.id] = entrada

    return Resultado(dados=tuple(dados), gabarito=gabarito)
