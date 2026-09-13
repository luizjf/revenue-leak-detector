"""Parâmetros base da geração sintética.

DECLARAÇÃO, não cálculo: não sorteia, não lê arquivo, não tem efeito colateral.
Importa só biblioteca padrão — se precisar de numpy, deixou de ser declaração.

PROCEDÊNCIA: todas as faixas são arbitradas, não medidas (não há base real).
Ver docs/parametros-e-cenarios.md, seção 2.

FRONTEIRA: nenhum valor aqui pode vir de um limiar do motor — seção 1, regra 2.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Final

SEMENTE_PADRAO: Final[int] = 42
"""Semente única de toda a geração. Reprodutibilidade: seção 8 da estratégia."""


@dataclass(frozen=True)
class Janela:
    """Recorte temporal da simulação, em dias."""

    baseline: int
    analisado: int
    maturacao: int


# maturacao=30 vem da ADR 0001: coorte imatura não entra em comparação de CAC.
JANELA_PADRAO: Final[Janela] = Janela(baseline=60, analisado=30, maturacao=30)

# Âncora fixa do calendário. Sem ela, gerar("normal", 42) mudaria de resultado
# a cada dia e o critério de saída da etapa 1.6 quebraria sozinho.
# Segunda-feira de propósito: começar no meio da semana desequilibraria ainda
# mais a contagem de fins de semana entre os dois períodos. Resta um viés de
# -1,7% no volume do período analisado (60 e 30 não são múltiplos de 7) —
# declarado, não corrigido: está abaixo do ruído diário de ±18%.
DATA_INICIO_BASELINE: Final[date] = date(2026, 3, 2)

# O CRM entrega ISO 8601 com -03:00 (docs/contrato-de-dados.md, seção 4).
# Timestamp com fuso desde a origem: datetime "ingênuo" que só por convenção
# significa -03:00 é uma convenção que nenhum teste verifica.
FUSO_BRASILIA: Final[timezone] = timezone(timedelta(hours=-3))


class Estagio(StrEnum):
    """Estágios do negócio. Valores conforme docs/contrato-de-dados.md, 5.2."""

    NOVO = "novo"
    CONTATO_FEITO = "contato_feito"
    QUALIFICADO = "qualificado"
    PROPOSTA = "proposta"
    NEGOCIACAO = "negociacao"
    GANHO = "ganho"
    PERDIDO = "perdido"


# Dias tolerados por estágio antes de o negócio ser considerado parado (R6).
# GANHO e PERDIDO ficam de fora: são terminais, não têm SLA.
# MappingProxyType porque dict comum é mutável e furaria a garantia do frozen.
SLA_POR_ESTAGIO: Final[Mapping[Estagio, int]] = MappingProxyType(
    {
        Estagio.NOVO: 3,
        Estagio.CONTATO_FEITO: 5,
        Estagio.QUALIFICADO: 7,
        Estagio.PROPOSTA: 10,
        Estagio.NEGOCIACAO: 14,
    }
)


@dataclass(frozen=True)
class Conta:
    """Uma conta da agência. Arbitrada — ver seção 3 da estratégia."""

    id: str
    segmento: str
    ticket_base: int
    leads_dia: int
    cpl_base: int
    margem_base: float
    lag_mediano_dias: int
    n_campanhas: int


# A dispersão é deliberada: ticket varia 4x, lag 5x, margem 2,4x. Contas
# parecidas fariam um limiar único funcionar, e o projeto não provaria nada.
CONTAS_PADRAO: Final[tuple[Conta, ...]] = (
    Conta(
        id="acme_odonto",
        segmento="Saúde / odontologia",
        ticket_base=3500,
        leads_dia=22,
        cpl_base=38,
        margem_base=0.42,
        lag_mediano_dias=12,
        n_campanhas=4,
    ),
    Conta(
        id="belaforma_estetica",
        segmento="Estética",
        ticket_base=4200,
        leads_dia=18,
        cpl_base=45,
        margem_base=0.45,
        lag_mediano_dias=10,
        n_campanhas=5,
    ),
    Conta(
        id="construtora_horizonte",
        segmento="Imobiliário",
        ticket_base=14000,
        leads_dia=9,
        cpl_base=130,
        margem_base=0.26,
        lag_mediano_dias=38,
        n_campanhas=4,
    ),
    Conta(
        id="imob_costa_verde",
        segmento="Imobiliário",
        ticket_base=11000,
        leads_dia=12,
        cpl_base=110,
        margem_base=0.28,
        lag_mediano_dias=34,
        n_campanhas=5,
    ),
    Conta(
        id="edu_prime_cursos",
        segmento="Educação",
        ticket_base=3200,
        leads_dia=25,
        cpl_base=28,
        margem_base=0.5,
        lag_mediano_dias=8,
        n_campanhas=4,
    ),
    Conta(
        id="edu_carreira_tech",
        segmento="Educação",
        ticket_base=5800,
        leads_dia=20,
        cpl_base=42,
        margem_base=0.47,
        lag_mediano_dias=14,
        n_campanhas=5,
    ),
    Conta(
        id="contabil_nexus",
        segmento="Serviços B2B",
        ticket_base=6500,
        leads_dia=11,
        cpl_base=85,
        margem_base=0.38,
        lag_mediano_dias=26,
        n_campanhas=4,
    ),
    Conta(
        id="juridico_menezes",
        segmento="Serviços B2B",
        ticket_base=9000,
        leads_dia=8,
        cpl_base=120,
        margem_base=0.4,
        lag_mediano_dias=30,
        n_campanhas=5,
    ),
    Conta(
        id="saas_gestor_pro",
        segmento="Software B2B",
        ticket_base=7400,
        leads_dia=14,
        cpl_base=95,
        margem_base=0.55,
        lag_mediano_dias=24,
        n_campanhas=4,
    ),
    Conta(
        id="saas_fluxo",
        segmento="Software B2B",
        ticket_base=4900,
        leads_dia=16,
        cpl_base=70,
        margem_base=0.58,
        lag_mediano_dias=20,
        n_campanhas=5,
    ),
    Conta(
        id="clinica_vitalis",
        segmento="Saúde",
        ticket_base=8200,
        leads_dia=10,
        cpl_base=105,
        margem_base=0.35,
        lag_mediano_dias=22,
        n_campanhas=4,
    ),
    Conta(
        id="solar_energia_ma",
        segmento="Energia solar",
        ticket_base=12500,
        leads_dia=13,
        cpl_base=115,
        margem_base=0.24,
        lag_mediano_dias=42,
        n_campanhas=5,
    ),
)


@dataclass(frozen=True)
class Funil:
    """Taxas de passagem entre etapas. Arbitradas."""

    taxa_lead_qualificado: float
    taxa_qualificado_proposta: float
    taxa_proposta_ganho: float
    toques_ate_perda_mediana: int


# Conversão ponta a ponta = produto das três taxas ≈ 0,047.
# `toques_ate_perda_mediana` é MEDIANA, não constante: se todo perdido levasse
# 4 toques, a R7 (perdidos com menos de 3) não teria o que detectar.
@dataclass(frozen=True)
class Operacao:
    """Falhas operacionais no estado NORMAL. Arbitradas.

    São a BASE que os cenários 4 (`sla_estourado`), 7 (`pipeline_parado`) e 8
    (`follow_up_insuficiente`) substituem. Sem elas declaradas, o cenário
    perturbado não teria contra o que ser comparado — e o `normal` teria
    operação perfeita, que não existe em conta nenhuma.
    """

    alto_fit_fora_sla: float
    negocios_parados: float
    perdidos_ate_2_toques: float


OPERACAO_BASE: Final[Operacao] = Operacao(
    alto_fit_fora_sla=0.12,
    negocios_parados=0.15,
    perdidos_ate_2_toques=0.15,  # a estratégia já citava estes 15%
)


FUNIL_BASE: Final[Funil] = Funil(
    taxa_lead_qualificado=0.35,
    taxa_qualificado_proposta=0.45,
    taxa_proposta_ganho=0.30,
    toques_ate_perda_mediana=4,
)


@dataclass(frozen=True)
class FaixaFit:
    """Faixa de score_fit: onde começa, quanto do funil ocupa, e o SLA (R3).

    Os três dados moram juntos de propósito — corte, proporção e SLA são a
    mesma decisão, e separá-los faria os três divergirem na primeira alteração.
    """

    nome: str
    score_min: int  # inclusivo; vai até o score_min da faixa acima
    proporcao_leads: float
    sla_minutos: int


# As proporções têm que somar 1,0. `4*60` em vez de 240 porque "quatro horas"
# é a decisão; 240 é só a aritmética dela.
SLA_PRIMEIRO_CONTATO: Final[tuple[FaixaFit, ...]] = (
    FaixaFit(nome="alto", score_min=70, proporcao_leads=0.25, sla_minutos=60),
    FaixaFit(nome="medio", score_min=40, proporcao_leads=0.50, sla_minutos=4 * 60),
    FaixaFit(nome="baixo", score_min=0, proporcao_leads=0.25, sla_minutos=24 * 60),
)


@dataclass(frozen=True)
class DistribuicaoLag:
    """Forma do atraso entre entrada do lead e fechamento.

    Lognormal: o atraso é sempre positivo e assimétrico à direita, e é a cauda
    longa que a ADR 0001 existe para tratar. A mediana varia por conta
    (Conta.lag_mediano_dias); aqui fica só a forma, comum a todas.
    """

    razao_p90_mediana: float
    corte_dias: int


# corte_dias=120 e não 90: a conta de maior ciclo (solar, mediana 42 d) tem
# p90 = 92 d, e cortar em 90 amputaria a cauda abaixo do próprio p90.
# Negócio que não fecha dentro da janela permanece `aberto` — é o insumo da R6.
DISTRIBUICAO_LAG: Final[DistribuicaoLag] = DistribuicaoLag(
    razao_p90_mediana=2.2,
    corte_dias=120,
)


@dataclass(frozen=True)
class Completude:
    """Qualidade de origem do dado no estado NORMAL. Arbitrada."""

    utm_valida: float
    campaign_source_nulo: float
    contato_duplicado: float


# Linha de base que o cenário `origem_perdida` (R8) e a condição
# `dados_incompletos` (R0) perturbam. Nulo aqui é fenômeno, não violação —
# ver docs/contrato-de-dados.md, seção 7.
COMPLETUDE_BASE: Final[Completude] = Completude(
    utm_valida=0.88,
    campaign_source_nulo=0.08,
    contato_duplicado=0.03,
)


@dataclass(frozen=True)
class Ruido:
    """Variação que existe para o dado não sair liso demais."""

    variacao_diaria_amplitude: float  # aplicada como (1 ± amplitude)
    fim_de_semana_mult: float  # MULTIPLICADOR: 0.55 = 55% do volume do dia útil


# fim_de_semana_mult é multiplicador, não desconto — guardar -0.45 deixaria
# ambíguo se a aplicação é (1 + x) ou (1 - x). Queda de 45% => resta 0,55.
# Fim de semana é ARMADILHA, não problema (estratégia, seção 7, armadilha 4).
RUIDO: Final[Ruido] = Ruido(
    variacao_diaria_amplitude=0.18,
    fim_de_semana_mult=0.55,
)
