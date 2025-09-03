from datetime import datetime
import logging
from abc import ABC, abstractmethod
from functools import wraps
import os
from mongodb_connections import MongoDBConnections
from enum import Enum
import traceback
import re

logger = logging.getLogger(__name__)
UUID = os.environ['UUID']
SQS_RETRY_QUEUE = os.environ['SQS_RETRY_QUEUE']
AGREGADOR = os.environ["AGREGADOR"]
SIMILARITY_LIST = os.environ["SIMILARITY_LIST"]
DOCUMENT_ID = os.environ["DOCUMENT_ID"]
DOCUMENT_LABEL = os.environ["DOCUMENT_LABEL"]

class ValidationResultCode(Enum):
    NAO_ENCONTRADO = 404
    INCORRETO = 400
    INVALIDO = 422 
    ESPERAR_DOCUMENTOS = 409
    ERRO_INTERNO = 500
    SERVICO_INDISPONIVEL = 503
    OK = 200


def required_docs(*docs, include_matriz=False, include_docs_same_type_from_proposal=False):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *func_args, **func_kwargs):
            docs_json = {}
            required_docs_missed = []
            mongo_conn = MongoDBConnections()

            # Garante que UUID e AGREGADOR sejam atualizados para cada execução se vier de os.environ
            current_uuid = os.environ.get('UUID', UUID)
            current_doc_id = os.environ.get('DOCUMENT_ID', DOCUMENT_ID)
            current_agregador = os.environ.get('AGREGADOR', AGREGADOR)
            current_doc_label = os.environ.get('DOCUMENT_LABEL', DOCUMENT_LABEL)
            parent_company = mongo_conn.lookup_parent_company(current_uuid)

            if include_matriz:
                docs_json['matriz'] = {}

            similarity_list = SIMILARITY_LIST.split("|")
            for doc in docs:
                # Busca dados no MongoDB com base no parâmetro
                if include_docs_same_type_from_proposal and doc in similarity_list :
                    docs_json[doc] = mongo_conn.similarity_documents(current_agregador, doc, current_doc_id)
                    
                else:
                    docs_json[doc] = mongo_conn.request_data_mongodb(doc, current_doc_label, current_uuid)
                    if docs_json[doc] is None and doc not in required_docs_missed:
                        required_docs_missed.append(doc)
                    if include_matriz and parent_company:
                        docs_json['matriz'][doc] = mongo_conn.request_data_mongodb(doc, current_doc_label, parent_company)
                        if docs_json['matriz'][doc] is None and doc not in required_docs_missed:
                            required_docs_missed.append(doc)
            # Armazena os dados de documentos faltantes
            self._required_docs_missed_cache = required_docs_missed
            return func(self, *func_args, **func_kwargs, **docs_json)
        return wrapper
    return decorator

def check_error(campo, valid):
    if valid:
        return ValidationResultCode.OK
    if campo is not None:
        # Verifica se campo é string antes de chamar upper()
        if (not isinstance(campo, dict) and isinstance(campo, str) and campo.upper() == "NOT FOUND"):
            return ValidationResultCode.NAO_ENCONTRADO
        else:
            return ValidationResultCode.INCORRETO
    else:
        return ValidationResultCode.INVALIDO


def create_validation_decorator(error_key_name: str):
    def validation_decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Chama a função original
            name_fn = func.__name__
            val_name_fn = name_fn[name_fn.find('_')+1:]
            result = None

            try:
                result = func(self, *args, **kwargs)

            except (ValueError, TypeError) as e:
                if re.search(r'data|tempo', val_name_fn) and val_name_fn != 'metadado_datas':
                    # Erro esperado para funções que lidam com data/tempo
                    print(f"Data não encontrada. Possível erro ao fazer parse de data com datetime")
                    result = {
                        "valid": False,
                        "percent_match": 0,
                        "trecho_encontrado": "",
                        error_key_name: ValidationResultCode.NAO_ENCONTRADO.value
                    }
                else:
                    # Erro interno para outras funções
                    logger.exception(f"Erro interno inesperado durante a validação {val_name_fn}: {e}")
                    result = {
                        "valid": False,
                        "percent_match": 0,
                        "trecho_encontrado": "",
                        error_key_name: ValidationResultCode.ERRO_INTERNO.value
                    }

            except Exception as e:
                # Outros erros não mapeados
                logger.exception(f"Erro não mapeado encontrado durante a validação {val_name_fn}: {e}")
                result = {
                    "valid": False,
                    "percent_match": 0,
                    "trecho_encontrado": "",
                    error_key_name: ValidationResultCode.ERRO_INTERNO.value
                }

            if not isinstance(result, dict):
                logger.info(f"Necessário fornecer como output um payload válido para '{name_fn}'.")
                return None
            
            valid = result.get('valid')
            target = result.get('target', val_name_fn)
            trecho_procurado = result.get('trecho_procurado', getattr(self.cartao_proposta, target, None))
            trecho_encontrado = result.get('trecho_encontrado', getattr(self.dados_extraidos, target, None))

            score = max(0, float(result.get('percent_match', 100)))

            errorcode = result.get(error_key_name, check_error(trecho_encontrado, valid).value)

            if error_key_name == 'regras_subscricao_errors' and errorcode == ValidationResultCode.ESPERAR_DOCUMENTOS.value:
                docs_missed = getattr(self, '_required_docs_missed_cache', [])
                logger.info(f'[INFO] {docs_missed} não disponível ainda para {target}.')
                return {
                    "valid": False,
                    "target": target,
                    "trecho_procurado": "",
                    'trecho_encontrado': docs_missed,
                    "percent_match": 0,
                    error_key_name: ValidationResultCode.ESPERAR_DOCUMENTOS.name
                }
            
            # Retorna o dicionário formatado
            return {
                "valid": valid,
                "target": target,
                "trecho_procurado": trecho_procurado,
                "trecho_encontrado": trecho_encontrado,
                "percent_match": score,
                error_key_name: ValidationResultCode(errorcode).name
            }
        
        wrapper._validate = True
        return wrapper
    return validation_decorator

# Criando instâncias específicas do decorator
validate = create_validation_decorator("regras_subscricao_errors")
fraud_validate = create_validation_decorator("fraud_errors")

class ValidateDocument(ABC):
        
          
    @abstractmethod
    def set_validate_functions_list(self):
        pass

    @abstractmethod
    def get_validate_type(self):
        pass

    def set_validate_sign_functions_list(self):
        pass
    
    def set_validate_fraud_functions_list(self):
        pass

    def validate(self):
        document_validations = {}
        
        if(self.get_validate_type() == "signature"):
            validacoes = self.set_validate_sign_functions_list()
        elif self.get_validate_type() == "fraud_metadata":
            validacoes = self.set_validate_fraud_functions_list()
        else:
            validacoes = self.set_validate_functions_list()
        
        for val in validacoes:
            fn = getattr(self, val)
            try:
                output_fn = fn()
            except Exception as e:
                logger.error(f"Erro Validaçao: {val}")
                logger.error(f"Exception: {e}")
                logger.error(f"Traceback: {traceback.print_exc()}")
                output_fn = {
                    "valid": False,
                    "target": val.replace("validacao_", ""),
                    "trecho_procurado": '',
                    "trecho_encontrado": '',
                    "percent_match": 0,
                    "regras_subscricao_errors": ValidationResultCode(500).name
                }
                document_validations[val] = output_fn
            if output_fn is not None and hasattr(fn, '_validate'):
                document_validations[val] = output_fn
                
        return document_validations
