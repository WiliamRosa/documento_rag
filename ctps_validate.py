import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate, fraud_validate
from Distances import distances
from fraud_tools import SimilarTextValidator, ValidadorMetadadosPDF
from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined
from validacao_endereco import Validacao_endereco, Endereco
from fraud_tools import ValidadorMetadadosPDF


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Cpts:
    nome: str
    cpf: str
    data_nascimento: str
    nome_mae: str
    razao_social: str
    cnpj: str
    endereco_empresa: Endereco
    data_admissao: str
    cbo: Optional[str] = None
    documento_digital: Optional[str] = None
    pagina_foto_assinatura: Optional[str] = None
    pagina_qualificacao: Optional[str] = None
    pagina_contrato: Optional[str] = None
    documento_assinado_digitalmente: Optional[str] = None
    data_assinatura: Optional[str] = None
    extracted_text: Optional[str] = None
    data_emissao: Optional[str] = None


@dataclass
class Cpts_validations:
    validacao_nome: str
    validacao_cpf: str
    validacao_data_nascimento: str 
    validacao_nome_mae: str
    validacao_cnpj: str
    validacao_razao_social: str
    validacao_cbo: str
    validacao_data_admissao: str
    validacao_endereco_empresa: str
    validacao_documento_digital: str
    validacao_data_assinatura: str
    validacao_fraude_docs_similares: str
    

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Cpts_sign:
    assinatura_titular: str
    assinatura_empresa: str
    documento_digital: str

@dataclass
class Cpts_sign_validations:
    validacao_assinatura_fisica: str



@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Cpts_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Cpts_fraud_validations:
    validacao_metadado_datas: str

class ctps_validate(ValidateDocument):
    
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.message_type = message_type
        self.cartao_proposta = Cpts(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Cpts_sign(**dados_extraidos)
        elif(message_type == "fraud_metadata"):
            self.dados_extraidos = Cpts_fraud(**dados_extraidos)
        else:
            self.dados_extraidos = Cpts(**dados_extraidos)

    def set_validate_functions_list(self):
        return list(Cpts_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Cpts_sign_validations.__annotations__.keys())
    
    def set_validate_fraud_functions_list(self):
        return list(Cpts_fraud_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type
    

    
    @validate
    def validacao_nome(self, limiar=90):
        """
        Valida se o nome do cartao_proposta corresponde ao nome extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.nome
        s2 = self.dados_extraidos.nome
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}
    

    @validate
    def validacao_cpf(self):
        """
        Valida se o CPF do cartao_proposta corresponde ao CPF extraído da CTPS.
    
        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cpf))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}


    @validate   
    def validacao_nome_mae(self, limiar=90):
        """
        Valida se o nome da mãe do cartao_proposta corresponde o nome da mãe extraído da CTPS.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.nome_mae
        s2 = self.dados_extraidos.nome_mae
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}
        
    @validate
    def validacao_data_nascimento(self):
        """
        Valida se a data de nascimento do cartao_proposta corresponde a data de nascimento extraída da CTPS.
    
        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_nascimento, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_nascimento, '%d-%m-%Y')
        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
            
    @validate
    def validacao_razao_social(self, limiar=80):
        """
        Valida se a razão social do cartao_proposta corresponde a razão social extraída da CTPS.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 80
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
        Valida se o CNPJ do cartao_proposta corresponde ao CNPJ extraído da CTPS.
        Primeiro tentaremos validar todo o número dos CNPJs. Caso algum deles não tenha vindo
        completo, será validado a raiz.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))

        if len(s1) > 8 and len(s2) > 8:
            if s1 == s2:
                return {'valid': True, 'percent_match': 100}
            else:
                return {'valid': False, 'percent_match': 0}
            
        else:
            new_s1 = s1[:8]
            new_s2 = s2[:8]
            if new_s1 == new_s2:
                return {'valid': True, 'percent_match': 100}
            else:
                return {'valid': False, 'percent_match': 0}


    @validate 
    def validacao_endereco_empresa(self, limiar=70):
        """
        Valida se o nome da rua do endereço empresarial do cartao_proposta corresponde ao nome da rua extraído da CTPS.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """

        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        
        s1 = val_endereco.cartao_proposta.rua
        s2 = val_endereco.dados_extraidos.rua
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}


    @validate 
    def validacao_cbo(self):
        """
        Valida se o CBO está preenchido na CTPS.
    
        Lógica de Retorno:
        - TRUE: Se o CBO for encontrado;
        - FALSE: Caso contrário.
        """

        if self.dados_extraidos.cbo.upper() != "NOT FOUND":
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
            

    @validate 
    def validacao_data_admissao(self):
        """
        Valida se a data de admissão do cartao_proposta corresponde a data de admissão extraída da CTPS.
    
        Lógica de Retorno:
        - TRUE: Se as datas forem iguais;
        - FALSE: Caso contrário.
        """

        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_admissao, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_admissao, '%d-%m-%Y')
        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}
        

    @validate        
    def validacao_documento_digital(self):
        """
        Verifica se o documento é físico ou digital. 
        Se for físico, valida se o documento enviado tem as páginas com foto, qualificação e registro.
    
        Lógica de Retorno:
        - TRUE: Se for digital ou físico com todas as páginas indicadas;
        - FALSE: Caso contrário.
        """

        documento_digital = self.dados_extraidos.documento_digital
        
        if(documento_digital == 'Verdadeiro'):
            return {'valid': True, 'percent_match': 100}
        else:
            
            pagina_foto_assinatura = self.dados_extraidos.pagina_foto_assinatura
            pagina_qualificacao    = self.dados_extraidos.pagina_qualificacao
            pagina_contrato        = self.dados_extraidos.pagina_contrato
            
            variaveis = [pagina_foto_assinatura, pagina_qualificacao, pagina_contrato]
            
            score = sum(var == "Verdadeiro" for var in variaveis)
            
            if all(var == "Verdadeiro" for var in variaveis):
                return {'valid': True, 'percent_match': 100}
            else:
                return {'valid': False, 'percent_match': round(score,2)}


    @validate         
    def validacao_data_assinatura(self):
        """
        Verifica se o documento é físico ou digital. 
        Se for digital, valida se foi assinado digitalmente pela Dataprev com data de até 30 dias.
    
        Lógica de Retorno:
        - TRUE: Se for digital com as datas dentro do intervalo especificado;
        - FALSE: Caso contrário.
        """
        
        data_assinatura = datetime.datetime.strptime(self.dados_extraidos.data_assinatura, '%d-%m-%Y') if self.dados_extraidos.data_assinatura != 'Not Found' else self.dados_extraidos.data_assinatura
        data_limite = datetime.datetime.now() - datetime.timedelta(days=30)

        if data_assinatura == 'Not Found':
            return {'valid': False, 'percent_match': 0, 'target': 'data_assinatura', 'trecho_encontrado': data_assinatura, 'regras_subscricao_errors': 404}
        elif data_assinatura >= data_limite:
            return {'valid': True, 'percent_match': 100}
        else: 
            return {'valid': False, 'percent_match': 0}
        


    @validate         
    def validacao_assinatura_fisica(self):
        """
        Valida se o documento está assinado pelo portador e pela empresa. 

        Lógica de Retorno:
        - TRUE: Se estiver assinado;
        - FALSE: Caso contrário.
        """

        documento_digital = (lambda x: False if x in {'False', 'false', 'Falso', 'falso'} else True)(self.dados_extraidos.documento_digital)

        if(documento_digital):
            return {"valid": True, "target": "assinatura_fisica", "percent_match": 100, 
            "trecho_procurado": "",
            "trecho_encontrado": "Documento digital. Validação não aplicável."}

        assinatura_titular = self.dados_extraidos.assinatura_titular
        assinatura_titular = (lambda x: False if x in {'False', 'false', 'Falso', 'falso'} else True)(assinatura_titular)

        assinatura_empresa = self.dados_extraidos.assinatura_empresa
        assinatura_empresa = (lambda x: False if x in {'False', 'false', 'Falso', 'falso'} else True)(assinatura_empresa)

        valid, confianca = (lambda x, y: (True, 100) if x and y else (False, 0))(assinatura_empresa, assinatura_titular)

        return {"valid": valid, "target": "assinatura_fisica", "percent_match": confianca, 
            "trecho_procurado": "",
            "trecho_encontrado": ""}
    

    @fraud_validate
    @required_docs('ctps', include_docs_same_type_from_proposal=True)
    def validacao_fraude_docs_similares(self, ctps, limiar=.85):
        # ID do documento atual (definido em variável de ambiente)
        doc_atual = ctps.get('doc_atual')
        doc_list = ctps.get('doc_list')
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
    @required_docs('ctps')
    def validacao_metadado_datas(self, ctps):
        """
        Valida se a data de emissão extraída do CTPS é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se a data de emissão for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """

        if(ctps is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}
        
        val = ValidadorMetadadosPDF()
        
        documento_digital = (lambda x: False if x in {'False', 'false', 'Falso', 'falso'} else True)(ctps.get('documento_digital'))
        creation_date = self.dados_extraidos.creationDate
        data_emissao = ctps.get('data_emissao')

        creation_date_convertida = val.converter_data(creation_date)
        data_emissao_convertida = val._converter_data_emissao(data_emissao)

        creation_date_str = creation_date_convertida.strftime("%d-%m-%Y") if creation_date_convertida is not None else creation_date
        data_emissao_str = data_emissao_convertida.strftime("%d-%m-%Y") if data_emissao_convertida is not None else data_emissao

        if(documento_digital == False):
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: " + str(creation_date_str) + " | Data de emissão: " +str(data_emissao_str) , "trecho_encontrado": "CTPS física sem validação." }
        

        if(creation_date_convertida == None or data_emissao_convertida == None):
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: " + creation_date_str + " | Data de emissão: " + data_emissao_str, "trecho_encontrado": "Data de criação ou data de emissão não encontrada." }

        if creation_date_convertida < data_emissao_convertida:
            return {
                "valid": False, 'percent_match': 0, "trecho_procurado": "Data de criação: "+creation_date_str, 
                "trecho_encontrado": "Data de criação do arquivo é anterior a data de emissão:" + data_emissao_str
            }
        else:
            return {'valid': True, 'percent_match': 100, "trecho_procurado": "Data de criação: "+creation_date_str, "trecho_encontrado": "Data de emissão: " +data_emissao_str}
    