import re
import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict
from dataclasses_json import dataclass_json, Undefined
from ValidateDocument import ValidateDocument, validate
from Distances import distances

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class TermoReducaoCarencia:
    operadora: str
    produto: str
    segmentacao: str
    acomodacao: str
    abrangencia: str
    vigencia: str
    plano_destino: str
    oriundo_unimed: str
    template_termo_reducao_carencia: Optional[str] = None
    numero_vidas: Optional[int] = None

@dataclass
class TermoReducaoCarenciaValidations:
    validacao_codigo_reducao_carencia: str

class termo_reducao_carencia_validate(ValidateDocument):
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.message_type = message_type
        self.cartao_proposta = TermoReducaoCarencia(**cartao_proposta)
        self.dados_extraidos = TermoReducaoCarencia(**dados_extraidos)

    def set_validate_functions_list(self):
        return list(TermoReducaoCarenciaValidations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type

    def _is_regional(self):
        return self.dados_extraidos.abrangencia.upper() == "R"

    def _is_nacional(self):
        return self.dados_extraidos.abrangencia.upper() == "N"

    def _is_termo_corporativo(self):
        return self.dados_extraidos.template_termo_reducao_carencia and "CORPORATIVO" in self.dados_extraidos.template_termo_reducao_carencia.upper()

    def _vigencia_meses(self):
        # Espera-se vigência no formato "mm/yyyy" ou "dd-mm-yyyy"
        vig = self.dados_extraidos.vigencia
        if not vig or vig.upper() == "NOT FOUND":
            return 0
        try:
            if re.match(r"\d{2}/\d{4}", vig):
                dt = datetime.datetime.strptime(vig, "%m/%Y")
            elif re.match(r"\d{2}-\d{2}-\d{4}", vig):
                dt = datetime.datetime.strptime(vig, "%d-%m-%Y")
            else:
                return 0
            hoje = datetime.datetime.now()
            diff = (hoje.year - dt.year) * 12 + (hoje.month - dt.month)
            return abs(diff)
        except Exception:
            return 0

    def _tem_plano_relacionado(self):
        # Adapte conforme necessário para buscar planos relacionados
        # Exemplo: checar se produto está em uma lista de planos relacionados
        return False

    def _is_congenere(self):
        # Adapte conforme necessário para buscar se é congênere
        return False

    def _codigo_por_fluxo(self):
        # Fluxo principal conforme imagem e regras
        vidas = self.dados_extraidos.numero_vidas or 0

        # CA.1 - 10 a 29 vidas
        if 10 <= vidas <= 29:
            return "CP"

        # CA.2 - 30 a 99 vidas
        if 30 <= vidas <= 99:
            return None  # Isento de carência

        # CA.3 - 2 a 9 vidas
        if 2 <= vidas <= 9:
            # Fluxo do diagrama
            vigencia = self._vigencia_meses()
            is_regional = self._is_regional()
            is_nacional = self._is_nacional()
            is_termo_corp = self._is_termo_corporativo()
            oriundo_unimed = self.dados_extraidos.oriundo_unimed == "1"

            # Exemplo de lógica simplificada (adapte conforme o fluxo detalhado)
            if is_termo_corp:
                if vigencia <= 6:
                    return "TRC2"
                else:
                    return "TRC"
            elif is_regional:
                if vigencia <= 12:
                    if self._tem_plano_relacionado():
                        return "TRC2"
                    elif 6 <= vigencia <= 12:
                        return "TRC1"
                    else:
                        return "TRC"
                else:
                    return "TRC"
            elif is_nacional:
                if vigencia <= 12:
                    if self._is_congenere():
                        return "TRC2"
                    elif 6 <= vigencia <= 12:
                        return "TRC1"
                    else:
                        return "TRC"
                else:
                    return "TRC"
            elif oriundo_unimed:
                if vigencia <= 12:
                    return "TRC2"
                elif 6 <= vigencia <= 12:
                    return "TRC1"
                else:
                    return "TRC"
            else:
                return "TRC"
        # Fora das faixas
        return "Erro. Plano não encontrado para classificação de TRC"

    @validate
    def validacao_codigo_reducao_carencia(self):
        """
        Valida e retorna o código de redução de carência (TRC, TRC1, TRC2, CP ou isento) conforme regras do fluxo.
        """
        codigo = self._codigo_por_fluxo()
        if codigo is None:
            return {
                "valid": True,
                "percent_match": 100,
                "target": "codigo_reducao_carencia",
                "trecho_procurado": "",
                "trecho_encontrado": "Isento de carência"
            }
        elif codigo.startswith("Erro"):
            return {
                "valid": False,
                "percent_match": 0,
                "target": "codigo_reducao_carencia",
                "trecho_procurado": "",
                "trecho_encontrado": codigo,
                "regras_subscricao_errors": 404
            }
        else:
            return {
                "valid": True,
                "percent_match": 100,
                "target": "codigo_reducao_carencia",
                "trecho_procurado": "",
                "trecho_encontrado": codigo
            }