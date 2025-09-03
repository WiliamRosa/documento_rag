import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate
from Distances import distances
from dataclasses_json import dataclass_json, Undefined
from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)     
@dataclass
class Esocial:
    razao_social: str
    nome: str
    cnpj: str
    cpf: str
    data_admissao: str
    cbo: Optional[str] = None

@dataclass
class Esocial_validations:
    validacao_razao_social: str
    validacao_nome: str
    validacao_cnpj: str
    validacao_cpf: str
    validacao_data_admissao: str
    validacao_cbo: str #interdoc



class esocial_validate(ValidateDocument):
    
    #cartao proposta = cartao_proposta + proposta de contratacao?
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        
        self.cartao_proposta = Esocial(**cartao_proposta)
        self.dados_extraidos = Esocial(**dados_extraidos)
        self.message_type = message_type
        
    
    def set_validate_functions_list(self):
        return list(Esocial_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type
    
    @validate
    def validacao_nome(self, limiar=90):
        """
        Valida se o nome extraído corresponde ao nome do cartão proposta.

        Lógica de Retorno:
        - TRUE: Se a similaridade entre os nomes for igual ou superior ao limiar;
        - FALSE: Caso contrário.

        Parâmetros:
        - limiar: Valor mínimo de similaridade para considerar válido (padrão: 90).
        """
        s1 = self.cartao_proposta.nome
        s2 = self.dados_extraidos.nome
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >= limiar
        return {'valid': is_valid, 'percent_match': sim_score}

    @validate
    def validacao_razao_social(self, limiar=90):
        """
        Valida se a razão social extraída corresponde à razão social do cartão proposta.

        Lógica de Retorno:
        - TRUE: Se a similaridade entre as razões sociais for igual ou superior ao limiar;
        - FALSE: Caso contrário.

        Parâmetros:
        - limiar: Valor mínimo de similaridade para considerar válido (padrão: 90).
        """
        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >= limiar
        return {'valid': is_valid, 'percent_match': sim_score}

    @validate
    def validacao_cnpj(self):
        """
        Valida se o CNPJ extraído corresponde ao CNPJ do cartão proposta.

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
    def validacao_cpf(self):
        """
        Valida se o CPF extraído corresponde ao CPF do cartão proposta.

        Lógica de Retorno:
        - TRUE: Se os CPFs forem idênticos após a remoção de caracteres não numéricos;
        - FALSE: Caso contrário.
        """
        s1 = ''.join(re.findall(r'\d+', self.cartao_proposta.cpf))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate
    def validacao_data_admissao(self):
        """
        Valida se a data de admissão extraída corresponde à data de admissão do cartão proposta.

        Lógica de Retorno:
        - TRUE: Se as datas de admissão forem idênticas;
        - FALSE: Caso contrário.

        Detalhes:
        - Converte as strings de data para objetos datetime antes da comparação.
        - Assume que ambas as datas estão no formato 'dd-mm-yyyy'.
        """
        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_admissao, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_admissao, '%d-%m-%Y')
        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}



    @validate 
    def validacao_cbo(self):
        """
        Valida se o CBO está preenchido na CTPS.
    
        Lógica de Retorno:
        - TRUE: Se o CBO for encontrado;
        - FALSE: Caso contrário.
        """

        if self.dados_extraidos.cbo.upper() != "NOT FOUND":
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
            