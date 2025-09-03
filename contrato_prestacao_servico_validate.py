import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined
from validacao_endereco import Validacao_endereco, Endereco



@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Contrato_prestacao_servico:
    razao_social_matriz: str
    cnpj_matriz: str
    endereco_empresa_matriz: str
    razao_social: str
    cnpj: str
    endereco_empresa: str
    tempo_contrato: Optional[str] = None
    data_emissao: Optional[str] = None
    inicio_vigencia_contrato: Optional[str] = None


@dataclass
class Contrato_prestacao_servico_validations:
    validacao_razao_social_matriz: str
    validacao_cnpj_matriz: str
    validacao_endereco_empresa_matriz: str
    validacao_razao_social_subestipulante: str
    validacao_cnpj_subestipulante: str
    validacao_endereco_subestipulante: str
    validacao_tempo_contrato: str
    validacao_data_emissao: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Contrato_prestacao_servico_sign:
    ha_assinatura_empresa_contratante: str
    ha_assinatura_empresa_contratada: str
    nome_assinatura_empresa_contratante: str
    nome_assinatura_empresa_contratada: str
    descricao_assinaturas: str
    fisica_ou_digital: str


@dataclass
class Contrato_prestacao_servico_sign_validations:
    validacao_assinatura: str


class contrato_prestacao_servico_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):

        self.message_type = message_type
        self.cartao_proposta = Contrato_prestacao_servico(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Contrato_prestacao_servico_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Contrato_prestacao_servico(**dados_extraidos)

    
    def set_validate_functions_list(self):
        return list(Contrato_prestacao_servico_validations.__annotations__.keys())

    def set_validate_sign_functions_list(self):
        return list(Contrato_prestacao_servico_sign_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type
    

    @validate
    def validacao_razao_social_matriz(self, limiar=90):
        """
        Valida se o nome da estipulante do cartao_proposta corresponde ao nome da estipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.razao_social_matriz
        s2 = self.dados_extraidos.razao_social_matriz
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >=limiar:
            return {'valid': True, 'percent_match': sim_score}
        else:
            return {'valid': False, 'percent_match': sim_score}   
              

    @validate 
    def validacao_razao_social_subestipulante(self, limiar=90):
        """
        Valida se o nome da subestipulante do cartao_proposta corresponde ao nome da subestipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 90
        """

        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social
        
        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        if sim_score >= limiar:
            return {'valid': True, 'percent_match': sim_score, "trecho_procurado": s1, "trecho_encontrado": s2}
        else:
            return {'valid': False, 'percent_match': sim_score, "trecho_procurado": s1, "trecho_encontrado": s2}


    @validate 
    def validacao_cnpj_matriz(self):
        """
        Valida se o CNPJ da estipulante do cartao_proposta corresponde ao CNPJ da estipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj_matriz))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj_matriz))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate 
    def validacao_cnpj_subestipulante(self):
        """
        Valida se o CNPJ da subestipulante do cartao_proposta corresponde ao CNPJ da subestipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100, "trecho_procurado": s1, "trecho_encontrado": s2}
        else:
            return {'valid': False, 'percent_match': 0, "trecho_procurado": s1, "trecho_encontrado": s2}
    
    
    @validate 
    def validacao_endereco_empresa_matriz(self, limiar=0.5):
        """
        Valida se o endereço da estipulante do cartao_proposta corresponde ao endereço da estipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 1) para considerar a validação válida. 
                                O valor padrão é 0.5
        """
        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa_matriz, self.dados_extraidos.endereco_empresa_matriz)
        valid, score = val_endereco.validar_endereco(limiar)

        return {'valid': valid, 'percent_match': score} 

    @validate 
    def validacao_endereco_subestipulante(self, limiar=0.5):
        """
        Valida se o endereço da subestipulante do cartao_proposta corresponde ao endereço da subestipulante extraído deste documento.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 1) para considerar a validação válida. 
                                O valor padrão é 0.5
        """
        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        valid, score = val_endereco.validar_endereco(limiar)
        
        return {'valid': valid, 'percent_match': score, "trecho_procurado": self.cartao_proposta.endereco_empresa, "trecho_encontrado": self.dados_extraidos.endereco_empresa}

    @validate
    def validacao_tempo_contrato(self):
        """
        Valida se no contrato entre as partes, possui a cláusula de 12 meses de prestação de serviços.

        Lógica de Retorno:
        - TRUE: Se identificar a cláusula;
        - FALSE: Caso contrário.
        """

        tempo_contrato = self.dados_extraidos.tempo_contrato

        if tempo_contrato.upper() == 'indeterminado'.upper():
            return {'valid': True, 'percent_match': 100} 
        
        tempo_inteiro = re.search(r'\d+', tempo_contrato)
        tempo_texto = re.search(r'\b(anos|meses|ano|mês)\b', tempo_contrato)

        if not tempo_inteiro or not tempo_texto:
            return {'valid': False, 'percent_match': 0} 

        tempo_inteiro = int(tempo_inteiro.group())
        tempo_texto = tempo_texto.group()

        if tempo_texto in {'meses', 'mês'}:
            return {'valid': True, 'percent_match': 100}  if tempo_inteiro >= 12 else {'valid': False, 'percent_match': 0} 
        
        if tempo_texto in {'anos', 'ano'}:
            return {'valid': True, 'percent_match': 100} if tempo_inteiro >= 1 else {'valid': False, 'percent_match': 0} 

        return {'valid': False, 'percent_match': 0} 

    @validate
    def validacao_data_emissao(self):
        """
        Valida se o contrato está em uma vigência válida (no mínimo 3 meses do momento da validação).

        Lógica de Retorno:
        - TRUE: Se estiver em uma vigência válida;
        - FALSE: Caso contrário.
        """

        s1 = self.dados_extraidos.inicio_vigencia_contrato
        tempo_contrato = self.dados_extraidos.tempo_contrato

        if(s1 == 'Not Found'):
            return {'valid': False, 'percent_match': 0, 'target': 'data_emissao',
                        "trecho_procurado": "",
                        "trecho_encontrado": "Início da vigência: "+ s1 + " | Tempo de contrato: " + tempo_contrato}

        try:
            inicio_vigencia_contrato = datetime.datetime.strptime(s1, '%d-%m-%Y').date()
        except Exception as e:
            print(e)
            return {'valid': False, 'percent_match': 0, 'target': 'data_emissao',
                        "trecho_procurado": "",
                        "trecho_encontrado": "Data inválida: "+ s1,
                        "regras_subscricao_errors": 422}

        # Converte para que possa validar a vigencia pelos meses, ignorando o dia
        now = datetime.datetime.now().date()
        now_replaced = now.replace(day=1)
        inicio_vigencia_contrato = inicio_vigencia_contrato.replace(day=1)
        score = 0

        # Valida período mínimo de 3 meses
        if inicio_vigencia_contrato <= (now_replaced - relativedelta(months=3)):
            score += 50
        else:
            return {'valid': False, 'percent_match': score}

        # Verifica vigência indeterminada
        if tempo_contrato.upper() == 'INDETERMINADO':
            return {'valid': True, 'percent_match': score + 50}

        # Extrai valor e unidade de tempo
        tempo_inteiro = re.search(r'\d+', tempo_contrato)
        tempo_texto = re.search(r'\b(anos|meses|ano|mês)\b', tempo_contrato)

        if not tempo_inteiro or not tempo_texto:
            return {'valid': False, 'percent_match': score} 

        # Calcula data máxima com base na unidade de tempo
        delta_args = {'months': int(tempo_inteiro.group())} if tempo_texto.group() in {'meses', 'mês'} else {'years': int(tempo_inteiro.group())}
        max_tempo_contrato = inicio_vigencia_contrato + relativedelta(**delta_args)

        # Verifica se o contrato ainda está vigente
        return {'valid': True, 'percent_match': score + 50} if max_tempo_contrato >= now else {'valid': False, 'percent_match': score} 

    def find_responsavel_legal(self, contrato_social, estatuto_social, ata_assembleia, mei, procuracao, requerimento_empresario):
        names = []

        if(contrato_social is not None and contrato_social.get('nomes_assinatura') is not None):
            names.extend([nome.strip() for nome in contrato_social['nomes_assinatura'].split(",")])

        if(estatuto_social is not None and ata_assembleia is not None):
            for cargo in estatuto_social.get("cargo_responsavel_legal"):
                # verifica diretamente no dict ou busca uma chave semelhante
                cargos_eleitos = ata_assembleia.get("cargos_eleitos")
                if(cargos_eleitos is not None):
                    new_cargo = re.sub(r'[^A-Za-z]', '', cargo.upper())
                    for key in cargos_eleitos:
                          new_key = re.sub(r'[^A-Za-z]', '', key.upper())
                          if new_cargo in new_key:
                            responsavel_legal = cargos_eleitos.get(cargo) or cargos_eleitos[key]
                    if type(responsavel_legal) is not list:
                        names.extend([responsavel_legal])
                    else:
                        names.extend(responsavel_legal)
        if(mei is not None):
            names.extend([mei["nome"]])

        if(procuracao is not None):
            names.extend([nome.strip() for nome in procuracao['procuradores'].split(",")])

        if(requerimento_empresario is not None):
            names.extend([requerimento_empresario["nome_empresario"]])
        
        return names



    @validate
    @required_docs('contrato_social', 'estatuto_social', 'ata_assembleia', 'mei', 'procuracao', 'requerimento_empresario', include_matriz=True)
    def validacao_assinatura(self, matriz, contrato_social, estatuto_social, ata_assembleia, mei, procuracao, requerimento_empresario, limiar=80):
        """
        Valida se quem assinou pelas duas empresas partes do contrato são os respectivos responsáveis legais.
    
        Lógica de Retorno:
        - TRUE: Se há assinatura dos responsáveis legais;
        - FALSE: Caso contrário.
        """
        responsavel_legal_estipulante = self.find_responsavel_legal(matriz.get("contrato_social"), 
                                                                       matriz.get("estatuto_social"), 
                                                                       matriz.get("ata_assembleia"),
                                                                       matriz.get("mei"),
                                                                       matriz.get("procuracao"),
                                                                       matriz.get("requerimento_empresario"))
        
        responsavel_legal_subestipulante = self.find_responsavel_legal(contrato_social, estatuto_social, ata_assembleia, mei, procuracao, requerimento_empresario)
        # checa se algum responsavel legal foi encontrado
        if(responsavel_legal_estipulante == [] or responsavel_legal_subestipulante == [] or 
            responsavel_legal_estipulante == None or responsavel_legal_subestipulante == None):

            return {'valid': False, 'percent_match': 0, 'target': 'assinatura',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}

        ha_assinatura_contratante = self.dados_extraidos.ha_assinatura_empresa_contratante
        ha_assinatura_contratada = self.dados_extraidos.ha_assinatura_empresa_contratada
        nome_contratante = [self.dados_extraidos.nome_assinatura_empresa_contratante] if type(self.dados_extraidos.nome_assinatura_empresa_contratante) is not list else self.dados_extraidos.nome_assinatura_empresa_contratante
        nome_contratada  = [self.dados_extraidos.nome_assinatura_empresa_contratada] if type(self.dados_extraidos.nome_assinatura_empresa_contratada) is not list else self.dados_extraidos.nome_assinatura_empresa_contratada
        score, valid = 0, False

        if(isinstance(ha_assinatura_contratante, str)):
            ha_assinatura_contratante = (lambda x: False if x in {'False', 'false'} else True)(ha_assinatura_contratante)

        match_contratante = False
        if(ha_assinatura_contratante == True):
            for responsavel_legal in responsavel_legal_estipulante:
                for nome in nome_contratante:
                    sim_score = distances(nome.upper(), responsavel_legal.upper()).norm_score()
                    if sim_score >= limiar:
                        match_contratante = True
                        score = 50

        if(isinstance(ha_assinatura_contratada, str)):
            ha_assinatura_contratada = (lambda x: False if x in {'False', 'false'} else True)(ha_assinatura_contratada)

        match_contratada = False
        if(ha_assinatura_contratada == True):
            for responsavel_legal in responsavel_legal_subestipulante:
                for nome in nome_contratada:
                    sim_score = distances(nome.upper(), responsavel_legal.upper()).norm_score()
                    if sim_score >= limiar:
                        match_contratada = True
                        score = 50

        if(match_contratada and match_contratante):
            valid = True
            score = 100

        return {
            'valid': valid,
            'percent_match': score,
            'target': 'assinatura',
            "trecho_procurado": "Assinatura Contratante: " + re.sub(r"[\[\]']", "", str(nome_contratante)) +
                                " | Assinatura Contratada: " + re.sub(r"[\[\]']", "", str(nome_contratada)),
            "trecho_encontrado": "Responsável Estipulante: " + re.sub(r"[\[\]']", "", str(responsavel_legal_estipulante)) +
                                " |  Responsável Subestipulante: " + re.sub(r"[\[\]']", "", str(responsavel_legal_subestipulante))
        }                        