import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from validacao_endereco import Validacao_endereco, Endereco
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Ficha_registro:
    razao_social: str
    cnpj: str
    endereco_empresa: Endereco
    nome: str
    endereco_pessoal: Endereco
    nome_mae: str
    data_nascimento: str
    cpf: str
    data_admissao: str
    rg: Optional[str] = None
    pis: Optional[str] = None
    cargo: Optional[str] = None
    cbo: Optional[str] = None

@dataclass
class Ficha_registro_validations:
    validacao_razao_social: str
    validacao_cnpj: str
    validacao_endereco_empresa: str
    validacao_nome: str
    validacao_endereco_pessoal: str
    validacao_cpf: str
    validacao_data_admissao: str
    validacao_nome_mae: str 
    validacao_data_nascimento: str 
    validacao_cargo: str 
    validacao_cbo: str 
    #validacao_rg: str
    
@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Ficha_registro_sign:
    espaco_assinatura_empresa: str
    espaco_assinatura_funcionario: str
    assinatura_funcionario: str
    assinatura_empresa: str
    descricao_assinatura_empresa: str
    descricao_assinatura_funcionario: str

@dataclass
class Ficha_registro_sign_validations:
    validacao_assinatura_empresa: str
    validacao_assinatura_funcionario: str


class ficha_registro_validate(ValidateDocument):
    
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        
        self.message_type = message_type
        self.cartao_proposta = Ficha_registro(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Ficha_registro_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Ficha_registro(**dados_extraidos)

    
    def set_validate_functions_list(self):
        return list(Ficha_registro_validations.__annotations__.keys())
    
    def set_validate_sign_functions_list(self):
        return list(Ficha_registro_sign_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type

    @validate
    def validacao_nome(self, limiar=90):
        """
        Valida se o nome do cartao_proposta corresponde ao nome extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.nome
        s2 = self.dados_extraidos.nome
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}
            

    @validate
    def validacao_endereco_pessoal(self):
        """
        Valida se o endereço pessoal do cartao_proposta corresponde ao endereço pessoal extraído da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """

        if not isinstance(self.dados_extraidos.endereco_pessoal, dict):
            return {
                'valid': False,
                'percent_match': 0,
                "trecho_procurado": self.cartao_proposta.endereco_pessoal,
                "trecho_encontrado": self.dados_extraidos.endereco_pessoal,
                "regras_subscricao_errors": 404
            }
        
        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_pessoal, self.dados_extraidos.endereco_pessoal)
        valid, score = val_endereco.validar_endereco()
        
        return {'valid': valid, 'percent_match': score}
    
    
    #@validate
    def validacao_rg(self):
        """
        Valida se o RG do cartao_proposta corresponde ao RG extraído da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se os RGs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.rg))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.rg))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}


    @validate
    def validacao_cpf(self):
        """
        Valida se o CPF do cartao_proposta corresponde ao CPF extraído da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cpf))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
            

    @validate  
    def validacao_data_admissao(self):
        """
        Valida se a data de admissão do cartao_proposta corresponde a data de admissão extraída da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_admissao, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_admissao, '%d-%m-%Y')
        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
    

    @validate
    def validacao_nome_mae(self, limiar=90):
        """
        Valida se o nome da mãe do cartao_proposta corresponde o nome da mãe extraído da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.nome_mae
        s2 = self.dados_extraidos.nome_mae
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}
        

    @validate
    def validacao_data_nascimento(self):
        """
        Valida se a data de nascimento do cartao_proposta corresponde a data de nascimento extraída da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_nascimento, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_nascimento, '%d-%m-%Y')
        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
            

    @validate   
    def validacao_razao_social(self, limiar=90):
        """
        Valida se a razão social do cartao_proposta corresponde a razão social extraída da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}   


    @validate    
    def validacao_cnpj(self):
        """
        Valida se o CNPJ do cartao_proposta corresponde ao CNPJ extraído da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
            

    @validate 
    def validacao_endereco_empresa(self):
        """
        Valida se o endereço empresarial do cartao_proposta corresponde ao endereço empresarial extraído da Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """
        if not isinstance(self.dados_extraidos.endereco_empresa, dict):
            return {
                'valid': False,
                'percent_match': 0,
                "trecho_procurado": self.cartao_proposta.endereco_empresa,
                "trecho_encontrado": self.dados_extraidos.endereco_empresa,
                "regras_subscricao_errors": 404
            }

        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        valid, score = val_endereco.validar_endereco()
        
        return {'valid': valid, 'percent_match': score}
        
    
    @validate
    @required_docs('ctps')
    def validacao_cargo(self, ctps, limiar=95):
        """
        Valida se o cargo extraído da Ficha de Registro corresponde ao cargo extraído da CTPS.
    
        Lógica de Retorno:
        - TRUE: Se os cargos forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 95
        """ 

        if(ctps is None):
            return {'valid': False, 'percent_match': 0, 'target': 'cargo',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}

        s1 = ctps['cargo']
        s2 = self.dados_extraidos.cargo
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': sim_score, 'target': 'cargo',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': sim_score, 'target': 'cargo',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
            
        
    @validate
    @required_docs('ctps', 'esocial')
    def validacao_cbo(self, ctps, esocial):
        """
        Valida se o CBO extraído da Ficha de Registro corresponde ao CBO extraído da CTPS ou esocial.
    
        Lógica de Retorno:
        - TRUE: Se os dígitos forem iguais;
        - FALSE: Caso contrário.
        """
        cbo_referencia = ''.join(re.findall(r'\d+', self.dados_extraidos.cbo))
            
        cbo_ctps = ''.join(re.findall(r'\d+', ctps['cbo'])) if ctps and ctps.get('cbo') else None
        cbo_esocial = ''.join(re.findall(r'\d+', esocial['cbo'])) if esocial and esocial.get('cbo') else None

        if not cbo_ctps and not cbo_esocial:
            return {
                'valid': False,
                'percent_match': 0,
                'target': 'cbo',
                "trecho_procurado": cbo_referencia,
                "trecho_encontrado": "",
                "regras_subscricao_errors": 409
            }

        if cbo_ctps == cbo_referencia or cbo_esocial == cbo_referencia:
            return {
                'valid': True,
                'percent_match': 100,
                'target': 'cbo',
                "trecho_procurado": cbo_referencia,
                "trecho_encontrado": cbo_ctps or cbo_esocial
            }

        return {
            'valid': False,
            'percent_match': 0,
            'target': 'cbo',
            "trecho_procurado": cbo_referencia,
            "trecho_encontrado": cbo_ctps or cbo_esocial
        }
        
    @validate   
    def validacao_assinatura_empresa(self):
        """
        Valida se há assinatura da empresa na Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se há assinatura da empresa;
        - FALSE: Caso contrário.
        """

        assinatura_empresa = self.dados_extraidos.assinatura_empresa

        assinatura_empresa = (lambda x: False if x in {'False', 'false', 'falso', 'Falso'} else True)(assinatura_empresa)
        
        score = 100 if assinatura_empresa else 0
        return {"valid": assinatura_empresa, "target": "assinatura_empresa", "percent_match": score, 
            "trecho_procurado": "",
            "trecho_encontrado": self.dados_extraidos.descricao_assinatura_empresa}
    

    @validate   
    def validacao_assinatura_funcionario(self):
        """
        Valida se há assinatura do funcionário na Ficha de Registro.
    
        Lógica de Retorno:
        - TRUE: Se há assinatura do funcionário;
        - FALSE: Caso contrário.
        """

        assinatura_funcionario = self.dados_extraidos.assinatura_funcionario

        assinatura_funcionario = (lambda x: False if x in {'False', 'false', 'falso', 'Falso'} else True)(assinatura_funcionario)

        score = 100 if assinatura_funcionario else 0
        return {"valid": assinatura_funcionario, "target": "assinatura_funcionario", "percent_match": score, 
            "trecho_procurado": "",
            "trecho_encontrado": self.dados_extraidos.descricao_assinatura_funcionario}
