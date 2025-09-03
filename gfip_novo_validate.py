import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate, fraud_validate
from Distances import distances
from collections import namedtuple
from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, Undefined
from fraud_tools import ValidadorMetadadosPDF


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Gfip_novo:
    cnpj: str
    razao_social: str
    data_emissao: Optional[str] = None
    compulsoriedade: Optional[str] = None
    numero_vidas: Optional[str] = None
    trabalhadores_collection: Optional[str] = None
    competencia: Optional[str] = None


@dataclass
class Gfip_novo_validations:
    #validacao_nome: str
    #validacao_cpf: str
    validacao_cnpj: str
    validacao_razao_social: str
    validacao_aceitacao_facultativa: str
    validacao_competencia_apuracao: str
    #validacao_vinculo: str



@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Gfip_novo_fraud:
    creator: str 
    producer: str
    trapped: str
    encryption: str 
    creationDate: Optional[str]
    modDate: Optional[str]

@dataclass
class Gfip_novo_fraud_validations:
    validacao_metadado_datas: str


compulsoriedade = {
    "FGTS_GFIP": "0",
    "CATEGORIA_FUNCIONAL": "1",
    "REGIAO": "2",
    "FACULTATIVA": "4"}

tipo_vinculo = {
    'socio': '1',
    'empregado': '2',
    'empregado_temporario': '3',
    'pj': '4',
    'administrador': '5',
    'jovem_aprendiz': '6',
    'procurador': '7',
    'estagiario': '8',
    'estatutario': '9',
    'demitidos_aposentados': '10'
}


class Name:
    def __init__(self, nome, limiar):
        self.nome = nome
        self.limiar = limiar

    # Lógica personalizada para comparação de igualdade
    def __eq__(self, other):
        if isinstance(other, Name):
            score = distances(self.nome, other.nome).norm_score()
            return score >= self.limiar
        return False

    def __hash__(self):
        return hash(self.nome)

    def __repr__(self):
        return self.nome


class gfip_novo_validate(ValidateDocument):

    def __init__(self, cartao_proposta, dados_extraidos, message_type):
        self.cartao_proposta = Gfip_novo(**cartao_proposta)
        self.message_type = message_type

        if (message_type == "fraud_metadata"):
            self.dados_extraidos = Gfip_novo_fraud(**dados_extraidos)
        else:
            self.dados_extraidos = Gfip_novo(**dados_extraidos)
   
    def set_validate_functions_list(self):
        return list(Gfip_novo_validations.__annotations__.keys())
    
    def set_validate_fraud_functions_list(self):
        return list(Gfip_novo_fraud_validations.__annotations__.keys())

    def get_validate_type(self):
        return self.message_type

    def _set_comparison(self, set_1, set_2, modo_comparacao):
        """
        Lógica de Comparação:
        - 'somente_proposta': A comparação é feita apenas entre os nomes presentes na proposta e os nomes extraídos do documento ('trabalhadores_collection'). 
        Retorna TRUE se todos os nomes da proposta forem encontrados no documento. 
        Ou seja, todos os nomes presentes em `fgts_trabalhadores` devem ser encontrados em `trabalhadores_collection`.

        - 'somente_documento': A comparação é feita apenas entre os nomes presentes no documento e os nomes da proposta. 
        Retorna TRUE se todos os nomes extraídos do documento forem encontrados na proposta. 
        Ou seja, todos os nomes presentes em `trabalhadores_collection` devem ser encontrados em `fgts_trabalhadores`.

        - 'interseccao_completa': A comparação verifica se os dois conjuntos de nomes possuem exatamente os mesmos elementos, 
        ou seja, se a interseção entre os dois conjuntos é igual a ambos os conjuntos. 
        Retorna TRUE apenas se os dois conjuntos de nomes forem idênticos, sem diferenças.
        """
        dif_s1_set = list(set_1 - set_2)
        dif_s2_set = list(set_2 - set_1)
        dif_simetric = list(set_1 ^ set_2)
        match modo_comparacao:
            case 'somente_proposta':
                is_valid = len(dif_s1_set) == 0
                missed = dif_s1_set
            case 'somente_documento':
                is_valid = len(dif_s2_set) == 0
                missed = dif_s2_set
            case 'interseccao_completa':
                is_valid = len(dif_simetric) == 0
                missed = dif_simetric

        if is_valid:
            return {'valid': True, 'percent_match': 100,
                    "trecho_procurado": str(set_1),
                    "trecho_encontrado": str(set_2)}
        else:
            return {'valid': False, 'percent_match': 0,
                    "trecho_procurado": str(missed),
                    "trecho_encontrado": str(set_2),
                    "regras_subscricao_errors": 404}

    #@validate
    #@required_docs('gfip_novo')
    def validacao_nome(self, gfip_novo, modo_comparacao='somente_proposta', limiar=.98):
        """
        Valida se os nomes extraídos do 'fgts_trabalhadores' correspondem aos nomes extraídos do documento, 
        usando a lógica de comparação especificada.

        Parâmetros:
        - `fgts_trabalhadores`: Conjunto de dados com os trabalhadores extraídos da proposta.
        - `modo_comparacao`: Tipo de comparação que será realizada entre os conjuntos de nomes.
        - `limiar`: Limite de similaridade para considerar uma correspondência válida.
        """
        if(len(gfip_novo['funcionarios']) == 0):
            return {'valid': False, 'percent_match': 0,
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        s1_set = set([Name(i['nome'], limiar)
                     for i in gfip_novo['funcionarios']])
        s2_set = set([Name(i['Nome Trabalhador'], limiar)
                     for i in self.dados_extraidos.trabalhadores_collection])
        return self._set_comparison(s1_set, s2_set, modo_comparacao)

    #@validate
    #@required_docs('gfip_novo')
    def validacao_cpf(self, gfip_novo, modo_comparacao='somente_proposta'):
        """
        Valida se os cpfs extraídos do 'fgts_trabalhadores' correspondem aos cpfs extraídos do documento, 
        usando a lógica de comparação especificada.

        Parâmetros:
        - `fgts_trabalhadores`: Conjunto de dados com os trabalhadores extraídos da proposta.
        - `modo_comparacao`: Tipo de comparação que será realizada entre os conjuntos de nomes.
        - `limiar`: Limite de similaridade para considerar uma correspondência válida.
        """
        if(len(gfip_novo['funcionarios']) == 0):
            return {'valid': False, 'percent_match': 0,
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        s1_set = set([''.join(re.findall(r'\d+', i['cpf']))
                     for i in gfip_novo['funcionarios']])
        s2_set = set([''.join(re.findall(r'\d+', i['CPF']))
                     for i in self.dados_extraidos.trabalhadores_collection])
        return self._set_comparison(s1_set, s2_set, modo_comparacao)

    @validate
    def validacao_cnpj(self):
        """
        Valida se a raiz do CNPJ do cartao_proposta corresponde ao CNPJ raiz extraído do documento.

        Lógica de Retorno:
        - TRUE: Se as raízes dos CNPJs forem iguais;
        - FALSE: Caso contrário.
        """
        s1 = ''.join(re.findall(
            r'\d+', self.cartao_proposta.cnpj))[:8]
        s2 = ''.join(re.findall(
            r'\d+', self.dados_extraidos.cnpj.split('/')[0]))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate
    def validacao_razao_social(self, limiar=90):
        """
        Valida se a razão social do cartao_proposta corresponde a razão social extraída do documento.

        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """
        s1 = self.cartao_proposta.razao_social
        s2 = self.dados_extraidos.razao_social

        sim_score = distances(s1.upper(), s2.upper()).norm_score()
        is_valid = sim_score >= limiar
        return {'valid': is_valid, 'percent_match': sim_score}

    @validate
    def validacao_aceitacao_facultativa(self):
        """
        Valida a elegibilidade da proposta com base nas regras de aceitação facultativa.

        Lógica de Retorno:
        - TRUE: Se a proposta atender aos critérios de elegibilidade facultativa ou ser de elegibilidade compulsória.
        - FALSE: Se a proposta não atender aos critérios de elegibilidade facultativa.

        Regras:
        1. Verifica se a elegibilidade é 'facultativa'.
        2. Para cada CNPJ raiz:
        - Se for uma filial (mesmo CNPJ raiz da estipulante), a soma total de vidas não pode exceder 99.
        - Se for uma coligada (CNPJ raiz diferente), cada CNPJ individualmente não pode ter mais de 99 vidas.
        """
        s1 = self.cartao_proposta.compulsoriedade
        s2_list = [''.join(re.findall(r'\d+', i['Estabelecimento'].split('/')[0]))
                   for i in self.dados_extraidos.trabalhadores_collection]

        if int(s1) == int(compulsoriedade["FACULTATIVA"]):
            c = {}
            for i in s2_list:
                if i in c:
                    c[i] += 1
                else:
                    c[i] = 1

            # Verificar se a quantidade de elementos é maior que 99
            for i, k in c.items():
                if k > 99:
                    return {'valid': False, 'percent_match': 0, 'trecho_encontrado': f'{k} vidas ultrapassam o limite para compulsoriedade facultativa {s1}'}
                else:
                    return {'valid': True, 'percent_match': 100, 'trecho_encontrado': f'{k} vidas para compulsoriedade facultativa {s1}'}
        else:
            return {'valid': True, 'percent_match': 100, 'trecho_encontrado': f'Compulsoriedade {s1} não verifica elegibilidade'}

    @validate
    def validacao_competencia_apuracao(self, days=60):
        """
        Verifica se a competência de apuração está dentro dos últimos dois meses.
        
        Lógica de Retorno:
        - TRUE: Caso a competência seja no máximo há dois meses antes da validação.
        - FALSE: Caso contrário.
        """

        now = datetime.datetime.now().date()
        
        competencia_str = self.dados_extraidos.competencia.strip()
        extracted_competencia_date = datetime.datetime.strptime(competencia_str, "%m/%Y").date().replace(day=1)

        limite_data = now - relativedelta(days=days)

        if extracted_competencia_date >= limite_data:
            return {'valid': True, 'percent_match': 100, 'target': 'competencia_apuracao', 
                    "trecho_encontrado": extracted_competencia_date.strftime('%m/%Y'),
                    "trecho_procurado": ""}
        else:
            return {'valid': False, 'percent_match': 0, 'target': 'competencia_apuracao', 
                    "trecho_encontrado": extracted_competencia_date.strftime('%m/%Y'),
                    "trecho_procurado": ""}

    #@validate
    #@required_docs('gfip_novo')
    def validacao_vinculo(self, gfip_novo, modo_comparacao='interseccao_completa'):
        """
        Verifica se para todos os CPFs com as categorias 101 (Empregado) ou 103 (Jovem aprendiz), 
        o vínculo corresponde ao informado:
        - Categoria 101 (FGTS) deve corresponder a 'empregado' (vínculo).
        - Categoria 103 (FGTS) deve corresponder a 'jovem aprendiz' (vínculo).
        Parâmetros:
        - `fgts_trabalhadores`: Conjunto de dados com os trabalhadores extraídos da proposta.
        - `modo_comparacao`: Tipo de comparação que será realizada entre os conjuntos de nomes.
        Se houver qualquer inconsistência, por exemplo, um cpf não está em ambas as relações de trabalhodres ou o vínculo é diferente,
        retorna False.
        """
        # Aplica-se somente quando elegibilidade for 'compulsoria_100_fgts'
        if(len(gfip_novo['funcionarios']) == 0):
            return {'valid': False, 'percent_match': 0,
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "regras_subscricao_errors": 409}
        if int(self.cartao_proposta.compulsoriedade) != int(compulsoriedade['FGTS_GFIP']):
            return {'valid': True, 'percent_match': 100}

        categoria_vinculo_depara = {'101': '2', '103': '6', 101: '2', 103: '6'}
        worker = namedtuple('worker', ['cpf', 'vinculo'])
        t_cp = list(filter(lambda d: int(d['tipo_vinculo']) in [
                    2, 6], gfip_novo['funcionarios']))
        t_de = list(filter(lambda d: int(d['Categoria']) in [
                    101, 103], self.dados_extraidos.trabalhadores_collection))

        t_cp_set = set([worker(cpf=''.join(re.findall(r'\d+', i['cpf'])),
                       vinculo=int(i['tipo_vinculo'])) for i in t_cp])
        t_de_set = set([worker(cpf=''.join(re.findall(r'\d+', i['CPF'])),
                       vinculo=int(categoria_vinculo_depara[i['Categoria']])) for i in t_de])

        return self._set_comparison(t_cp_set, t_de_set, modo_comparacao)
    

    
    @fraud_validate
    @required_docs('gfip_novo')
    def validacao_metadado_datas(self, gfip_novo):
        """
        Valida se a data de emissão extraída do FGTS é anterior a data de criação do documento extraída dos metadados.

        Lógica de Retorno:
        - TRUE: Se a data de emissão for anterior a data de criação do documento.
        - FALSE: Caso contrário.
        """

        if(gfip_novo is None):
            return {'valid': False, 'percent_match': 0, 'target': 'metadado_datas',
                        "trecho_procurado": "", "trecho_encontrado": "",
                        "fraud_errors": 409}
        
        val = ValidadorMetadadosPDF()

        creation_date = self.dados_extraidos.creationDate
        data_emissao = gfip_novo.get('data_emissao')

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
    