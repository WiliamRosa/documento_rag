from pymongo import MongoClient
import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from datetime import datetime

REGION_NAME     = os.environ['REGION_NAME']
SECRET_NAME     = os.environ['SECRET_NAME']
INFORMATION     = os.environ['INFORMATION']
SIMILARITY_LIST = os.environ["SIMILARITY_LIST"]

dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)

class SecretsManager:
    def __init__(self):
        self.region_name = REGION_NAME
        self.secret_name = SECRET_NAME

    def get_secret(self):

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=self.region_name
        )

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=self.secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e

        return json.loads(get_secret_value_response['SecretString'])


class MongoDBConnections:

    def __init__(self):
        self.secret_instance = SecretsManager()
        self.mongo_secret = self.secret_instance.get_secret()

        self.mongo_client = MongoClient(host=self.mongo_secret['Host'], 
                                    port=int(self.mongo_secret['Port']), 
                                    username=self.mongo_secret['User'], 
                                    password=self.mongo_secret['PWD'], 
                                    connect=True, 
                                    retryWrites=False)
                                    
        self.mdb = self.mongo_client[self.mongo_secret['DB']]

    def lookup_parent_company(self, uuid):
        mdb_object = self.mdb['beneficiarios'].find_one({"id": uuid}) 

        if mdb_object.get('tipo') != 'EMPRESA_FILIAL':
            return None

        if mdb_object.get('tipo') == 'EMPRESA_FILIAL':
            cnpj_matriz = mdb_object['cartao_proposta'].get('cnpj_matriz')
            agregador_matriz = mdb_object['agregador']

        matriz_object = self.mdb['beneficiarios'].find({ 'agregador': agregador_matriz })
        ret = None
        for matriz_data in matriz_object:
            if matriz_data.get('tipo') == 'EMPRESA_MATRIZ' and matriz_data['cartao_proposta'].get('cnpj') == cnpj_matriz:
                ret = matriz_data.get('id')
                return ret
        return ret
    
    def request_data_mongodb(self, document_type, document_label, UUID):
        '''
        mock_db = {
            'certidao_casamento': {"nome_titular":"JOSÉ MENDES FERREIRA JUNIOR",
                "nome_dependente": "MARIA SOUZA PEREIRA",
                "cpf_titular":"Not Found",
                "data_nascimento_titular":"08-02-1991",
                "nome_mae_titular":"ZULEIDE HENRIQUE MENDES FERREIRA",
                "data_nascimento_dependente":"27-09-1991",
                "nome_mae_dependente":"JOSE FERREIRA DE OLIVEIRA | MARIA INES DOS SANTOS SERRA OLIVEIRA",
                "data_registro_civil":"18-07-2009",
                "numero_matricula":"011615 01 55 2009 2 00047 081 0012102-34"
            },
                'cnh': {'numero': '1234567890', 'categoria': 'B'},
                'cpf': {'numero': '123.456.789-00'}
            }
        '''
        if document_type.upper() == "NOTA_FISCAL":
            request = self.mdb['beneficiarios'].find_one({"id": UUID})
            mdb_object = {}

            for data in request['documentos']:
                if data['label'] == document_label:
                    mdb_object.update({'documentos': [data]})

        else:
            mdb_object = self.mdb["beneficiarios"].find_one(
            {"id": UUID},
            {
                "documentos": {
                    "$elemMatch": {
                        "document_type": { "$eq": document_type.upper() },
                        "status": {                                      
                            "$nin": [
                                "ERRO_DOCUMENTO_NAO_IDENTIFICADO",
                                "TIPO_INVALIDO",
                                "ERRO_VALIDACAO_TIPO_DOCUMENTO"
                            ]
                        }
                    }
                }
            })

        if mdb_object is None:
            return None

        if('documentos' not in mdb_object):
            return None

        extracted_information = mdb_object['documentos'][0].get('extracted_information')

        similarity_list = SIMILARITY_LIST.split("|")
        if document_type in similarity_list:
            extracted_information['document_id'] = mdb_object['documentos'][0].get('document_id')

        if extracted_information is None:
            return None

        if document_type.upper() == "GFIP_NOVO":
            agregador = self.mdb["beneficiarios"].find_one({"id": UUID},{"agregador"})
            funcs = self.mdb["funcionario_empresa"].find(
                {"agregador": agregador['agregador']}
            )

            extracted_information['funcionarios'] = []
            
            for f in funcs:
                item = {
                    'cnpj': f.get('cnpj'),
                    'cpf': f.get('cpf'),
                    'nome': f.get('nome'),
                    'proposta_id': f.get('proposta_id'),
                    'agregador': f.get('agregador'),
                    'uuid': f.get('uuid'),
                    'tipo_vinculo': f.get('tipo_vinculo'),
                }
                extracted_information['funcionarios'].append(item)

        extracted_information['label'] = mdb_object['documentos'][0].get('label')
        return extracted_information

    def _return_similar_docs(self, docs_same_type_from_proposal, current_doc_id):
        doc_atual = next((doc for doc in docs_same_type_from_proposal if doc.get('document_id') == current_doc_id), None)
        if doc_atual is None:
                raise ValueError(f'Documento com ID {current_doc_id} não encontrado.')
        doc_text = doc_atual.get('extracted_text', '')
        doc_list = [doc for doc in docs_same_type_from_proposal if doc.get('document_id') != current_doc_id]
        doc_ids = [doc.get('document_id') for doc in docs_same_type_from_proposal if doc.get('document_id') != current_doc_id]

        # Se não há outros documentos, retorna como válido
        if len(doc_ids) == 0:
            return {
                'valid': True,
                'target': 'fraude_docs_similares',
                'trecho_encontrado': 'Não há outros documentos na mesma proposta'
            }
        return {'doc_atual': doc_atual, 'doc_list': doc_list}
        

    def similarity_documents(self, agregador, document_type, current_doc_id):
        '''
        retorno é uma lista com seguinte estrutura
        { 'ctps':
            [
                {
                    'document_id': '1223445',
                    'extracted_text': 'texto extraido arquivo 1'
                },
                {
                    'document_id': '122344555',
                    'extracted_text': 'texto extraido arquivo 2'
                },
                ...
            ]
        }
        '''
        items = self.mdb.beneficiarios.find(
                {'agregador': agregador}
            )

        doc_list = []
        for benef in items:
            nome = benef.get('cartao_proposta', {}).get('nome')
            for doc in benef['documentos']:
                doc_type = doc.get('document_type')
                if doc_type and doc_type.lower() == document_type.lower():
                    ret = {
                        'document_id': doc.get('document_id'),
                        'nome': nome,
                        'extracted_text': doc.get('extracted_text')
                    }
                    doc_list.append(ret)
        return self._return_similar_docs(doc_list, current_doc_id)

    def update_subscription_rules(self, message, output):
        
        information = INFORMATION.split("|")
        # doc que veio da extract information, sem assinatura
        if message['document_type'].lower() in information:
            self.mdb['beneficiarios'].update_one({
                'id': message['uuid'],
                'documentos.document_id': message['document_id']
            },
            {
                '$set': {
                    'documentos.$.subscription_rules': output,
                    'documentos.$.timestamp.end_subscription_process_timestamp': f"{datetime.now().timestamp()}",
                    'documentos.$.subscription_processed': True
                }
            })
        # doc que passa pela assinatura + extract information    
        else:
            request = self.mdb['beneficiarios'].find_one({"id": message["uuid"]})

            for data in request['documentos']:

                if data['document_id'] == message['document_id']:
                    update_query = {
                        "id": message["uuid"], 
                        "documentos.document_id": message['document_id']
                    }

                    if data.get('subscription_rules') is None:
                        update_data = {
                            "$set": {
                                "documentos.$.subscription_rules": output,
                                "documentos.$.timestamp.end_subscription_process_timestamp": f"{datetime.now().timestamp()}"
                            }
                        }

                    if data.get('subscription_rules') is not None:
                        input_value = data['subscription_rules'] | output

                        if message['end_retry']:
                            update_data = {
                                "$set": {
                                    "documentos.$.subscription_rules": input_value,
                                    "documentos.$.timestamp.end_subscription_process_timestamp": f"{datetime.now().timestamp()}",
                                    'documentos.$.subscription_processed': True
                                }
                            }
                        else:
                            update_data = {
                                "$set": {
                                    "documentos.$.subscription_rules": input_value,
                                    "documentos.$.timestamp.end_subscription_process_timestamp": f"{datetime.now().timestamp()}"
                                }
                            }

                    self.mdb['beneficiarios'].update_one(update_query, update_data)

    def update_similarity_data(self, message, output):
        if message['end_retry']:
            output['validacao_fraude_docs_similares']['fraud_errors'] = 'OK' if output['validacao_fraude_docs_similares']['fraud_errors'] == 'ESPERAR_DOCUMENTOS' else output['validacao_fraude_docs_similares']['fraud_errors']
            self.mdb.beneficiarios.update_one({
                    'id': message['uuid'],
                    'documentos.document_id': message['document_id']
                },
                {
                    '$set': {
                        'documentos.$.similarity_validation': output,
                        'documentos.$.timestamp.end_similarity_process_timestamp': f"{datetime.now().timestamp()}",
                        'documentos.$.similarity_validation_processed': True
                    }
                })
        
    def update_metadata_data(self, message, output):
        if message['end_retry']:
            self.mdb.beneficiarios.update_one({
                'id': message['uuid'],
                'documentos.document_id': message['document_id']
            },
            {
                '$set': {
                    'documentos.$.metadata_validation': output,
                    'documentos.$.timestamp.end_metadata_process_timestamp': f"{datetime.now().timestamp()}",
                    'documentos.$.metadata_validation_processed': True
                }
            })