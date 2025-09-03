import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Cartao_plano:
    nome: str
    nome_titular: Optional[str] = None
    acomodacao: Optional[str] = None
    razao_social: Optional[str] = None
    data_nascimento: Optional[str] = None
    numero_cartao: Optional[str] = None
    data_validade: Optional[str] = None
    nome_congenere: Optional[str] = None
    segmentacao: Optional[str] = None

@dataclass
class Cartao_plano_validations:
    validacao_nome: str
    validacao_data_nascimento: str
    validacao_data_validade: str


class cartao_plano_validate(ValidateDocument):

    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        
        cartao_proposta["nome"] = cartao_proposta["nome_responsavel"] if "nome_responsavel" in cartao_proposta else cartao_proposta.get("nome")

        self.cartao_proposta = Cartao_plano(**cartao_proposta)
        self.dados_extraidos = Cartao_plano(**dados_extraidos)
        self.message_type = message_type

        self.congeneres_validas = ["bradesco", "sulamerica", "notredame", "unimed nacional", "allianz", "care plus", "porto seguro", "omint", "mediservice", "amil"]

        self.set_nome_congenere()

    def set_validate_functions_list(self):
        return list(Cartao_plano_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type
    

    def set_nome_congenere(self):

        s1 = self.dados_extraidos.nome_congenere

        best_match = None
        highest_jaro_wink = 0

        for s2 in self.congeneres_validas:
            current_score = distances(s1.upper(), s2.upper()).jaro_winkler_similarity()
            if(current_score > highest_jaro_wink):
                highest_jaro_wink = current_score
                best_match = s2

        if(highest_jaro_wink > 75):
            self.dados_extraidos.nome_congenere = best_match
        

    @validate
    def validacao_nome(self, limiar=90):
        """
        Valida se o nome do beneficiário extraído do documento corresponde ao nome do beneficiário extraído do cartao_proposta.

        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """
        s1 = self.cartao_proposta.nome
        s2 = self.dados_extraidos.nome
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}


    @validate
    def validacao_data_nascimento(self):
        """
        Valida se a data de nascimento extraída do documento corresponde a data de nascimento extraída do cartao_proposta.

        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        # checa congeneres sem essa validacao
        nome_congenere = self.dados_extraidos.nome_congenere
        congeneres_sem_val = ["bradesco", "notredame", "unimed nacional", "allianz", "care plus", "mediservice", "omint",]
        if(nome_congenere in congeneres_sem_val):
            return {'valid': True, 'percent_match': 100, 'target': 'data_nascimento', 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}

        if self.dados_extraidos.data_nascimento.upper() == 'NOT FOUND':
            return {'valid': False, 'percent_match': 0, 'target': 'data_nascimento', 'trecho_encontrado': self.dados_extraidos.data_nascimento, 'regras_subscricao_errors': 404}

        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_nascimento, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_nascimento, '%d-%m-%Y')

        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}


    @validate
    def validacao_data_validade(self):
        """
        Valida se a data de validade do Cartão Plano está em vigência.

        Lógica de Retorno:
        - TRUE: Se a data estiver em vigência;
        - FALSE: Caso contrário.
        """

        # checa congeneres sem essa validacao
        nome_congenere = self.dados_extraidos.nome_congenere
        congeneres_sem_val = ["sulamerica", "notre dame", "amil"]
        if(nome_congenere in congeneres_sem_val):
            return {'valid': True, 'percent_match': 100, 'target': 'data_validade', 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}

        if self.dados_extraidos.data_validade.upper() == 'NOT FOUND':
            return {'valid': False, 'percent_match': 0, 'target': 'data_validade', 'trecho_encontrado': self.dados_extraidos.data_validade, 'regras_subscricao_errors': 404}

        data_validade = datetime.datetime.strptime(self.dados_extraidos.data_validade, '%d-%m-%Y').date()
        now = datetime.datetime.now().date()
        if now <= data_validade:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
