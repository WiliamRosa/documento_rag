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
class Carta_permanencia:
    razao_social: str
    nome: Optional[str] = None
    data_nascimento: Optional[str] = None
    beneficiarios: Optional[str] = None
    segmentacao: Optional[str] = None
    regulamentacao: Optional[str] = None
    descricao_regulamentacao: Optional[str] = None
    acomodacao: Optional[str] = None
    data_emissao: Optional[str] = None
    nome_congenere: Optional[str] = None
    numero_cartao_plano: Optional[str] = None 
    data_inclusao: Optional[str] = None 
    data_exclusao: Optional[str] = None 
    titular_ou_dependente: Optional[str] = None


@dataclass
class Carta_permanencia_validations:
    validacao_data_emissao: str
    validacao_nome: str
    validacao_numero_cartao_plano: str
    validacao_data_nascimento: str
    validacao_segmentacao: str 
    validacao_data_inclusao: str 
    validacao_data_exclusao: str
    validacao_regulamentacao: str  
    validacao_acomodacao: str
    validacao_razao_social: str    
    validacao_nome_congenere: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Carta_permanencia_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Carta_permanencia_fraud_validations:
    validacao_metadado_datas: str


class Beneficiario:
    def __init__(self, beneficiario, limiar):
        self.beneficiario = beneficiario
        self.limiar = limiar

    # Lógica personalizada para comparação de igualdade
    def __eq__(self, other):
        if isinstance(other, Beneficiario):
            score = distances(self.beneficiario, other.beneficiario).norm_score()
            return score >= self.limiar
        return False

    def __hash__(self):
        return hash(self.beneficiario)

    def __repr__(self):
        return self.beneficiario


class carta_permanencia_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Carta_permanencia(**cartao_proposta)
        self.message_type = message_type

        if (message_type == "fraud_metadata"):
            self.dados_extraidos = Carta_permanencia_fraud(**dados_extraidos)
        else: 
            self.dados_extraidos = Carta_permanencia(**dados_extraidos)
            
            self.congeneres_validas = ["bradesco", "sul america", "notredame", "unimed nacional", "allianz", "care plus", "porto seguro", "omint", "mediservice", "amil"]
            self.acomodacao_apartamento = ["QUARTO", "APARTAMENTO", "INDIVIDUAL", "QUARTO PRIVATIVO", "PARTICULAR"]
            self.acomodacao_enfermaria = ["ENFERMARIA", "COLETIVA"]

            self.set_nome_congenere()


    def set_validate_functions_list(self):
        return list(Carta_permanencia_validations.__annotations__.keys())
    
    def set_validate_fraud_functions_list(self):
        return list(Carta_permanencia_fraud_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type


    def set_nome_congenere(self):

        s1 = self.dados_extraidos.nome_congenere

        best_match = None
        highest_jaro_wink = 0

        for s2 in self.congeneres_validas:
            current_score = distances(s1.upper(), s2.upper()).jaro_winkler_similarity()
            if(current_score > highest_jaro_wink):
                highest_jaro_wink = current_score
                best_match = s2

        if(highest_jaro_wink > 75):
            self.dados_extraidos.nome_congenere = best_match
        

    @validate
    def validacao_data_emissao(self):
        """
        Valida se a data de emissão do documento extraída dos dados tem menos de 60 dias.

        Lógica de Retorno:
        - TRUE: Se a data de expedição for dentro do período de 60 dias;
        - FALSE: Caso contrário.
        """
        
        data_emissao = datetime.datetime.strptime(self.dados_extraidos.data_emissao, '%d-%m-%Y').date()

        now = datetime.datetime.now().date()
        data_min = now - relativedelta(months=2)

        if data_emissao >= data_min: 
            return {'valid': True, 'percent_match': 100, 'trecho_encontrado': data_emissao.strftime('%d/%m/%Y')}
        else:
            return {'valid': False, 'percent_match': 0, 'trecho_encontrado': data_emissao.strftime('%d/%m/%Y')}


    def _obter_nome(self, beneficiarios: dict, nome: str, limiar:int):
        """
        Procura o nome igual ou similar no dicionário com os beneficiários.

        No retorno, primeiro checa se dicionario contém apenas um beneficiário 
        e retorna nome, informações e score encontrado.

        Caso venha mais de um beneficiário no dict, valida a similaridade dos nomes
        e retorna a chave, informações e score encontrados para o nome similar.

        Por fim, caso não tenha correspondência, retorna nulo.
        """
        nome_ref = Beneficiario(nome.upper(), limiar)
        for key in beneficiarios:
            candidato = Beneficiario(key.upper(), limiar)
            current_score = distances(nome_ref.beneficiario, candidato.beneficiario).norm_score()

            if len(beneficiarios.keys()) == 1:
                return key, beneficiarios[key], current_score
            else:
                if nome_ref == candidato:
                    return key, beneficiarios[key], current_score

        return None

    @validate
    def validacao_nome(self, limiar=90):
        """
        Valida se o nome do beneficiário no cartão proposta está na Carta de Permanência.

        Lógica de Retorno:
        - TRUE: Se o nome estiver no documento;
        - FALSE: Caso contrário.
        """

        nome = self.cartao_proposta.nome
        beneficiarios = self.dados_extraidos.beneficiarios

        result = self._obter_nome(beneficiarios, nome, limiar)

        if result is not None:
            found_name_key, infos_beneficiario, score = result

            self.dados_extraidos.nome = found_name_key
            self.dados_extraidos.numero_cartao_plano = infos_beneficiario.get("numero_cartao_plano")
            self.dados_extraidos.data_nascimento = infos_beneficiario.get("data_nascimento")
            self.dados_extraidos.data_inclusao = infos_beneficiario.get("data_inclusao_plano")
            self.dados_extraidos.data_exclusao = infos_beneficiario.get("data_exclusao_plano")
            self.dados_extraidos.titular_ou_dependente = infos_beneficiario.get("titular_ou_dependente")

            if score >= limiar:
                return {'valid': True, 'percent_match': int(score), 'trecho_encontrado': self.dados_extraidos.nome}
            else:
                return {'valid': False, 'percent_match': int(score), 'trecho_encontrado': self.dados_extraidos.nome}
        else:
            return {'valid': False, 'percent_match': 0, 'trecho_encontrado': self.dados_extraidos.nome}

    @validate
    def validacao_data_nascimento(self):
        """
        Valida se a data de nascimento extraída do cartao_proposta corresponde à data de nascimento extraída dos dados.
        Essa validação só deve ser considerada para algumas congêneres. 

        Lógica de Retorno:
        - TRUE: Se as datas de nascimento forem iguais;
        - FALSE: Caso contrário.
        """

        # checa congeneres sem essa validacao
        nome_congenere = self.dados_extraidos.nome_congenere
        congeneres_sem_val = ["bradesco", "unimed nacional", "allianz", "care plus", "porto seguro", "omint", "mediservice"]
        if(nome_congenere in congeneres_sem_val):
            return {'valid': True, 'percent_match': 100, 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}
        
        data_nascimento = datetime.datetime.strptime(self.dados_extraidos.data_nascimento, '%d-%m-%Y').date()
        if(self.dados_extraidos.data_nascimento == None):
            return {'valid': False, 'percent_match': 0, "trecho_encontrado": data_nascimento.strftime('%d/%m/%Y')}

        date_1 = datetime.datetime.strptime(self.cartao_proposta.data_nascimento, '%d/%m/%Y')
        date_2 = datetime.datetime.strptime(self.dados_extraidos.data_nascimento, '%d-%m-%Y')

        if date_1 == date_2:
            return {'valid': True, 'percent_match': 100, "trecho_encontrado": data_nascimento.strftime('%d/%m/%Y')}
        else:
            return {'valid': False, 'percent_match': 0, "trecho_encontrado": data_nascimento.strftime('%d/%m/%Y')}

    @validate
    def validacao_data_inclusao(self):
        """
        Valida se a data de inclusão no plano, extraída da Carta de Permanência, é menor que a data atual.

        Lógica de Retorno:
        - TRUE: Se a data inclusão for menor que a data atual;
        - FALSE: Caso contrário.
        """
        if(self.dados_extraidos.data_inclusao == None):
            return {'valid': False, 'percent_match': 0, 'trecho_encontrado': self.dados_extraidos.data_inclusao}

        data_inclusao = datetime.datetime.strptime(self.dados_extraidos.data_inclusao, '%d-%m-%Y').date()

        now = datetime.datetime.now().date()
        if now > data_inclusao:
            return {'valid': True, 'percent_match': 100, "trecho_encontrado": data_inclusao.strftime('%d/%m/%Y')}
        else:
            return {'valid': False, 'percent_match': 0, "trecho_encontrado": data_inclusao.strftime('%d/%m/%Y')} 

    @validate
    def validacao_data_exclusao(self):
        """
        Valida se a data de exclusão do plano, extraída da Carta de Permanência, é inferior a 60 dias.

        Lógica de Retorno:
        - TRUE: Se a data for inferior a 60 dias
        - FALSE: Caso contrário.
        """

        data_exclusao = self.dados_extraidos.data_exclusao

        if(data_exclusao == None):
            return {'valid': False, 'percent_match': 0, 'trecho_encontrado': data_exclusao}

        ativas = ['Ativo', 'Até a presente data']
        if(data_exclusao in ativas):
            return {'valid': True, 'percent_match': 100}

        data_exclusao = datetime.datetime.strptime(data_exclusao, '%d-%m-%Y').date()

        now = datetime.datetime.now().date()
        data_min = now - relativedelta(months=2)

        if data_exclusao >= data_min:
            return {'valid': True, 'percent_match': 100, 'trecho_encontrado': data_exclusao.strftime('%d/%m/%Y')}
        else:
            return {'valid': False, 'percent_match': 0, 'trecho_encontrado': data_exclusao.strftime('%d/%m/%Y')}

    @validate
    def validacao_regulamentacao(self):
        """
        Valida se há alguma menção no documento sobre o plano ser regulamentado pela ANS e elegível a redução de carências.

        Lógica de Retorno:
        - TRUE: Se for identificada menção à regulamentação;
        - FALSE: Caso contrário.
        """

        # checa congeneres sem essa validacao
        nome_congenere = self.dados_extraidos.nome_congenere
        congeneres_sem_val = ["allianz", "porto seguro", "amil"]
        if(nome_congenere in congeneres_sem_val):
            return {'valid': False, 'percent_match': 0, 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}

        regulamentacao = self.dados_extraidos.regulamentacao

        if(regulamentacao == True or regulamentacao.upper() == 'TRUE'):
            return {'valid': True, 'percent_match': 100, 'trecho_encontrado': str(self.dados_extraidos.descricao_regulamentacao)}
        else:
            return {'valid': False, 'percent_match': 0, 'trecho_encontrado': ''}

    @validate
    def validacao_nome_congenere(self):
        """
        Valida se o plano está na lista das congêneres válidas.

        Lógica de Retorno:
        - TRUE: Se for uma congênere válida;
        - FALSE: Caso contrário.
        """

        nome_congenere = self.dados_extraidos.nome_congenere

        if(nome_congenere in self.congeneres_validas):
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}


    @validate
    @required_docs('cartao_plano')
    def validacao_numero_cartao_plano(self, cartao_plano):
        """
        Valida se o número do cartão plano extraído da Carta de Permanência corresponde ao número extraído do Cartão Plano.
        Essa validação só deve ser considerada para algumas congêneres. 

        Lógica de Retorno:
        - TRUE: Se os números forem iguais;
        - FALSE: Caso contrário.
        """
        if(cartao_plano is None):
            return {'valid': False, 'percent_match': 0, 'target': 'numero_cartao_plano',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        
        # checa congeneres sem essa validacao
        nome_congenere = self.dados_extraidos.nome_congenere
        congeneres_sem_val = ["porto seguro", "omint"]
        if(nome_congenere in congeneres_sem_val):
            return {'valid': True, 'percent_match': 100, 'target': 'numero_cartao_plano', "trecho_procurado": self.dados_extraidos.numero_cartao_plano, 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}

        s1 = ''.join(re.findall( r'\d+', cartao_plano.get('numero_cartao')))
        s2 = None
        if(self.dados_extraidos.numero_cartao_plano != None):
            s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.numero_cartao_plano))
        
        if s1 == s2:
            return {'valid': True, 'percent_match': 100, 'target': 'numero_cartao_plano',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'numero_cartao_plano',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}

    @validate
    @required_docs('cartao_plano')
    def validacao_segmentacao(self, cartao_plano, limiar=90):
        """
        Valida se a segmentação do plano extraída da Carta de Permanência corresponde a segmentação extraída do Cartão Plano.
        Essa validação só deve ser considerada para algumas congêneres. 
        
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """
        if(cartao_plano is None):
            return {'valid': False, 'percent_match': 0, 'target': 'segmentacao',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}

        # checa congeneres sem essa validacao
        nome_congenere = self.dados_extraidos.nome_congenere
        congeneres_sem_val = ["bradesco", "unimed nacional", "allianz", "care plus", "porto seguro", "amil", "mediservice"]
        if(nome_congenere in congeneres_sem_val):
            return {'valid': True, 'percent_match': 100, 'target': 'segmentacao', "trecho_procurado": self.dados_extraidos.segmentacao, 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}

        s1 = cartao_plano['segmentacao']
        s2 = self.dados_extraidos.segmentacao

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score, 'target': 'segmentacao',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': sim_score, 'target': 'segmentacao',
                        "trecho_procurado": s2,
                        "trecho_encontrado": s1}
        

    def classificar_acomodacao(self, acomodacao):
        if(acomodacao.upper() in self.acomodacao_apartamento):
            return "APARTAMENTO"
        elif(acomodacao.upper() in self.acomodacao_enfermaria):
            return "ENFERMARIA"
        else:
            return acomodacao

    @validate
    @required_docs('cartao_plano')
    def validacao_acomodacao(self, cartao_plano, limiar=90):
        """
        Valida se a acomodação do plano extraída da Carta de Permanência corresponde a acomodação extraída do Cartão Plano.
        
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        if(cartao_plano is None):
            return {'valid': False, 'percent_match': 0, 'target': 'acomodacao',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}

        # checa congeneres sem essa validacao
        # nome_congenere = self.dados_extraidos.nome_congenere
        # congeneres_sem_val = ["care plus", "omint"]
        # if(nome_congenere in congeneres_sem_val):
        #     return {'valid': True, 'percent_match': 100, 'target': 'acomodacao', "trecho_procurado": self.dados_extraidos.acomodacao, 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}

        s1 = cartao_plano['acomodacao']
        s2 = self.dados_extraidos.acomodacao

        # adaptar acomodacao com um de-para (apartamento ou enfermaria)
        s1 = self.classificar_acomodacao(s1)
        s2 = self.classificar_acomodacao(s2)

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': sim_score, 'target': 'acomodacao',
                        "trecho_procurado": s2, "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': sim_score, 'target': 'acomodacao',
                        "trecho_procurado": s2, "trecho_encontrado": s1}
    

    @validate
    @required_docs('cartao_plano')
    def validacao_razao_social(self, cartao_plano, limiar=80):
        """
        Valida se a razão social do plano extraída da Carta de Permanência corresponde a razão social extraída do Cartão Plano.
        
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        if(cartao_plano is None):
            return {'valid': False, 'percent_match': 0, 'target': 'razao_social',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}

        # checa congeneres sem essa validacao
        nome_congenere = self.dados_extraidos.nome_congenere
        # congeneres_sem_val = ["sulamerica", "unimed", "allianz", "care plus", "porto seguro", "amil", "omint", "mediservice"]
        congeneres_sem_val = ["sulamerica", "allianz", "care plus", "porto seguro", "amil"]

        if(nome_congenere in congeneres_sem_val):
            return {'valid': True, 'percent_match': 100, 'target': 'razao_social', "trecho_procurado": self.dados_extraidos.razao_social, 'trecho_encontrado': 'Não encontrado. Congênere sem validação.'}
        
        s1 = cartao_plano['razao_social']
        s2 = self.dados_extraidos.razao_social

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score, 'target': 'razao_social',
                        "trecho_procurado": s2, "trecho_encontrado": s1}
        else:
            return {'valid': False, 'percent_match': sim_score, 'target': 'razao_social',
                        "trecho_procurado": s2, "trecho_encontrado": s1}
        

        

    @fraud_validate
    @required_docs('carta_permanencia')
    def validacao_metadado_datas(self, carta_permanencia):
        """
        Valida se a data de emissão extraída do Carta de Permanência é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se a data de emissão for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """

        if(carta_permanencia is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}
        
        val = ValidadorMetadadosPDF()

        creation_date = self.dados_extraidos.creationDate
        data_emissao = carta_permanencia.get('data_emissao')

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
    