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
class Comprovante_pagamento_gfd:
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    destinatario: Optional[str] = None
    valor_recolhimento: Optional[str] = None
    data_vencimento: Optional[str] = None
    data_pagamento: Optional[str] = None

@dataclass
class Comprovante_pagamento_gfd_validations:
    validacao_razao_social: str
    validacao_cnpj: str
    validacao_destinatario: str
    validacao_valor_recolhimento: str
    validacao_data_vencimento: str 


class comprovante_pagamento_gfd_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Comprovante_pagamento_gfd(**cartao_proposta)
        self.dados_extraidos = Comprovante_pagamento_gfd(**dados_extraidos)
        self.message_type = message_type

    def set_validate_functions_list(self):
        return list(Comprovante_pagamento_gfd_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type
    

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
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}  

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
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate
    def validacao_destinatario(self, limiar=90):
        """
        Valida se o nome do destinatário do comprovante de pagamento corresponde à Caixa Econômica Federal.
    
        Lógica de Retorno:
        - TRUE: Se o nome do destinatário for correspondente a "CAIXA ECONOMICA FEDERAL" ou "CEF MATRIZ";
        - FALSE: Caso contrário.
        """

        destinatario = self.dados_extraidos.destinatario
        destinatario_comp = "CAIXA ECONOMICA FEDERAL"
        destinatario_comp_2 = "CEF MATRIZ"

        sim_score_1 = distances(destinatario.upper(), destinatario_comp.upper()).norm_score()
        sim_score_2 = distances(destinatario.upper(), destinatario_comp_2.upper()).norm_score()

        if sim_score_1 >= limiar or sim_score_2 >= limiar:
            return {'valid': True, 'percent_match': max(sim_score_1, sim_score_2)}
        else:
            return {'valid': False, 'percent_match': max(sim_score_1, sim_score_2)}


    @validate     
    @required_docs('gfd')
    def validacao_valor_recolhimento(self, gfd):
        """
        Valida se o valor do recolhimento extraído corresponde ao valor do recolhimento extraído do documento GFD.
    
        Lógica de Retorno:
        - TRUE: Se o valor for igual;
        - FALSE: Caso contrário.
        """

        if(gfd is None):
            return {'valid': False, 'percent_match': 0, 'target': 'valor_recolhimento',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = gfd['valor_recolhimento']
        s2 = self.dados_extraidos.valor_recolhimento
        
        s1 = ''.join(re.findall(r'[\d]+[\.,\d]*', s1))
        s1 = float(s1.replace(".", "").replace(",", "."))

        s2 = ''.join(re.findall(r'[\d]+[\.,\d]*', s2))
        s2 = float(s2.replace(".", "").replace(",", "."))

        if s1 == s2:
            return {'valid': True, 'percent_match': 100, 'target': 'valor_recolhimento',
                    "trecho_procurado": str(s1), "trecho_encontrado": str(s2)}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'valor_recolhimento',
                    "trecho_procurado": str(s1), "trecho_encontrado": str(s2)}


    @validate
    @required_docs('gfd')
    def validacao_data_vencimento(self, gfd):
        """
        Valida se a data de vencimento extraída corresponde a data de vencimento extraída do documento GFD.
    
        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        if(gfd is None):
            return {'valid': False, 'percent_match': 0, 'target': 'data_vencimento',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        data_vencimento1 = datetime.datetime.strptime(self.dados_extraidos.data_vencimento, '%d-%m-%Y').date() if self.dados_extraidos.data_vencimento != 'Not Found' else self.dados_extraidos.data_vencimento
        data_vencimento2 = datetime.datetime.strptime(gfd['data_vencimento'], '%d-%m-%Y').date()

        if data_vencimento1 == data_vencimento2:
            return {'valid': True, 'percent_match': 100, 'target': 'data_vencimento',
                    "trecho_procurado": gfd['data_vencimento'], "trecho_encontrado": self.dados_extraidos.data_vencimento}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'data_vencimento',
                    "trecho_procurado": gfd['data_vencimento'], "trecho_encontrado": self.dados_extraidos.data_vencimento}
