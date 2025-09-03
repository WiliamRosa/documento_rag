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
class Procuracao:
    razao_social: str
    cnpj: str
    cpf_responsavel: str
    cpfs_procuradores: Optional[str] = None
    lista_poderes: Optional[str] = None
    nome_responsavel: Optional[str] = None
    procuradores: Optional[str] = None
    validade: Optional[str] = None


@dataclass
class Procuracao_validations:
    validacao_cnpj: str
    validacao_cpf_responsavel: str
    validacao_razao_social: str
    validacao_procuradores: str
    validacao_data_validade: str
    validacao_lista_poderes: str

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Procuracao_sign:
    ha_assinatura: str
    ha_selo_carimbo: str
    descricao_assinatura: Optional[str] = None
    confianca_assinatura: Optional[str] = None
    descricao_selo_carimbo: Optional[str] = None
    confianca_selo_carimbo: Optional[str] = None

@dataclass
class Procuracao_sign_validations:
    validacao_ha_assinatura: str
    validacao_ha_selo_carimbo: str



class procuracao_validate(ValidateDocument):

    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Procuracao(**cartao_proposta)
        self.message_type = message_type

        if (message_type == "signature"):
            self.dados_extraidos = Procuracao_sign(
                **dados_extraidos)
        else:
            self.dados_extraidos = Procuracao(**dados_extraidos)

    def set_validate_functions_list(self):
        return list(Procuracao_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Procuracao_sign_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type

    @validate
    def validacao_cnpj(self):
        """
        Valida se o CNPJ do cartao_proposta corresponde ao CNPJ extraído da Procuração.
    
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
    def validacao_cpf_responsavel(self):
        """
        Valida se o CPF do cartao_proposta corresponde ao CPF de algum dos procuradores extraídos da Procuração.
    
        Lógica de Retorno:
        - TRUE: Se os CPF forem iguais;
        - FALSE: Caso contrário.
        """
        s2_list = self.dados_extraidos.cpfs_procuradores.split(",")

        for item in s2_list:
            s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cpf_responsavel))
            s2 = ''.join(re.findall(r'\d+', item))
            if s1 == s2:
                return {'valid': True, 'percent_match': 100, 'target': 'cpf_responsavel',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}
           
        return {'valid': False, 'percent_match': 0}

    @validate
    def validacao_razao_social(self, limiar=90):
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
    def validacao_procuradores(self, limiar=90):
        s1 = self.cartao_proposta.nome_responsavel
        s2_list = self.dados_extraidos.procuradores.split(',')
        max_score = 0
        best_s2 = None
        for s2 in s2_list:
            score = distances(s1, s2.strip()).norm_score()
            if score >= limiar:
                return {'valid': True, 'percent_match': score, 'target': 'procuradores',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}

            if max(0,score) >= max_score:
                max_score = score
                best_s2 = s2

        return {'valid': False, 'percent_match': max_score, 'target': 'procuradores',
                "trecho_procurado": s1,
                "trecho_encontrado": best_s2}

    @validate
    def validacao_data_validade(self):
        """
        Verifica se a vigência da procuração está ativa.

        Lógica de Retorno:
        - TRUE: Caso a data atual esteja entre os intervalos de início e fim de vigência especificados no contrato;
        - FALSE: Caso contrário.
        """
        dates = re.findall(r'\d{2}[-/]\d{2}[-/]\d{4}',
                           self.dados_extraidos.validade)
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
            return {'valid': is_valid, "trecho_procurado": '', "trecho_encontrado": f'Vigência de {start.strftime("%d/%m/%Y")} até {end.strftime("%d/%m/%Y")}',
                'percent_match': 100 if is_valid else 0}
        else:
            formatted_date = converted_dates[0].strftime("%d/%m/%Y")
            return {'valid': False, 'percent_match': 0, "trecho_procurado": '',
                "trecho_encontrado": str(formatted_date), "regras_subscricao_errors": 422}
            
    def _is_valid(self, campo, confianca, descricao, target):
        set_true = {'True', 'true', True, 'Verdadeiro',
                    'verdadeiro', 'VERDADEIRO', 'TRUE'}

        if campo in set_true:
            is_valid = True
        else:
            is_valid = False
        return {
            "valid": is_valid,
            "target": target,
            "percent_match": confianca,
            "trecho_procurado": "",
            "trecho_encontrado": descricao
        }

    @validate
    def validacao_lista_poderes(self):
        """
        Valida se o procurador pode assinar um documento ou não.
    
        Lógica de Retorno:
        - TRUE: Se for identificao o poder para assinar documentos;
        - FALSE: Caso contrário.
        """

        ha_poder = self.dados_extraidos.lista_poderes

        if(isinstance(ha_poder, str)):
            ha_poder = (lambda x: False if x in {'False', 'false', False, 'Falso', 'FALSO', 'FALSE'} else True)(ha_poder)

        return {"valid": ha_poder, "target": "lista_poderes", "percent_match": 100 if ha_poder else 0, 
            "trecho_procurado": "", "trecho_encontrado": str(ha_poder)}

        
    @validate
    def validacao_ha_assinatura(self):
        """
        Valida se o documento está assinado.

        Lógica de Retorno:
        - TRUE: Se o documento estiver assinado;
        - FALSE: Caso contrário.
        """
        assinatura = self.dados_extraidos.ha_assinatura
        return self._is_valid(assinatura, self.dados_extraidos.confianca_assinatura, self.dados_extraidos.descricao_assinatura, 'ha_assinatura')

    @validate
    def validacao_ha_selo_carimbo(self):
        """
        Valida se o documento contém um selo ou carimbo.

        Lógica de Retorno:
        - TRUE: Se o documento conter um selo;
        - FALSE: Caso contrário.
        """
        selo = self.dados_extraidos.ha_selo_carimbo
        return self._is_valid(selo, self.dados_extraidos.confianca_selo_carimbo, self.dados_extraidos.descricao_selo_carimbo, 'ha_selo_carimbo')