import re
from typing import List, Dict, Any, Optional, Union
from difflib import SequenceMatcher
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from dateutil import parser
from datetime import datetime, timedelta


class SimilarTextValidator:
    def __init__(self, corpus_texts: List[Dict[str, Any]]):
        """
        corpus_texts: lista de dicts com {'text': str, 'id': qualquer}
        """
        self.corpus_texts = corpus_texts

    def preprocess_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        try:
            stop_words = set(stopwords.words('portuguese'))
            tokens = word_tokenize(text, language='portuguese')
            tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
            return ' '.join(tokens)
        except Exception:
            return text


    def jaccard_similarity(self, text1: str, text2: str, preprocess=True) -> float:
        if preprocess:
            text1 = self.preprocess_text(text1)
            text2 = self.preprocess_text(text2)

        words1 = set(text1.split())
        words2 = set(text2.split())

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        if union == 0:
            return 0.0

        return intersection / union

    def sequential_similarity(self, text1: str, text2: str) -> float:
        return SequenceMatcher(None, text1, text2).ratio()

    def validate(self, text: dict, threshold=0.9, metric="sequential") -> List[Dict[str, Any]]:
        """
        Validate text similarity using a chosen metric.
        metric: 'tfidf', 'jaccard', or 'sequential'

        Returns list de alertas com 'text', 'id' e 'score'
        """

        valid_metrics = {
            'jaccard': self.jaccard_similarity,
            'sequential': self.sequential_similarity
        }

        if metric not in valid_metrics:
            raise ValueError(f"Invalid metric '{metric}'. Choose from 'jaccard', or 'sequential'.")

        similarity_function = valid_metrics[metric]
        alerts = []

        for item in self.corpus_texts:
            base_text = item['extracted_text']
            if base_text:
                score = similarity_function(text.get('extracted_text'), base_text)
                if score > threshold:
                    alerts.append({
                        'nome': item['nome'],
                        'score': int(round(score * 100))
                    })

        return alerts



class ValidadorMetadadosPDF:
    """
    Classe para validar metadados de PDF focando na data de emissão
    para detectar possíveis fraudes em documentos.
    """
    
    def __init__(self, config = {
            'score_maximo_suspeita': 100,
            'threshold_bloqueio': 40,
            'dias_maximos_apos_emissao': 60,
            'dias_alerta_apos_emissao': 30,
            'intervalo_max_edicao_horas': 48,
            'dias_documento_antigo': 90,
            'dias_pdf_recente': 7,
            'tolerancia_horas_antes': 24*3
        }):
        # Configurações de validação relacionadas apenas às datas
        self.config = config
    
    def configurar_thresholds(self, **kwargs) -> None:
        """
        Configura os thresholds de validação
        """
        for chave, valor in kwargs.items():
            if chave in self.config:
                self.config[chave] = valor
                
    def fix_timezone(self, m):
        sign = m.group(1)
        hour = m.group(2)
        minute = m.group(3) if m.group(3) else "00"
        hour = hour.zfill(2)  # garante 2 dígitos
        return f"{sign}{hour}:{minute}"
    
    def _normalizar_timezone(self, dt):
        """
        Normaliza datetime para remover timezone info para comparações
        """
        if dt is None:
            return None
        
        # Se tem timezone, converte para UTC e remove timezone info
        if dt.tzinfo is not None:
            dt_utc = dt.utctimetuple()
            return datetime(*dt_utc[:6])
        
        return dt
    
    def converter_data(self, data):
        try:
            x_str = str(data).strip()

            if not x_str or x_str in ["0", "D:", "None", "null"]:
                return None

            if x_str.startswith("D:"):
                x_str = x_str[2:]

            x_str = x_str.replace("'", "")

            # Normaliza Z00... para +0000
            x_str = re.sub(r"Z(\d{2})(\d{2})", r"+\1\2", x_str)

            # Normaliza fuso horário com 1 dígito (-3 ou +5) para dois dígitos (-03, +05)
            x_str = re.sub(r"([+-])(\d{1,2}):?(\d{2})?", self.fix_timezone, x_str)

            dt = parser.parse(x_str)
            
            # Normalizar timezone para evitar erros de comparação
            return self._normalizar_timezone(dt)

        except Exception as e:
            print(f"Erro ao processar '{data}': {e}")
            return None
    
    def _extrair_metadados(self, dados: Dict) -> Dict:
        """
        Extrai e normaliza os metadados do formato fornecido
        """
        metadados = {
            'bucket': dados.get('bucket'),
            'key': dados.get('key'),
            'size_file': dados.get('size_file'),
            'num_pages': dados.get('num_pages'),
            'is_encrypted': dados.get('is_encrypted'),
            'last_modified_s3': dados.get('LastModified_s3'),
            'etag': dados.get('etag'),
            'content_type': dados.get('content_type'),
            'title': dados.get('Title'),
            'author': dados.get('Author'),
            'subject': dados.get('Subject'),
            'creator': dados.get('Creator'),
            'producer': dados.get('Producer'),
            'data_criacao': dados.get('CreationDate'),
            'data_modificacao': dados.get('ModDate'),
            'keywords': dados.get('Keywords')
        }
        
        return metadados
    
    def _converter_data_emissao(self, data_emissao: Union[datetime, str]) -> Optional[datetime]:
        """Converte data de emissão para datetime com formatos expandidos"""
        if isinstance(data_emissao, datetime):
            return self._normalizar_timezone(data_emissao)
        elif isinstance(data_emissao, str):
            try:
                # Formatos mais comuns primeiro para otimização
                formatos = [
                    '%d/%m/%Y',  # Formato brasileiro primeiro
                    '%Y-%m-%d',
                    '%Y-%m-%d %H:%M:%S',
                    '%d/%m/%Y %H:%M:%S',
                    '%Y/%m/%d',
                    '%m/%d/%Y',
                    '%d-%m-%Y',
                    '%Y%m%d',
                    '%d/%m/%Y %H:%M',
                    '%Y-%m-%d %H:%M'
                ]
                for formato in formatos:
                    try:
                        dt = datetime.strptime(data_emissao.strip(), formato)
                        return self._normalizar_timezone(dt)
                    except ValueError:
                        continue
                        
                # Se nenhum formato funcionou, tenta o parser genérico
                try:
                    dt = parser.parse(data_emissao, dayfirst=True)  # Assume formato brasileiro
                    return self._normalizar_timezone(dt)
                except:
                    pass
                    
            except Exception:
                pass
        return None
    
    def _validar_datas_emissao(self, metadados: Dict, data_emissao_documento: Optional[datetime]) -> Dict:
        """Valida as datas do PDF em relação à data de emissão com lógica aprimorada"""
        resultado = {'alertas': [], 'score': 0, 'detalhes': {}}
        
        data_criacao_pdf = self.converter_data(metadados.get('data_criacao'))
        data_modificacao_pdf = self.converter_data(metadados.get('data_modificacao'))
        data_emissao_doc = self._converter_data_emissao(data_emissao_documento)
        
        if not data_emissao_doc:
            resultado['alertas'].append("Data de emissão do documento não fornecida ou inválida")
            resultado['score'] += 5
            return resultado
        
        resultado['detalhes']['data_emissao_documento'] = data_emissao_doc.strftime('%Y-%m-%d %H:%M:%S')
        agora = datetime.now()
        
        # Adicionar informações das datas extraídas para debug
        if data_criacao_pdf:
            resultado['detalhes']['data_criacao_pdf'] = data_criacao_pdf.strftime('%Y-%m-%d %H:%M:%S')
        if data_modificacao_pdf:
            resultado['detalhes']['data_modificacao_pdf'] = data_modificacao_pdf.strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Validação crítica: PDF criado ANTES da data de emissão (com tolerância)
        if data_criacao_pdf:
            try:
                diferenca_horas = (data_emissao_doc - data_criacao_pdf).total_seconds() / 3600
                diferenca_dias = diferenca_horas / 24
                
                if diferenca_horas > self.config['tolerancia_horas_antes']:
                    resultado['alertas'].append(
                        f"PDF criado {diferenca_dias:.1f} dias ({diferenca_horas:.1f} horas) ANTES da emissão do documento"
                    )
                    resultado['score'] += 60  # Score alto para situação crítica
                    resultado['detalhes']['criacao_antes_emissao'] = {
                        'pdf_criado': data_criacao_pdf.strftime('%Y-%m-%d %H:%M:%S'),
                        'documento_emitido': data_emissao_doc.strftime('%Y-%m-%d %H:%M:%S'),
                        'diferenca_dias': round(diferenca_dias, 1),
                        'diferenca_horas': round(diferenca_horas, 1),
                        'tolerancia_aplicada_horas': self.config['tolerancia_horas_antes']
                    }
            except Exception as e:
                resultado['alertas'].append(f"Erro ao comparar datas de criação: {str(e)}")
                resultado['score'] += 10
        
        # 2. PDF criado muito tempo DEPOIS da emissão
        if data_criacao_pdf and data_criacao_pdf > data_emissao_doc:
            try:
                dias_diferenca = (data_criacao_pdf.date() - data_emissao_doc.date()).days
                
                if dias_diferenca > self.config['dias_maximos_apos_emissao']:
                    resultado['alertas'].append(
                        f"PDF criado {dias_diferenca} dias após emissão do documento (limite: {self.config['dias_maximos_apos_emissao']} dias)"
                    )
                    resultado['score'] += 25
                    resultado['detalhes']['criacao_muito_tardia'] = {
                        'dias_diferenca': dias_diferenca,
                        'limite_maximo_dias': self.config['dias_maximos_apos_emissao']
                    }
                elif dias_diferenca > self.config['dias_alerta_apos_emissao']:
                    resultado['alertas'].append(
                        f"PDF criado {dias_diferenca} dias após emissão (atenção - limite alerta: {self.config['dias_alerta_apos_emissao']} dias)"
                    )
                    resultado['score'] += 10
                    resultado['detalhes']['criacao_tardia'] = {
                        'dias_diferenca': dias_diferenca,
                        'limite_alerta_dias': self.config['dias_alerta_apos_emissao']
                    }
            except Exception as e:
                resultado['alertas'].append(f"Erro ao calcular diferença de dias: {str(e)}")
                resultado['score'] += 5
        
        # 3. Validação de modificação vs emissão
        if data_modificacao_pdf:
            try:
                diferenca_horas_mod = (data_emissao_doc - data_modificacao_pdf).total_seconds() / 3600
                diferenca_dias_mod = diferenca_horas_mod / 24
                
                if diferenca_horas_mod > self.config['tolerancia_horas_antes']:
                    resultado['alertas'].append(
                        f"PDF modificado {diferenca_dias_mod:.1f} dias ({diferenca_horas_mod:.1f} horas) ANTES da emissão"
                    )
                    resultado['score'] += 55
                    resultado['detalhes']['modificacao_antes_emissao'] = {
                        'pdf_modificado': data_modificacao_pdf.strftime('%Y-%m-%d %H:%M:%S'),
                        'diferenca_dias': round(diferenca_dias_mod, 1),
                        'diferenca_horas': round(diferenca_horas_mod, 1),
                        'tolerancia_aplicada_horas': self.config['tolerancia_horas_antes']
                    }
            except Exception as e:
                resultado['alertas'].append(f"Erro ao comparar datas de modificação: {str(e)}")
                resultado['score'] += 10
        
        # 4. Intervalo suspeito entre criação e modificação
        if data_criacao_pdf and data_modificacao_pdf:
            try:
                diferenca_segundos = abs((data_modificacao_pdf - data_criacao_pdf).total_seconds())
                horas_diferenca = diferenca_segundos / 3600
                dias_diferenca = horas_diferenca / 24
                
                if horas_diferenca > self.config['intervalo_max_edicao_horas']:
                    resultado['alertas'].append(
                        f"Grande intervalo entre criação e modificação: {dias_diferenca:.1f} dias ({horas_diferenca:.1f} horas) - limite: {self.config['intervalo_max_edicao_horas']} horas"
                    )
                    resultado['score'] += 15
                    resultado['detalhes']['intervalo_edicao_suspeito'] = {
                        'intervalo_dias': round(dias_diferenca, 1),
                        'intervalo_horas': round(horas_diferenca, 1),
                        'limite_maximo_horas': self.config['intervalo_max_edicao_horas']
                    }
            except Exception as e:
                resultado['alertas'].append(f"Erro ao calcular intervalo de edição: {str(e)}")
                resultado['score'] += 5
        
        # 5. Documento antigo com PDF recém-criado
        if data_criacao_pdf and data_emissao_doc:
            try:
                idade_documento = (agora - data_emissao_doc).days
                idade_pdf = (agora - data_criacao_pdf).days
                
                if (idade_documento > self.config['dias_documento_antigo'] and 
                    idade_pdf < self.config['dias_pdf_recente']):
                    resultado['alertas'].append(
                        f"Documento de {idade_documento} dias com PDF criado há {idade_pdf} dias (limites: doc>{self.config['dias_documento_antigo']} dias, PDF<{self.config['dias_pdf_recente']} dias)"
                    )
                    resultado['score'] += 30
                    resultado['detalhes']['documento_antigo_pdf_novo'] = {
                        'idade_documento_dias': idade_documento,
                        'idade_pdf_dias': idade_pdf,
                        'limite_documento_antigo': self.config['dias_documento_antigo'],
                        'limite_pdf_recente': self.config['dias_pdf_recente']
                    }
            except Exception as e:
                resultado['alertas'].append(f"Erro ao calcular idades: {str(e)}")
                resultado['score'] += 5
        
        # 6. Validação de datas futuras
        try:
            if data_emissao_doc > agora:
                dias_futuro = (data_emissao_doc - agora).days
                resultado['alertas'].append(f"Data de emissão do documento está {dias_futuro} dias no futuro")
                resultado['score'] += 40
            
            if data_criacao_pdf and data_criacao_pdf > agora + timedelta(hours=1):
                dias_futuro_pdf = (data_criacao_pdf - agora).days
                resultado['alertas'].append(f"Data de criação do PDF está {dias_futuro_pdf} dias no futuro")
                resultado['score'] += 35
        except Exception as e:
            resultado['alertas'].append(f"Erro ao validar datas futuras: {str(e)}")
            resultado['score'] += 5
        
        return resultado

    def _validar_consistencia_datas(self, metadados: Dict) -> Dict:
        """Valida a consistência interna das datas do PDF"""
        resultado = {'alertas': [], 'score': 0, 'detalhes': {}}
        
        data_criacao = self.converter_data(metadados.get('data_criacao'))
        data_modificacao = self.converter_data(metadados.get('data_modificacao'))
        
        # Modificação antes da criação
        if data_criacao and data_modificacao:
            try:
                if data_modificacao < data_criacao:
                    resultado['alertas'].append("PDF modificado antes de ser criado")
                    resultado['score'] += 50
                    resultado['detalhes']['modificacao_antes_criacao'] = True
            except Exception as e:
                resultado['alertas'].append(f"Erro ao comparar datas internas: {str(e)}")
                resultado['score'] += 10
        
        # Datas ausentes
        if not data_criacao:
            resultado['alertas'].append("Data de criação do PDF ausente")
            resultado['score'] += 15
        
        return resultado

    def _validar_metadados_adicionais(self, metadados: Dict) -> Dict:
        """Valida metadados adicionais específicos do formato fornecido"""
        resultado = {'alertas': [], 'score': 0, 'detalhes': {}}
        
        # Validação de arquivo criptografado
        if metadados.get('is_encrypted'):
            resultado['alertas'].append("PDF está criptografado")
            resultado['score'] += 20
            resultado['detalhes']['arquivo_criptografado'] = True
        
        # Validação de tamanho suspeito
        size_file = metadados.get('size_file', 0)
        if size_file < 1000:  # Menos de 1KB
            resultado['alertas'].append(f"Arquivo muito pequeno: {size_file} bytes")
            resultado['score'] += 15
            resultado['detalhes']['arquivo_muito_pequeno'] = size_file
        
        # Validação de número de páginas
        num_pages = metadados.get('num_pages', 0)
        if num_pages == 0:
            resultado['alertas'].append("PDF sem páginas")
            resultado['score'] += 25
            resultado['detalhes']['sem_paginas'] = True
        
        # Validação de metadados ausentes críticos
        campos_criticos = ['title', 'author', 'creator', 'producer']
        campos_ausentes = []
        for campo in campos_criticos:
            if not metadados.get(campo) or metadados.get(campo) in [None, 'None', '']:
                campos_ausentes.append(campo)
        
        if len(campos_ausentes) >= 3:
            resultado['alertas'].append(f"Muitos metadados ausentes: {', '.join(campos_ausentes)}")
            resultado['score'] += 10
            resultado['detalhes']['metadados_ausentes'] = campos_ausentes
        
        return resultado

    def validar(self, dados: Dict, data_emissao_documento: Optional[Union[datetime, str]] = None) -> Dict:
        """
        Valida metadados de PDF focando nas datas para detectar possíveis fraudes
        """
        
        # Extrair metadados do formato fornecido
        metadados = self._extrair_metadados(dados)
        
        resultado_final = {
            'aprovado': True,
            'alertas': [],
            'score_suspeita': 0,
            'detalhes': {
                'arquivo_info': {
                    'bucket': metadados.get('bucket'),
                    'key': metadados.get('key'),
                    'size_file': metadados.get('size_file'),
                    'num_pages': metadados.get('num_pages'),
                    'is_encrypted': metadados.get('is_encrypted')
                }
            },
            'timestamp_validacao': datetime.now().isoformat()
        }
        
        # Executar validações focadas em datas e metadados
        try:
            validacoes = [
                self._validar_datas_emissao(metadados, data_emissao_documento),
                self._validar_consistencia_datas(metadados),
                self._validar_metadados_adicionais(metadados)
            ]
            
            # Consolidar resultados
            for validacao in validacoes:
                resultado_final['alertas'].extend(validacao['alertas'])
                resultado_final['score_suspeita'] += validacao['score']
                resultado_final['detalhes'].update(validacao['detalhes'])
                
        except Exception as e:
            resultado_final['alertas'].append(f"Erro durante validação: {str(e)}")
            resultado_final['score_suspeita'] += 20
        
        # Garantir que score não ultrapasse os limites
        resultado_final['score_suspeita'] = max(0, min(
            self.config['score_maximo_suspeita'], 
            resultado_final['score_suspeita']
        ))
        
        # Decisão final baseada em critérios críticos de data
        if resultado_final['score_suspeita'] >= self.config['threshold_bloqueio']:
            resultado_final['aprovado'] = False
            resultado_final['motivo'] = f"Score de suspeita alto: {resultado_final['score_suspeita']}"
        elif any('ANTES da emissão' in alerta for alerta in resultado_final['alertas']):
            resultado_final['aprovado'] = False
            resultado_final['motivo'] = "Data de criação/modificação anterior à emissão do documento"
        elif any('modificado antes de ser criado' in alerta for alerta in resultado_final['alertas']):
            resultado_final['aprovado'] = False
            resultado_final['motivo'] = "Inconsistência nas datas internas do PDF"
        elif any('futuro' in alerta for alerta in resultado_final['alertas']):
            resultado_final['aprovado'] = False
            resultado_final['motivo'] = "Datas no futuro detectadas"
        
        self.resultado_final = resultado_final
        return resultado_final

    def gerar_relatorio(self, resultado: Dict = None) -> Dict:
        """
        Gera um relatório da validação no formato estruturado
        """
        if resultado is None:
            resultado = getattr(self, 'resultado_final', {})
        
        # Monta o texto detalhado do resultado
        relatorio_texto = []
        
        if resultado.get('aprovado', False):
            relatorio_texto.append("VALIDAÇÃO DE METADADOS APROVADA")
        else:
            relatorio_texto.append(f"VALIDAÇÃO REPROVADA: {resultado.get('motivo', 'Motivo não especificado')}")
        
        relatorio_texto.append(f"Score de suspeita: {resultado.get('score_suspeita', 0)}/100")
        relatorio_texto.append(f"Validação realizada em: {resultado.get('timestamp_validacao', 'N/A')}")
        
        # Configurações de tolerância aplicadas
        relatorio_texto.append(f"\nTolerâncias aplicadas:")
        relatorio_texto.append(f"  • Tolerância para criação antes da emissão: {self.config.get('tolerancia_horas_antes', 'N/A')} horas")
        relatorio_texto.append(f"  • Limite para criação após emissão (alerta): {self.config.get('dias_alerta_apos_emissao', 'N/A')} dias")
        relatorio_texto.append(f"  • Limite máximo para criação após emissão: {self.config.get('dias_maximos_apos_emissao', 'N/A')} dias")
        relatorio_texto.append(f"  • Intervalo máximo de edição: {self.config.get('intervalo_max_edicao_horas', 'N/A')} horas")
        relatorio_texto.append(f"  • Documento considerado antigo após: {self.config.get('dias_documento_antigo', 'N/A')} dias")
        relatorio_texto.append(f"  • PDF considerado recente até: {self.config.get('dias_pdf_recente', 'N/A')} dias")
        
        # Informações do arquivo
        arquivo_info = resultado.get('detalhes', {}).get('arquivo_info', {})
        if arquivo_info:
            relatorio_texto.append(f"\nInformações do arquivo:")
            relatorio_texto.append(f"  • Bucket: {arquivo_info.get('bucket', 'N/A')}")
            relatorio_texto.append(f"  • Arquivo: {arquivo_info.get('key', 'N/A')}")
            relatorio_texto.append(f"  • Tamanho: {arquivo_info.get('size_file', 0)} bytes")
            relatorio_texto.append(f"  • Páginas: {arquivo_info.get('num_pages', 0)}")
            relatorio_texto.append(f"  • Criptografado: {'Sim' if arquivo_info.get('is_encrypted') else 'Não'}")
        
        if resultado.get('alertas'):
            relatorio_texto.append("\nAlertas encontrados:")
            for i, alerta in enumerate(resultado['alertas'], 1):
                relatorio_texto.append(f"  {i}. {alerta}")
        
        detalhes = resultado.get('detalhes', {})
        if detalhes:
            relatorio_texto.append("\nDetalhes da validação:")
            for chave, valor in detalhes.items():
                if chave == 'arquivo_info':  # Já foi mostrado acima
                    continue
                if isinstance(valor, dict):
                    relatorio_texto.append(f"  • {chave}:")
                    for sub_chave, sub_valor in valor.items():
                        if 'dias' in sub_chave.lower():
                            relatorio_texto.append(f"    - {sub_chave}: {sub_valor} dias")
                        elif 'horas' in sub_chave.lower():
                            relatorio_texto.append(f"    - {sub_chave}: {sub_valor} horas")
                        elif 'limite' in sub_chave.lower() or 'tolerancia' in sub_chave.lower():
                            unidade = 'dias' if 'dias' in str(sub_valor) or isinstance(sub_valor, int) and sub_valor > 24 else 'horas'
                            relatorio_texto.append(f"    - {sub_chave}: {sub_valor} {unidade}")
                        else:
                            relatorio_texto.append(f"    - {sub_chave}: {sub_valor}")
                else:
                    if 'dias' in chave.lower():
                        relatorio_texto.append(f"  • {chave}: {valor} dias")
                    elif 'horas' in chave.lower():
                        relatorio_texto.append(f"  • {chave}: {valor} horas")
                    else:
                        relatorio_texto.append(f"  • {chave}: {valor}")

        return {
            'aprovado': resultado.get('aprovado', False),
            'score': resultado.get('score_suspeita', 0),
            'resultado': "\n".join(relatorio_texto)
        }