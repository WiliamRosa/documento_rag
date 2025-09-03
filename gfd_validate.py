import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate, fraud_validate
from Distances import distances
from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined
from fraud_tools import ValidadorMetadadosPDF


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Gfd:
    cnpj: str
    razao_social: str
    quantidade_trabalhadores: Optional[str] = None
    valor_recolhimento: Optional[str] = None
    data_vencimento: Optional[str] = None
    competencia: Optional[str] = None
    data_geracao_guia: Optional[str] = None
    identificador: Optional[str] = None
    tag: Optional[str] = None

@dataclass
class Gfd_validations:
    validacao_cnpj: str
    validacao_razao_social: str
    validacao_numero_vidas: str
    validacao_valor_recolhimento: str
    validacao_data_vencimento: str 
    validacao_competencia: str 
    validacao_identificador: str
    validacao_tag: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Gfd_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Gfd_fraud_validations:
    validacao_metadado_datas: str


class gfd_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Gfd(**cartao_proposta)
        self.message_type = message_type

        if (message_type == "fraud_metadata"):
            self.dados_extraidos = Gfd_fraud(**dados_extraidos)
        else:
            self.dados_extraidos = Gfd(**dados_extraidos)
   

    def set_validate_functions_list(self):
        return list(Gfd_validations.__annotations__.keys())
    
    def set_validate_fraud_functions_list(self):
        return list(Gfd_fraud_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type
    

    @validate
    def validacao_cnpj(self):
        """
        Valida se o CNPJ do cartao_proposta corresponde ao CNPJ extraído.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        if s1[:8] == s2[:8]:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate
    def validacao_razao_social(self, limiar=90):
        """
        Valida se a Razão Social do cartao_proposta corresponde a Razão Social extraída.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': sim_score} 
        else:
            return {'valid': False, 'percent_match': sim_score}     
    
    @validate
    def validacao_tag(self, limiar=95):
        """
        Valida se a Tag extraída corresponde ao padrão esperado: CNPJ + competencia + 'MENSAL'.
    
        Lógica de Retorno:
        - TRUE: Se a TAG estiver dentro do padrão esperado;
        - FALSE: Caso contrário.
        """
        
        tag = self.dados_extraidos.tag
        cnpj = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        competencia = self.dados_extraidos.competencia

        tag_comp = cnpj + " " + competencia + " MENSAL"

        sim_score = distances(tag.upper(), tag_comp.upper()).norm_score()
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': sim_score} 
        else:
            return {'valid': False, 'percent_match': sim_score}    


    @validate     
    @required_docs('gfip_novo')
    def validacao_numero_vidas(self, gfip_novo):
        """
        Valida se a quantidade de trabalhadores extraída corresponde ao número de vidas extraído do documento FGTS/GFIP.
    
        Lógica de Retorno:
        - TRUE: Se o número for igual;
        - FALSE: Caso contrário.
        """

        if(gfip_novo is None):
            return {'valid': False, 'percent_match': 0, 'target': 'quantidade_trabalhadores',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = gfip_novo.get('numero_vidas')
        s2 = self.dados_extraidos.quantidade_trabalhadores

        if(s1 != None):
            s1 = int(s1)

        if s1 == int(s2): 
            return {'valid': True, 'percent_match': 100, 'target': 'quantidade_trabalhadores',
                    "trecho_procurado": s1, "trecho_encontrado": s2}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'quantidade_trabalhadores',
                    "trecho_procurado": s1, "trecho_encontrado": s2}


    @validate     
    @required_docs('gfip_novo')
    def validacao_valor_recolhimento(self, gfip_novo):
        """
        Valida se o valor de recolhimento extraído corresponde ao total da guia extraído do documento FGTS/GFIP.
    
        Lógica de Retorno:
        - TRUE: Se os valores forem iguais;
        - FALSE: Caso contrário.
        """
        if(gfip_novo is None):
            return {'valid': False, 'percent_match': 0, 'target': 'valor_recolhimento',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = gfip_novo.get('total_guia')
        s2 = self.dados_extraidos.valor_recolhimento
        
        s1 = float(s1.replace(".", "").replace(",", "."))
        s2 = float(s2.replace(".", "").replace(",", "."))

        if s1 == s2:
            return {'valid': True, 'percent_match': 100, 'target': 'valor_recolhimento',
                    "trecho_procurado": str(s1), "trecho_encontrado": str(s2)}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'valor_recolhimento',
                    "trecho_procurado": str(s1), "trecho_encontrado": str(s2)}


    @validate     
    @required_docs('gfip_novo')
    def validacao_data_vencimento(self, gfip_novo):
        """
        Valida se a data de vencimento extraída corresponde a data de vencimento extraída do documento FGTS/GFIP.
    
        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """
        if(gfip_novo is None):
            return {'valid': False, 'percent_match': 0, 'target': 'data_vencimento',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        data_vencimento1 = datetime.datetime.strptime(self.dados_extraidos.data_vencimento, '%d-%m-%Y').date()
        data_vencimento2 = datetime.datetime.strptime(gfip_novo.get('data_vencimento'), '%d/%m/%Y').date()

        data_vencimento1_str = data_vencimento1.strftime('%d/%m/%Y')
        data_vencimento2_str = data_vencimento2.strftime('%d/%m/%Y')

        if data_vencimento1 == data_vencimento2:
            return {'valid': True, 'percent_match': 100, 'target': 'data_vencimento',
                    "trecho_procurado": data_vencimento2_str, "trecho_encontrado": data_vencimento1_str}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'data_vencimento',
                    "trecho_procurado": data_vencimento2_str, "trecho_encontrado": data_vencimento1_str}

    @validate     
    @required_docs('gfip_novo')
    def validacao_competencia(self, gfip_novo):
        """
        Valida se a competência extraída corresponde a competência extraída do documento FGTS/GFIP.
    
        Lógica de Retorno:
        - TRUE: Se as competências forem iguais;
        - FALSE: Caso contrário.
        """
        if(gfip_novo is None):
            return {'valid': False, 'percent_match': 0, 'target': 'competencia',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        competencia1 = datetime.datetime.strptime(self.dados_extraidos.competencia, '%m/%Y').date()
        competencia2 = datetime.datetime.strptime(gfip_novo.get('competencia'), '%m/%Y').date()

        competencia1_str = competencia1.strftime('%m/%Y')
        competencia2_str = competencia2.strftime('%m/%Y')

        if competencia1 == competencia2:
            return {'valid': True, 'percent_match': 100, 'target': 'competencia',
                    "trecho_procurado": competencia2_str, "trecho_encontrado": competencia1_str}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'competencia',
                    "trecho_procurado": competencia2_str, "trecho_encontrado": competencia1_str}

    @validate     
    @required_docs('gfip_novo')
    def validacao_identificador(self, gfip_novo):
        """
        Valida se o identificador extraído corresponde o identificador extraído do documento FGTS/GFIP.

        Lógica de Retorno:
        - TRUE: Se os identificadores forem iguais;
        - FALSE: Caso contrário.
        """
        if(gfip_novo is None):
            return {'valid': False, 'percent_match': 0, 'target': 'identificador',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = ''.join(re.findall( r'\d+', gfip_novo.get('identificador')))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.identificador))

        score = 0

        # regra 1
        if s1 == s2:
            score += 0.5

        # regra 2
        data_geracao_guia = self.dados_extraidos.data_geracao_guia.split("-")
        yy = data_geracao_guia[2][2:]
        mm = data_geracao_guia[1]
        dd = data_geracao_guia[0]

        if(yy+mm+dd == s2[2:8]):
            score += 0.5
        
        if(score == 1):
            return {'valid': True, 'percent_match': score, 'target': 'identificador',
                    "trecho_procurado": s1, "trecho_encontrado": s2}
        else:
            return {'valid': False, 'percent_match': score, 'target': 'identificador',
                    "trecho_procurado": s1, "trecho_encontrado": s2}

    @fraud_validate
    @required_docs('gfd')
    def validacao_metadado_datas(self, gfd):
        """
        Valida se a data de emissão extraída do GFD é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se a data de emissão for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """

        if(gfd is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}
        
        val = ValidadorMetadadosPDF()

        creation_date = self.dados_extraidos.creationDate
        data_emissao = gfd.get('data_geracao_guia')

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
        