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
class Escritura_uniao_estavel:
    nome_titular: str
    nome: str
    cpf_titular: str
    cpf: str
    nome_mae_titular: Optional[str] = None
    nome_mae: Optional[str] = None
    data_nascimento_titular: Optional[str] = None
    data_nascimento: Optional[str] = None

@dataclass
class Escritura_uniao_estavel_validations:
    validacao_nome_titular: str
    validacao_cpf_titular: str
    validacao_nome_dependente: str
    validacao_cpf_dependente: str
    validacao_nome_mae_titular: str
    validacao_nome_mae_dependente: str
    validacao_data_nascimento_titular: str
    validacao_data_nascimento_dependente: str


@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Escritura_uniao_estavel_sign:
    ha_selo_carimbo: str
    descricao_selo_carimbo: str
    confianca: str

@dataclass
class Escritura_uniao_estavel_sign_validations:
    validacao_selo_carimbo: str


class escritura_uniao_estavel_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):

        self.message_type = message_type
        self.cartao_proposta = Escritura_uniao_estavel(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Escritura_uniao_estavel_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Escritura_uniao_estavel(**dados_extraidos)
            self.checa_titular_dependente()
    
    def set_validate_functions_list(self):
        return list(Escritura_uniao_estavel_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Escritura_uniao_estavel_sign_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type

    def checa_titular_dependente(self, limiar=60):
        
        s1 = self.cartao_proposta.nome_titular
        s2 = self.dados_extraidos.nome
        
        # se o titular for igual ao dependente, então foram atribuidos incorretamente
        # nesse caso, troca os valores dos campos de titular e dependente 
        if(distances(s1.upper(), s2.upper()).norm_score() >= limiar):
            
            self.dados_extraidos.nome_titular, self.dados_extraidos.nome = (
                self.dados_extraidos.nome,
                self.dados_extraidos.nome_titular
            )
            
            # Troca de CPF do titular e dependente
            self.dados_extraidos.cpf_titular, self.dados_extraidos.cpf = (
                self.dados_extraidos.cpf,
                self.dados_extraidos.cpf_titular
            )
            
            # Troca de nome da mãe 
            self.dados_extraidos.nome_mae_titular, self.dados_extraidos.nome_mae = (
                self.dados_extraidos.nome_mae,
                self.dados_extraidos.nome_mae_titular
            )
            
            # Troca de data de nascimento
            self.dados_extraidos.data_nascimento_titular, self.dados_extraidos.data_nascimento = (
                self.dados_extraidos.data_nascimento,
                self.dados_extraidos.data_nascimento_titular
            )
    
    def _validar_nome(self, nome_cp, nome_de, limiar=90):
        
        score = distances(nome_cp.upper(), nome_de.upper()).norm_score()
        is_valid = score >= limiar
        return is_valid, score

    @validate      
    def validacao_nome_titular(self):
        """
        Valida se o nome do titular do cartao_proposta corresponde ao nome do titular extraído da Escritura.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        tit_cp = self.cartao_proposta.nome_titular
        tit_de = self.dados_extraidos.nome_titular

        is_valid, score = self._validar_nome(tit_cp, tit_de)
        return {'valid': is_valid, 'percent_match': score}

    @validate        
    def validacao_nome_dependente(self):
        """
        Valida se o nome do dependente do cartao_proposta corresponde ao nome do dependente extraído da Escritura.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        dep_cp = self.cartao_proposta.nome
        dep_de = self.dados_extraidos.nome

        is_valid, score = self._validar_nome(dep_cp, dep_de)
        return {"valid": is_valid, "percent_match": score, 
                "trecho_procurado": dep_cp,
                "trecho_encontrado": dep_de}
        

    def _validar_cpf(self, cpf_cp, cpf_de):
        
        if(cpf_cp == cpf_de):
            return True, 100
        else:
            return False, 0
            
    @validate 
    def validacao_cpf_titular(self):
        """
        Valida se o CPF do titular do cartao_proposta corresponde ao CPF do titular extraído da Escritura.
    
        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """
        
        tit_cp = ''.join(re.findall(r'\d+', self.cartao_proposta.cpf_titular))
        tit_de = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf_titular))
        
        is_valid, score = self._validar_cpf(tit_cp, tit_de)
        
        return {'valid': is_valid, 'percent_match': score}
    
    @validate 
    def validacao_cpf_dependente(self):
        """
        Valida se o CPF do dependente do cartao_proposta corresponde ao CPF do dependente extraído da Escritura.
    
        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """

        dep_cp = ''.join(re.findall(r'\d+', self.cartao_proposta.cpf))
        dep_de = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))
        
        is_valid, score = self._validar_cpf(dep_cp, dep_de)

        return {"valid": is_valid, "percent_match": score, 
                "trecho_procurado": dep_cp,
                "trecho_encontrado": dep_de}
    
    @validate   
    def validacao_selo_carimbo(self):
        """
        Valida se há selo ou carimbo no documento.
    
        Lógica de Retorno:
        - TRUE: Se identificar um selo ou carimbo;
        - FALSE: Caso contrário.
        """

        ha_selo_carimbo = self.dados_extraidos.ha_selo_carimbo
        return self._is_valid(ha_selo_carimbo, self.dados_extraidos.confianca, self.dados_extraidos.descricao_selo_carimbo)


    @validate      
    def validacao_nome_mae_titular(self):
        """
        Valida se o nome da mãe do titular do cartao_proposta corresponde ao nome da mãe do titular extraído da Escritura.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        tit_cp = self.cartao_proposta.nome_mae_titular
        tit_de = self.dados_extraidos.nome_mae_titular

        is_valid, score = self._validar_nome(tit_cp, tit_de)
        return {'valid': is_valid, 'percent_match': score}

    @validate        
    def validacao_nome_mae_dependente(self):
        """
        Valida se o nome da mãe do dependente do cartao_proposta corresponde ao nome da mãe do dependente extraído da Escritura.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        dep_cp = self.cartao_proposta.nome_mae
        dep_de = self.dados_extraidos.nome_mae

        is_valid, score = self._validar_nome(dep_cp, dep_de)
        return {"valid": is_valid, "percent_match": score, 
                "trecho_procurado": dep_cp,
                "trecho_encontrado": dep_de}
              
    @validate    
    def validacao_data_nascimento_titular(self):
        """
        Valida se a data de nascimento do titular extraída do cartao_proposta corresponde à data de nascimento do titular extraída dos dados.
    
        Lógica de Retorno:
        - TRUE: Se as datas de nascimento forem iguais;
        - FALSE: Caso contrário.
        """
        s1 = self.cartao_proposta.data_nascimento_titular
        s2 = self.dados_extraidos.data_nascimento_titular

        if(s2 == 'Not Found'):
            return {'valid': False, 'percent_match': 0}

        date_1 = datetime.datetime.strptime(s1, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(s2, '%d-%m-%Y')

        is_valid = date_1 == date_2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}
     

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
    def validacao_data_nascimento_dependente(self):
        """
        Valida se a data de nascimento do dependente extraída do cartao_proposta corresponde à data de nascimento do dependente extraída dos dados.
    
        Lógica de Retorno:
        - TRUE: Se as datas de nascimento forem iguais;
        - FALSE: Caso contrário.
        """
        s1 = self.cartao_proposta.data_nascimento
        s2 = self.dados_extraidos.data_nascimento

        if(s2 == 'Not Found'):
            return {'valid': False, 'percent_match': 0, 
                "trecho_procurado": s1,
                "trecho_encontrado": s2}

        date_1 = datetime.datetime.strptime(s1, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(s2, '%d-%m-%Y')

        is_valid = date_1 == date_2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0, 
                "trecho_procurado": s1,
                "trecho_encontrado": s2}
