import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from Distances import distances
from ValidateDocument import ValidateDocument, required_docs, validate
from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Certidao_casamento:
    nome_titular: str
    nome: str
    nome_mae_titular: str
    nome_mae: str
    data_nascimento_titular: str
    data_nascimento: str
    data_registro_civil: Optional[str] = None
    numero_matricula: Optional[str] = None
    cpf_titular: Optional[str] = None
    cpf: Optional[str] = None
    

@dataclass
class Certidao_casamento_validations:
    validacao_nome_titular: str
    validacao_nome_dependente: str
    validacao_nome_mae_titular: str
    validacao_nome_mae_dependente: str
    validacao_data_nascimento_titular: str
    validacao_data_nascimento_dependente: str
    validacao_cpf_titular: Optional[str] = None
    validacao_cpf_dependente: Optional[str] = None
    
    
    
@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Certidao_casamento_sign:
    ha_selo_carimbo: str
    descricao_selo_carimbo: str
    confianca: str

@dataclass
class Certidao_casamento_sign_validations:
    validacao_selo_carimbo: str


class certidao_casamento_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):

        self.message_type = message_type
        self.cartao_proposta = Certidao_casamento(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Certidao_casamento_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Certidao_casamento(**dados_extraidos)
            self.checa_titular_dependente()
    
    def set_validate_functions_list(self):
        return list(Certidao_casamento_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Certidao_casamento_sign_validations.__annotations__.keys())
    
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
            
            # Troca de CPF do titular e dependente (opcional, se aplicável)
            self.dados_extraidos.cpf_titular, self.dados_extraidos.cpf = (
                self.dados_extraidos.cpf,
                self.dados_extraidos.cpf_titular
            )
            
            # Troca de nome dos pais
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
    def validacao_nome_titular(self):
        """
        Valida se o nome do titular do cartao proposta corresponde ao nome do titular extraído da certidão.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """
        tit_cp = self.cartao_proposta.nome_titular
        tit_de = self.dados_extraidos.nome_titular
        is_valid, score = self._validar_nome(tit_cp, tit_de)
        return {"valid": is_valid, "percent_match": score}

    @validate       
    def validacao_nome_dependente(self):
        """
        Valida se o nome do dependente (cônjuge do titular) do cartao proposta corresponde ao nome do dependente extraído da certidão.
    
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
        
    
    @validate
    def validacao_nome_mae_titular(self):
        """
        Valida se o nome da mãe do titular do cartao proposta corresponde ao nome da mãe do titular extraído da certidão.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """
        mae_tit_cp = self.cartao_proposta.nome_mae_titular
        mae_tit_de = self.dados_extraidos.nome_mae_titular

        is_valid, score = self._validar_nome(mae_tit_cp, mae_tit_de)
        return {"valid": is_valid, "percent_match": score}
    
    @validate
    def validacao_nome_mae_dependente(self):
        """
        Valida se o nome da mãe do dependente (cônjuge do titular) do cartao proposta corresponde ao nome da mãe do dependente extraído da certidão.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """    
        mae_dep_cp = self.cartao_proposta.nome_mae
        mae_dep_de = self.dados_extraidos.nome_mae

        is_valid, score = self._validar_nome(mae_dep_cp, mae_dep_de)
        return {"valid": is_valid, "percent_match": score, 
                "trecho_procurado": mae_dep_cp,
                "trecho_encontrado": mae_dep_de}
        
        
    def _validar_data_nascimento(self, dn_cp, dn_de):
        date_1 = datetime.strptime(dn_cp, '%d/%m/%Y')
        date_2 = datetime.strptime(dn_de, '%d-%m-%Y')

        is_valid = date_1 == date_2
        score = 100 if is_valid else 0
        return is_valid, score

    @validate    
    def validacao_data_nascimento_titular(self):
        """
        Valida se a data de nascimento do titular do cartao proposta corresponde à data de nascimento do titular extraído da certidão.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """
        dn_tit_cp = self.cartao_proposta.data_nascimento_titular
        dn_tit_de = self.dados_extraidos.data_nascimento_titular
        
        is_valid, score = self._validar_data_nascimento(dn_tit_cp, dn_tit_de)
        return {"valid": is_valid, "percent_match": score}
        
        
    @validate    
    def validacao_data_nascimento_dependente(self):
        """
        Valida se a data de nascimento do dependente (cônjuge do titular) do cartao proposta corresponde à data de nascimento do dependente extraído da certidão.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """
        dn_dep_cp = self.cartao_proposta.data_nascimento
        dn_dep_de = self.dados_extraidos.data_nascimento
        
        is_valid, score = self._validar_data_nascimento(dn_dep_cp, dn_dep_de)
        return {"valid": is_valid, "percent_match": score, 
                "trecho_procurado": dn_dep_cp,
                "trecho_encontrado": dn_dep_de}
        
    def _validar_cpf(self, cpf_cp, cpf_de):

        is_valid = cpf_cp == cpf_de
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0, "trecho_procurado": cpf_cp, "trecho_encontrado": cpf_de}
        
    @validate    
    def validacao_cpf_titular(self):
        """
        Valida se o CPF do titular extraído do cartao_proposta corresponde ao CPF extraído dos dados.
    
        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """
        
        tit_cp = ''.join(re.findall(r'\d+', self.cartao_proposta.cpf_titular))
        tit_de = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf_titular))
        
        return self._validar_cpf(tit_cp, tit_de)
    
    @validate
    def validacao_cpf_dependente(self):
        """
        Valida se o CPF do dependdente extraído do cartao_proposta corresponde ao CPF extraído dos dados.
    
        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """
        
        dep_cp = ''.join(re.findall(r'\d+', self.cartao_proposta.cpf))
        dep_de = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))
         
        return self._validar_cpf(dep_cp, dep_de)

            
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
        
    