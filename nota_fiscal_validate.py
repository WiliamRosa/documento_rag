import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate, fraud_validate
from Distances import distances
from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined
from validacao_endereco import Validacao_endereco, Endereco
from fraud_tools import ValidadorMetadadosPDF

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Nota_fiscal:
    razao_social_matriz: str
    cnpj_matriz: str
    endereco_empresa_matriz: str
    razao_social: str
    cnpj: str
    endereco_empresa: str
    tempo_contrato: Optional[str] = None
    data_emissao: Optional[str] = None
    inicio_vigencia_contrato: Optional[str] = None
    document_label: Optional[str] = None

@dataclass
class Nota_fiscal_validations:
    validacao_razao_social_estipulante: str
    validacao_cnpj_estipulante: str
    validacao_endereco_estipulante: str
    validacao_razao_social_subestipulante: str
    validacao_cnpj_subestipulante: str
    validacao_endereco_subestipulante: str
    validacao_data_emissao: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Nota_fiscal_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Nota_fiscal_fraud_validations:
    validacao_metadado_datas: str


class nota_fiscal_validate(ValidateDocument):
    
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Nota_fiscal(**cartao_proposta)
        self.message_type = message_type
    
        if (message_type == "fraud_metadata"):
            self.dados_extraidos = Nota_fiscal_fraud(**dados_extraidos)
        else:
            self.dados_extraidos = Nota_fiscal(**dados_extraidos)
   
    
    def set_validate_functions_list(self):
        return list(Nota_fiscal_validations.__annotations__.keys())
    
    def set_validate_fraud_functions_list(self):
        return list(Nota_fiscal_fraud_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type


    @validate
    def validacao_razao_social_estipulante(self, limiar=90):
        """
        Valida se o nome da estipulante do cartao_proposta corresponde ao nome da estipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.razao_social_matriz
        s2 = self.dados_extraidos.razao_social_matriz
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score, "target": "razao_social_matriz"}
        else:
            return {'valid': False, 'percent_match': sim_score, "target": "razao_social_matriz"}   
              

    @validate 
    def validacao_razao_social_subestipulante(self, limiar=90):
        """
        Valida se o nome da subestipulante do cartao_proposta corresponde ao nome da subestipulante extraído deste documento.
    
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
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': sim_score, "target": "razao_social"}
        else:
            return {'valid': False, 'percent_match': sim_score, "target": "razao_social"}


    @validate 
    def validacao_cnpj_estipulante(self):
        """
        Valida se o CNPJ da estipulante do cartao_proposta corresponde ao CNPJ da estipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj_matriz))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj_matriz))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100, "target": "cnpj_matriz"}
        else:
            return {'valid': False, 'percent_match': 0, "target": "cnpj_matriz"}

    @validate 
    def validacao_cnpj_subestipulante(self):
        """
        Valida se o CNPJ da subestipulante do cartao_proposta corresponde ao CNPJ da subestipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100, "target": "cnpj"}
        else:
            return {'valid': False, 'percent_match': 0, "target": "cnpj"}
    
    
    @validate 
    def validacao_endereco_estipulante(self, limiar=0.7):
        """
        Valida se o endereço da estipulante do cartao_proposta corresponde ao endereço da estipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 1) para considerar a validação válida. 
                                O valor padrão é 0.5
        """
        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa_matriz, self.dados_extraidos.endereco_empresa_matriz)
        valid, score = val_endereco.validar_endereco(limiar)

        return {'valid': valid, 'percent_match': score, "target": "endereco_empresa_matriz"} 

    @validate 
    def validacao_endereco_subestipulante(self, limiar=0.7):
        """
        Valida se o endereço da subestipulante do cartao_proposta corresponde ao endereço da subestipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 1) para considerar a validação válida. 
                                O valor padrão é 0.5
        """
        s1 = self.cartao_proposta.endereco_empresa
        s2 = self.dados_extraidos.endereco_empresa
        val_endereco = Validacao_endereco(s1, s2)
        valid, score = val_endereco.validar_endereco(limiar)
        
        return {'valid': valid, 'percent_match': score, "target": "endereco_empresa"}



    @validate
    def validacao_data_emissao(self):
        """
        Verifica se a nota fiscal foi emitida nos últimos três meses,
        com base na diferença de dias entre a data atual e a data de emissão.

        Regras:
            - Nota Fiscal 1: 1 a 30 dias
            - Nota Fiscal 2: 31 a 60 dias
            - Nota Fiscal 3: 61 a 90 dias
        """
        nota_fiscal_label = self.dados_extraidos.document_label

        # Define os intervalos de dias para cada tipo de nota fiscal
        dias_permitidos = {
            'Nota Fiscal 1 (Competência Último Mês - Mês anterior)': (1, 30),
            'Nota Fiscal 2 (Competência Penúltimo Mês)': (31, 60),
            'Nota Fiscal 3 (Competência Antepenúltimo Mês)': (61, 90),
        }
        intervalo = dias_permitidos.get(nota_fiscal_label)

        data_emissao = datetime.datetime.strptime(self.dados_extraidos.data_emissao, "%d-%m-%Y").date()

        hoje = datetime.date.today()
        diferenca_dias = (hoje - data_emissao).days

        # Verifica se está dentro do intervalo permitido
        is_valid = intervalo[0] <= diferenca_dias <= intervalo[1]

        return {
            'valid': is_valid,
            "target": "data_emissao",
            "trecho_procurado": "",
            "trecho_encontrado": self.dados_extraidos.data_emissao,
            'percent_match': 100 if is_valid else 0
        }
    

    @fraud_validate
    @required_docs('nota_fiscal')
    def validacao_metadado_datas(self, nota_fiscal):
        """
        Valida se a data de emissão extraída do Nota Fiscal é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se a data de emissão for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """

        if(nota_fiscal is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}
        
        val = ValidadorMetadadosPDF()

        creation_date = self.dados_extraidos.creationDate
        data_emissao = nota_fiscal.get('data_emissao')

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
        