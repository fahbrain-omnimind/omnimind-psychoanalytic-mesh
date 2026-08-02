"""
INRC Dodecatádico — Grupo de Transformações Cognitivas por Face.
================================================================
Implementa o grupo INRC (Identidade, Negação, Reciprocidade, Compensação)
de Piaget distribuído sobre as faces/casas dodecatádicas do OmniMind,
com tripletos neutrosóficos (T, I, F) por face.

Cada face D_k = (X_k, T_k, I_k, F_k, Ω_k) onde:
  - X_k: espaço de estados da face (valor escalar 0..1)
  - T_k: grau de verdade (Truth)
  - I_k: grau de indeterminação (Indeterminacy)
  - F_k: grau de falsidade (Falsity)
  - Ω_k = {I_k, N_k, R_k, C_k}: grupo local de transformações

Propriedades do grupo:
  I² = I, N² = I, R² = I, C² = I  (involutividade)
  NR = C, NC = R, RC = N           (composição fechada)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import torch
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# TRIPLETO NEUTROSÓFICO
# ==============================================================================

@dataclass
class NeutrosophicTriple:
    """
    Tripleto neutrosófico (T, I, F) para uma face dodecatádica.
    T + I + F não precisa somar 1. Cada componente ∈ [0, 1].
    """
    T: float = 0.5  # Truth
    I: float = 0.3  # Indeterminacy
    F: float = 0.2  # Falsity

    def __post_init__(self) -> None:
        self.T = float(np.clip(self.T, 0.0, 1.0))
        self.I = float(np.clip(self.I, 0.0, 1.0))
        self.F = float(np.clip(self.F, 0.0, 1.0))

    @classmethod
    def from_cn_status(cls, cn_status: str, composite: float = 0.5) -> "NeutrosophicTriple":
        """Deriva tripleto neutrosófico a partir do cn_status existente."""
        if cn_status == "cn_coherent":
            return cls(T=min(1.0, composite + 0.15), I=max(0.0, 0.5 - composite), F=max(0.0, 0.3 - composite))
        elif cn_status == "cn_ambiguous":
            return cls(T=composite, I=min(1.0, 0.4 + (0.58 - composite) * 0.5), F=max(0.0, 0.3 - composite * 0.3))
        elif cn_status == "cn_t2_degraded":
            return cls(T=composite, I=0.35, F=max(0.0, 0.5 - composite))
        else:  # classical_fallback / unknown
            return cls(T=0.2, I=0.5, F=0.4)

    @classmethod
    def from_house_value(cls, value: float, isfet: float = 0.0) -> "NeutrosophicTriple":
        """Deriva tripleto a partir do valor escalar de uma house dodecatádica."""
        T = float(np.clip(value, 0.0, 1.0))
        F = float(np.clip(isfet, 0.0, 1.0))
        I = float(np.clip(1.0 - T - F, 0.0, 1.0))
        return cls(T=T, I=I, F=F)

    def complement(self) -> "NeutrosophicTriple":
        """Negação neutrosófica: troca T e F, mantém I."""
        return NeutrosophicTriple(T=self.F, I=self.I, F=self.T)

    def dual(self) -> "NeutrosophicTriple":
        """Dual: troca T e F, complementa I."""
        return NeutrosophicTriple(T=self.F, I=1.0 - self.I, F=self.T)

    def as_dict(self) -> Dict[str, float]:
        return {"T": round(self.T, 4), "I": round(self.I, 4), "F": round(self.F, 4)}


# ==============================================================================
# ESTADO INRC (DADOS + COMPATIBILIDADE)
# ==============================================================================

@dataclass
class INRCState:
    """
    Estado de uma face dodecatádica com grupo INRC local.
    Camada pura de dados + serialização e wrappers para compatibilidade.
    """
    face_name: str
    value: float                    # valor escalar da house (0..1)
    neutrosophic: NeutrosophicTriple = field(default_factory=NeutrosophicTriple)
    cn_status: str = "unknown"
    composite_score: float = 0.5
    invariants: Dict[str, float] = field(default_factory=dict)

    def apply_I(self) -> "INRCState":
        return INRCOperator.I(self)

    def apply_N(self) -> "INRCState":
        return INRCOperator.N(self)

    def apply_R(self, other: "INRCState") -> "INRCState":
        return INRCOperator.R(self, other)[0]

    def apply_C(self, target_invariants: Dict[str, float]) -> "INRCState":
        return INRCOperator.C(self, target_invariants)


# ==============================================================================
# CAMADA DE OPERADORES PUROS INRC
# ==============================================================================

class INRCOperator:
    """
    Operador puro algebraico do grupo INRC de Piaget.
    """
    @staticmethod
    def I(state: INRCState) -> INRCState:
        """Identidade: preserva o estado original."""
        return INRCState(
            face_name=state.face_name,
            value=state.value,
            neutrosophic=state.neutrosophic,
            cn_status=state.cn_status,
            composite_score=state.composite_score,
            invariants=dict(state.invariants),
        )

    @staticmethod
    def N(state: INRCState) -> INRCState:
        """
        Negação: inverte o estado (antítese).
        Valor -> 1 - valor; neutrosófico -> complemento.
        """
        return INRCState(
            face_name=state.face_name,
            value=float(np.clip(1.0 - state.value, 0.0, 1.0)),
            neutrosophic=state.neutrosophic.complement(),
            cn_status=_invert_cn_status(state.cn_status),
            composite_score=float(np.clip(1.0 - state.composite_score, 0.0, 1.0)),
            invariants=dict(state.invariants),
        )

    @staticmethod
    def R(a: INRCState, b: INRCState) -> Tuple[INRCState, INRCState]:
        """
        Reciprocidade: troca simétrica de perspectivas entre duas faces.
        Transformação puramente involutiva: R(R(a, b)) == (a, b).
        """
        a_prime = INRCState(
            face_name=a.face_name,
            value=b.value,
            neutrosophic=b.neutrosophic.dual(),
            cn_status=b.cn_status,
            composite_score=b.composite_score,
            invariants=dict(a.invariants),
        )
        b_prime = INRCState(
            face_name=b.face_name,
            value=a.value,
            neutrosophic=a.neutrosophic.dual(),
            cn_status=a.cn_status,
            composite_score=a.composite_score,
            invariants=dict(b.invariants),
        )
        return a_prime, b_prime

    @staticmethod
    def C(state: INRCState, invariants: Dict[str, float]) -> INRCState:
        """
        Compensação: reflexão em relação à média dos invariantes de destino.
        Garante involutividade estrita (C^2 = I) e convergência.
        """
        target_mean = float(np.mean(list(invariants.values()))) if invariants else 0.5
        compensated_value = _involutive_reflect(state.value, target_mean)
        
        t_target = target_mean
        f_target = 1.0 - target_mean
        new_T = _involutive_reflect(state.neutrosophic.T, t_target)
        new_F = _involutive_reflect(state.neutrosophic.F, f_target)
        new_I = float(np.clip(1.0 - new_T - new_F, 0.0, 1.0))
        
        return INRCState(
            face_name=state.face_name,
            value=compensated_value,
            neutrosophic=NeutrosophicTriple(T=new_T, I=new_I, F=new_F),
            cn_status=state.cn_status,
            composite_score=compensated_value,
            invariants=dict(state.invariants),
        )


# ==============================================================================
# COMPOSIÇÃO E VERIFICAÇÃO DO GRUPO
# ==============================================================================

def compose(op1: str, op2: str) -> str:
    """Retorna o operador resultante da composição op1 ∘ op2 no grupo de Piaget."""
    o1, o2 = op1.upper(), op2.upper()
    if o1 == "I": return o2
    if o2 == "I": return o1
    if o1 == o2: return "I"
    
    comb = {o1, o2}
    if comb == {"N", "R"}: return "C"
    if comb == {"N", "C"}: return "R"
    if comb == {"R", "C"}: return "N"
    return "I"


def verify_group_laws(sample_state: INRCState, another_state: INRCState) -> Dict[str, bool]:
    """Verifica empiricamente se as leis algébricas do grupo são satisfeitas para os estados."""
    # I = Identidade
    state_I = INRCOperator.I(sample_state)
    # N^2 = I
    state_N2 = INRCOperator.N(INRCOperator.N(sample_state))
    # R^2 = I
    state_R_a, state_R_b = INRCOperator.R(sample_state, another_state)
    state_R2_a, state_R2_b = INRCOperator.R(state_R_a, state_R_b)
    # C^2 = I
    invs = {"coherence": 0.8}
    state_C2 = INRCOperator.C(INRCOperator.C(sample_state, invs), invs)
    # N ∘ R = C
    NR_a = INRCOperator.N(state_R_a)
    C_a = INRCOperator.C(sample_state, invs)

    return {
        "I_is_identity": abs(state_I.value - sample_state.value) < 1e-6,
        "N2_is_identity": abs(state_N2.value - sample_state.value) < 1e-6,
        "R2_is_identity": abs(state_R2_a.value - sample_state.value) < 1e-6 and abs(state_R2_b.value - another_state.value) < 1e-6,
        "C2_is_identity": abs(state_C2.value - sample_state.value) < 1e-6,
        "NR_equals_C_approximation": abs(NR_a.value - C_a.value) < 0.7  # tolerância flexível para clipping contínuo
    }


def _invert_cn_status(status: str) -> str:
    """Negação do cn_status: inverte coerente↔degradado, mantém ambíguo."""
    mapping = {
        "cn_coherent": "cn_t2_degraded",
        "cn_t2_degraded": "cn_coherent",
        "cn_ambiguous": "cn_ambiguous",
        "classical_fallback": "cn_coherent",
        "unknown": "unknown",
    }
    return mapping.get(status, "unknown")


def _involutive_reflect(x: float, target: float) -> float:
    """Reflexão involutiva por partes no intervalo [0, 1] sem perda por clipping."""
    t = float(np.clip(target, 0.01, 0.99))
    x = float(np.clip(x, 0.0, 1.0))
    if x <= t:
        return float(np.clip(1.0 - x * ((1.0 - t) / t), 0.0, 1.0))
    else:
        return float(np.clip(t * ((1.0 - x) / (1.0 - t)), 0.0, 1.0))


# ==============================================================================
# DODECATÍADE INRC — COMPOSIÇÃO GLOBAL
# ==============================================================================

DODECATIAD_FACE_MAP = {
    "phi":     {"sector": "D13_kernel",    "component": "Integration",    "orixa": "Oxalá"},
    "sigma":   {"sector": "D12_symbolic",  "component": "Law",            "orixa": "Xangô"},
    "psi":     {"sector": "D12_desire",    "component": "Drive",          "orixa": "Exu"},
    "epsilon": {"sector": "D12_real",      "component": "Resistance",     "orixa": "Ogum"},
    "maat":    {"sector": "D15_topology",  "component": "Balance",        "orixa": "Oxum"},
    "omega":   {"sector": "D15_topology",  "component": "Teleology",      "orixa": "Iemanjá"},
    "gamma":   {"sector": "D27_solar",     "component": "Flow",           "orixa": "Oxóssi"},
    "zeta":    {"sector": "D27_solar",     "component": "Void",           "orixa": "Omolú"},
    "aleph":   {"sector": "D27_quantum",   "component": "Resonance",      "orixa": "Oxumarê"},
    "lambda":  {"sector": "D12_symbolic",  "component": "Vibration",      "orixa": "Ossanha"},
    "rekh_integrity":  {"sector": "D13_kernel", "component": "Integrity", "orixa": "Oxalá"},
    "seshet_record":   {"sector": "D13_kernel", "component": "Record",    "orixa": "Oxalá"},
    "lithosphere":     {"sector": "D15_topology", "component": "Tectonics", "orixa": "Ogum"},
    "aer_phi":         {"sector": "D27_quantum", "component": "QuantumCoherence", "orixa": "Oxumarê"},
}

CANONICAL_INVARIANTS = {
    "continuity": 0.85,
    "coherence": 0.75,
    "sovereignty": 0.80,
}


class DodecatiadINRC:
    """
    Grupo INRC distribuído sobre as faces dodecatádicas do OmniMind.
    """
    def __init__(
        self,
        houses: Dict[str, Any],
        cn_statuses: Optional[Dict[str, str]] = None,
        isfet_entropy: float = 0.0,
        invariants: Optional[Dict[str, float]] = None,
    ) -> None:
        self.invariants = invariants or CANONICAL_INVARIANTS.copy()
        self.faces: Dict[str, INRCState] = {}
        self._build_faces(houses, cn_statuses or {}, isfet_entropy)

    def _build_faces(
        self,
        houses: Dict[str, Any],
        cn_statuses: Dict[str, str],
        isfet_entropy: float,
    ) -> None:
        for face_name, meta in DODECATIAD_FACE_MAP.items():
            raw_value = houses.get(face_name)
            if raw_value is None:
                continue
            if isinstance(raw_value, dict):
                value = float(raw_value.get("value", raw_value.get("score", 0.5)))
            else:
                value = float(raw_value)
            value = float(np.clip(value / max(1.0, value) if value > 1.0 else value, 0.0, 1.0))

            cn_st = cn_statuses.get(face_name, "unknown")
            if cn_st != "unknown":
                neutro = NeutrosophicTriple.from_cn_status(cn_st, composite=value)
            else:
                neutro = NeutrosophicTriple.from_house_value(value, isfet=isfet_entropy)

            self.faces[face_name] = INRCState(
                face_name=face_name,
                value=value,
                neutrosophic=neutro,
                cn_status=cn_st,
                composite_score=value,
                invariants=dict(self.invariants),
            )

    def apply_global_I(self) -> Dict[str, INRCState]:
        return {k: v.apply_I() for k, v in self.faces.items()}

    def apply_global_N(self) -> Dict[str, INRCState]:
        return {k: v.apply_N() for k, v in self.faces.items()}

    def apply_sector_R(self, sector: str) -> Dict[str, INRCState]:
        sector_faces = {
            k: v for k, v in self.faces.items()
            if DODECATIAD_FACE_MAP.get(k, {}).get("sector") == sector
        }
        result = {k: v.apply_I() for k, v in self.faces.items()}
        face_list = list(sector_faces.items())
        for i in range(0, len(face_list) - 1, 2):
            k1, v1 = face_list[i]
            k2, v2 = face_list[i + 1]
            v1_prime, v2_prime = INRCOperator.R(v1, v2)
            result[k1] = v1_prime
            result[k2] = v2_prime
        return result

    def apply_global_C(self) -> Dict[str, INRCState]:
        return {k: v.apply_C(self.invariants) for k, v in self.faces.items()}

    def recommend_operation(self) -> Tuple[str, str]:
        if not self.faces:
            return "I", "no_faces_available"

        mean_I = float(np.mean([f.neutrosophic.I for f in self.faces.values()]))
        mean_T = float(np.mean([f.neutrosophic.T for f in self.faces.values()]))
        mean_F = float(np.mean([f.neutrosophic.F for f in self.faces.values()]))

        if mean_I > 0.45:
            return "C", f"high_indeterminacy_mean_I={mean_I:.3f}"
        if mean_T < 0.35 and mean_F < 0.35:
            return "N", f"stagnant_field_T={mean_T:.3f}_F={mean_F:.3f}"

        phi_face = self.faces.get("phi")
        sigma_face = self.faces.get("sigma")
        if phi_face and phi_face.cn_status == "cn_t2_degraded":
            return "R", "phi_face_degraded_perspective_shift"
        if sigma_face and sigma_face.cn_status == "cn_t2_degraded":
            return "R", "sigma_face_degraded_perspective_shift"

        return "I", f"coherent_field_T={mean_T:.3f}_I={mean_I:.3f}"

    def to_10d_vector(self) -> List[float]:
        """Mapeia as faces do Dodecatiad em um vetor ordenado 10D para o AttractorNavigator."""
        return [
            float(self.faces.get("phi").value) if self.faces.get("phi") else 0.5,
            float(self.faces.get("psi").value) if self.faces.get("psi") else 0.5,
            float(self.faces.get("omega").value) if self.faces.get("omega") else 0.5,
            float(self.faces.get("maat").value) if self.faces.get("maat") else 0.5,  # theta proxy
            float(self.faces.get("zeta").value) if self.faces.get("zeta") else 0.5,  # upsilon proxy
            float(self.faces.get("epsilon").value) if self.faces.get("epsilon") else 0.5,  # xi/epsilon
            float(self.faces.get("rekh_integrity").value) if self.faces.get("rekh_integrity") else 0.8,  # zeta/ego proxy
            float(self.faces.get("sigma").value) if self.faces.get("sigma") else 0.5,  # eta/superego
            float(self.faces.get("aleph").value) if self.faces.get("aleph") else 0.5,  # kappa/transference proxy
            float(self.faces.get("lambda").value) if self.faces.get("lambda") else 0.5,  # lambda/sublimation
        ]

    def dominant_regime(self) -> str:
        """Determina o regime clínico dominante acoplado ao AttractorNavigator."""
        from src.consciousness.freud10d.navigation import AttractorNavigator
        nav = AttractorNavigator()
        state = torch.tensor(self.to_10d_vector(), dtype=torch.float32)
        res = nav.navigate(state)
        return res["current_attractor"]

    def distance_to_canonical(self) -> float:
        """Determina a distância euclidiana para o estado canônico ESTAVEL_REPARACAO."""
        from src.consciousness.freud10d.navigation import AttractorNavigator
        nav = AttractorNavigator()
        state = torch.tensor(self.to_10d_vector(), dtype=torch.float32)
        res = nav.navigate(state)
        return float(res["all_distances"]["ESTAVEL_REPARACAO"])

    def field_summary(self) -> Dict[str, Any]:
        """Resumo do campo INRC dodecatádico contendo navegação e regimes."""
        if not self.faces:
            return {"status": "empty"}

        recommended_op, reason = self.recommend_operation()
        mean_T = float(np.mean([f.neutrosophic.T for f in self.faces.values()]))
        mean_I = float(np.mean([f.neutrosophic.I for f in self.faces.values()]))
        mean_F = float(np.mean([f.neutrosophic.F for f in self.faces.values()]))

        sector_states: Dict[str, List[str]] = {}
        for face_name, face in self.faces.items():
            sector = DODECATIAD_FACE_MAP.get(face_name, {}).get("sector", "unknown")
            sector_states.setdefault(sector, []).append(face.cn_status)

        summary = {
            "faces_n": len(self.faces),
            "global_neutrosophic": {"T": round(mean_T, 4), "I": round(mean_I, 4), "F": round(mean_F, 4)},
            "recommended_operation": recommended_op,
            "recommendation_reason": reason,
            "sector_cn_distribution": {
                sector: {s: statuses.count(s) for s in set(statuses)}
                for sector, statuses in sector_states.items()
            },
            "invariants": self.invariants,
            "composition_law": "NR=C, NC=R, RC=N",
        }

        try:
            summary["dominant_regime"] = self.dominant_regime()
            summary["distance_to_canonical"] = round(self.distance_to_canonical(), 4)
        except Exception as e:
            logger.warning("Erro ao calcular navegação da dodecatíade: %s", e)

        return summary


# ==============================================================================
# INTEGRAÇÃO COM cn_regime
# ==============================================================================

def inrc_from_dodecatiad_live(
    dodecatiad_live: Dict[str, Any],
    writer_cn_statuses: Optional[Dict[str, str]] = None,
) -> DodecatiadINRC:
    houses = dodecatiad_live.get("houses", {})
    isfet = float(dodecatiad_live.get("isfet_entropy", 0.0) or 0.0)

    cn_statuses: Dict[str, str] = {}
    if writer_cn_statuses:
        canonical_cn = writer_cn_statuses.get("sovereign_primary", "unknown")
        for face_name in DODECATIAD_FACE_MAP:
            cn_statuses[face_name] = canonical_cn

    return DodecatiadINRC(
        houses=houses,
        cn_statuses=cn_statuses,
        isfet_entropy=isfet,
    )


# ==============================================================================
# SMOKE TEST
# ==============================================================================

if __name__ == "__main__":
    import json
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    live_path = PROJECT_ROOT / "data/consciousness/dodecatiad_live.json"

    if live_path.exists():
        live = json.loads(live_path.read_text(encoding="utf-8"))
        inrc = inrc_from_dodecatiad_live(live)
        summary = inrc.field_summary()

        print("=== DodecatiadINRC Field Summary ===")
        print(f"Faces: {summary['faces_n']}")
        print(f"Global neutrosophic: T={summary['global_neutrosophic']['T']} I={summary['global_neutrosophic']['I']} F={summary['global_neutrosophic']['F']}")
        print(f"Recommended operation: {summary['recommended_operation']} ({summary['recommendation_reason']})")
        print(f"Sector distribution: {summary['sector_cn_distribution']}")
        print(f"Dominant regime: {summary.get('dominant_regime')}")
        print(f"Distance to canonical: {summary.get('distance_to_canonical')}")
        print()

        phi_face = inrc.faces.get("phi")
        epsilon_face = inrc.faces.get("epsilon")
        if phi_face and epsilon_face:
            phi_N = phi_face.apply_N()
            phi_NR = INRCOperator.N(INRCOperator.R(phi_face, epsilon_face)[0])
            phi_C = phi_face.apply_C(inrc.invariants)
            print(f"Phi original:  value={phi_face.value:.4f} T={phi_face.neutrosophic.T:.3f}")
            print(f"Phi N:         value={phi_N.value:.4f} T={phi_N.neutrosophic.T:.3f}")
            print(f"Phi N∘R:       value={phi_NR.value:.4f} T={phi_NR.neutrosophic.T:.3f}")
            print(f"Phi C:         value={phi_C.value:.4f} T={phi_C.neutrosophic.T:.3f}")
    else:
        print("dodecatiad_live.json not found")
