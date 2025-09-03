from dataclasses import dataclass
from ValidateDocument import ValidateDocument, validate
from Distances import distances
from typing import Optional
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dataclasses_json import dataclass_json, Undefined

def interdoc(method):
    method._validation_type = 'interdoc'
    return method

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Termo_guarda:
    nome_crianca: Optional[str] = None
    nome_primeiro_guardiao: Optional[str] = None
    nome_segundo_guardiao: Optional[str] = None
    cpf_primeiro_guardiao: Optional[str] = None
    cpf_segundo_guardiao: Optional[str] = None
    data_expedicao: Optional[str] = None
    is_termo_de_guarda: Optional[str] = None
    is_provisorio: Optional[str] = None
    nome_titular: Optional[str] = None  

@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Termo_guarda_sign:
    ha_logo_tribunal: str
    descricao_logo: Optional[str] = None
    

@dataclass
class Termo_guarda_validations:
    validacao_nome_titular: Optional[str] = None
    validacao_is_termo_de_guarda: Optional[str] = None
    validacao_data_expedicao: Optional[str] = None

@dataclass
class Termo_guarda_sign_validations:
    validacao_ha_logo_tribunal: str
    
class termo_guarda_validate(ValidateDocument):
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.message_type = message_type
        self.cartao_proposta = Termo_guarda(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Termo_guarda_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Termo_guarda(**dados_extraidos)
        
    def set_validate_functions_list(self):
        return list(Termo_guarda_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Termo_guarda_sign_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type

    def _is_valid(self, campo, confianca, descricao):
        set_true = {'True', 'true', True, 'Verdadeiro', 'verdadeiro', 'VERDADEIRO', 'TRUE'}
        
        if campo in set_true:
            is_valid = True
        else:
            is_valid = False
        return {
            "valid": is_valid,
            "percent_match": confianca,
            "trecho_procurado": "",
            "trecho_encontrado": descricao
        }
        
    @validate    
    def validacao_nome_titular(self, limiar=90):
        """
        Valida se o nome do titular do cartão proposta corresponde ao nome de um dos guardiões extraídos da certidão.

        Lógica de Retorno:
        - TRUE: Se a similaridade entre o nome do titular e qualquer um dos guardiões for maior ou igual ao limiar;
        - FALSE: Caso contrário.
        """
        s1 = self.cartao_proposta.nome_titular
        s2_list = [self.dados_extraidos.nome_primeiro_guardiao, self.dados_extraidos.nome_segundo_guardiao]

        s2_list = [x for x in s2_list if x != "Not Found"]
        self.dados_extraidos.nome_titular = s2_list
        for s2 in s2_list:
            score = distances(s1, s2).norm_score()
            if score >= limiar:
                return {'valid': True, 'percent_match': score}
        return {'valid': False, 'percent_match': score}


    @validate        
    def validacao_is_termo_de_guarda(self, limiar=97):
        """
        Valida se o documento indica que é um termo de guarda.

        Lógica de Retorno:
        - TRUE: Se o campo 'is_termo_de_guarda' for 'True';
        - FALSE: Caso contrário.
        """
        if self.dados_extraidos.is_termo_de_guarda in {'True', 'true', True, 'Verdadeiro', 'verdadeiro', 'VERDADEIRO', 'TRUE'}:
            return {'valid': True, 'percent_match': 100, 'trecho_encontrado': 'É termo de guarda'}
        return {'valid': False, 'percent_match': 0, 'trecho_encontrado': 'Não é termo de guarda'}


    @validate   
    def validacao_data_expedicao(self):
        """
        Valida se a data de expedição do documento está dentro do prazo válido.

        Lógica de Retorno:
        - TRUE: Se o documento não for provisório, ou se a data de expedição for nos últimos 12 meses;
        - FALSE: Caso contrário.
        """
        now = datetime.now().date()
        extracted_dispatch_date = datetime.strptime(self.dados_extraidos.data_expedicao, "%d-%m-%Y").date()
        data_expedicao = extracted_dispatch_date.strftime('%Y-%m-%d')
        if self.dados_extraidos.is_provisorio in {'False', 'false', False, 'Falso', 'falso', 'FALSO', 'FALSE'}:
            return {'valid': True, 'percent_match': 100, 'trecho_procurado': '', 'trecho_encontrado': 'termo de guarda permanente'}
        if extracted_dispatch_date >= (now - relativedelta(years=1)):
            return {'valid': True, 'percent_match': 100, 'trecho_procurado': '', 'trecho_encontrado': data_expedicao}
        return {'valid': False, 'percent_match': 0, 'trecho_procurado': '', 'trecho_encontrado': data_expedicao}

    @validate
    def validacao_ha_logo_tribunal(self):
        """
        Valida se há logo do tribunal presente no documento.

        Lógica de Retorno:
        - TRUE: Se o logo do tribunal foi detectado;
        - FALSE: Caso contrário.
        """
        ha_logo_tribunal = self.dados_extraidos.ha_logo_tribunal
        score = 100 if ha_logo_tribunal else 0
        return self._is_valid(ha_logo_tribunal, score, self.dados_extraidos.descricao_logo)