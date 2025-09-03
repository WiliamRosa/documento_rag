import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from validacao_endereco import Validacao_endereco, Endereco
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Requerimento_empresario:
    razao_social: str
    cnpj: str
    endereco_empresa: str


@dataclass
class Requerimento_empresario_validations:
    validacao_razao_social: str
    validacao_cnpj: str
    validacao_endereco_empresa: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Requerimento_empresario_sign:
    ha_assinatura: str
    ha_selo_carimbo: str
    descricao_assinatura: Optional[str] = None
    confianca_assinatura: Optional[str] = None
    descricao_selo_carimbo: Optional[str] = None
    confianca_selo_carimbo: Optional[str] = None


@dataclass
class Requerimento_empresario_sign_validations:
    validacao_ha_assinatura: str
    validacao_ha_selo_carimbo: str


class requerimento_empresario_validate(ValidateDocument):
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.message_type = message_type
        self.cartao_proposta = Requerimento_empresario(**cartao_proposta)

        if (message_type == "signature"):
            self.dados_extraidos = Requerimento_empresario_sign(
                **dados_extraidos)
        else:
            self.dados_extraidos = Requerimento_empresario(**dados_extraidos)

    def set_validate_functions_list(self):
        return list(Requerimento_empresario_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Requerimento_empresario_sign_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type

    @validate
    def validacao_razao_social(self, limiar=80):
        """
        Valida se a razão social extraída corresponde à razão social do requerimento.

        Lógica de Retorno:
        - TRUE: Se a similaridade entre as razões sociais for igual ou superior ao limiar;
        - FALSE: Caso contrário.

        Parâmetros:
        - limiar: Valor mínimo de similaridade para considerar válido (padrão: 80).
        """
        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >= limiar
        return {'valid': is_valid, 'percent_match': sim_score}

    @validate
    def validacao_cnpj(self):
        """
        Valida se o CNPJ extraído corresponde ao CNPJ do requerimento.

        Lógica de Retorno:
        - TRUE: Se os CNPJs forem idênticos após a remoção de caracteres não numéricos;
        - FALSE: Caso contrário.
        """
        s1 = ''.join(re.findall(r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate
    def validacao_endereco_empresa(self):
        """
        Valida se o endereço da empresa extraído corresponde ao endereço do requerimento.

        Lógica de Retorno:
        - Determinada pela classe Validacao_endereco.
        """
        val_endereco = Validacao_endereco(
            self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        valid, score = val_endereco.validar_endereco()

        return {'valid': valid, 'percent_match': score}

    def _is_valid(self, campo, confianca, descricao, target):
        set_true = {'True', 'true', True, 'Verdadeiro',
                    'verdadeiro', 'VERDADEIRO', 'TRUE'}

        if campo in set_true:
            is_valid = True
        else:
            is_valid = False
        return {
            "valid": is_valid,
            "target": target,
            "percent_match": confianca,
            "trecho_procurado": "",
            "trecho_encontrado": descricao
        }

    @validate
    def validacao_ha_assinatura(self):
        """
        Valida se o documento está assinado.

        Lógica de Retorno:
        - TRUE: Se o documento estiver assinado;
        - FALSE: Caso contrário.
        """
        assinatura = self.dados_extraidos.ha_assinatura
        return self._is_valid(assinatura, self.dados_extraidos.confianca_assinatura, self.dados_extraidos.descricao_assinatura, 'ha_assinatura')

    @validate
    def validacao_ha_selo_carimbo(self):
        """
        Valida se o documento contém um selo ou carimbo.

        Lógica de Retorno:
        - TRUE: Se o documento conter um selo;
        - FALSE: Caso contrário.
        """
        selo = self.dados_extraidos.ha_selo_carimbo
        return self._is_valid(selo, self.dados_extraidos.confianca_selo_carimbo, self.dados_extraidos.descricao_selo_carimbo, 'ha_selo_carimbo')