import re
import datetime
from dateutil.relativedelta import relativedelta
from ValidateDocument import ValidateDocument, required_docs, validate
from Distances import distances

from dataclasses import dataclass
from typing import Optional
from validacao_endereco import Validacao_endereco, Endereco
from dataclasses_json import dataclass_json, Undefined


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Estatuto_social:
    razao_social: str
    cnpj: str
    endereco_empresa: str
    cargo_responsavel_legal: Optional[str] = None
    assinatura_isolada: Optional[str] = None
    tempo_mandato: Optional[str] = None
    regras_assinatura_conjunto: Optional[str] = None
    nomes_assinatura: Optional[str] = None

@dataclass
class Estatuto_social_validations:
    validacao_razao_social: str
    validacao_cnpj: str
    validacao_endereco_empresa: str
    validacao_responsavel_legal: str 


@dataclass_json(undefined=Undefined.EXCLUDE)  
@dataclass
class Estatuto_social_sign:
    ha_assinatura: str
    descricao_assinatura: str
    confianca_assinatura: str
    ha_selo: str
    descricao_selo: str
    confianca_selo: str
    ha_carimbo: str
    descricao_carimbo: str
    confianca_carimbo: str
    ha_termo_autenticidade: str
    descricao_termo_autenticidade: str
    confianca_termo_autenticidade: str


@dataclass
class Estatuto_social_sign_validations:
    validacao_assinatura: str
    validacao_selo_carimbo: str


class estatuto_social_validate(ValidateDocument):
    
    def __init__(self, cartao_proposta, dados_extraidos, message_type):

        self.message_type = message_type
        self.cartao_proposta = Estatuto_social(**cartao_proposta)

        if (message_type == "signature"): 
            self.dados_extraidos = Estatuto_social_sign(**dados_extraidos)
        else:
            self.dados_extraidos = Estatuto_social(**dados_extraidos)
    
    
    def set_validate_functions_list(self):
        return list(Estatuto_social_validations.__annotations__.keys())
    
    
    def set_validate_sign_functions_list(self):
        return list(Estatuto_social_sign_validations.__annotations__.keys())
    
    def get_validate_type(self):
        return self.message_type
    
    
    @validate
    def validacao_razao_social(self, limiar=90):
        """
        Valida se a razão social do cartao_proposta corresponde a razão social extraída do Estatuto Social.
    
        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
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
        Valida se o CNPJ do cartao_proposta corresponde ao CNPJ extraído do Estatuto Social.
    
        Lógica de Retorno:
        - TRUE: Se os CNPJs forem iguais;
        - FALSE: Caso contrário.
        """

        s1 = ''.join(re.findall( r'\d+', self.cartao_proposta.cnpj))
        s2 = ''.join(re.findall(r'\d+', self.dados_extraidos.cnpj))
        if s1 == s2:
            return {'valid': True, 'percent_match': 100}
        else:
            return {'valid': False, 'percent_match': 0}

    @validate       
    def validacao_endereco_empresa(self, limiar=0.5):
        """
        Valida se o endereço do cartao_proposta corresponde ao endereço extraído do Estatuto Social.
    
        Lógica de Retorno:
        - TRUE: Se os endereços forem iguais;
        - FALSE: Caso contrário.
        """

        val_endereco = Validacao_endereco(self.cartao_proposta.endereco_empresa, self.dados_extraidos.endereco_empresa)
        valid, score = val_endereco.validar_endereco(limiar)
        
        return {'valid': valid, 'percent_match': score}


    def gerar_retorno(self, valid, percent_match, trecho_procurado="", trecho_encontrado="", erros=None):
        """
        Gera retorno no formato de dicionário esperado.
        """
        if(erros == None):
            return {
                'valid': valid,
                'percent_match': percent_match,
                'target': 'responsavel_legal',
                "trecho_procurado": trecho_procurado,
                "trecho_encontrado": trecho_encontrado
            }
        else:
            return {
                'valid': valid,
                'percent_match': percent_match,
                'target': 'responsavel_legal',
                "trecho_procurado": trecho_procurado,
                "trecho_encontrado": trecho_encontrado,
                "regras_subscricao_errors": erros or []
            }
    
        
    def _check_responsaveis(self, responsavel_legal, nomes_assinatura, threshold=90):
        """
        Procura uma correspondência válida entre os nomes das listas responsavel_legal e nomes_assinatura.

        Lógica de Retorno:
        - valid: True, se encontrar nomes iguais; False, caso contrário
        - trecho_encontrado: Nome correspondente encontrado do responsável legal 
        - trecho_procurado: Nome da pessoa que assinou 
        - score: Score de similaridade dos nomes analisados
        """
        
        # encontra o primeiro par de elementos com similaridade acima do limiar
        nomes_assinatura = [nomes_assinatura] if isinstance(nomes_assinatura, str) else nomes_assinatura
        responsavel_legal = [responsavel_legal] if isinstance(responsavel_legal, str) else responsavel_legal
        for item1 in responsavel_legal:
            for item2 in nomes_assinatura:
                score = distances(item1.upper(), item2.upper()).norm_score()
                if score >= threshold:
                    return True, item1, item2, score

        # retorno padrão caso nenhum elemento similar seja encontrado
        return False, nomes_assinatura, responsavel_legal, 0


    def check_assinatura_isolada(self, cargo_responsavel_legal, cargos_eleitos, nomes_assinatura):
        """
        Checa correspondência da assinatura exclusivamente nos casos de assinatura isolada (uma única pessoa assinando a proposta).

        Lógica de Retorno:
        - valid: True, se encontrar nomes forem iguais; False, caso contrário
        - score: Score de similaridade dos nomes analisados
        - trecho_procurado: Nome da pessoa que assinou
        - trecho_encontrado: Nomes encontrados dos responsáveis legais
        """
        
        for cargo in cargo_responsavel_legal:
            # verifica diretamente no dict ou busca uma chave semelhante
            responsavel_legal = cargos_eleitos.get(cargo) or next(
                (cargos_eleitos[key] for key in cargos_eleitos if cargo in key), None
            )

            if responsavel_legal:
                valid, trecho_procurado, trecho_encontrado, score = self._check_responsaveis(responsavel_legal, nomes_assinatura)
                if valid:
                    return self.gerar_retorno(valid, score, trecho_procurado, trecho_encontrado)

        # retorno padrão caso nenhuma validação seja bem sucedida
        return self.gerar_retorno(False, 0, trecho_procurado, trecho_encontrado)
    

    def plural_para_singular(self, palavra):
        """
        Converte palavras/cargos do plural para o singular.
        Exemplo: "diretores" -> "diretor"

        Lógica de Retorno:
        - Palavra no singular, se for possível converter;
        - Palavra original:
        """
        
        if palavra.endswith("res"):
            return palavra[:-2]  
        elif palavra.endswith("s"):
            return palavra[:-1]  
        return palavra 


    def padronizar_regras_assinatura(self, texto):
        """
        Padroniza entrada para formato mais viável de processar.
        As entradas podem vir em diversos formatos, como, por exemplo: ['2 Diretores'], ['1 Diretor', '1 procurador'], ['2 procuradores']
        Essa função padroniza essa entrada, criando uma lista no formato do exemplo: ['2 Diretores'] -> ['Diretor', 'Diretor']

        Lógica de Retorno:
        - Regra padronizada, se possível aplicar as alterações;
        - Regra no formato original:
        """

        # regex para identificar padrões como "1 Diretor", "2 Diretores", etc.
        padrao = r"(\d*)\s*([A-Za-zÀ-ú\-]+(?:\s[A-Za-zÀ-ú\-]+)*)"
        matches = re.findall(padrao, texto)

        resultados = []

        for qtd, cargo in matches:
            # se quantidade estiver vazia (ex: "Diretor"), assume 1
            qtd = int(qtd) if qtd else 1

            cargo_singular = " ".join(self.plural_para_singular(palavra) for palavra in cargo.split())
            
            # adiciona o cargo repetido conforme a quantidade
            resultados.extend([cargo_singular] * qtd)

        return resultados

    
    def _obter_cargos(self, cargos_eleitos, cargo):
        """
        Procura o cargo igual ou similar no dicionário com os cargos e nomes correspondentes.

        Lógica de Retorno:
        - Nomes dos responsáveis correspondentes ao cargo buscado;
        - None, caso não seja possível encontrar o cargo.
        """
        resultados = [cargos_eleitos[key] for key in cargos_eleitos if cargo in key]

        return cargos_eleitos.get(cargo) or resultados

        #return cargos_eleitos.get(cargo) or next(
        #    (cargos_eleitos[key] for key in cargos_eleitos if cargo in key), None
        #)


    def _encontrar_match(self, cargos, nomes_restantes, threshold):
        """
        Encontra o primeiro nome do assinante com similaridade acima do limiar.
        Retorna uma tupla (nome_assinado, nome_esperado) ou None se não houver match.
        """
        
        for nome_esperado in cargos:
            nome_assinado = next(
                (nome for nome in nomes_restantes if distances(nome_esperado.upper(), nome.upper()).norm_score() >= threshold),
                None
            )
            if nome_assinado:
                return nome_assinado, nome_esperado
        return None
    
    def verificar_assinaturas(self, cargos_eleitos, regra_assinatura, nome_assinou, threshold=90):
        """
        Verifica se os nomes de quem assinou são similares aos nomes dos responsáveis legais.
        Retorna o resultado final (True/False) e os matches encontrados.
        """
        nomes_restantes = set(nome_assinou)
        resultados = []

        for cargo in regra_assinatura:
            # obtém os nomes dos responsáveis legais
            cargos = self._obter_cargos(cargos_eleitos, cargo)

            if not cargos:
                return False, resultados

            if(isinstance(cargos, str)):
                cargos = [cargos]

            match = self._encontrar_match(cargos, nomes_restantes, threshold)
            if match:
                nome_assinado, nome_esperado = match
                resultados.append(nome_esperado)
                nomes_restantes.remove(nome_assinado)
            else:
                return False, resultados

        return True, resultados

    
    @validate
    @required_docs('ata_assembleia')
    def validacao_responsavel_legal(self, ata_assembleia):
        """
        Valida se o(s) nome(s) da(s) pessoa(s) que assinaram os documentos internos (Cartão Proposta, Proposta de Contração, etc) 
        corresponde aos responsáveis legais por assinar contratos da empresa (informação extraída da Ata de Eleição e Estatuto Social).

        Lógica de Retorno:
        - TRUE: Se os nomes forem iguais;
        - FALSE: Caso contrário.
        """

        if ata_assembleia is None:
            return self.gerar_retorno(False, 0, erros=409)
        
        cargos_eleitos = ata_assembleia['cargos_eleitos']
        cargo_responsavel_legal = self.dados_extraidos.cargo_responsavel_legal
        assinatura_isolada = self.dados_extraidos.assinatura_isolada
        
        if(isinstance(assinatura_isolada, str)):
            assinatura_isolada = assinatura_isolada.lower() == "true"
        
        regras_assinatura_conjunto = self.dados_extraidos.regras_assinatura_conjunto

        # normalizar lista para reduzir um nível da hierarquia caso retorne apenas um elemento
        if isinstance(regras_assinatura_conjunto, list) and len(regras_assinatura_conjunto) == 1:
            primeiro = regras_assinatura_conjunto[0]
            if isinstance(primeiro, list):
                # Achata só um nível
                regras_assinatura_conjunto_normalizado = primeiro
        else:
            regras_assinatura_conjunto_normalizado = regras_assinatura_conjunto

        nomes_assinatura = self.cartao_proposta.nomes_assinatura
        nomes_assinatura = [nomes_assinatura] if isinstance(nomes_assinatura, str) else nomes_assinatura
        # assinatura isolada (uma única pessoa assinando a proposta)
        if assinatura_isolada:
            return self.check_assinatura_isolada(cargo_responsavel_legal, cargos_eleitos, nomes_assinatura)

        # assinatura em conjunto (verificar todos os responsáveis legais nos nomes assinados)
        lista_nomes_encontrados = []
        
        for regra in regras_assinatura_conjunto_normalizado:
            # padroniza a regra, ex.: ['2 Diretores'] -> ['Diretor', 'Diretor']
            regra_corrente = self.padronizar_regras_assinatura(", ".join(regra))
            valid, nomes_encontrados = self.verificar_assinaturas(cargos_eleitos, regra_corrente, nomes_assinatura)
             
            lista_nomes_encontrados.extend(nomes_encontrados)

            if valid:
                return self.gerar_retorno(valid, 100, nomes_assinatura, nomes_encontrados)

        score = len(set(lista_nomes_encontrados)) / len(nomes_assinatura) if nomes_assinatura else 0

        regras_sep = []
        for sublist in regras_assinatura_conjunto_normalizado:
            if len(sublist) == 1:
                regras_sep.append(sublist[0])
            elif len(sublist) == 2:
                regras_sep.append(f'{sublist[0]} e {sublist[1]}')
            else:
                # Caso a sublista tenha mais de 2 elementos, juntamos com 
                # " e " para os dois primeiros e deixando o resto como está
                regras_sep.append(' e '.join(sublist[:2]) + (f' e {", ".join(sublist[2:])}' if len(sublist) > 2 else ''))

        # regras_sep = [f'{x} e {y}' for x, y in regras_assinatura_conjunto_final]
        
        regras_assinatura_str = ' ou '.join(regras_sep)

        nomes = ", ".join(set(lista_nomes_encontrados))
        trecho_encontrado = "Responsáveis legais encontrados: "+nomes+" | Este documento deve ser assinado em conjunto. Regras para assinatura: "+regras_assinatura_str

        return self.gerar_retorno(False, score, nomes_assinatura, trecho_encontrado)

    @validate   
    def validacao_selo_carimbo(self):
        """
        Valida se há selo ou carimbo no documento.
    
        Lógica de Retorno:
        - TRUE: Se identificar um selo ou carimbo;
        - FALSE: Caso contrário.
        """

        ha_selo = self.dados_extraidos.ha_selo
        if(isinstance(ha_selo, str)):
            ha_selo = (lambda x: False if x in {'False', 'false'} else True)(ha_selo)
        
        ha_carimbo = self.dados_extraidos.ha_carimbo
        if(isinstance(ha_carimbo, str)):
            ha_carimbo = (lambda x: False if x in {'False', 'false'} else True)(ha_carimbo)

        ha_termo_autenticidade = self.dados_extraidos.ha_termo_autenticidade
        if(isinstance(ha_termo_autenticidade, str)):
            ha_termo_autenticidade = (lambda x: False if x in {'False', 'false'} else True)(ha_termo_autenticidade)

        if(ha_selo or ha_carimbo or ha_termo_autenticidade):
            ha_selo_carimbo = True
            confianca = max(int(self.dados_extraidos.confianca_selo), int(self.dados_extraidos.confianca_carimbo), int(self.dados_extraidos.confianca_termo_autenticidade)) 
        else:
            ha_selo_carimbo = False
            confianca = 0 
            
        return {"valid": ha_selo_carimbo, "target": "selo_carimbo", "percent_match": confianca, 
            "trecho_procurado": "",
            "trecho_encontrado": self.dados_extraidos.descricao_carimbo + " | " + self.dados_extraidos.descricao_selo + " | " + self.dados_extraidos.descricao_termo_autenticidade}
    

    @validate   
    def validacao_assinatura(self):
        """
        Valida se há assinatura no documento.
    
        Lógica de Retorno:
        - TRUE: Se for identificada assinatura;
        - FALSE: Caso contrário.
        """

        ha_assinatura = self.dados_extraidos.ha_assinatura
        if(isinstance(ha_assinatura, str)):
            ha_assinatura = (lambda x: False if x in {'False', 'false'} else True)(ha_assinatura)

        return {"valid": ha_assinatura, "target": "ha_assinatura", "percent_match": self.dados_extraidos.confianca_assinatura, 
            "trecho_procurado": "",
            "trecho_encontrado": self.dados_extraidos.descricao_assinatura}
    
