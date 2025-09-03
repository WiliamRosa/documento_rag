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
class Mei:
    razao_social: str
    cnpj: str
    endereco_empresa: Endereco
    nome: Optional[str] = None
    cpf: Optional[str] = None
    situacao_cadastral: Optional[str] = None
    numero_cnae: Optional[str] = None
    data_situacao_cadastral: Optional[str] = None
    data_abertura_empresa: Optional[str] = None


@dataclass
class Mei_validations:
    validacao_razao_social: str
    validacao_cnpj: str
    validacao_endereco_empresa: str 
    validacao_situacao_cadastral: str
    validacao_nome: str 
    validacao_cpf: str 
    validacao_cnae: str
    validacao_data_situacao_cadastral: str 
    validacao_data_abertura_empresa: str 


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Mei_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Mei_fraud_validations:
    validacao_metadado_datas: str


class mei_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Mei(**cartao_proposta)
        self.message_type = message_type

        if (message_type == "fraud_metadata"):
            self.dados_extraidos = Mei_fraud(**dados_extraidos)
        else:
            self.dados_extraidos = Mei(**dados_extraidos)

    def set_validate_functions_list(self):
        return list(Mei_validations.__annotations__.keys())
    
    def set_validate_fraud_functions_list(self):
        return list(Mei_fraud_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type



    @validate
    def validacao_razao_social(self, limiar=90):
        """
        Valida se a razão social do cartao_proposta corresponde a razão social extraída do MEI.
    
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
        Valida se o CNPJ do cartao_proposta corresponde ao CNPJ extraído do MEI.
    
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
        Valida se o endereço do cartao_proposta corresponde ao endereço extraído do MEI.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """

        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        valid, score = val_endereco.validar_endereco()
        
        return {'valid': valid, 'percent_match': score}   
        

    @validate
    def validacao_situacao_cadastral(self):
        """
        Valida se a situação cadastral extraída do MEI está com status ativo.
    
        Lógica de Retorno:
        - TRUE: Se o status estiver ativo;
        - FALSE: Caso contrário.
        """

        situacao = ["ATIVA", "ATIVO"]
        if self.dados_extraidos.situacao_cadastral.upper() in situacao:
            return {'valid': True, 'percent_match': 100}   
        else:
            return {'valid': False, 'percent_match': 0}   
            
            
    @validate
    @required_docs('rg', 'cnh')
    def validacao_nome(self, rg, cnh, limiar=90):
        """
        Valida se o nome extraído do MEI corresponde ao nome (no RG ou CNH) do representante legal.

        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        if(rg is None and cnh is None):
            return {'valid': False, 'percent_match': 0, 'target': 'nome',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = rg['nome'] if rg is not None else cnh['nome']
        s2 = self.dados_extraidos.nome
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': 100, 'target': 'nome',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'nome',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}  
            
        
    @validate
    @required_docs('rg', 'cnh')
    def validacao_cpf(self, rg, cnh):
        """
        Valida se o CPF extraído do MEI corresponde ao CPF (no RG ou CNH) do representante legal.

        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """

        if(rg is None and cnh is None):
            return {'valid': False, 'percent_match': 0, 'target': 'cpf',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = rg['cpf'] if rg is not None else cnh['cpf']

        s1 = ''.join(re.findall(r'\d+', s1))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100, 'target': 'cpf',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'cpf',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
            

    @validate
    @required_docs('cnpj')
    def validacao_cnae(self, cnpj):
        """
        Valida se o número do CNAE extraído do MEI corresponde ao CNAE extraído do CNPJ.

        Lógica de Retorno:
        - TRUE: Se os números forem iguais;
        - FALSE: Caso contrário.
        """

        if(cnpj is None):
            return {'valid': False, 'percent_match': 0, 'target': 'cnae',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}

        s1 = ''.join(re.findall( r'\d+', cnpj.get('numero_cnae')))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.numero_cnae))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100, 'target': 'numero_cnae',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'numero_cnae',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
           
                            
    @validate
    @required_docs('cnpj')
    def validacao_data_situacao_cadastral(self, cnpj):
        """
        Valida se a data da situação cadastral extraída do MEI corresponde a data da situação cadastral extraída do CNPJ.

        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        if(cnpj is None):
            return {'valid': False, 'percent_match': 0, 'target': 'data_situacao_cadastral',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        
        s1 = cnpj.get('data_situacao_cadastral')
        s2 = self.dados_extraidos.data_situacao_cadastral

        if(s1 == 'Not Found' or s2 == 'Not Found'):
            return {'valid': False, 'percent_match': 0, 'target': 'data_situacao_cadastral',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}

        date_1 = datetime.datetime.strptime(s1, '%d-%m-%Y')
        date_2 = datetime.datetime.strptime(s2, '%d-%m-%Y')

        date_1_str = date_1.strftime('%d/%m/%Y')
        date_2_str = date_2.strftime('%d/%m/%Y')

        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100, 'target': 'data_situacao_cadastral',
                        "trecho_procurado": date_2_str,
                        "trecho_encontrado": date_1_str}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'data_situacao_cadastral',
                        "trecho_procurado": date_2_str,
                        "trecho_encontrado": date_1_str}
    
    
    @validate
    @required_docs('cnpj')
    def validacao_data_abertura_empresa(self, cnpj):
        """
        Valida se a data de abertura da empresa extraída do MEI corresponde a data de abertura da empresa extraída do CNPJ.

        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        if(cnpj is None):
            return {'valid': False, 'percent_match': 0, 'target': 'data_abertura_empresa',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = cnpj.get('data_abertura')
        s2 = self.dados_extraidos.data_abertura_empresa

        if(s1 == 'Not Found' or s2 == 'Not Found'):
            return {'valid': False, 'percent_match': 0, 'target': 'data_abertura_empresa',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}

        date_1 = datetime.datetime.strptime(s1, '%d-%m-%Y')
        date_2 = datetime.datetime.strptime(s2, '%d-%m-%Y')

        date_1_str = date_1.strftime('%d/%m/%Y')
        date_2_str = date_2.strftime('%d/%m/%Y')

        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100, 'target': 'data_abertura_empresa',
                        "trecho_procurado": date_2_str,
                        "trecho_encontrado": date_1_str}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'data_abertura_empresa',
                        "trecho_procurado": date_2_str,
                        "trecho_encontrado": date_1_str}
    

    @fraud_validate
    @required_docs('mei')
    def validacao_metadado_datas(self, mei):
        """
        Valida se a data de emissão extraída do MEI é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se a data de emissão for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """
        
        if(mei is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}

        val = ValidadorMetadadosPDF()

        creation_date = self.dados_extraidos.creationDate
        data_emissao = mei.get('data_emissao')

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
    