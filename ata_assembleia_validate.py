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
class Ata_assembleia:
    razao_social: str
    cnpj: str
    endereco_empresa: str
    cargos_eleitos: Optional[str] = None
    departamentos: Optional[str] = None
    data_ata_eleicao: Optional[str] = None
    tempo_mandato: Optional[str] = None

@dataclass
class Ata_assembleia_validations:
    validacao_razao_social: str
    validacao_cnpj: str
    validacao_endereco_empresa: str
    validacao_tempo_mandato: str 

@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Ata_assembleia_sign:
    ha_assinatura: str
    descricao_assinatura: str
    confianca_assinatura: str
    ha_selo: str
    descricao_selo: str
    confianca_selo: str
    ha_carimbo: str
    descricao_carimbo: str
    confianca_carimbo: str
    ha_termo_autenticidade: str
    descricao_termo_autenticidade: str
    confianca_termo_autenticidade: str


@dataclass
class Ata_assembleia_sign_validations:
    validacao_assinatura: str
    validacao_selo_carimbo: str


class ata_assembleia_validate(ValidateDocument):
    
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):

        self.message_type = message_type
        self.cartao_proposta = Ata_assembleia(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Ata_assembleia_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Ata_assembleia(**dados_extraidos)
    
    
    def set_validate_functions_list(self):
        return list(Ata_assembleia_validations.__annotations__.keys())
    
    def set_validate_sign_functions_list(self):
        return list(Ata_assembleia_sign_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type
    

    @validate
    def validacao_razao_social(self, limiar=90):
        """
        Valida se a razão social do cartao_proposta corresponde a razão social extraída da Ata de Assembleia.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
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
        Valida se o CNPJ do cartao_proposta corresponde ao CNPJ extraído da Ata de Assembleia.
    
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
    def validacao_endereco_empresa(self, limiar=0.6):
        """
        Valida se o endereço do cartao_proposta corresponde ao endereço extraído da Ata de Assembleia.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """

        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        valid, score = val_endereco.validar_endereco(limiar)
        
        return {'valid': valid, 'percent_match': score}
    
    @validate
    @required_docs('estatuto_social')
    def validacao_tempo_mandato(self, estatuto_social):
        """
        Valida se o tempo de mandato extraído da Ata de Assembleia corresponde ao tempo de mandato extraído do Estatuto Social.
    
        Lógica de Retorno:
        - TRUE: Se o tempo de mandato for igual entre os documentos;
        - FALSE: Caso contrário.
        """
        
        if(estatuto_social is None):
            return {'valid': False, 'percent_match': 0, 'target': 'tempo_mandato',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        tempo_mandato = estatuto_social['tempo_mandato']
        data_ata_eleicao = datetime.datetime.strptime(self.dados_extraidos.data_ata_eleicao, '%d-%m-%Y').date()
        
        # extrai apenas o numero da variavel tempo_mandato (esta no formato x anos)
        tempo_mandato = re.search(r'\d+', tempo_mandato)
        if(tempo_mandato == None):
            return False, 0
        else:
            tempo_mandato = int(tempo_mandato.group())

        # extrai a data atual
        now = datetime.datetime.now().date()
        
        # calcula a data minima que a ata pode ter, baseado no tempo de mandato
        min_data = now - relativedelta(years=tempo_mandato)
        min_data_str = min_data.strftime('%d-%m-%Y')

        data_ata_eleicao_str = data_ata_eleicao.strftime('%d-%m-%Y')

        if data_ata_eleicao >= min_data: 
            return {'valid': True, 'percent_match': 100, 'target': 'tempo_mandato',
                        "trecho_procurado": data_ata_eleicao_str,
                        "trecho_encontrado": estatuto_social['tempo_mandato'] + " | Data mínima considerada válida: " + min_data_str}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'tempo_mandato',
                        "trecho_procurado": data_ata_eleicao_str,
                        "trecho_encontrado": estatuto_social['tempo_mandato'] + " | Data mínima considerada válida: " + min_data_str}


    @validate   
    def validacao_selo_carimbo(self):
        """
        Valida se há selo ou carimbo no documento.
    
        Lógica de Retorno:
        - TRUE: Se identificar um selo ou carimbo;
        - FALSE: Caso contrário.
        """
        ha_selo = self.dados_extraidos.ha_selo
        if(isinstance(ha_selo, str)):
            ha_selo = (lambda x: False if x in {'False', 'false'} else True)(ha_selo)
        
        ha_carimbo = self.dados_extraidos.ha_carimbo
        if(isinstance(ha_carimbo, str)):
            ha_carimbo = (lambda x: False if x in {'False', 'false'} else True)(ha_carimbo)

        ha_termo_autenticidade = self.dados_extraidos.ha_termo_autenticidade
        if(isinstance(ha_termo_autenticidade, str)):
            ha_termo_autenticidade = (lambda x: False if x in {'False', 'false'} else True)(ha_termo_autenticidade)

        if(ha_selo or ha_carimbo or ha_termo_autenticidade):
            ha_selo_carimbo = True
            confianca = max(int(self.dados_extraidos.confianca_selo), int(self.dados_extraidos.confianca_carimbo), int(self.dados_extraidos.confianca_termo_autenticidade)) 
        else:
            ha_selo_carimbo = False
            confianca = 0 

        return {"valid": ha_selo_carimbo, "target": "selo_carimbo", "percent_match": confianca, 
            "trecho_procurado": "",
            "trecho_encontrado": self.dados_extraidos.descricao_carimbo + " | " + self.dados_extraidos.descricao_selo + " | " + self.dados_extraidos.descricao_termo_autenticidade}
    

    @validate   
    def validacao_assinatura(self):
        """
        Valida se há assinatura no documento.
    
        Lógica de Retorno:
        - TRUE: Se for identificada assinatura;
        - FALSE: Caso contrário.
        """

        ha_assinatura = self.dados_extraidos.ha_assinatura

        if(isinstance(ha_assinatura, str)):
            ha_assinatura = (lambda x: False if x in {'False', 'false'} else True)(ha_assinatura)

        return {"valid": ha_assinatura, "target": "ha_assinatura", "percent_match": self.dados_extraidos.confianca_assinatura, 
            "trecho_procurado": "",
            "trecho_encontrado": self.dados_extraidos.descricao_assinatura}
    
