import re
import datetime
from fraud_tools import SimilarTextValidator, ValidadorMetadadosPDF
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate, fraud_validate
from Distances import distances
from dataclasses import dataclass
from typing import Optional
from validacao_endereco import Validacao_endereco, Endereco
from dataclasses_json import dataclass_json, Undefined
import os

 
@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Comprovante_residencia:
    nome: str
    endereco_pessoal: Endereco
    data_referencia: Optional[str] = None
    vencimento: Optional[str] = None
    data_emissao: Optional[str] = None
    data_emissao_documento: Optional[str] = None

@dataclass
class Comprovante_residencia_validations:
    validacao_data_emissao: str
    validacao_endereco_pessoal: str
    validacao_nome: str
    validacao_fraude_docs_similares: str

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Comprovante_residencia_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Comprovante_residencia_fraud_validations:
    validacao_metadado_datas: str


class comprovante_residencia_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Comprovante_residencia(**cartao_proposta)
        self.message_type = message_type

        if (message_type == "fraud_metadata"):
            self.dados_extraidos = Comprovante_residencia_fraud(**dados_extraidos)
        else:
            self.dados_extraidos = Comprovante_residencia(**dados_extraidos)
   
    
    def set_validate_functions_list(self):
        return list(Comprovante_residencia_validations.__annotations__.keys())

    def set_validate_fraud_functions_list(self):
        return list(Comprovante_residencia_fraud_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type

    
    @validate
    def validacao_endereco_pessoal(self):
        """
        Valida se o endereço do cartao_proposta corresponde ao endereço extraído do comprovante de residência.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """

        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_pessoal, self.dados_extraidos.endereco_pessoal)
        is_valid, score = val_endereco.validar_endereco()

        return {'valid': is_valid, 'percent_match': score}

    @validate
    def validacao_data_emissao(self):
        """
        Valida se a data de emissão extraída do comprovante de residência está dentro do intervalo de dois meses a partir da data atual.
    
        Lógica de Retorno:
        - TRUE: Se tiver dentro do intervalo especificado;
        - FALSE: Caso contrário.
        """
        data_referencia = datetime.datetime.strptime(self.dados_extraidos.data_referencia, '%m/%Y').date() if self.dados_extraidos.data_referencia != 'Not Found' else self.dados_extraidos.data_referencia
        vencimento = self.dados_extraidos.vencimento
        if(vencimento != 'Not Found' and data_referencia != 'Not Found'):
            vencimento = datetime.datetime.strptime(vencimento, '%d-%m-%Y').date()
            data_emissao = vencimento if vencimento > data_referencia else data_referencia
        else:
            data_emissao = data_referencia
            return {'valid': False, 'percent_match': 0, 'target': 'data_emissao', 'trecho_encontrado': data_emissao, 'regras_subscricao_errors': 404}
 
        # atribui o valor da data de emissao ao objeto
        self.dados_extraidos.data_emissao = data_emissao.strftime('%m/%Y')
        
        now = datetime.datetime.now().date()
        now = now - relativedelta(day=1)
        #min_data = now - relativedelta(months=2)
        # min_data = now - relativedelta(months=1)
        min_data = now - relativedelta(months=5)
        
        if data_emissao >= min_data: 
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate     
    @required_docs('certidao_casamento', 'rg', 'cnh', 'escritura_uniao_estavel')
    def validacao_nome(self, certidao_casamento, rg, cnh, escritura_uniao_estavel, limiar=90):
        """
        Valida se o nome extraído do comprovante de residência corresponde ao nome do titular, dos pais do titular ou cônjuge do titular.
        O nome do titular é extraído do cartao_proposta, os nomes pais do titular do RG ou CNH e 
        o nome do cônjuge é verificado com a certidão de casamento ou escritura de uniao estavel.

        Lógica de Retorno:
        - TRUE: Se o nome extraído for igual a um dos nomes aceitos;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """
        
        s1 = self.dados_extraidos.nome
        nome_titular_cp = self.cartao_proposta.nome

        lista_nomes = []
        lista_nomes.append(nome_titular_cp)

        for documento in [certidao_casamento, escritura_uniao_estavel]:
            if documento is not None:
                score_1 = distances(documento['nome_titular'], nome_titular_cp).norm_score()
                score_2 = distances(documento['nome_dependente'], nome_titular_cp).norm_score()
                if(score_1 >= 90 or score_2 >= 90):
                    lista_nomes.extend([documento['nome_dependente'], documento['nome_titular']])

        for documento in [rg, cnh]:
            if documento is not None:
                lista_nomes.extend([documento['nome_pai'], documento['nome_mae']])

        best_score = 0
        invalid_to_return = None
        for s2 in lista_nomes:
            score = distances(s1, s2).norm_score()
            if score >= limiar:
                return {'valid': True, 'percent_match': score, 'target': 'nome',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
            else:
                if score > best_score:
                    best_score = score
                    invalid_to_return =  {'valid': False, 'percent_match': score, 'target': 'nome',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1,
                        "regras_subscricao_errors": 422}
        
        if invalid_to_return is not None:
            return invalid_to_return

        # checa se faltou algum documento 
        documento_estado_civil = certidao_casamento is None and escritura_uniao_estavel is None
        documento_pessoal = rg is None and cnh is None
        if(documento_estado_civil and documento_pessoal):
            return {'valid': False, 'percent_match': score, 'target': 'nome',
                        "trecho_procurado": ', '.join(lista_nomes),
                        "trecho_encontrado": s1,
                        "regras_subscricao_errors": 409}

        return {'valid': False, 'percent_match': score, 'target': 'nome',
                        "trecho_procurado": ', '.join(lista_nomes),
                        "trecho_encontrado": s1}
 

    @fraud_validate
    @required_docs('comprovante_residencia', include_docs_same_type_from_proposal=True)
    def validacao_fraude_docs_similares(self, comprovante_residencia, limiar=.85):
        # ID do documento atual (definido em variável de ambiente)
        doc_atual = comprovante_residencia.get('doc_atual')
        doc_list = comprovante_residencia.get('doc_list')
        # Se não há outros documentos, adiciona a logica de esperar doc para o retry.
        # Caso exceda as 5 tentativas, o status sera alterado para OK dentro da funcao no
        # arquivo de conexoes com o Mongo e retornara como válido.
        # Lógica adicionada pois pode ser que o doc de comparação ainda nao tenha sido salvo
        # no banco.
        texto_extraido = doc_list[0]['extracted_text']
        if not doc_list or not texto_extraido:
            return {
                'valid': True,
                'target': 'fraude_docs_similares',
                'trecho_encontrado': 'Não há outros documentos na mesma proposta',
                'fraud_errors': 409
            }

        # Valida similaridade entre o texto atual e os demais
        similar_texts = SimilarTextValidator(corpus_texts=doc_list)
        alerts = similar_texts.validate(doc_atual, threshold=limiar, metric="sequential")
        if not alerts:
            return {'valid': True, 'target': 'fraude_docs_similares',
                    "trecho_encontrado": "Sem indícios de duplicidade"}
        #formato de alerts: [{'id': 123. 'score': 94}, {'id: 234, 'score':96}]
        highest_score_item = max(alerts, key=lambda x: x['score'])
        highest_score = highest_score_item['score']
        str_list_alerts = []
        for item in alerts:
            str_list_alerts.append(f"'nome': '{item['nome']}', 'score': {item['score']}")
        alerts = '; '.join(str_list_alerts)
        return {'valid': False, 'target': 'fraude_docs_similares',
                    "trecho_encontrado": f'Indícios de duplicidade: {alerts}',
                    'percent_match': 100 - float(highest_score) }

    @fraud_validate
    @required_docs('comprovante_residencia')
    def validacao_metadado_datas(self, comprovante_residencia):
        """
        Valida se a data de emissão ou data/mês de referência extraída do comprovante de residência é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se o mês de referência for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """
        
        if(comprovante_residencia is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}
        
        val = ValidadorMetadadosPDF()

        creation_date = self.dados_extraidos.creationDate
        data_referencia = comprovante_residencia.get('data_referencia')
        data_emissao = comprovante_residencia.get('data_emissao_documento')

        creation_date_convertida = val.converter_data(creation_date)
        data_emissao_convertida = val._converter_data_emissao(data_emissao)
        
        if(creation_date_convertida == None or data_emissao_convertida == None):
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: " + str(creation_date) + " | Data de emissão: " + str(data_referencia) , "trecho_encontrado": "Data de criação ou data de emissão não encontrada." }

        data_referencia_convertida = datetime.datetime.strptime(f"01/{data_referencia}", "%d/%m/%Y")

        creation_date_str = creation_date_convertida.strftime("%d-%m-%Y")
        data_emissao_str = data_emissao_convertida.strftime("%d-%m-%Y")

        if(data_emissao != 'Not Found'):
            if creation_date_convertida < data_emissao_convertida:
                return {
                    "valid": False, 'percent_match': 0, "trecho_procurado": "Data de criação: "+creation_date_str, 
                    "trecho_encontrado": "Data de criação do arquivo é anterior a data de emissão:" + data_emissao_str
                }
            else:
                return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: "+creation_date_str, "trecho_encontrado": "Data de emissão: "+data_emissao_str }
        else:
            if creation_date_convertida < data_referencia_convertida:
                return {
                    "valid": False, 'percent_match': 0, "trecho_procurado": "Data de criação: "+creation_date_str, 
                    "trecho_encontrado": "Data de criação do arquivo é anterior ao mês de referência:" + data_referencia
                }
            else:
                return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: "+creation_date_str, "trecho_encontrado": "Mês de referência: "+data_referencia }
