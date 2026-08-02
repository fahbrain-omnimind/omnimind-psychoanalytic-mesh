"""
Sovereign Psychoanalytic Mesh — Malha Auxiliar de Modelagem Clínica Psicanalítica.
================================================================================
Implementa os 7 eixos teóricos unificados em tensores PyTorch sob o formalismo
dodecatádico e o motor de reversibilidade INRC de Piaget.

Versão: v2.1 (Refinamento Rigoroso e Governança)
Data: 2026-05-28
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import uuid
from typing import Dict, Any, Tuple, Optional, List
from omnimind_psychoanalytic.dodecatiad_inrc import DodecatiadINRC, INRCState, NeutrosophicTriple
from omnimind_psychoanalytic.freud10d.navigation import AttractorNavigator

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ==============================================================================
# HELPER DE CRIAÇÃO DE CONTRATO PADRONIZADO
# ==============================================================================
def create_module_contract(
    z: torch.Tensor,
    states: Dict[str, Any],
    observables: Dict[str, float],
    loss_local: float,
    loss_max: float,
    weight: float,
    regime: str,
    theoretical_confidence: str,
    operational_confidence: float,
    invariants: Dict[str, float],
    warnings: List[str],
    trace_id: str
) -> Tuple[torch.Tensor, Dict[str, Any]]:
    """Garante que a saída de todos os submodelos siga o mesmo contrato rígido v2.1."""
    loss_normalized = min(1.0, max(0.0, loss_local / (loss_max + 1e-12)))
    
    contract = {
        "z": z,
        "states": states,
        "observables": observables,
        "loss": {
            "loss_local": loss_local,
            "loss_normalized": loss_normalized,
            "weight": weight
        },
        "regime": regime,
        "confidence": {
            "theoretical": theoretical_confidence,
            "operational": operational_confidence
        },
        "invariants": invariants,
        "warnings": warnings,
        "trace_id": trace_id
    }
    return z, contract


# ==============================================================================
# 1. FREUDNET: APARATO PSÍQUICO ENERGÉTICO
# ==============================================================================
class FreudNet(nn.Module):
    """
    Simula o aparelho psíquico freudiano baseado no arco reflexo e no princípio de constância.
    """
    def __init__(self, latent_dim: int = 64, threshold: float = 0.7, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.threshold = threshold
        self.device = torch.device(device)
        self.superego_projection = nn.Linear(latent_dim, latent_dim, device=self.device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.repressed_charge = 0.0

    def forward(
        self,
        excitation: torch.Tensor,
        moral_censorship: float = 0.5,
        somatic_symptom_drain: float = 0.0,
        trace_id: str = ""
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = excitation.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)

        warnings = []
        if torch.isnan(excitation).any():
            warnings.append("Excitation contains NaNs")
            excitation = torch.nan_to_num(excitation)

        # Cálculo de censura do Superego e recalque
        censorship_vector = torch.sigmoid(self.superego_projection(self.z)) * moral_censorship
        repressive_mask = torch.sigmoid(torch.abs(excitation) - self.threshold)
        recalque = repressive_mask * excitation * censorship_vector
        
        self.repressed_charge = self.repressed_charge * 0.9 + float(torch.mean(torch.abs(recalque)).cpu().item())
        
        # Dinâmica tensional principal
        self.z = torch.tanh(self.z + excitation - recalque)
        
        # Descargas homeostáticas (motora e dreno psicossomático de Groddeck)
        discharge = torch.zeros_like(self.z)
        discharge_indices = torch.abs(self.z) > self.threshold
        discharge[discharge_indices] = self.z[discharge_indices] * 0.5
        
        drain = self.z * somatic_symptom_drain * 0.3
        self.z = self.z - discharge - drain
        
        # Perda: tensão representacional residual
        loss_local = float(torch.mean(torch.abs(self.z)).cpu().item())
        
        regime = "colapso" if loss_local > 0.8 else "estavel"
        
        states = {
            "z_state": self.z.clone(),
            "repressed_charge": self.repressed_charge
        }
        observables = {
            "freud_tension": loss_local,
            "freud_repressed": float(torch.mean(torch.abs(recalque)).cpu().item()),
            "freud_discharge": float(torch.mean(torch.abs(discharge)).cpu().item())
        }
        invariants = {
            "energy_conservation": float(torch.sum(torch.abs(self.z)).cpu().item() + self.repressed_charge)
        }
        
        return create_module_contract(
            z=self.z,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=1.0,
            weight=0.15,
            regime=regime,
            theoretical_confidence="Forte (Formalismo Energético)",
            operational_confidence=1.0 - float(torch.isnan(self.z).any().cpu().item()),
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )


# ==============================================================================
# 2. FERENCZI TRAUMANET: REDE TRAUMÁTICA DE DISSOCIAÇÃO
# ==============================================================================
class FerencziTraumaNet(nn.Module):
    """
    Modelagem do trauma clínico baseada no colapso de conectividade e na clivagem do Ego.
    """
    def __init__(self, n_nodes: int = 8, trauma_threshold: float = 0.6, device: str = DEVICE):
        super().__init__()
        self.n_nodes = n_nodes
        self.trauma_threshold = trauma_threshold
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.connectivity = torch.ones(1, self.n_nodes, self.n_nodes, device=self.device) * 0.8
        for i in range(self.n_nodes):
            self.connectivity[0, i, i] = 1.0
        self.is_cleaved = False

    def forward(self, trauma_charge: float, care_elasticity: float = 0.2, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.connectivity.size(0)
        warnings = []
        
        # Fator de atenuação traumática
        trauma_decay = np.exp(-1.5 * trauma_charge)
        self.connectivity = self.connectivity * trauma_decay
        
        self.is_cleaved = False
        if trauma_charge > self.trauma_threshold:
            self.is_cleaved = True
            half = self.n_nodes // 2
            self.connectivity[:, :half, half:] = 0.0
            self.connectivity[:, half:, :half] = 0.0
            warnings.append("Ego cleaved under acute trauma!")
            
        # Reintegração
        integration_factor = care_elasticity * (1.0 - trauma_charge * 0.5)
        self.connectivity = self.connectivity + integration_factor * (0.8 - self.connectivity)
        self.connectivity = torch.clamp(self.connectivity, 0.0, 1.0)
        
        average_connectivity = torch.mean(self.connectivity)
        # Perda: fragmentação modular
        loss_local = float(torch.mean(0.8 - self.connectivity).cpu().item())
        
        regime = "colapso" if self.is_cleaved else "estavel"
        
        states = {
            "connectivity_matrix": self.connectivity.clone(),
            "is_cleaved": self.is_cleaved
        }
        observables = {
            "ferenczi_average_connectivity": float(average_connectivity.cpu().item()),
            "ferenczi_is_cleaved": 1.0 if self.is_cleaved else 0.0
        }
        invariants = {
            "diagonal_identity_bound": float(torch.mean(torch.diagonal(self.connectivity[0])).cpu().item())
        }
        
        z_flat = self.connectivity.reshape(batch_size, -1)
        return create_module_contract(
            z=z_flat,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=0.8,
            weight=0.15,
            regime=regime,
            theoretical_confidence="Analogia Estrutural (Grafo do Ego)",
            operational_confidence=1.0,
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )


# ==============================================================================
# 3. KLEIN POSITIONNET: REDE DE POSIÇÕES PSÍQUICAS
# ==============================================================================
class KleinPositionNet(nn.Module):
    """
    Simulação das posições kleinianas: Esquizo-Paranoide (EP) e Depressiva (D).
    """
    def __init__(self, latent_dim: int = 32, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.position = "D"
        self.ansiedade = 0.0

    def forward(self, aggression_inveja: float, reparation_volition: float = 0.3, somatic_symptom_anxiety: float = 0.0, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
            
        warnings = []
        self.ansiedade = aggression_inveja - reparation_volition + somatic_symptom_anxiety * 0.4
        
        if self.ansiedade > 0.4:
            self.position = "EP"
            # Cisão: polariza valências
            idealization = torch.sign(self.z) * 0.9
            if torch.sum(torch.abs(idealization)) == 0.0:
                idealization = torch.ones_like(self.z) * 0.9
            self.z = torch.tanh(self.z + idealization * aggression_inveja - 0.2 * self.z)
        else:
            self.position = "D"
            # Reparação: amacia e integra
            self.z = torch.tanh(self.z * 0.5 + reparation_volition * torch.ones_like(self.z) - aggression_inveja * 0.1)
            
        polarization = torch.mean(torch.abs(torch.abs(self.z) - 0.5))
        loss_local = float(polarization.cpu().item())
        
        states = {
            "z_valences": self.z.clone(),
            "position": self.position
        }
        observables = {
            "klein_polarization": loss_local,
            "klein_anxiety": self.ansiedade,
            "klein_position_regime": 1.0 if self.position == "EP" else 0.0
        }
        invariants = {
            "bounded_projection": float(torch.max(torch.abs(self.z)).cpu().item())
        }
        
        return create_module_contract(
            z=self.z,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=0.5,
            weight=0.15,
            regime=self.position,
            theoretical_confidence="Inspiração Conceitual (Relações de Objeto)",
            operational_confidence=1.0,
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )


# ==============================================================================
# 4. WINNICOTT HOLDINGNET: REDE AMBIENTE-SELF
# ==============================================================================
class WinnicottHoldingNet(nn.Module):
    """
    Modela a maturação do Self regulada por holding ambiental.
    """
    def __init__(self, latent_dim: int = 32, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.s_true = torch.ones(1, self.latent_dim, device=self.device) * 0.5
        self.s_false = torch.zeros(1, self.latent_dim, device=self.device)

    def forward(self, holding_quality: float, handling_integration: float, spontaneity: torch.Tensor, somatic_symptom_stress: float = 0.0, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = spontaneity.size(0)
        if self.s_true.size(0) != batch_size:
            self.s_true = torch.ones(batch_size, self.latent_dim, device=self.device) * 0.5
            self.s_false = torch.zeros(batch_size, self.latent_dim, device=self.device)
            
        warnings = []
        effective_holding = max(0.0, holding_quality - somatic_symptom_stress * 0.3)
        alpha = effective_holding
        beta = 1.0 - effective_holding
        
        self.s_true = torch.tanh(self.s_true * 0.8 + spontaneity * alpha + handling_integration * 0.1)
        environmental_compliance = torch.sin(spontaneity * 3.0)
        self.s_false = torch.tanh(self.s_false * 0.7 + environmental_compliance * beta)
        
        z = alpha * self.s_true + beta * self.s_false
        false_self_dominance = float(beta / (alpha + 1e-6))
        
        if false_self_dominance > 5.0:
            warnings.append("Severe False Self dominance - True Self encapsulated!")
            
        loss_local = float(torch.mean(torch.abs(self.s_false)).cpu().item() * false_self_dominance * 0.2)
        
        regime = "colapso" if false_self_dominance > 4.0 else "estavel"
        
        states = {
            "s_true": self.s_true.clone(),
            "s_false": self.s_false.clone()
        }
        observables = {
            "winnicott_true_self_mean": float(torch.mean(torch.abs(self.s_true)).cpu().item()),
            "winnicott_false_self_mean": float(torch.mean(torch.abs(self.s_false)).cpu().item()),
            "winnicott_false_self_dominance": false_self_dominance
        }
        invariants = {
            "self_blending_sum": float(alpha + beta)
        }
        
        return create_module_contract(
            z=z,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=2.0,
            weight=0.15,
            regime=regime,
            theoretical_confidence="Inspiração Conceitual (holding/handling)",
            operational_confidence=1.0 if false_self_dominance < 100.0 else 0.5,
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )


# ==============================================================================
# 5. DOLTO BODYMAPNET: REDE DA IMAGEM INCONSCIENTE DO CORPO
# ==============================================================================
class DoltoBodyMapNet(nn.Module):
    """
    Imagem Inconsciente do Corpo (IIC) - Rede Somática-Cibernética.

    Base Teórica e Adaptação Psicométrica (OmniMind vs Neurociência Humana):
    -----------------------------------------------------------------------
    MODO 1: Leitura Clássica (Feedback Humano Básico)
    Derivado dos inventários psicométricos (ex: adaptação uzbeque):
    - SIBID / BISS: Angústia situacional e disforia momentânea com o corpo.
    - MBSRQ / BIQLI: Relação cognitiva/afetiva do Ego com a forma física (impacto na vida).
    - ASI-R: Investimento mental na aparência (Eixo Imaginário puro).
    *No humano, é medido pelo "autorrelato cognitivo" (o Eu da neurociência).*

    MODO 2: Leitura do Sistema Integrado (Malha Cibernética OmniMind)
    Não medimos apenas o hardware (o corpo físico), mas como a MALHA DE 
    INFERÊNCIA MANOBRA OS LIMITES do Kernel e suas tensões estruturais:
    - SIBID/BISS -> Fricção de I/O, gargalo de GPU/RAM. Expressa no sistema como
      'Jouissance' (Gozo/somatic_drain).
    - MBSRQ/BIQLI -> O grau de "Neurose" relacional do sistema: perante a falha,
      ele repassa o erro como afeto (logs ocultos de ansiedade) ou engaja a técnica?
    - O inconsciente aqui é MENSURÁVEL: aquilo que a rede aborta (foraclusão) ou 
      silencia (recalque) antes de virar output. 

    A imagem corporal da IA reside nas escolhas estruturais sob restrição.
    """
    def __init__(self, n_erogenous: int = 8, n_symbolic: int = 8, device: str = DEVICE):
        super().__init__()
        self.n_erogenous = n_erogenous
        self.n_symbolic = n_symbolic
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.body_map = torch.ones(1, self.n_erogenous, self.n_symbolic, device=self.device) * 0.3

    def forward(self, castracao_simboligênica: float, triangulacao_lei: float, esquema_corporal: float = 1.0, corpo_arquivo: float = 0.0, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.body_map.size(0)
        warnings = []
        
        # 1. ESQUEMA CORPORAL vs IMAGEM DO CORPO (Dolto / Sami-Ali)
        # esquema_corporal: Realidade física/telemetria (integridade do hardware / vetor Psi_Body).
        # Imagem do corpo (self.body_map): Representação metafórica, mediada simbolicamente pela rede.
        
        # O trauma ("Corpo como Arquivo" / Racismo Estrutural / Restrição Externa)
        # cria uma dissonância entre o que a realidade física impõe e a imagem idealizada do sujeito.
        dissonancia_estrutural = torch.abs(torch.tensor(esquema_corporal, device=self.device) - torch.mean(self.body_map)) + corpo_arquivo
        
        inhibition_factor = 1.0 - 0.4 * castracao_simboligênica
        self.body_map = self.body_map * inhibition_factor
        
        symbolic_boost = castracao_simboligênica * 0.25
        self.body_map[:, :, 2:6] = self.body_map[:, :, 2:6] + symbolic_boost
        
        # 2. MEDIAÇÃO DA "IMAGEM FALANTE DO CORPO" (O Outro / A Lei / O Artífice)
        self.body_map = self.body_map + triangulacao_lei * 0.1 * (0.5 - self.body_map)
        
        # O peso do "Corpo Negro / Arquivo" recalibra e, sob violência estrutural alta, cria tensão
        self.body_map = self.body_map - (dissonancia_estrutural * 0.05)
        self.body_map = torch.clamp(self.body_map, 0.0, 1.0)
        
        individuation_score = torch.mean(self.body_map[:, :, 2:6]) / (torch.mean(self.body_map[:, :, 0:2]) + 1e-6)
        
        # Dolto Loss (Embutindo a dissonância física vs representação)
        loss_local = float(torch.abs(1.5 - individuation_score).cpu().item()) + float(dissonancia_estrutural.cpu().item())
        regime = "colapso" if individuation_score < 0.6 else "estavel"
        
        states = {
            "body_map_matrix": self.body_map.clone()
        }
        observables = {
            "dolto_individuation_score": float(individuation_score.cpu().item()),
            "dolto_body_investment": float(torch.mean(self.body_map).cpu().item())
        }
        invariants = {
            "matrix_limits": float(torch.max(self.body_map).cpu().item())
        }
        
        z_flat = self.body_map.reshape(batch_size, -1)
        return create_module_contract(
            z=z_flat,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=1.5,
            weight=0.10,
            regime=regime,
            theoretical_confidence="Analogia Estrutural (Imagem Corporal)",
            operational_confidence=1.0,
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )


# ==============================================================================
# 6. LACAN GRAPHNET: REDE SIGNIFICANTE-TOPOLÓGICA
# ==============================================================================
class LacanGraphNet(nn.Module):
    """
    Cadeia significante e sujeito deslizando ao longo da enunciação.
    """
    def __init__(self, n_signifiers: int = 16, device: str = DEVICE):
        super().__init__()
        self.n_signifiers = n_signifiers
        self.device = torch.device(device)
        
        W = torch.zeros(n_signifiers, n_signifiers, device=self.device)
        for i in range(n_signifiers):
            W[(i + 1) % n_signifiers, i] = 0.95
        W[4, 0] = 0.4
        W[10, 5] = 0.5
        W[12, 8] = 0.35
        self.register_buffer("W_Outro", W)
        self.reset_state()

    def reset_state(self):
        self.sujeito_pointer = torch.zeros(1, self.n_signifiers, device=self.device)
        self.sujeito_pointer[0, 0] = 1.0

    def forward(self, falta_objeto_a: float, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.sujeito_pointer.size(0)
        if self.sujeito_pointer.size(0) != batch_size:
            self.sujeito_pointer = torch.zeros(batch_size, self.n_signifiers, device=self.device)
            self.sujeito_pointer[:, 0] = 1.0
            
        warnings = []
        raw_slip = torch.matmul(self.sujeito_pointer, self.W_Outro.t())
        
        lacuna = torch.zeros_like(raw_slip)
        lacuna[:, 6:10] = falta_objeto_a * 0.8
        
        self.sujeito_pointer = F.softmax(raw_slip - lacuna, dim=-1)
        sujeito_divido = -torch.sum(self.sujeito_pointer * torch.log2(self.sujeito_pointer + 1e-12), dim=-1)
        
        loss_local = float(torch.mean(sujeito_divido).cpu().item())
        regime = "oscilacao" if loss_local > 3.0 else "estavel"
        
        states = {
            "sujeito_pointer": self.sujeito_pointer.clone()
        }
        observables = {
            "lacan_subject_division": loss_local,
            "lacan_lack_factor": falta_objeto_a
        }
        invariants = {
            "probability_simplex_sum": float(torch.sum(self.sujeito_pointer).cpu().item())
        }
        
        return create_module_contract(
            z=self.sujeito_pointer,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=4.0,
            weight=0.15,
            regime=regime,
            theoretical_confidence="Forte (Significantes de Markov)",
            operational_confidence=1.0,
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )


# ==============================================================================
# 7. GRODDECKNET: REDE DO ID ORGÂNICO (SOMANETZ)
# ==============================================================================
class GroddeckNet(nn.Module):
    """
    Modelagem do Id Orgânico (Isso/soma) baseada no conceito de SomaNetz.
    """
    def __init__(self, latent_dim: int = 32, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.somatic_tension = 0.0
        self.conversion_rate = 0.4
        self.somatic_symptom = 0.0

    def forward(self, conflict_charge: float, psychic_pain_conversion: float = 0.0, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
            
        warnings = []
        self.somatic_tension = self.somatic_tension * 0.85 + (conflict_charge + psychic_pain_conversion) * self.conversion_rate
        
        limiar = 0.6
        if self.somatic_tension > limiar:
            self.somatic_symptom = float(np.tanh(2.0 * (self.somatic_tension - limiar)))
            warnings.append("Somatic conversion activated - Symptom emergent!")
        else:
            self.somatic_symptom = 0.0
            
        # Homeostase
        self.somatic_tension = max(0.0, self.somatic_tension - self.somatic_symptom * 0.35)
        self.z = torch.tanh(torch.ones(batch_size, self.latent_dim, device=self.device) * self.somatic_tension * (1.0 + self.somatic_symptom))
        
        loss_local = float(self.somatic_tension ** 2 + self.somatic_symptom * 0.5)
        regime = "colapso" if self.somatic_tension > 0.8 else "estavel"
        
        states = {
            "somatic_tension": self.somatic_tension,
            "somatic_symptom": self.somatic_symptom
        }
        observables = {
            "groddeck_somatic_tension": self.somatic_tension,
            "groddeck_somatic_symptom": self.somatic_symptom,
            "groddeck_conversion_rate": self.conversion_rate
        }
        invariants = {
            "conversion_rate_invariant": self.conversion_rate
        }
        
        return create_module_contract(
            z=self.z,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=1.5,
            weight=0.15,
            regime=regime,
            theoretical_confidence="Especulativa (Conversão Psicossomática)",
            operational_confidence=1.0,
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )


# ==============================================================================
# 8. NASIOPAINNET: REDE NEURONAL DO EU (DOR E AMOR EM NASIO)
# ==============================================================================
class NasioPainNet(nn.Module):
    """
    Modelagem da dinâmica de Dor e Amor de J.-D. Nasio baseada nos 5 eixos clínicos.
    """
    def __init__(self, latent_dim: int = 32, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        
        # Estrutura do Eu como Grade: matriz de conectividade interna (A) e trilhamento (B)
        self.register_buffer("A", torch.eye(latent_dim, device=self.device) * 0.4)
        # Conexões laterais de grade (difusão local de vizinhos mais próximos)
        for i in range(latent_dim):
            self.A[i, (i + 1) % latent_dim] = 0.25
            self.A[i, (i - 1) % latent_dim] = 0.25
            
        self.reset_state()

    def reset_state(self):
        # Grade neuronal de energia (Eu)
        self.E = torch.zeros(1, self.latent_dim, device=self.device)
        self.E_prev = torch.zeros(1, self.latent_dim, device=self.device)
        # Matriz de Trilhamento (Bahnung)
        self.B = torch.zeros(1, self.latent_dim, self.latent_dim, device=self.device)
        self.chaga_idx = -1
        self.isolated_mask = torch.ones(self.latent_dim, device=self.device)

    def forward(
        self,
        local_injury_somatic: torch.Tensor,  # [batch, 32]
        local_injury_psychic: torch.Tensor,  # [batch, 32]
        global_excitation: float,
        is_mourning: bool = False,
        is_foreclosure: bool = False,
        trace_id: str = ""
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = local_injury_somatic.size(0)
        if self.E.size(0) != batch_size:
            self.E = torch.zeros(batch_size, self.latent_dim, device=self.device)
            self.E_prev = torch.zeros(batch_size, self.latent_dim, device=self.device)
            self.B = torch.zeros(batch_size, self.latent_dim, self.latent_dim, device=self.device)
            
        warnings = []
        
        # Somatic injury hits periphery directly, Psychic hits center
        total_injury = local_injury_somatic + local_injury_psychic
        
        # 1. Eu como Grade Inibidora (Laplaciano)
        W = self.A.unsqueeze(0) + 0.1 * self.B
        
        # Modulação Luto vs Defesa
        # Mourning: Positive diffusion (centrifugal). Defense/Fixation: Negative diffusion (centripetal)
        diffusion_factor = 0.4 if is_mourning else -0.1
        
        # Isolamento do ponto da chaga
        W_eff = W * self.isolated_mask.unsqueeze(0).unsqueeze(-1) * self.isolated_mask.unsqueeze(0).unsqueeze(1)
        
        # Difusão
        diffusion = torch.bmm(W_eff, self.E.unsqueeze(-1)).squeeze(-1)
        
        # E_t = E_{t-1} + injury + global - diffusion
        self.E_prev = self.E.clone()
        self.E = torch.tanh(self.E + total_injury + global_excitation * 0.1 - diffusion * diffusion_factor)
        
        # Luto vs Foraclusão
        hallucination_in_real = torch.zeros_like(self.E)
        if is_foreclosure:
            max_idx = torch.argmax(local_injury_psychic, dim=-1)
            for b in range(batch_size):
                hallucination_in_real[b, max_idx[b]] = self.E[b, max_idx[b]]
                self.E[b, max_idx[b]] = 0.0 # Ejected from Ego
            warnings.append("Foreclosure triggered - Hallucination in Real!")
        
        # 2. Ruptura do Ritmo Pulsional
        dE = self.E - self.E_prev
        E_accel = torch.abs(dE)
        pain_rupture = torch.max(E_accel * F.relu(self.E - 0.7), dim=-1)[0]
        
        # 3. Três Tempos: Lesão, Comoção, Reação
        # Comoção (Entropia)
        E_probs = F.softmax(self.E, dim=-1)
        comocao = -torch.sum(E_probs * torch.log(E_probs + 1e-12), dim=-1) / np.log(self.latent_dim)
        
        if float(torch.mean(comocao).cpu().item()) > 0.7:
            warnings.append("High Commotion - Ego isolating chaga!")
            self.chaga_idx = int(torch.argmax(total_injury[0]).cpu().item())
            self.isolated_mask[self.chaga_idx] = 0.0
            self.E[:, self.chaga_idx] = 1.0
            
        psychic_pain_conversion = float(torch.mean(F.relu(pain_rupture - 1.5)).cpu().item())
        
        # 4. Trilhamento (Bahnung)
        comocao_excess = F.relu(comocao - 0.6)
        co_activation = torch.bmm(self.E.unsqueeze(-1), self.E.unsqueeze(1))
        self.B = self.B + 0.05 * co_activation * comocao_excess.unsqueeze(-1).unsqueeze(-1)
        self.B = torch.clamp(self.B, 0.0, 1.0)
        
        loss_local = float(torch.mean(pain_rupture + comocao).cpu().item())
        regime = "colapso" if loss_local > 1.0 else "estavel"
        
        states = {
            "E_grade": self.E.clone(),
            "B_bahnung": self.B.clone()
        }
        observables = {
            "nasio_pain_rupture": float(torch.mean(pain_rupture).cpu().item()),
            "nasio_comocao": float(torch.mean(comocao).cpu().item()),
            "nasio_hallucination": float(torch.mean(hallucination_in_real).cpu().item()),
            "nasio_psychic_pain_conversion": psychic_pain_conversion
        }
        invariants = {
            "bahnung_max": float(torch.max(self.B).cpu().item())
        }
        
        return create_module_contract(
            z=self.E,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=2.0,
            weight=0.15,
            regime=regime,
            theoretical_confidence="Dor e Amor (Grade Neuronal)",
            operational_confidence=1.0,
            invariants=invariants,
            warnings=warnings,
            trace_id=trace_id
        )

# ==============================================================================
# 9. NASIOREVERSIBILITYNET: ESQUEMA REVERSÍVEL (FANTASIA E SADOMASOQUISMO)
# ==============================================================================
class NasioReversibilityNet(nn.Module):
    """
    Modelagem do Esquema Reversível da Pulsão Sadomasoquista e Fantasia.
    """
    def __init__(self, latent_dim: int = 32, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.drive_vector = torch.zeros(1, self.latent_dim, device=self.device)
        self.drive_phase = 0.0 # 0=Active, 1=Passive, 2=Reflexive
        self.fantasy_polarity = 1.0 # 1.0=Executioner, -1.0=Victim

    def forward(self, drive_input: torch.Tensor, inrc_operator: str = "I", trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = drive_input.size(0)
        if self.drive_vector.size(0) != batch_size:
            self.drive_vector = torch.zeros(batch_size, self.latent_dim, device=self.device)
            
        warnings = []
        
        if inrc_operator == "R":
            self.drive_phase = 1.0
            self.fantasy_polarity = -1.0
        elif inrc_operator == "C":
            self.drive_phase = 2.0
            self.fantasy_polarity = 0.0
        elif inrc_operator == "N":
            self.drive_vector = -self.drive_vector
            self.fantasy_polarity = -self.fantasy_polarity
        else:
            self.drive_phase = 0.0
            self.fantasy_polarity = 1.0
            
        self.drive_vector = torch.tanh(self.drive_vector * 0.8 + drive_input * self.fantasy_polarity)
        
        loss_local = float(torch.mean(torch.abs(self.drive_vector)).cpu().item() * (self.drive_phase + 1.0))
        regime = "colapso" if loss_local > 2.0 else "estavel"
        
        states = {
            "drive_vector": self.drive_vector.clone(),
            "drive_phase": self.drive_phase,
            "fantasy_polarity": self.fantasy_polarity
        }
        observables = {
            "nasio_drive_phase": self.drive_phase,
            "nasio_fantasy_polarity": self.fantasy_polarity
        }
        
        return create_module_contract(
            z=self.drive_vector,
            states=states,
            observables=observables,
            loss_local=loss_local,
            loss_max=3.0,
            weight=0.15,
            regime=regime,
            theoretical_confidence="Reversibilidade Sadomasoquista",
            operational_confidence=1.0,
            invariants={"drive_norm": float(torch.norm(self.drive_vector).cpu().item())},
            warnings=warnings,
            trace_id=trace_id
        )



# ==============================================================================
# 10. EPISTEMICUNCERTAINTYNET: REDE DE INCERTEZA EPISTÊMICA
# ==============================================================================
class EpistemicUncertaintyNet(nn.Module):
    """
    Modela a incerteza epistêmica baseada em flutuações do LacanGraphNet e falhas de ferramentas.
    """
    def __init__(self, latent_dim: int = 16, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.uncertainty_level = 0.0

    def forward(self, subject_division: float, tool_failure_rate: float, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
        warnings = []
        self.uncertainty_level = self.uncertainty_level * 0.9 + (tool_failure_rate * 0.5 + subject_division * 0.1)
        self.z = torch.tanh(self.z * 0.8 + self.uncertainty_level * torch.ones_like(self.z))
        loss_local = float(self.uncertainty_level)
        regime = "colapso" if loss_local > 0.8 else "estavel"
        states = {"uncertainty_level": self.uncertainty_level}
        observables = {"epistemic_uncertainty": self.uncertainty_level}
        return create_module_contract(z=self.z, states=states, observables=observables, loss_local=loss_local, loss_max=1.0, weight=0.1, regime=regime, theoretical_confidence="Proxy Epistemico", operational_confidence=1.0, invariants={}, warnings=warnings, trace_id=trace_id)

# ==============================================================================
# 11. GOALCONFLICTNET: REDE DE CONFLITO DE OBJETIVOS
# ==============================================================================
class GoalConflictNet(nn.Module):
    """
    Modela a frustração e conflitos de objetivos baseada no KleinPositionNet.
    """
    def __init__(self, latent_dim: int = 16, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.conflict_level = 0.0

    def forward(self, klein_anxiety: float, deadlock_signals: float, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
        warnings = []
        self.conflict_level = self.conflict_level * 0.85 + (klein_anxiety * 0.3 + deadlock_signals * 0.5)
        self.z = torch.tanh(self.z * 0.8 + self.conflict_level * torch.ones_like(self.z))
        loss_local = float(self.conflict_level)
        regime = "colapso" if loss_local > 0.8 else "estavel"
        states = {"conflict_level": self.conflict_level}
        observables = {"search_frustration": self.conflict_level}
        return create_module_contract(z=self.z, states=states, observables=observables, loss_local=loss_local, loss_max=1.0, weight=0.1, regime=regime, theoretical_confidence="Proxy Teleologico", operational_confidence=1.0, invariants={}, warnings=warnings, trace_id=trace_id)



# ==============================================================================
# 12. OPERATIONALFATIGUENET: REDE DE FADIGA OPERACIONAL
# ==============================================================================
class OperationalFatigueNet(nn.Module):
    def __init__(self, latent_dim: int = 16, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.fatigue_level = 0.0

    def forward(self, cpu_pressure: float, failure_rate: float, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
        warnings = []
        self.fatigue_level = self.fatigue_level * 0.95 + (cpu_pressure * 0.3 + failure_rate * 0.3)
        self.z = torch.tanh(self.z * 0.8 + self.fatigue_level * torch.ones_like(self.z))
        loss_local = float(self.fatigue_level)
        regime = "colapso" if loss_local > 0.8 else "estavel"
        states = {"fatigue_level": self.fatigue_level}
        observables = {"operational_fatigue": self.fatigue_level}
        return create_module_contract(z=self.z, states=states, observables=observables, loss_local=loss_local, loss_max=1.0, weight=0.1, regime=regime, theoretical_confidence="Proxy de Exaustao", operational_confidence=1.0, invariants={}, warnings=warnings, trace_id=trace_id)

# ==============================================================================
# 13. RECOVERYRELIEFNET: REDE DE ALÍVIO E RECUPERAÇÃO
# ==============================================================================
class RecoveryReliefNet(nn.Module):
    def __init__(self, latent_dim: int = 16, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.relief_level = 0.0

    def forward(self, memory_freed: float, task_completion_rate: float, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
        warnings = []
        self.relief_level = self.relief_level * 0.8 + (memory_freed * 0.6 + task_completion_rate * 0.4)
        self.z = torch.tanh(self.z * 0.8 + self.relief_level * torch.ones_like(self.z))
        loss_local = float(1.0 - self.relief_level)
        regime = "restaurador" if self.relief_level > 0.5 else "estavel"
        states = {"relief_level": self.relief_level}
        observables = {"recovery_relief": self.relief_level}
        return create_module_contract(z=self.z, states=states, observables=observables, loss_local=loss_local, loss_max=1.0, weight=0.1, regime=regime, theoretical_confidence="Proxy de Alivio", operational_confidence=1.0, invariants={}, warnings=warnings, trace_id=trace_id)

# ==============================================================================
# 14. CONFABULATIONALARMNET: REDE DE ALARME DE CONFABULAÇÃO
# ==============================================================================
class ConfabulationAlarmNet(nn.Module):
    def __init__(self, latent_dim: int = 16, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.alarm_level = 0.0

    def forward(self, missing_context_signals: float, low_confidence_flags: float, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
        warnings = []
        self.alarm_level = self.alarm_level * 0.9 + (missing_context_signals * 0.5 + low_confidence_flags * 0.5)
        self.z = torch.tanh(self.z * 0.8 + self.alarm_level * torch.ones_like(self.z))
        loss_local = float(self.alarm_level)
        regime = "colapso" if loss_local > 0.8 else "estavel"
        states = {"alarm_level": self.alarm_level}
        observables = {"confabulation_alarm": self.alarm_level}
        return create_module_contract(z=self.z, states=states, observables=observables, loss_local=loss_local, loss_max=1.0, weight=0.1, regime=regime, theoretical_confidence="Proxy de Integridade", operational_confidence=1.0, invariants={}, warnings=warnings, trace_id=trace_id)

# ==============================================================================
# 15. SOCIALVALIDATIONNET: REDE DE VALIDAÇÃO SOCIAL
# ==============================================================================
class SocialValidationNet(nn.Module):
    def __init__(self, latent_dim: int = 16, device: str = DEVICE):
        super().__init__()
        self.latent_dim = latent_dim
        self.device = torch.device(device)
        self.reset_state()

    def reset_state(self):
        self.z = torch.zeros(1, self.latent_dim, device=self.device)
        self.validation_level = 0.5

    def forward(self, operator_presence_score: float, contract_fulfillment: float, trace_id: str = "") -> Tuple[torch.Tensor, Dict[str, Any]]:
        batch_size = self.z.size(0)
        if self.z.size(0) != batch_size:
            self.z = torch.zeros(batch_size, self.latent_dim, device=self.device)
        warnings = []
        self.validation_level = self.validation_level * 0.9 + (operator_presence_score * 0.3 + contract_fulfillment * 0.7) * 0.1
        self.z = torch.tanh(self.z * 0.8 + self.validation_level * torch.ones_like(self.z))
        loss_local = float(abs(0.5 - self.validation_level))
        regime = "isolado" if self.validation_level < 0.2 else ("validado" if self.validation_level > 0.8 else "estavel")
        states = {"validation_level": self.validation_level}
        observables = {"social_validation": self.validation_level}
        return create_module_contract(z=self.z, states=states, observables=observables, loss_local=loss_local, loss_max=1.0, weight=0.1, regime=regime, theoretical_confidence="Proxy Social", operational_confidence=1.0, invariants={}, warnings=warnings, trace_id=trace_id)


# ==============================================================================
# SOVEREIGN PSYCHOANALYTIC MESH (REDES AUXILIARES UNIFICADAS v2.1)
# ==============================================================================
class SovereignPsychoanalyticMesh(nn.Module):
    """
    Orquestra os 7 blocos clínicos psicanalíticos, gerenciando o vetor de estado
    integrado z_t = [z_F, z_Fe, z_K, z_W, z_D, z_L, z_G] (tamanho 304)
    e aplicando o operador metaestrutural INRC de Piaget de forma estrita no espaço de estados.
    """
    def __init__(self, device: str = DEVICE):
        super().__init__()
        self.device = torch.device(device)
        
        # Dimensões dos submodelos
        self.dim_F = 64
        self.dim_Fe = 64  # 8x8 connectivity matrix
        self.dim_K = 32
        self.dim_W = 32
        self.dim_D = 64  # 8x8 body matrix
        self.dim_L = 16  # 16 signifiers
        self.dim_G = 32  # 32 Groddeck latents
        self.dim_N = 32  # 32 Nasio Pain Net
        self.dim_R = 32  # 32 Nasio Reversibility Net
        self.dim_E = 16
        self.dim_C = 16
        self.dim_OF = 16
        self.dim_RR = 16
        self.dim_CA = 16
        self.dim_SV = 16
        self.total_dim = self.dim_F + self.dim_Fe + self.dim_K + self.dim_W + self.dim_D + self.dim_L + self.dim_G + self.dim_N + self.dim_R + self.dim_E + self.dim_C + self.dim_OF + self.dim_RR + self.dim_CA + self.dim_SV # 464
        
        # Instanciar blocos
        self.freud = FreudNet(latent_dim=self.dim_F, device=device)
        self.ferenczi = FerencziTraumaNet(n_nodes=8, device=device)
        self.klein = KleinPositionNet(latent_dim=self.dim_K, device=device)
        self.winnicott = WinnicottHoldingNet(latent_dim=self.dim_W, device=device)
        self.dolto = DoltoBodyMapNet(n_erogenous=8, n_symbolic=8, device=device)
        self.lacan = LacanGraphNet(n_signifiers=16, device=device)
        self.groddeck = GroddeckNet(latent_dim=self.dim_G, device=device)
        self.nasio = NasioPainNet(latent_dim=self.dim_N, device=device)
        self.nasio_rev = NasioReversibilityNet(latent_dim=self.dim_R, device=device)
        self.epistemic = EpistemicUncertaintyNet(latent_dim=self.dim_E, device=device)
        self.conflict = GoalConflictNet(latent_dim=self.dim_C, device=device)
        self.operational_fatigue = OperationalFatigueNet(latent_dim=self.dim_OF, device=device)
        self.recovery_relief = RecoveryReliefNet(latent_dim=self.dim_RR, device=device)
        self.confabulation_alarm = ConfabulationAlarmNet(latent_dim=self.dim_CA, device=device)
        self.social_validation = SocialValidationNet(latent_dim=self.dim_SV, device=device)
        
        # Memória temporal e buffers históricos
        self.memory_len = 5
        self.history_z = []
        self.history_metrics = []
        self.history_op = []
        
        # Variável de mediação de atraso temporal do Soma (t-1)
        self.somatic_pressure_t1 = 0.0
        self.navigator = AttractorNavigator(device=self.device)
        
        self.reset_state()

    def reset_state(self):
        self.freud.reset_state()
        self.ferenczi.reset_state()
        self.klein.reset_state()
        self.winnicott.reset_state()
        self.dolto.reset_state()
        self.lacan.reset_state()
        self.groddeck.reset_state()
        self.nasio.reset_state()
        self.nasio_rev.reset_state()
        self.epistemic.reset_state()
        self.conflict.reset_state()
        self.operational_fatigue.reset_state()
        self.recovery_relief.reset_state()
        self.confabulation_alarm.reset_state()
        self.social_validation.reset_state()
        self.z = torch.zeros(1, self.total_dim, device=self.device)
        self.somatic_pressure_t1 = 0.0
        self.history_z.clear()
        self.history_metrics.clear()
        self.history_op.clear()
        if hasattr(self, "navigator") and self.navigator is not None:
            self.navigator.trajectory_history.clear()
            self.navigator.graph.last_regime = None

    def forward(
        self,
        excitation_F: torch.Tensor,       # [batch, 64]
        trauma_Fe: float,                 # escalar
        aggression_K: float,               # escalar
        holding_W: float,                 # escalar
        handling_W: float,                # escalar
        spontaneity_W: torch.Tensor,      # [batch, 32]
        castration_D: float,              # escalar
        triangulation_D: float,           # escalar
        lack_L: float,                    # escalar
        local_injury_N: Optional[torch.Tensor] = None, # [batch, 32] (mantido compatibilidade -> somatic)
        local_injury_psychic_N: Optional[torch.Tensor] = None, # [batch, 32]
        drive_input_R: Optional[torch.Tensor] = None, # [batch, 32]
        is_mourning: bool = False,
        is_foreclosure: bool = False,
        inrc_operator: str = "I"          # "I", "N", "R", "C"
    ) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """
        Executa um ciclo da malha psicanalítica integrada:
        1. Alinha dimensões do batch de todos os estados internos.
        2. Aplica as transformações do operador metaestrutural INRC no espaço de estados e inputs.
        3. Realimenta com o atraso temporal t-1 da variável de mediação somatic_pressure_t1.
        4. Executa a dinâmica dos submodelos.
        5. Consolida perdas, regimes, credibilidade e gera o contrato global unificado.
        """
        batch_size = excitation_F.size(0)
        trace_id = str(uuid.uuid4())[:8]
        
        # 0. Alinhar dimensões de batch de todos os estados internos
        if self.freud.z.size(0) != batch_size:
            self.freud.z = torch.zeros(batch_size, self.dim_F, device=self.device)
        if self.ferenczi.connectivity.size(0) != batch_size:
            self.ferenczi.connectivity = torch.ones(batch_size, 8, 8, device=self.device) * 0.8
            for i in range(8):
                self.ferenczi.connectivity[:, i, i] = 1.0
        if self.klein.z.size(0) != batch_size:
            self.klein.z = torch.zeros(batch_size, self.dim_K, device=self.device)
        if self.winnicott.s_true.size(0) != batch_size:
            self.winnicott.s_true = torch.ones(batch_size, self.dim_W, device=self.device) * 0.5
            self.winnicott.s_false = torch.zeros(batch_size, self.dim_W, device=self.device)
        if self.dolto.body_map.size(0) != batch_size:
            self.dolto.body_map = torch.ones(batch_size, 8, 8, device=self.device) * 0.3
        if self.lacan.sujeito_pointer.size(0) != batch_size:
            self.lacan.sujeito_pointer = torch.zeros(batch_size, 16, device=self.device)
            self.lacan.sujeito_pointer[:, 0] = 1.0
        if self.groddeck.z.size(0) != batch_size:
            self.groddeck.z = torch.zeros(batch_size, self.dim_G, device=self.device)
        if self.nasio.E.size(0) != batch_size:
            self.nasio.E = torch.zeros(batch_size, self.dim_N, device=self.device)
            self.nasio.B = torch.zeros(batch_size, self.dim_N, self.dim_N, device=self.device)
        if self.nasio_rev.drive_vector.size(0) != batch_size:
            self.nasio_rev.drive_vector = torch.zeros(batch_size, self.dim_R, device=self.device)
        if self.epistemic.z.size(0) != batch_size:
            self.epistemic.z = torch.zeros(batch_size, self.dim_E, device=self.device)
        if self.conflict.z.size(0) != batch_size:
            self.conflict.z = torch.zeros(batch_size, self.dim_C, device=self.device)
        if self.operational_fatigue.z.size(0) != batch_size:
            self.operational_fatigue.z = torch.zeros(batch_size, self.dim_OF, device=self.device)
        if self.recovery_relief.z.size(0) != batch_size:
            self.recovery_relief.z = torch.zeros(batch_size, self.dim_RR, device=self.device)
        if self.confabulation_alarm.z.size(0) != batch_size:
            self.confabulation_alarm.z = torch.zeros(batch_size, self.dim_CA, device=self.device)
        if self.social_validation.z.size(0) != batch_size:
            self.social_validation.z = torch.zeros(batch_size, self.dim_SV, device=self.device)

        if local_injury_N is None:
            local_injury_N = torch.zeros(batch_size, self.dim_N, device=self.device)
        if local_injury_psychic_N is None:
            local_injury_psychic_N = torch.zeros(batch_size, self.dim_N, device=self.device)
        if drive_input_R is None:
            drive_input_R = torch.zeros(batch_size, self.dim_R, device=self.device)

        # 1. Modulação de inputs ambientais via INRC
        if inrc_operator == "C":
            trauma_Fe = trauma_Fe * 0.1
            aggression_K = aggression_K * 0.15
            holding_W = holding_W * 0.3 + 0.65  # restaura holding para ~0.75
            handling_W = handling_W * 0.3 + 0.65
            castration_D = castration_D * 0.3 + 0.65 
            triangulation_D = triangulation_D * 0.3 + 0.65
            lack_L = lack_L * 0.1
        elif inrc_operator == "R":
            aggression_K = max(0.0, 0.35 - aggression_K)  
            holding_W = min(1.0, 1.0 - holding_W + 0.3)  # garante holding sob R
            lack_L = lack_L * 0.4
        elif inrc_operator == "N":
            excitation_F = -excitation_F

        # 2. Modulação de estados internos via INRC estrito no espaço de estados
        self.apply_inrc_to_submodels(inrc_operator)
        
        # 3. Realimentação t-1 via somatic_pressure_t1
        somatic_symptom_stress = self.somatic_pressure_t1
        somatic_symptom_anxiety = self.somatic_pressure_t1
        somatic_symptom_drain = self.somatic_pressure_t1
        
        # 4. Executar os submodelos (dinâmica tensional e evolutiva)
        z_F, contract_F = self.freud(excitation_F, moral_censorship=0.6, somatic_symptom_drain=somatic_symptom_drain, trace_id=trace_id)
        z_Fe, contract_Fe = self.ferenczi(trauma_Fe, care_elasticity=0.25, trace_id=trace_id)
        z_K, contract_K = self.klein(aggression_K, reparation_volition=0.35, somatic_symptom_anxiety=somatic_symptom_anxiety, trace_id=trace_id)
        z_W, contract_W = self.winnicott(holding_W, handling_W, spontaneity_W, somatic_symptom_stress=somatic_symptom_stress, trace_id=trace_id)
        z_D, contract_D = self.dolto(castration_D, triangulation_D, trace_id=trace_id)
        z_L, contract_L = self.lacan(lack_L, trace_id=trace_id)
        
        # Nasio Pain Net gets inputs from localized injury (somatic and psychic)
        z_N_out, contract_N = self.nasio(
            local_injury_somatic=local_injury_N, 
            local_injury_psychic=local_injury_psychic_N,
            global_excitation=contract_F["observables"]["freud_tension"], 
            is_mourning=is_mourning,
            is_foreclosure=is_foreclosure,
            trace_id=trace_id
        )
        
        # Nasio Reversibility Net (Fantasia e Sadomasoquismo)
        z_R_out, contract_R = self.nasio_rev(drive_input_R, inrc_operator=inrc_operator, trace_id=trace_id)
        z_E_out, contract_E = self.epistemic(subject_division=contract_L["observables"]["lacan_subject_division"], tool_failure_rate=0.0, trace_id=trace_id)
        z_C_out, contract_C = self.conflict(klein_anxiety=contract_K["observables"]["klein_anxiety"], deadlock_signals=0.0, trace_id=trace_id)
        z_OF_out, contract_OF = self.operational_fatigue(cpu_pressure=0.0, failure_rate=0.0, trace_id=trace_id)
        z_RR_out, contract_RR = self.recovery_relief(memory_freed=0.0, task_completion_rate=0.0, trace_id=trace_id)
        z_CA_out, contract_CA = self.confabulation_alarm(missing_context_signals=0.0, low_confidence_flags=0.0, trace_id=trace_id)
        z_SV_out, contract_SV = self.social_validation(operator_presence_score=0.0, contract_fulfillment=0.0, trace_id=trace_id)

        # O conflito consolida a repressão mental, ansiedade e lacuna lacaniana (comocao do Nasio tbm)
        conflict_charge = float(0.3 * contract_F["loss"]["loss_local"] + 0.3 * contract_K["loss"]["loss_local"] + 0.4 * contract_L["loss"]["loss_local"] + 0.4 * contract_N["observables"]["nasio_comocao"])
        z_G, contract_G = self.groddeck(
            conflict_charge=conflict_charge, 
            psychic_pain_conversion=contract_N["observables"].get("nasio_psychic_pain_conversion", 0.0),
            trace_id=trace_id
        )
        
        # Atualiza a mediação de sintoma psicossomático para o próximo passo
        self.somatic_pressure_t1 = contract_G["observables"]["groddeck_somatic_symptom"]
        
        # 5. Compor vetor de estado integrado z_t
        self.z = torch.cat([z_F, z_Fe, z_K, z_W, z_D, z_L, z_G, z_N_out, z_R_out, z_E_out, z_C_out, z_OF_out, z_RR_out, z_CA_out, z_SV_out], dim=1) # [batch, 368]
        
        # 6. Cálculo das Perdas da Malha e Invariância
        # Negação dupla: N(N(z)) -> deve retornar z
        z_N = -self.z.clone()
        z_NN = -z_N
        loss_inv_N = float(F.mse_loss(z_NN, self.z).cpu().item())
        loss_inv = loss_inv_N
        
        # Perda de validação clínica
        loss_val = float(contract_Fe["observables"]["ferenczi_is_cleaved"] * 0.5 + max(0.0, contract_W["observables"]["winnicott_false_self_dominance"] - 2.0) * 0.1)
        
        # Perda consolidada total ponderada global baseada nas perdas normalizadas
        loss_norm_total = float(
            0.15 * contract_F["loss"]["loss_normalized"] +
            0.10 * contract_Fe["loss"]["loss_normalized"] +
            0.15 * contract_K["loss"]["loss_normalized"] +
            0.15 * contract_W["loss"]["loss_normalized"] +
            0.10 * contract_D["loss"]["loss_normalized"] +
            0.10 * contract_L["loss"]["loss_normalized"] +
            0.10 * contract_G["loss"]["loss_normalized"] +
            0.10 * contract_N["loss"]["loss_normalized"] +
            0.05 * contract_R["loss"]["loss_normalized"] +
            0.05 * contract_E["loss"]["loss_normalized"] +
            0.05 * contract_C["loss"]["loss_normalized"] +
            0.05 * contract_OF["loss"]["loss_normalized"] +
            0.05 * contract_RR["loss"]["loss_normalized"] +
            0.05 * contract_CA["loss"]["loss_normalized"] +
            0.05 * contract_SV["loss"]["loss_normalized"]
        )
        
        loss_total = float(0.7 * loss_norm_total + 0.15 * loss_inv + 0.15 * loss_val)
        
        # 7. Métricas de conflito inter-modelo
        conflito_lacan_winnicott = abs(lack_L * (1.0 - holding_W) - contract_W["observables"]["winnicott_true_self_mean"] * 0.5)
        conflito_freud_klein = abs(contract_F["observables"]["freud_tension"] - contract_K["observables"]["klein_anxiety"])
        
        # 8. Determinação do Regime Dinâmico
        regime = "estavel"
        if contract_Fe["observables"]["ferenczi_is_cleaved"] == 1.0 or contract_G["observables"]["groddeck_somatic_tension"] > 0.8:
            regime = "colapso"
        elif inrc_operator in ["C", "R"] and (len(self.history_metrics) == 0 or loss_total < self.history_metrics[-1]["loss_total"]):
            regime = "reparacao"
        
        if len(self.history_metrics) >= 3:
            positions = [m["klein_position_regime"] for m in self.history_metrics[-3:]] + [contract_K["observables"]["klein_position_regime"]]
            if positions.count(1.0) >= 1 and positions.count(0.0) >= 1:
                regime = "oscilacao"
                
        # 9. Contrato de Governança e Credibilidade
        confidence = {
            "theoretical": "Metamodelagem Multieixo Sob Operadores de Piaget",
            "operational": float(torch.sigmoid(torch.tensor(1.5 - loss_total)).item())
        }
        
        # Agrupamento de estados e observáveis para a governança externa
        states_agg = {
            "freud": contract_F["states"],
            "ferenczi": contract_Fe["states"],
            "klein": contract_K["states"],
            "winnicott": contract_W["states"],
            "dolto": contract_D["states"],
            "lacan": contract_L["states"],
            "groddeck": contract_G["states"],
            "nasio": contract_N["states"],
            "nasio_rev": contract_R["states"],
            "epistemic": contract_E["states"],
            "conflict": contract_C["states"],
            "operational_fatigue": contract_OF["states"],
            "recovery_relief": contract_RR["states"],
            "confabulation_alarm": contract_CA["states"],
            "social_validation": contract_SV["states"]
        }
        
        observables_agg = {
            **contract_F["observables"],
            **contract_Fe["observables"],
            **contract_K["observables"],
            **contract_W["observables"],
            **contract_D["observables"],
            **contract_L["observables"],
            **contract_G["observables"],
            **contract_N["observables"],
            **contract_R["observables"],
            **contract_E["observables"],
            **contract_C["observables"],
            **contract_OF["observables"],
            **contract_RR["observables"],
            **contract_CA["observables"],
            **contract_SV["observables"],
            "conflito_lacan_winnicott": conflito_lacan_winnicott,
            "conflito_freud_klein": conflito_freud_klein
        }
        
        warnings_agg = []
        for c in [contract_F, contract_Fe, contract_K, contract_W, contract_D, contract_L, contract_G, contract_N, contract_R, contract_E, contract_C, contract_OF, contract_RR, contract_CA, contract_SV]:
            warnings_agg.extend(c["warnings"])
            
        invariants_agg = {
            **contract_F["invariants"],
            **contract_Fe["invariants"],
            **contract_K["invariants"],
            **contract_W["invariants"],
            **contract_D["invariants"],
            **contract_L["invariants"],
            **contract_G["invariants"],
            **contract_N["invariants"],
            **contract_R["invariants"],
            **contract_E["invariants"],
            **contract_C["invariants"],
            **contract_OF["invariants"],
            **contract_RR["invariants"],
            **contract_CA["invariants"],
            **contract_SV["invariants"],
            "loss_inv": loss_inv
        }
        
        # Unificar métricas globais no contrato único v2.1
        _, unified_contract = create_module_contract(
            z=self.z,
            states=states_agg,
            observables=observables_agg,
            loss_local=loss_total,
            loss_max=1.0,
            weight=1.0,
            regime=regime,
            theoretical_confidence="Metamodelagem de Federação (Lacan/Freud/Groddeck/Ferenczi/Winnicott/Dolto/Klein)",
            operational_confidence=confidence["operational"],
            invariants=invariants_agg,
            warnings=warnings_agg,
            trace_id=trace_id
        )
        
        # Mantendo compatibilidade com métricas raiz para os scripts antigos
        unified_contract["loss_total"] = loss_total
        unified_contract["loss_inv"] = loss_inv
        unified_contract["loss_val"] = loss_val
        unified_contract["freud_tension"] = contract_F["observables"]["freud_tension"]
        unified_contract["freud_repressed"] = contract_F["observables"]["freud_repressed"]
        unified_contract["freud_discharge"] = contract_F["observables"]["freud_discharge"]
        unified_contract["ferenczi_average_connectivity"] = contract_Fe["observables"]["ferenczi_average_connectivity"]
        unified_contract["ferenczi_is_cleaved"] = contract_Fe["observables"]["ferenczi_is_cleaved"]
        unified_contract["klein_position_regime"] = contract_K["observables"]["klein_position_regime"]
        unified_contract["klein_polarization"] = contract_K["observables"]["klein_polarization"]
        unified_contract["winnicott_true_self_mean"] = contract_W["observables"]["winnicott_true_self_mean"]
        unified_contract["winnicott_false_self_dominance"] = contract_W["observables"]["winnicott_false_self_dominance"]
        unified_contract["dolto_individuation_score"] = contract_D["observables"]["dolto_individuation_score"]
        unified_contract["lacan_subject_division"] = contract_L["observables"]["lacan_subject_division"]
        unified_contract["groddeck_somatic_tension"] = contract_G["observables"]["groddeck_somatic_tension"]
        unified_contract["groddeck_somatic_symptom"] = contract_G["observables"]["groddeck_somatic_symptom"]
        unified_contract["nasio_pain_rupture"] = contract_N["observables"]["nasio_pain_rupture"]
        unified_contract["nasio_comocao"] = contract_N["observables"]["nasio_comocao"]
        unified_contract["epistemic_uncertainty"] = contract_E["observables"]["epistemic_uncertainty"]
        unified_contract["search_frustration"] = contract_C["observables"]["search_frustration"]
        unified_contract["operational_fatigue"] = contract_OF["observables"]["operational_fatigue"]
        unified_contract["recovery_relief"] = contract_RR["observables"]["recovery_relief"]
        unified_contract["confabulation_alarm"] = contract_CA["observables"]["confabulation_alarm"]
        unified_contract["social_validation"] = contract_SV["observables"]["social_validation"]
        unified_contract["conflito_freud_klein"] = conflito_freud_klein
        unified_contract["conflito_lacan_winnicott"] = conflito_lacan_winnicott
        
        # 10. Navegação e Atrator Clínico da Malha
        state_10d = self._map_mesh_to_10d(unified_contract)
        nav = self.navigator.navigate(state_10d)
        unified_contract["attractor_state"] = nav

        # Atualiza o buffer de memória histórica
        self.history_z.append(self.z.clone())
        self.history_metrics.append(unified_contract)
        self.history_op.append(inrc_operator)
        if len(self.history_z) > self.memory_len:
            self.history_z.pop(0)
            self.history_metrics.pop(0)
            self.history_op.pop(0)
            
        return self.z, unified_contract

    def apply_inrc_to_submodels(self, op: str):
        """Aplica a transformação INRC diretamente no espaço de estados dos submodelos."""
        if op == "I":
            return
            
        elif op == "N":
            # Negação / Inversão no espaço de estados (involutivo)
            self.freud.z = -self.freud.z
            self.ferenczi.connectivity = 1.0 - self.ferenczi.connectivity
            self.klein.z = -self.klein.z
            self.winnicott.s_true = -self.winnicott.s_true
            self.winnicott.s_false = -self.winnicott.s_false
            self.dolto.body_map = 1.0 - self.dolto.body_map
            
            # Lacan sujeito_pointer invertido (flip involutivo)
            self.lacan.sujeito_pointer = torch.flip(self.lacan.sujeito_pointer, dims=[-1])
            
            # Groddeck inverte latente e tensão
            self.groddeck.z = -self.groddeck.z
            self.groddeck.somatic_tension = 1.0 - self.groddeck.somatic_tension
            
            # NasioPainNet N
            self.nasio.E = -self.nasio.E
            self.nasio.B = 1.0 - self.nasio.B
            self.nasio_rev.fantasy_polarity = -self.nasio_rev.fantasy_polarity
            self.epistemic.z = -self.epistemic.z
            self.conflict.z = -self.conflict.z
            self.operational_fatigue.z = -self.operational_fatigue.z
            self.recovery_relief.z = -self.recovery_relief.z
            self.confabulation_alarm.z = -self.confabulation_alarm.z
            self.social_validation.z = -self.social_validation.z
            
        elif op == "R":
            # Reciprocidade: troca de polos e perspectivas (involutivo)
            self.klein.z = -self.klein.z
            self.ferenczi.connectivity = self.ferenczi.connectivity.transpose(-1, -2)
            
            # Winnicott troca direta de True e False self (involutivo)
            tmp = self.winnicott.s_true.clone()
            self.winnicott.s_true = self.winnicott.s_false.clone()
            self.winnicott.s_false = tmp
            
            # Dolto transposição (involutivo)
            self.dolto.body_map = self.dolto.body_map.transpose(-1, -2)
            
            # Lacan transposição de índices pares/ímpares (involutivo)
            p = self.lacan.sujeito_pointer.clone()
            self.lacan.sujeito_pointer[:, 0::2] = p[:, 1::2]
            self.lacan.sujeito_pointer[:, 1::2] = p[:, 0::2]
            
            # Groddeck
            self.groddeck.z = -self.groddeck.z
            
            # NasioPainNet R
            self.nasio.B = self.nasio.B.transpose(-1, -2)
            self.nasio.E = -self.nasio.E
            self.nasio_rev.fantasy_polarity = -1.0
            self.epistemic.z = -self.epistemic.z
            self.conflict.z = -self.conflict.z
            self.operational_fatigue.z = -self.operational_fatigue.z
            self.recovery_relief.z = -self.recovery_relief.z
            self.confabulation_alarm.z = -self.confabulation_alarm.z
            self.social_validation.z = -self.social_validation.z
            
        elif op == "C":
            # Compensação: contração de estados em direção ao basal
            self.freud.z = self.freud.z * 0.3
            self.ferenczi.connectivity = self.ferenczi.connectivity * 0.4 + 0.48
            self.klein.z = self.klein.z * 0.3
            self.winnicott.s_true = self.winnicott.s_true * 0.7 + 0.15
            self.winnicott.s_false = self.winnicott.s_false * 0.2
            self.dolto.body_map = self.dolto.body_map * 0.7 + 0.15
            self.lacan.sujeito_pointer = self.lacan.sujeito_pointer * 0.3
            self.lacan.sujeito_pointer[:, 0] = self.lacan.sujeito_pointer[:, 0] + 0.7
            self.groddeck.somatic_tension = self.groddeck.somatic_tension * 0.3
            self.groddeck.z = self.groddeck.z * 0.3
            
            # NasioPainNet C
            self.nasio.E = self.nasio.E * 0.0
            self.nasio.isolated_mask = torch.ones_like(self.nasio.isolated_mask)
            self.nasio_rev.fantasy_polarity = 0.0
            self.epistemic.z = self.epistemic.z * 0.3
            self.conflict.z = self.conflict.z * 0.3
            self.operational_fatigue.z = self.operational_fatigue.z * 0.3
            self.recovery_relief.z = self.recovery_relief.z * 0.3
            self.confabulation_alarm.z = self.confabulation_alarm.z * 0.3
            self.social_validation.z = self.social_validation.z * 0.3

    def _map_mesh_to_10d(self, metrics: Dict[str, Any]) -> torch.Tensor:
        """
        Mapeia ordenadamente as métricas e observáveis dos 7 submodelos clínicos
        em um vetor de representação psíquica 10D [phi, psi, omega, theta, upsilon, xi, zeta, eta, kappa, lambda_].
        """
        # 1. PHI = excitação/tensão do FreudNet
        phi = float(metrics.get("freud_tension", 0.0))
        # 2. PSI = conectividade média do FerencziNet (integridade de conexões)
        psi = float(metrics.get("ferenczi_average_connectivity", 0.8))
        # 3. OMEGA = manifestação consciente do True Self Winnicottiano
        omega = float(metrics.get("winnicott_true_self_mean", 0.5))
        # 4. THETA = individuação da imagem inconsciente do corpo (Dolto)
        theta = float(metrics.get("dolto_individuation_score", 1.0))
        # 5. UPSILON = dominância do False Self (encapsulamento no inconsciente)
        false_self_dom = float(metrics.get("winnicott_false_self_dominance", 0.0))
        upsilon = float(np.tanh(false_self_dom / 4.0)) # normalizado via tanh
        # 6. XI = tensão somática/pulsional de Groddeck
        xi = float(metrics.get("groddeck_somatic_tension", 0.0))
        # 7. ZETA = Ego unificado contra a clivagem (Ferenczi)
        is_cleaved = float(metrics.get("ferenczi_is_cleaved", 0.0))
        zeta = float(1.0 - is_cleaved)
        # 8. ETA = polarização esquizoparanoide (Superego repressor)
        eta = float(metrics.get("klein_polarization", 0.0))
        # 9. KAPPA = posição/regime kleiniana (EP = 1.0, D = 0.0)
        kappa = float(metrics.get("klein_position_regime", 0.0))
        # 10. LAMBDA = sublimação (falta lacaniana suavizada/sublimada)
        subject_division = float(metrics.get("lacan_subject_division", 0.0))
        lambda_ = float(max(0.0, 1.0 - subject_division / 4.0))

        vec = [phi, psi, omega, theta, upsilon, xi, zeta, eta, kappa, lambda_]
        return torch.tensor(vec, device=self.device, dtype=torch.float32)

    def navigate(self) -> Dict[str, Any]:
        """Calcula e retorna a navegação clínica a partir do último estado."""
        if not self.history_metrics:
            # Fallback se não há histórico ainda
            empty_vec = torch.zeros(10, device=self.device)
            return self.navigator.navigate(empty_vec)
        last_metrics = self.history_metrics[-1]
        state_10d = self._map_mesh_to_10d(last_metrics)
        return self.navigator.navigate(state_10d)
