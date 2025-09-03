import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from validacao_endereco import Validacao_endereco, Endereco
from dataclasses_json import dataclass_json, Undefined

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Contrato_social:
    razao_social: str
    cnpj: str
    endereco_empresa: str
    nomes_assinatura: str
    socios: Optional[str] = None
    tipo_assinatura: Optional[str] = None

@dataclass
class Contrato_social_validations:
    validacao_razao_social: str
    validacao_cnpj: str
    validacao_endereco_empresa: str
    validacao_tipo_assinatura: str
    #validacao_responsaveis_assinatura: str

@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Contrato_social_sign:
    ha_assinatura: str
    ha_registro_orgao_competente: str
    sem_valor_certidao: str
    descricao_sem_valor_certidao: Optional[str] = None
    confianca_sem_valor_certidao: Optional[str] = None
    descricao_assinatura: Optional[str] = None
    confianca_assinatura: Optional[str] = None
    descricao_registro_orgao_competente: Optional[str] = None
    confianca_registro_orgao_competente: Optional[str] = None



@dataclass
class Contrato_social_sign_validations:
    validacao_ha_assinatura: str
    validacao_sem_valor_certidao: str
    validacao_ha_registro_orgao_competente: str


class contrato_social_validate(ValidateDocument):
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.message_type = message_type
        self.cartao_proposta = Contrato_social(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Contrato_social_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Contrato_social(**dados_extraidos)
    
    
    def set_validate_functions_list(self):
        return list(Contrato_social_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Contrato_social_sign_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type
    
    @validate
    def validacao_razao_social(self, limiar=80):
        """
        Valida se a razão social extraída corresponde à razão social do cartão proposta.

        Lógica de Retorno:
        - TRUE: Se a similaridade entre as razões sociais for igual ou superior ao limiar;
        - FALSE: Caso contrário.

        Parâmetros:
        - limiar: Valor mínimo de similaridade para considerar válido (padrão: 80).
        """
        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >= limiar
        return {'valid': is_valid, 'percent_match': sim_score}

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
    def validacao_endereco_empresa(self):
        """
        Valida se o endereço da empresa extraído corresponde ao endereço do cartão proposta.

        Lógica de Retorno:
        - Determinada pela classe Validacao_endereco.
        """
        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        valid, score = val_endereco.validar_endereco()
        
        return {'valid': valid, 'percent_match': score}
        
    def _is_valid(self, campo, confianca, descricao, invert_bool=False):
        set_true = {'TRUE', True, 'VERDADEIRO', 'SIM', 'YES'}
        campo = campo.upper().strip() if isinstance(campo, str) else campo
        if campo in set_true:
            is_valid = True
        else:
            is_valid = False
        is_valid = not is_valid if invert_bool else is_valid
        return {
            "valid": is_valid,
            "percent_match": confianca if is_valid else 0,
            "trecho_procurado": "",
            "trecho_encontrado": f'{descricao}'
        }

    @validate
    def validacao_ha_assinatura(self):
        """
        Valida se o documento está assinado.
    
        Lógica de Retorno:
        - TRUE: Se o documento estiver assinado;
        - FALSE: Caso contrário.
        """
        assinatura = self.dados_extraidos.ha_assinatura
        return self._is_valid(assinatura, self.dados_extraidos.confianca_assinatura, self.dados_extraidos.descricao_assinatura)


    @validate
    def validacao_tipo_assinatura(self):
        """
        Valida o tipo de assinatura do documento em relação ao número de assinantes.

        Lógica de Retorno:
        - TRUE: Se o tipo de assinatura for compatível com o número de assinantes;
        - FALSE: Se o tipo de assinatura for 'em conjunto' e houver apenas um assinante.

        Detalhes:
        - Verifica se o tipo de assinatura 'em conjunto' é válido para o número de assinantes.
        - Considera válido qualquer outro tipo de assinatura ou quando há mais de um assinante.
        """
        nomes_assinatura = self.cartao_proposta.nomes_assinatura
        num_assinantes = len(nomes_assinatura)
        tipo_assinatura = self.dados_extraidos.tipo_assinatura.lower()
        if tipo_assinatura in ['em conjunto', 'individual']:
            return {"valid": True, "percent_match": 100, 
                    "trecho_procurado": "",
                    "trecho_encontrado": tipo_assinatura}
        else:
            return {"valid": False, "percent_match": 0, 
                    "trecho_procurado": "",
                    "trecho_encontrado": tipo_assinatura}

    #@validate
    def validacao_responsaveis_assinatura(self, limiar=90):
        """
        Valida se os responsáveis pela assinatura correspondem aos assinantes do cartão proposta.

        Lógica de Retorno:
        - TRUE: Se todos os assinantes do cartão proposta têm correspondência com os responsáveis pela assinatura;
        - FALSE: Se algum assinante não tem correspondência suficiente com os responsáveis pela assinatura.

        Detalhes:
        - Compara cada assinante do cartão proposta com todos os responsáveis pela assinatura.
        - Utiliza um algoritmo de similaridade para calcular a correspondência entre nomes.
        - Se nenhum responsável pela assinatura corresponder a um assinante acima do limiar, a validação falha.
        - A pontuação final é a média das melhores correspondências para cada assinante.

        Parâmetros:
        - limiar: Valor mínimo de similaridade para considerar uma correspondência válida (padrão: 90).
        """
        nomes_assinatura_de = self.dados_extraidos.nomes_assinatura.split(',')
        nomes_assinatura_de = [i.strip() for i in nomes_assinatura_de]
        nomes_assinatura_cp = self.cartao_proposta.nomes_assinatura
        
    
        for i in nomes_assinatura_cp:
            assinante_score = 0
            scores = []
            for j in nomes_assinatura_de:
                sim_score = distances(i.upper(), j.upper()).norm_score()
                scores.append(sim_score)
            if all(score < limiar for score in scores):
                return {"valid": False, "percent_match": max(scores), 
                    "trecho_procurado": i,
                    "trecho_encontrado": nomes_assinatura_de}
            assinante_score += max(scores)
        final_score = assinante_score/len(nomes_assinatura_cp)
        
        return {"valid": True, "percent_match": final_score, 
                    "trecho_procurado": nomes_assinatura_cp,
                    "trecho_encontrado": nomes_assinatura_de}

    @validate
    def validacao_ha_registro_orgao_competente(self):
        """
        Valida se o documento contém um selo, carimbo ou termo de autenticidade que identifique o órgão competente.
    
        Lógica de Retorno:
        - TRUE: Se o documento conter um selo/carimbo/termo de autenticidade;
        - FALSE: Caso contrário.
        """
        selo = self.dados_extraidos.ha_registro_orgao_competente
        return self._is_valid(selo, self.dados_extraidos.confianca_registro_orgao_competente, self.dados_extraidos.descricao_registro_orgao_competente)     


    @validate
    def validacao_sem_valor_certidao(self):
        """
        Valida se o documento contém um marca d'água com a expressão 'sem valor de certidão'.
    
        Lógica de Retorno:
        - TRUE: Se o documento não conter essa marca d'água;
        - FALSE: Caso contrário.
        """
        sem_valor_certidao = self.dados_extraidos.sem_valor_certidao
        return self._is_valid(sem_valor_certidao, self.dados_extraidos.confianca_sem_valor_certidao, self.dados_extraidos.descricao_sem_valor_certidao, invert_bool=True)
        



    '''    
    @interdoc    
    def validacao_socios(self, qsa, limiar=70):
        set_s1 = set(qsa.socios.split(', '))
        set_s2 = set(self.dados_extraidos.socios.split(', '))
        
        if len(set_s1) != len(set_s2):
            return False, 0
        
        for s1,s2 in zip(sorted(set_s1),sorted(set_s2)):
            sim_score = distances(s1.upper(), s2.upper()).norm_score()
            if sim_score < limiar:
                return False, sim_score
        return True, sim_score
    '''   

        