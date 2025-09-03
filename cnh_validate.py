import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class CNH:
    nome: str
    cpf: str
    nome_mae: str
    data_nascimento: str
    data_validade: Optional[str] = None
    numero_registro: Optional[str] = None
    nome_pai: Optional[str] = None
    responsavel_legal: Optional[bool] = None

@dataclass
class CNH_validations:
    validacao_nome: str
    validacao_cpf: str
    validacao_nome_mae: str
    validacao_data_nascimento: str
    validacao_data_validade: str 



class cnh_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        
        cartao_proposta["nome"] = cartao_proposta["nome_responsavel"] if "nome_responsavel" in cartao_proposta else cartao_proposta.get("nome")
        cartao_proposta["cpf"] = cartao_proposta["cpf_responsavel"] if "cpf_responsavel" in cartao_proposta else cartao_proposta.get("cpf")

        cartao_proposta["responsavel_legal"] = "nome_responsavel" in cartao_proposta

        self.cartao_proposta = CNH(**cartao_proposta)
        self.dados_extraidos = CNH(**dados_extraidos)
        self.message_type = message_type

    def set_validate_functions_list(self):
        return list(CNH_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type
    
    
    @validate        
    def validacao_nome(self, limiar=90):
        """
        Valida se o nome extraído do cartao_proposta corresponde ao nome extraído dos dados, com base na similaridade.

        Lógica de Retorno:
            - TRUE: Se a similaridade for maior ou igual ao limiar especificado, a validação é considerada válida;
            - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 95.
        """
        s1 = self.cartao_proposta.nome
        s2 = self.dados_extraidos.nome

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >=limiar
        return {'valid': is_valid, 'percent_match': sim_score}
    
    @validate
    def validacao_cpf(self):
        """
        Valida se o CPF extraído do cartao_proposta corresponde ao CPF extraído dos dados.
    
        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """
        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cpf))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))

        is_valid = s1 == s2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}
    
    @validate    
    def validacao_nome_mae(self, limiar=90):
        """
        Valida se o nome da mãe extraído do cartao_proposta corresponde ao nome da mãe extraído dos dados, com base na similaridade.
    
        Lógica de Retorno:
        - TRUE: Se a similaridade for maior ou igual ao limiar especificado, a validação é considerada válida;
        - FALSE: Caso contrário.
    
        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 95.
        """
        s1 = self.cartao_proposta.nome_mae
        s2 = self.dados_extraidos.nome_mae

        responsavel_legal = self.cartao_proposta.responsavel_legal
        if(responsavel_legal and len(s1.strip()) == 0):
            return {'valid': True, 'percent_match': 100, 
            'trecho_procurado': 'Validação não aplicável ao documento do representante legal',
            'trecho_encontrado': 'Validação não aplicável ao documento do representante legal'}

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >=limiar
        return {'valid': is_valid, 'percent_match': sim_score}
            
    @validate    
    def validacao_data_nascimento(self):
        """
        Valida se a data de nascimento extraída do cartao_proposta corresponde à data de nascimento extraída dos dados.
    
        Lógica de Retorno:
        - TRUE: Se as datas de nascimento forem iguais;
        - FALSE: Caso contrário.
        """
        s1 =  self.cartao_proposta.data_nascimento

        responsavel_legal = self.cartao_proposta.responsavel_legal
        if(responsavel_legal and len(s1.strip()) == 0):
            return {'valid': True, 'percent_match': 100, 
            'trecho_procurado': 'Validação não aplicável ao documento do representante legal',
            'trecho_encontrado': 'Validação não aplicável ao documento do representante legal'}

        date_1 = datetime.datetime.strptime(s1, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_nascimento, '%d-%m-%Y')

        is_valid = date_1 == date_2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}

    @validate
    def validacao_data_validade(self):
        """
        Valida se a data de validade extraída dos dados é válida, ou seja, se ainda não passou.

        Lógica de Retorno:
        - TRUE: Se a data de validade for maior ou igual à data de hoje (indicando que ainda é válida);
        - FALSE: Caso contrário (indicando que a data de validade já passou).
        """
        date = datetime.datetime.strptime(self.dados_extraidos.data_validade, '%d-%m-%Y')

        is_valid = date >= datetime.datetime.now()
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}
