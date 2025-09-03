import json
import logging
import os
import boto3
from mongodb_connections import MongoDBConnections

logger = logging.getLogger()
logger.setLevel("INFO")

SQS_RETRY_QUEUE = os.environ['SQS_RETRY_QUEUE']
DELAY_SECONDS = os.environ['DELAY_SECONDS']
FOLDER_NAME = os.environ['FOLDER_NAME']
S3_BUCKET = os.environ['S3_BUCKET']

def get_object_from_s3(message):
  s3 = boto3.client('s3')
  s3_key = f"{FOLDER_NAME}/{message['file_name']}"

  try:
    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    json_content = response['Body'].read().decode('utf-8')
    data = json.loads(json_content)
    print(f"Arquivo '{message['file_name']}' buscado com sucesso de s3://{S3_BUCKET}/{s3_key}")
    return json.loads(data)
  except s3.exceptions.NoSuchKey:
    print(f"Erro: O arquivo '{s3_key}' não foi encontrado no bucket '{S3_BUCKET}'.")
    return None
  except Exception as e:
    print(f"Erro ao buscar o arquivo JSON do S3: {e}")
    return None

def process_document(message):
    sqs = boto3.client('sqs')
    s3_object = None
    if message.get('flag_large_file'):
       s3_object = get_object_from_s3(message)
       if s3_object is not None:
          message = s3_object

    document_type = message["document_type"].lower()
  
    module = __import__(document_type+'_validate')
    cls_validate = getattr(module, document_type+'_validate')

    obj_validate = cls_validate(message["cartao_proposta"], message["document_information"], message["message_type"])
    validate = getattr(obj_validate, 'validate')

    output = validate()
    message['end_retry'] = True
    tentativa = 1 if message.get('tentativa') is None else message['tentativa']+1
    message['tentativa'] = tentativa

    for doc in output.values():
      if ((doc.get('fraud_errors') == 'ESPERAR_DOCUMENTOS' or doc.get('fraud_errors') == 'ERRO_INTERNO') or \
        (doc.get('regras_subscricao_errors') == 'ESPERAR_DOCUMENTOS' or doc.get('regras_subscricao_errors') == 'ERRO_INTERNO')) and \
        tentativa <= 5:
        message['end_retry'] = False

        delay = pow(int(DELAY_SECONDS), tentativa)
        sqs.send_message(QueueUrl=SQS_RETRY_QUEUE, MessageBody=json.dumps(message),
                          DelaySeconds=delay)

      if tentativa > 5:
          message['end_retry'] = True
          logger.info('[INFO] Mais de 5 tentativas. Parando.')
          break

    logger.info(f'output {output}')

    mongo_conn = MongoDBConnections()

    if 'validacao_metadado_datas' in output:
      mongo_conn.update_metadata_data(message, output)
    else:
      if 'validacao_fraude_docs_similares' in output:
        new_output = {}
        new_output['validacao_fraude_docs_similares'] = output['validacao_fraude_docs_similares']
        mongo_conn.update_similarity_data(message, new_output)

        output.pop('validacao_fraude_docs_similares')
        mongo_conn.update_subscription_rules(message, output)

      else:
        mongo_conn.update_subscription_rules(message, output)

      payload = json.dumps({
        "job_id": message['JobId'],
        "document_type": document_type,
        "document_id": message['document_id'],
        "cartao_proposta": message['cartao_proposta'],
        "dados_regras_subscricao": output
      })

      logger.info(f'payload {payload}')
      logger.info(f'message {message}')

      return payload

def lambda_handler(event, context):
  logger.info(event)
  for record in event['Records']:
    if record.get('Sns'):
      message = json.loads(record['Sns']['Message'])
      os.environ["UUID"] = message["uuid"]
      os.environ["AGREGADOR"] = message["agregador"]
      os.environ["DOCUMENT_ID"] = message["document_id"]
      os.environ["DOCUMENT_LABEL"] = message["document_label"]
      return process_document(message)
    
    print(record)
    message = json.loads(record['body'])
    os.environ["UUID"] = message["uuid"]
    os.environ["AGREGADOR"] = message["agregador"]
    os.environ["DOCUMENT_ID"] = message["document_id"]
    os.environ["DOCUMENT_LABEL"] = message["document_label"]
    return process_document(message)
