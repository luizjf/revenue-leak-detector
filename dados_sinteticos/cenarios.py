"""Cenários, condições transversais e armadilhas da geração sintética.

DECLARAÇÃO, como parametros.py: descreve de que faixa sortear, não sorteia.

FRONTEIRA: saber QUAL regra deve disparar é permitido (é o gabarito); saber
COM QUE CORTE ela dispara é proibido. As faixas atravessam o limiar do motor
de propósito — parte dos casos fica acima, parte abaixo. É isso que permite
medir recall em vez de encená-lo.

PROCEDÊNCIA: arbitradas. Ver docs/parametros-e-cenarios.md, seções 1, 2 e 5-7.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


@dataclass(frozen=True)
class Faixa:
    """Intervalo fechado do qual o gerador sorteia a magnitude."""

    minimo: float
    maximo: float

    def __post_init__(self) -> None:
        # frozen permite levantar, só não permite atribuir.
        if self.minimo > self.maximo:
            raise ValueError(f"faixa invertida: {self.minimo} > {self.maximo}")


class NomeCenario(StrEnum):
    """Nome do cenário. Aparece aqui, no gabarito e na matriz de confusão —
    string solta em qualquer um dos três zeraria a precisão daquela regra."""

    NORMAL = "normal"
    CPL_ALTO = "cpl_alto"
    CONVERSAO_CAIU = "conversao_caiu"
    VOLUME_BARATO_SEM_VENDA = "volume_barato_sem_venda"
    SLA_ESTOURADO = "sla_estourado"
    CARO_POREM_SAUDAVEL = "caro_porem_saudavel"
    BARATO_POREM_DESTRUTIVO = "barato_porem_destrutivo"
    PIPELINE_PARADO = "pipeline_parado"
    FOLLOW_UP_INSUFICIENTE = "follow_up_insuficiente"
    ORIGEM_PERDIDA = "origem_perdida"
    MUDANCA_DE_MIX = "mudanca_de_mix"


@dataclass(frozen=True)
class Perturbacao:
    """O que o cenário altera. `None` = não altera.

    O SUFIXO DIZ COMO O NÚMERO É APLICADO:
        *_mult      multiplica a base.  1.30 = +30%   |   0.75 = -25%
        *_delta_pp  soma pontos percentuais.  0.05 = +5 p.p.  |  -0.10 = -10 p.p.
        *_frac      fração de casos que substitui a base.  0.55 = 55% dos casos
    """

    cpl_mult: Faixa | None = None
    leads_mult: Faixa | None = None
    ticket_mult: Faixa | None = None
    taxa_lead_qualificado_mult: Faixa | None = None
    taxa_proposta_ganho_mult: Faixa | None = None
    margem_delta_pp: Faixa | None = None
    migracao_verba_delta_pp: Faixa | None = None
    alto_fit_fora_sla_frac: Faixa | None = None
    negocios_parados_frac: Faixa | None = None
    perdidos_ate_2_toques_frac: Faixa | None = None
    campaign_source_nulo_frac: Faixa | None = None
    utm_valida_frac: Faixa | None = None


@dataclass(frozen=True)
class Cenario:
    """Uma perturbação nomeada. Cada conta recebe um; o gabarito registra qual."""

    nome: NomeCenario
    descricao: str
    perturbacao: Perturbacao
    regras_esperadas: tuple[str, ...]


CENARIOS: Final[Mapping[NomeCenario, Cenario]] = MappingProxyType(
    {
        NomeCenario.NORMAL: Cenario(
            nome=NomeCenario.NORMAL,
            descricao="Sem perturbação. Achado do motor aqui é falso positivo.",
            perturbacao=Perturbacao(),
            regras_esperadas=(),
        ),
        NomeCenario.CPL_ALTO: Cenario(
            nome=NomeCenario.CPL_ALTO,
            descricao="CPL +30% a +70%; conversão, ticket e margem constantes.",
            perturbacao=Perturbacao(cpl_mult=Faixa(1.30, 1.70)),
            regras_esperadas=("R1",),
        ),
        NomeCenario.CONVERSAO_CAIU: Cenario(
            nome=NomeCenario.CONVERSAO_CAIU,
            descricao="Proposta→ganho cai 25% a 50%; CPL constante.",
            # -25% a -50% => resta 0,50 a 0,75 da taxa base.
            perturbacao=Perturbacao(taxa_proposta_ganho_mult=Faixa(0.50, 0.75)),
            regras_esperadas=("R1",),
        ),
        NomeCenario.VOLUME_BARATO_SEM_VENDA: Cenario(
            nome=NomeCenario.VOLUME_BARATO_SEM_VENDA,
            descricao="Lead barato e abundante, mas que não qualifica.",
            perturbacao=Perturbacao(
                cpl_mult=Faixa(0.55, 0.75),  # CPL -25% a -45%
                leads_mult=Faixa(1.40, 1.90),  # leads +40% a +90%
                taxa_lead_qualificado_mult=Faixa(0.40, 0.60),  # -40% a -60%
            ),
            regras_esperadas=("R2",),
        ),
        NomeCenario.SLA_ESTOURADO: Cenario(
            nome=NomeCenario.SLA_ESTOURADO,
            descricao="45% a 80% dos leads de alto fit não contatados no SLA.",
            perturbacao=Perturbacao(alto_fit_fora_sla_frac=Faixa(0.45, 0.80)),
            regras_esperadas=("R3",),
        ),
        NomeCenario.CARO_POREM_SAUDAVEL: Cenario(
            nome=NomeCenario.CARO_POREM_SAUDAVEL,
            descricao="CPL sobe, ticket e margem sobem mais. O payback melhorou.",
            perturbacao=Perturbacao(
                cpl_mult=Faixa(1.25, 1.50),
                ticket_mult=Faixa(1.40, 1.90),
                margem_delta_pp=Faixa(0.05, 0.12),  # +5 a +12 p.p.
            ),
            regras_esperadas=("R4",),
        ),
        NomeCenario.BARATO_POREM_DESTRUTIVO: Cenario(
            nome=NomeCenario.BARATO_POREM_DESTRUTIVO,
            descricao="CPL cai, mas ticket e margem caem mais. Não paga a aquisição.",
            perturbacao=Perturbacao(
                cpl_mult=Faixa(0.60, 0.80),  # CPL -20% a -40%
                ticket_mult=Faixa(0.45, 0.70),  # ticket -30% a -55%
                margem_delta_pp=Faixa(-0.20, -0.10),  # NEGATIVO: -10 a -20 p.p.
            ),
            regras_esperadas=("R5",),
        ),
        NomeCenario.PIPELINE_PARADO: Cenario(
            nome=NomeCenario.PIPELINE_PARADO,
            descricao="35% a 70% dos negócios abertos parados além do SLA do estágio.",
            perturbacao=Perturbacao(negocios_parados_frac=Faixa(0.35, 0.70)),
            regras_esperadas=("R6",),
        ),
        NomeCenario.FOLLOW_UP_INSUFICIENTE: Cenario(
            nome=NomeCenario.FOLLOW_UP_INSUFICIENTE,
            descricao="Perdidos com 0 a 2 toques sobem de 15% para 55% a 85%.",
            perturbacao=Perturbacao(perdidos_ate_2_toques_frac=Faixa(0.55, 0.85)),
            regras_esperadas=("R7",),
        ),
        NomeCenario.ORIGEM_PERDIDA: Cenario(
            nome=NomeCenario.ORIGEM_PERDIDA,
            descricao="campaign_source nulo sobe de 8% para 30% a 60%.",
            perturbacao=Perturbacao(campaign_source_nulo_frac=Faixa(0.30, 0.60)),
            regras_esperadas=("R8",),
        ),
        NomeCenario.MUDANCA_DE_MIX: Cenario(
            nome=NomeCenario.MUDANCA_DE_MIX,
            descricao=(
                "Verba migra 50 a 75 p.p. entre campanhas. O agregado sobe e "
                "NENHUMA campanha piora — paradoxo de Simpson, ADR 0003."
            ),
            # cpl_mult fica None de propósito: se alguma campanha piorasse,
            # deixaria de ser Simpson e viraria R1 legítima.
            perturbacao=Perturbacao(migracao_verba_delta_pp=Faixa(0.50, 0.75)),
            regras_esperadas=("R10",),
        ),
    }
)


class NomeCondicao(StrEnum):
    DADOS_INCOMPLETOS = "dados_incompletos"
    AMOSTRA_PEQUENA = "amostra_pequena"


@dataclass(frozen=True)
class CondicaoTransversal:
    """Estado do dado que se SOBREPÕE a qualquer cenário, sem substituí-lo.
    É o que produz os cenários triplos da etapa 3.6."""

    nome: NomeCondicao
    descricao: str
    perturbacao: Perturbacao
    regras_esperadas: tuple[str, ...]


CONDICOES_TRANSVERSAIS: Final[Mapping[NomeCondicao, CondicaoTransversal]] = MappingProxyType(
    {
        NomeCondicao.DADOS_INCOMPLETOS: CondicaoTransversal(
            nome=NomeCondicao.DADOS_INCOMPLETOS,
            descricao="Cobertura de UTM cai para 60% a 78% — abaixo do aceitável.",
            perturbacao=Perturbacao(utm_valida_frac=Faixa(0.60, 0.78)),
            regras_esperadas=("R0",),
        ),
        NomeCondicao.AMOSTRA_PEQUENA: CondicaoTransversal(
            nome=NomeCondicao.AMOSTRA_PEQUENA,
            descricao="Volume cai para 15% a 35% do base; nada é distinguível de ruído.",
            perturbacao=Perturbacao(leads_mult=Faixa(0.15, 0.35)),
            regras_esperadas=("R99",),
        ),
    }
)


@dataclass(frozen=True)
class Armadilha:
    """Dado que PARECE problema e não é. Resposta correta: silêncio.

    `regras_esperadas` é sempre vazio — é o que a distingue de um cenário.
    `mecanismo` preenchido significa que o gerador a implementa por estrutura
    (quando as coisas acontecem), não por magnitude.
    """

    nome: str
    descricao: str
    perturbacao: Perturbacao = Perturbacao()
    mecanismo: str = ""
    regras_esperadas: tuple[str, ...] = ()


ARMADILHAS: Final[Mapping[str, Armadilha]] = MappingProxyType(
    {
        "mix_de_campanha": Armadilha(
            nome="mix_de_campanha",
            descricao="CAC agregado sobe, mas nenhuma campanha piorou: a verba migrou (ADR 0003).",
            perturbacao=Perturbacao(migracao_verba_delta_pp=Faixa(0.50, 0.75)),
        ),
        "caro_porem_saudavel": Armadilha(
            nome="caro_porem_saudavel",
            descricao="CAC sobe 40%, mas a margem sobe mais. Pausar destruiria a "
            "campanha mais lucrativa.",
            perturbacao=Perturbacao(
                cpl_mult=Faixa(1.25, 1.50),
                ticket_mult=Faixa(1.40, 1.90),
                margem_delta_pp=Faixa(0.05, 0.12),
            ),
        ),
        "reposicionamento_de_ticket": Armadilha(
            nome="reposicionamento_de_ticket",
            descricao="Ticket sobe 60% a 120% e o volume cai. Decisão comercial "
            "deliberada — o CAC sobe por desenho, não por falha.",
            perturbacao=Perturbacao(
                ticket_mult=Faixa(1.60, 2.20),
                leads_mult=Faixa(0.50, 0.75),
            ),
        ),
        "outlier_de_ticket": Armadilha(
            nome="outlier_de_ticket",
            descricao="Um único negócio muito grande desloca a média; a mediana não se move.",
            mecanismo="Injetar um negócio ganho com valor de 8x a 15x o ticket base.",
        ),
        "sazonalidade_semanal": Armadilha(
            nome="sazonalidade_semanal",
            descricao="Queda de 45% em leads e custo no fim de semana. Acontece "
            "toda semana, inclusive no baseline.",
            mecanismo="Já é comportamento base: parametros.RUIDO.fim_de_semana_mult.",
        ),
        "campanha_sem_historico": Armadilha(
            nome="campanha_sem_historico",
            descricao="Campanha nasce dentro do período analisado. Não há baseline "
            "— comparar é inventar.",
            mecanismo="Iniciar uma campanha no primeiro dia do período analisado.",
        ),
        "janela_com_feriado": Armadilha(
            nome="janela_com_feriado",
            descricao="3 a 5 dias com queda de 60% a 80%. O período tem menos dias "
            "úteis, não menos eficiência.",
            mecanismo="Zerar parcialmente 3 a 5 dias consecutivos do período.",
        ),
    }
)
