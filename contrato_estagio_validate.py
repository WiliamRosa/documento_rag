import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from validacao_endereco import Validacao_endereco, Endereco
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Contrato_estagio:
    nome: str
    razao_social: str
    cnpj: str
    endereco_empresa: Endereco
    endereco_pessoal: Endereco
    instituicao_ensino: Optional[str] = None
    vigencia_contrato: Optional[str] = None


@dataclass
class Contrato_estagio_validations:
    validacao_nome: str
    validacao_razao_social: str
    validacao_endereco_empresa: str
    validacao_cnpj: str
    validacao_endereco_pessoal: str
    validacao_instituicao_ensino: str
    validacao_vigencia_contrato: str


    
@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Contrato_estagio_sign:
    assinatura_estagiario: str
    assinatura_empresa: str
    assinatura_instituicao_ensino: str
    espaco_assinatura_instituicao_ensino: Optional[str] = None
    espaco_assinatura_empresa: Optional[str] = None
    espaco_assinatura_estagiario: Optional[str] = None

@dataclass
class Contrato_estagio_sign_validations:
    validacao_assinatura: str



class contrato_estagio_validate(ValidateDocument):


    def __init__(self, cartao_proposta, dados_extraidos, message_type):

        self.message_type = message_type
        self.cartao_proposta = Contrato_estagio(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Contrato_estagio_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Contrato_estagio(**dados_extraidos)
    
    def set_validate_functions_list(self):
        return list(Contrato_estagio_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Contrato_estagio_sign_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type
    

    @validate
    def validacao_nome(self, limiar=95):
        """
        Valida se o nome do estagiário extraído do cartao_proposta corresponde ao nome extraído dos dados, com base na similaridade.

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
        is_valid = sim_score >= limiar
        return {'valid': is_valid, 'percent_match': sim_score}

    @validate
    def validacao_razao_social(self, limiar=95):
        """
        Valida se o nome da empresa extraído do cartao_proposta corresponde ao nome extraído dos dados, com base na similaridade.

        Lógica de Retorno:
            - TRUE: Se a similaridade for maior ou igual ao limiar especificado, a validação é considerada válida;
            - FALSE: Caso contrário.
        """
        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >= limiar
        return {'valid': is_valid, 'percent_match': sim_score}

    @validate
    def validacao_instituicao_ensino(self):
        """
        Valida se o nome da instituição de ensino existe.

        Lógica de Retorno:
            - TRUE: Caso o nome da instituição de ensino seja encontrada no documento;
            - FALSE: Quando não existe, retornando o valor 'Not Found'.

        """
        s2 = self.dados_extraidos.instituicao_ensino
        is_valid = s2 != 'Not Found'
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}

    @validate
    def validacao_endereco_pessoal(self):
        """
        Valida se o endereço pessoal do cartao_proposta corresponde ao endereço extraído no documento.

        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """
        val_endereco = Validacao_endereco(
            self.cartao_proposta.endereco_pessoal, self.dados_extraidos.endereco_pessoal)
        valid, score = val_endereco.validar_endereco()

        return {'valid': valid, 'percent_match': score}

    @validate
    def validacao_endereco_empresa(self):
        """
        Valida se o endereço da empresa do cartao_proposta corresponde ao endereço extraído no documento.

        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """
        val_endereco = Validacao_endereco(
            self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)

        valid, score = val_endereco.validar_endereco()

        return {'valid': valid, 'percent_match': score}

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
    def validacao_vigencia_contrato(self):
        """
        Verifica se a vigência do contrato de estágio está ativa.

        Lógica de Retorno:
        - TRUE: Caso a data atual esteja entre os intervalos de início e fim de vigência especificados no contrato;
        - FALSE: Caso contrário.
        """
        pattern = r'\d{2}[-/]\d{2}[-/]\d{4}'
        dates = re.findall(pattern, self.dados_extraidos.vigencia_contrato)

        converted_dates = []
        for date in dates:
            try:
                converted_dates.append(datetime.strptime(date, "%d-%m-%Y"))
            except ValueError:
                converted_dates.append(datetime.strptime(date, "%d/%m/%Y"))

        # Data atual
        date_now = datetime.now()

        # Verificar se a data atual está entre as duas datas
        if len(converted_dates) == 2:
            start, end = converted_dates
            is_valid = start <= date_now <= end
            return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}
        else:
            return {'valid': False, 'percent_match': 0}
        

    @validate   
    def validacao_assinatura(self):
        """
        Valida se o documento está assinado pela empresa, instituição de ensino e pelo estagiário.
    
        Lógica de Retorno:
        - TRUE: Se o documento estiver assinado pelas três partes;
        - FALSE: Caso contrário.
        """

        assinatura_estagiario = self.dados_extraidos.assinatura_estagiario
        falso_set = {'False', 'false', False, 'Falso', 'falso', 'FALSO', 'FALSE'}
        assinatura_estagiario = (lambda x: False if x in falso_set else True)(assinatura_estagiario)

        assinatura_empresa = self.dados_extraidos.assinatura_empresa
        assinatura_empresa = (lambda x: False if x in falso_set else True)(assinatura_empresa)
    
        assinatura_instituicao_ensino = self.dados_extraidos.assinatura_instituicao_ensino
        assinatura_instituicao_ensino = (lambda x: False if x in falso_set else True)(assinatura_instituicao_ensino)

        score = (sum([assinatura_estagiario, assinatura_empresa, assinatura_instituicao_ensino]) / 3)*100

        valid = (lambda score: True if score == 100 else False)(score)

        return {"valid": valid, "percent_match": score, 
            "trecho_procurado": "",
            "trecho_encontrado": ""}
        