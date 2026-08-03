"""Constantes da ferramenta Estaca Boa Vista / Chamados."""
from __future__ import annotations

# Alas da Estaca Boa Vista
WARD_STA_CANDIDA = "sta_candida"
WARD_BOA_VISTA = "boa_vista"
WARD_TIMBU = "timbu"
WARD_BACACHERI = "bacacheri"
WARD_JD_ALIANCA = "jd_alianca"

WARDS: list[tuple[str, str]] = [
    (WARD_STA_CANDIDA, "Sta. Cândida"),
    (WARD_BOA_VISTA, "Boa Vista"),
    (WARD_TIMBU, "Timbu"),
    (WARD_BACACHERI, "Bacacheri"),
    (WARD_JD_ALIANCA, "Jd. Aliança"),
]
WARD_SLUGS = frozenset(s for s, _ in WARDS)
WARD_LABELS = {s: lab for s, lab in WARDS}

# Flag is_admin (coluna) — Admin *só da Estaca Boa Vista*; pode coexistir com qualquer role.
# Não eleva tools_all nem acesso a Mercado/Ala/Finanças/Admin Bini.
ESTACA_ADMIN_RANK = 100

# Roles — estaca
ROLE_STAKE_PRESIDENCY = "stake_presidency"
ROLE_HIGH_COUNCIL = "high_council"
ROLE_STAKE_SECRETARY = "stake_secretary"

# Roles — ala
ROLE_BISHOPRIC = "bishopric"
ROLE_BISHOPRIC_SECRETARY = "bishopric_secretary"
ROLE_ELDERS_QUORUM = "elders_quorum_presidency"

STAKE_ROLES = frozenset(
    {ROLE_STAKE_PRESIDENCY, ROLE_HIGH_COUNCIL, ROLE_STAKE_SECRETARY}
)
WARD_ROLES = frozenset(
    {ROLE_BISHOPRIC, ROLE_BISHOPRIC_SECRETARY, ROLE_ELDERS_QUORUM}
)

# Hierarquia: cada líder só cria/edita papéis com rank <= o seu.
# Quem tem is_admin=True usa ESTACA_ADMIN_RANK (cria qualquer papel + exclui).
ROLE_RANKS: dict[str, int] = {
    ROLE_STAKE_PRESIDENCY: 80,
    ROLE_HIGH_COUNCIL: 60,
    ROLE_STAKE_SECRETARY: 60,
    ROLE_BISHOPRIC: 40,
    ROLE_BISHOPRIC_SECRETARY: 20,
    ROLE_ELDERS_QUORUM: 20,
}

ROLES: list[tuple[str, str, str]] = [
    (ROLE_STAKE_PRESIDENCY, "Presidência da estaca", "estaca"),
    (ROLE_HIGH_COUNCIL, "Membro do sumo conselho", "estaca"),
    (ROLE_STAKE_SECRETARY, "Secretário da estaca", "estaca"),
    (ROLE_BISHOPRIC, "Bispado", "ala"),
    (ROLE_BISHOPRIC_SECRETARY, "Secretário do bispado", "ala"),
    (ROLE_ELDERS_QUORUM, "Presidência do quorum de elderes", "ala"),
]
ROLE_SLUGS = frozenset(s for s, _, _ in ROLES)
ROLE_LABELS = {s: lab for s, lab, _ in ROLES}
ROLE_KINDS = {s: kind for s, _, kind in ROLES}


def role_rank(role: str | None) -> int:
    if not role:
        return 0
    return int(ROLE_RANKS.get(role, 0))


def roles_at_or_below(max_rank: int) -> list[tuple[str, str, str]]:
    return [(s, lab, kind) for s, lab, kind in ROLES if ROLE_RANKS.get(s, 0) <= max_rank]

# Fluxo sequencial
STATUS_INDICATION = "indication"
STATUS_HC_SUPPORT = "hc_support"
STATUS_INTERVIEW = "interview"
STATUS_SACRAMENT = "sacrament"
STATUS_DESIGNATION = "designation"
STATUS_REGISTER_SYSTEM = "register_system"
STATUS_COMPLETED = "completed"
STATUS_REJECTED = "rejected"

ACTIVE_STATUSES = (
    STATUS_INDICATION,
    STATUS_HC_SUPPORT,
    STATUS_INTERVIEW,
    STATUS_SACRAMENT,
    STATUS_DESIGNATION,
    STATUS_REGISTER_SYSTEM,
)
HISTORY_STATUSES = (STATUS_COMPLETED, STATUS_REJECTED)

# (status, short label) — ordem visual do dashboard (sem números)
WORKFLOW_STEPS: list[tuple[str, str]] = [
    (STATUS_INDICATION, "Aprovação Presidência da Estaca"),
    (STATUS_HC_SUPPORT, "Apoio do Sumo Conselho"),
    (STATUS_INTERVIEW, "Entrevista"),
    (STATUS_SACRAMENT, "Apoio sacramental"),
    (STATUS_DESIGNATION, "Designação"),
    (STATUS_REGISTER_SYSTEM, "Registrar no Sistema"),
]
STEP_LABELS = {s: lab for s, lab in WORKFLOW_STEPS}
STEP_LABELS[STATUS_COMPLETED] = "Concluído"
STEP_LABELS[STATUS_REJECTED] = "Cancelado"
# Compat: número opcional para timeline antiga
STEP_NUMBERS = {s: i + 1 for i, (s, _) in enumerate(WORKFLOW_STEPS)}

# Ajuda por passo (UI — ícone ?)
WORKFLOW_STEP_HELP: dict[str, str] = {
    STATUS_INDICATION: (
        "A presidência da estaca analisa e aprova a indicação vinda da ala. "
        "Quem executa: Presidência da estaca (ou Admin Estaca)."
    ),
    STATUS_HC_SUPPORT: (
        "O Sumo Conselho dá apoio ao chamado proposto. "
        "Quem executa: Sumo Conselho, secretário da estaca ou presidência."
    ),
    STATUS_INTERVIEW: (
        "Entrevista com o membro indicado para o chamado. "
        "Quem executa: quem for designado responsável, ou líderes da estaca com permissão."
    ),
    STATUS_SACRAMENT: (
        "O chamado é apresentado e apoiado na reunião sacramental da ala. "
        "Quem executa: responsável atribuído ou líderes da estaca com permissão."
    ),
    STATUS_DESIGNATION: (
        "O líder competente designa o membro no chamado. "
        "Quem executa: bispado da ala (sua ala), responsável atribuído, ou líderes da estaca. "
        "Indica-se quem designou para o registo."
    ),
    STATUS_REGISTER_SYSTEM: (
        "Registo oficial da designação no sistema da Igreja (LCR / ferramentas oficiais). "
        "Quem executa: secretários da estaca; a presidência da estaca também pode concluir este passo. "
        "Usa os dados de quem designou e quando."
    ),
}

STATUS_ORDER = [
    STATUS_INDICATION,
    STATUS_HC_SUPPORT,
    STATUS_INTERVIEW,
    STATUS_SACRAMENT,
    STATUS_DESIGNATION,
    STATUS_REGISTER_SYSTEM,
    STATUS_COMPLETED,
]

# Eventos do histórico de processo (UI)
EVENT_CREATED = "created"
EVENT_APPROVE_INDICATION = "approve_indication"
EVENT_APPROVE_HC = "approve_hc"
EVENT_MARK_INTERVIEWED = "mark_interviewed"
EVENT_MARK_SACRAMENT = "mark_sacrament"
EVENT_MARK_DESIGNATED = "mark_designated"
EVENT_MARK_REGISTERED = "mark_registered"
EVENT_CANCEL = "cancel"
EVENT_RESUME = "resume"
EVENT_ASSIGN_INTERVIEW = "assign_interview"
EVENT_ASSIGN_SACRAMENT = "assign_sacrament"
EVENT_ASSIGN_DESIGNATION = "assign_designation"

EVENT_LABELS: dict[str, str] = {
    EVENT_CREATED: "Indicação criada",
    EVENT_APPROVE_INDICATION: "Aprovado pela presidência da estaca",
    EVENT_APPROVE_HC: "Apoiado pelo Sumo Conselho",
    EVENT_MARK_INTERVIEWED: "Entrevista realizada",
    EVENT_MARK_SACRAMENT: "Apoiado na sacramental",
    EVENT_MARK_DESIGNATED: "Designação realizada",
    EVENT_MARK_REGISTERED: "Registado no sistema",
    EVENT_CANCEL: "Indicação cancelada",
    EVENT_RESUME: "Indicação retomada",
    EVENT_ASSIGN_INTERVIEW: "Responsável pela entrevista",
    EVENT_ASSIGN_SACRAMENT: "Responsável pelo apoio sacramental",
    EVENT_ASSIGN_DESIGNATION: "Responsável pela designação",
}

# Passos que aceitam responsável (entrevista / sacramental / designação)
ASSIGNABLE_STEPS = frozenset(
    {STATUS_INTERVIEW, STATUS_SACRAMENT, STATUS_DESIGNATION}
)
ASSIGNEE_FIELD_BY_STEP = {
    STATUS_INTERVIEW: "interview_assignee_id",
    STATUS_SACRAMENT: "sacrament_assignee_id",
    STATUS_DESIGNATION: "designation_assignee_id",
}
ASSIGN_EVENT_BY_STEP = {
    STATUS_INTERVIEW: EVENT_ASSIGN_INTERVIEW,
    STATUS_SACRAMENT: EVENT_ASSIGN_SACRAMENT,
    STATUS_DESIGNATION: EVENT_ASSIGN_DESIGNATION,
}
# Quem pode ser escolhido como responsável
ASSIGNABLE_ROLES = frozenset({ROLE_STAKE_PRESIDENCY, ROLE_HIGH_COUNCIL})
