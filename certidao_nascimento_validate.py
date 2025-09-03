import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate
from Distances import distances
from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Certidao_nascimento():
    nome: str
    nome_mae: str
    data_nascimento: str
    cpf: str
    aceitar_documento: Optional[str] = None
    nome_titular: Optional[str] = None
    nome_pai: Optional[str] = None
    municipio_nascimento: Optional[str] = None
    data_registro: Optional[str] = None
    numero_matricula: Optional[str] = None
    grau_parentesco: Optional[str] = None
    avos_maternos: Optional[str] = None
    avos_paternos: Optional[str] = None


@dataclass
class Certidao_nascimento_validations:
    validacao_nome: str
    validacao_cpf: str
    validacao_nome_titular: str
    validacao_nome_mae: str
    validacao_data_nascimento: str
    validacao_aceitar_documento: Optional[str] = None


class certidao_nascimento_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Certidao_nascimento(**cartao_proposta)
        self.dados_extraidos = Certidao_nascimento(**dados_extraidos)
        self.message_type = message_type

    def set_validate_functions_list(self):
        return list(Certidao_nascimento_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type
    

    @validate
    def validacao_aceitar_documento(self, n_anos=8):
        """
        Valida se o dependente pode aceitar o documento com base na sua idade e no tipo de parentesco.

        Lógica de Retorno:
        - A função calcula a diferença entre a data de nascimento do dependente e a data atual.
        - Se o dependente for "Filho", "Filha", "Enteado" ou "Enteada":
            - TRUE: Se a diferença de anos for menor ou igual ao limite de idade (`n_anos`);
            - FALSE: Caso contrário.
        - Se o dependente for "Neto" ou "Neta", a validação é automaticamente válida, independentemente da idade.

        Parâmetros:
        n_anos (int, opcional): O número máximo de anos para o qual o dependente pode aceitar o documento. O valor padrão é 8 anos..
        """
        date = datetime.strptime(
            self.dados_extraidos.data_nascimento, '%d-%m-%Y')
        match self.cartao_proposta.grau_parentesco:
            case 'Filho' | 'Filha' | 'Enteado' | 'Enteada':
                is_valid = timedelta(days=365*n_anos) >= datetime.now() - date
                print(is_valid)
                return {'valid': is_valid, 'score': 100 if is_valid else 0}
            case 'Neto' | 'Neta':
                return {'valid': True, 'score': 100}

    @validate
    def validacao_nome(self, limiar=90):
        """
        Valida se o nome extraído do cartao_proposta corresponde ao nome extraído dos dados, com base na similaridade.

        Lógica de Retorno:
            - TRUE: Se a similaridade for maior ou igual ao limiar especificado, a validação é considerada válida;
            - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 95.
        """
        s1 = self.cartao_proposta.nome
        s2 = self.dados_extraidos.nome

        score = distances(s1, s2).norm_score()
        is_valid = score >= limiar
        return {'valid': is_valid, 'percent_match': score}

    @validate
    def validacao_cpf(self):
        """
        Valida se o CPF extraído do cartao_proposta corresponde ao CPF extraído dos dados.

        Lógica de Retorno:
        - TRUE: Se os CPFs forem iguais;
        - FALSE: Caso contrário.
        """
        s1 = ''.join(re.findall(r'\d+', self.cartao_proposta.cpf))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cpf))

        is_valid = s1 == s2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}

    @validate
    def validacao_nome_mae(self, limiar=90):
        """
        Valida se o nome da mãe extraído do cartao_proposta corresponde ao nome da mãe extraído dos dados, com base na similaridade.

        Lógica de Retorno:
        - TRUE: Se a similaridade for maior ou igual ao limiar especificado, a validação é considerada válida;
        - FALSE: Caso contrário.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 95.
        """
        s1 = self.cartao_proposta.nome_mae
        s2 = self.dados_extraidos.nome_mae

        score = distances(s1, s2).norm_score()
        is_valid = score >= limiar
        return {'valid': is_valid, 'percent_match': score}

    @validate
    def validacao_data_nascimento(self):
        """
        Valida se a data de nascimento extraída do cartao_proposta corresponde à data de nascimento extraída dos dados.

        Lógica de Retorno:
        - TRUE: Se as datas de nascimento forem iguais;
        - FALSE: Caso contrário.
        """
        date_1 = datetime.strptime(
            self.cartao_proposta.data_nascimento, '%d/%m/%Y')
        date_2 = datetime.strptime(
            self.dados_extraidos.data_nascimento, '%d-%m-%Y')

        is_valid = date_1 == date_2
        return {'valid': is_valid, 'percent_match': 100 if is_valid else 0}

    def _validacao_nome_avos(self, limiar=90):
        s1 = self.cartao_proposta.nome_titular
        s2_list = self.dados_extraidos.avos_maternos + \
            ' | ' + self.dados_extraidos.avos_paternos
        nomes_avos = s2_list.split(' | ')
        max_score = 0
        best_s2 = None
        for s2 in nomes_avos:
            score = distances(s1, s2).norm_score()
            if score >= limiar:
                return {'valid': True, 'percent_match': score, 'target': 'nome_titular',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}

            if score > max_score:
                max_score = score
                best_s2 = s2
        return {'valid': False, 'percent_match': max_score, 'target': 'nome_titular',
                "trecho_procurado": s1,
                "trecho_encontrado": best_s2}

    def _validacao_nome_pais(self, limiar=90):
        s1 = self.cartao_proposta.nome_titular
        s2_list = [self.dados_extraidos.nome_pai,
                   self.dados_extraidos.nome_mae]
        max_score = 0
        best_s2 = None
        for s2 in s2_list:
            score = distances(s1, s2).norm_score()
            if score >= limiar:
                return {'valid': True, 'percent_match': score, 'target': 'nome_titular',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}

            if score > max_score:
                max_score = score
                best_s2 = s2
        return {'valid': False, 'percent_match': max_score, 'target': 'nome_titular',
                "trecho_procurado": s1,
                "trecho_encontrado": best_s2}

    @required_docs('certidao_casamento')
    def _validacao_nome_padrastro_madrastra(self, certidao_casamento, limiar=90):

        s1 = self.cartao_proposta.nome_titular
        if certidao_casamento is None:
            return {'valid': False, 'percent_match': 0, 'target': 'nome_titular',
                    "trecho_procurado": s1,
                    "trecho_encontrado": 'Not Found',
                    "regras_subscricao_errors": 409}
        s2_list = [certidao_casamento['nome_titular'],
                   certidao_casamento['nome']]
        max_score = 0
        best_s2 = None
        for s2 in s2_list:
            score = distances(s1, s2).norm_score()
            if score >= limiar:
                return {'valid': True, 'percent_match': score, 'target': 'nome_titular',
                        "trecho_procurado": s1,
                        "trecho_encontrado": s2}

            if score > max_score:
                max_score = score
                best_s2 = s2
        return {'valid': False, 'percent_match': max_score, 'target': 'nome_titular',
                "trecho_procurado": s1,
                "trecho_encontrado": best_s2}

    @validate
    def validacao_nome_titular(self, limiar=90):
        """
        Valida se o nome do titular extraído do cartao_proposta corresponde ao nome do titular extraído dos dados de acordo com o parentesco do dependente.

        Lógica de Retorno:
        - TRUE: Se o nome do titular for semelhante ao nome encontrado nos dados extraídos (com base em um limiar de similaridade);
        - FALSE: Caso contrário, retornando o maior índice de similaridade encontrado.
        Dependendo do parentesco do dependente, o nome do titular será comparado com os nomes dos avós, pais ou padrasto/madrasta do dependente:
        - Para 'Neto' ou 'Neta', o nome do titular será comparado com os nomes dos avós.
        - Para 'Filho' ou 'Filha', o nome do titular será comparado com os nomes dos pais.
        - Para 'Enteado' ou 'Enteada', o nome do titular será comparado com os nomes do padrasto ou madrasta.

        Parâmetros:
        limiar (int, opcional): O valor mínimo de similaridade (entre 0 e 100) para considerar a validação válida. 
                                O valor padrão é 95.
        """
        match self.cartao_proposta.grau_parentesco[:3].upper():
            case 'NET':  # neto(a)
                return self._validacao_nome_avos(limiar)
            case 'FIL':  # filho(a)
                return self._validacao_nome_pais(limiar)
            case 'ENT':  # enteado(a)
                return self._validacao_nome_padrastro_madrastra(limiar=limiar)