from ValidateDocument import ValidateDocument, required_docs, validate
from Distances import distances

from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Carta_nao_adesao:
    nome: str

@dataclass
class Carta_nao_adesao_validations:
    validacao_nome: str
    validacao_assinatura: str

class carta_nao_adesao_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
    
        cartao_proposta["nome"] = cartao_proposta["nome_responsavel"] if "nome_responsavel" in cartao_proposta else cartao_proposta.get("nome")

        self.cartao_proposta = Carta_nao_adesao(**cartao_proposta)
        self.dados_extraidos = Carta_nao_adesao(**dados_extraidos)
        self.message_type = message_type

    def set_validate_functions_list(self):
        return list(Carta_nao_adesao_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type

            
    @validate
    @required_docs('cartao_plano')
    def validacao_nome(self, cartao_plano, limiar=90):
        """
        Valida se o nome extraído da Carta de Não Adesão do sócio corresponde ao nome extraído do Cartão Plano.

        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        if(cartao_plano is None):
            return {'valid': False, 'percent_match': 0, 'target': 'nome',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        s1 = cartao_plano['nome']
        s2 = self.dados_extraidos.nome
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': sim_score, 'target': 'nome',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': sim_score, 'target': 'nome',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}  

                        
    @validate
    def validacao_assinatura(self):
        """
        Sempre gera alerta para analista validar manualmente.
        """

        return {'valid': False, 'percent_match': 0, 'target': 'assinatura',
                        "trecho_procurado": '',
                        "trecho_encontrado": ''}
    