import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate, fraud_validate
from Distances import distances
from dataclasses import dataclass
from typing import Optional
from validacao_endereco import Validacao_endereco, Endereco
from dataclasses_json import dataclass_json, Undefined
from fraud_tools import ValidadorMetadadosPDF

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Cnpj:
    cnpj: str
    razao_social: str
    situacao_cadastral: Optional[str] = None
    natureza_juridica: Optional[str] = None
    data_abertura: Optional[str] = None

@dataclass
class cnpj_validations:
    validacao_cnpj: str
    validacao_razao_social: str
    validacao_situacao_cadastral: str
    validacao_natureza_juridica: str
    validacao_data_abertura: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Cnpj_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Cnpj_fraud_validations:
    validacao_metadado_datas: str



class cnpj_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.message_type = message_type
        self.cartao_proposta = Cnpj(**cartao_proposta)

        if (message_type == "fraud_metadata"):
            self.dados_extraidos = Cnpj_fraud(**dados_extraidos)
        else:
            self.dados_extraidos = Cnpj(**dados_extraidos)
   
    def set_validate_functions_list(self):
        return list(cnpj_validations.__annotations__.keys())
    
    def set_validate_fraud_functions_list(self):
        return list(Cnpj_fraud_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type
    

    @validate        
    def validacao_situacao_cadastral(self):
        """
        Valida se a situação cadastral extraída da Ficha de Registro corresponde à situação 'ATIVA'.

        A validação compara a situação cadastrada com o valor "ATIVA" e retorna:
        - TRUE: Se a situação for "ATIVA".
        - FALSE: Se a situação for diferente de "ATIVA".
        """

        s1 = self.dados_extraidos.situacao_cadastral
        
        if s1=='ATIVA':
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "", "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': 0, "trecho_procurado": "", "trecho_encontrado": s1}

    @validate        
    def validacao_natureza_juridica(self):
        """
        Valida se a natureza jurídica extraída do cartão cnpj corresponde ao valor esperado "2135".

        A validação compara o código com "2135" e retorna:
        - TRUE: Se o código da natureza jurídica for diferente de "2135".
        - FALSE: Se for igual a "2135".
        """
        if self.dados_extraidos.natureza_juridica is None:
            return {'valid': False, 'percent_match': 0, "trecho_procurado": "Diferente de 2135", 
                "trecho_encontrado": "", "regras_subscricao_errors": 422}

        s1 = ''.join(re.findall( r'\d+', self.dados_extraidos.natureza_juridica))
        if s1=='2135':
            return {'valid': False, 'percent_match': 0, "trecho_procurado": "Diferente de 2135", "trecho_encontrado": self.dados_extraidos.natureza_juridica}
        else:
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "Diferente de 2135", "trecho_encontrado": self.dados_extraidos.natureza_juridica}

    @validate        
    def validacao_razao_social(self, limiar=80):
        """
        Valida se a razão social extraída do cartão cnpj corresponde à razão social do cartão de proposta,
        utilizando uma comparação de similaridade com um limiar mínimo.

        A validação compara as duas razões sociais e retorna:
        - TRUE: Se a similaridade for maior ou igual ao limiar (default: 80).
        - FALSE: Se a similaridade for menor que o limiar.
        """
        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >=limiar
        return {'valid': is_valid, 'percent_match': limiar}  
          
    @validate      
    def validacao_cnpj(self):
        """
        Valida se o CNPJ extraído do cartão de proposta corresponde ao CNPJ extraído do cartão cnpj.

        A validação compara os dois CNPJs e retorna:
        - TRUE: Se o CNPJ for igual.
        - FALSE: Se o CNPJ for diferente.
        """
        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        is_valid = s1 == s2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0} 

    @validate        
    def validacao_data_abertura(self):
        """
        Valida se a data de abertura extraída do cartão de proposta corresponde à data de abertura extraída da Ficha de Registro.

        A validação compara as duas datas de abertura e retorna:
        - TRUE: Se as datas forem iguais.
        - FALSE: Se as datas forem diferentes.
        """
        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_abertura, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_abertura, '%d-%m-%Y')
        is_valid = date_1 == date_2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}
        

    
    @fraud_validate
    @required_docs('cnpj')
    def validacao_metadado_datas(self, cnpj):
        """
        Valida se a data de emissão extraída do CNPJ é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se a data de emissão for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """

        if(cnpj is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}
        
        val = ValidadorMetadadosPDF()

        creation_date = self.dados_extraidos.creationDate
        data_emissao = cnpj.get('data_emissao')

        creation_date_convertida = val.converter_data(creation_date)
        data_emissao_convertida = val._converter_data_emissao(data_emissao)
        
        creation_date_str = creation_date_convertida.strftime("%d-%m-%Y") if creation_date_convertida is not None else creation_date
        data_emissao_str = data_emissao_convertida.strftime("%d-%m-%Y") if data_emissao_convertida is not None else data_emissao

        if(creation_date_convertida == None or data_emissao_convertida == None):
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: " + creation_date_str + " | Data de emissão: " + data_emissao_str, "trecho_encontrado": "Data de criação ou data de emissão não encontrada." }

        if creation_date_convertida < data_emissao_convertida:
            return {
                "valid": False, 'percent_match': 0, "trecho_procurado": "Data de criação: "+creation_date_str, 
                "trecho_encontrado": "Data de criação do arquivo é anterior a data de emissão:" + data_emissao_str
            }
        else:
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: "+creation_date_str, "trecho_encontrado": "Data de emissão: " +data_emissao_str}
        