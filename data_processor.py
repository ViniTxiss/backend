import pandas as pd
import os

class DataProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self._load_data()

    def _clean_currency(self, value):
        """Converte valores monetários brasileiros para float."""
        if pd.isna(value) or str(value).strip() in ['-', '']: 
            return 0.0
        clean_val = str(value).replace('R$', '').replace('.', '').replace(',', '.').replace(' ', '').strip()
        try: 
            return float(clean_val)
        except: 
            return 0.0

    def _load_data(self):
        """Carrega dados de arquivo Excel ou CSV."""
        if not os.path.exists(self.file_path): 
            return
        
        # Tenta ler Excel primeiro
        if self.file_path.endswith(('.xlsx', '.xls')):
            try:
                self.df = pd.read_excel(self.file_path)
            except Exception as e:
                print(f"Erro ao ler Excel: {e}")
                return
        else:
            # Tenta ler CSV
            try:
                self.df = pd.read_csv(self.file_path, encoding='utf-8', sep=';')
            except:
                try:
                    self.df = pd.read_csv(self.file_path, encoding='latin-1', sep=';')
                except:
                    self.df = pd.read_csv(self.file_path, encoding='latin-1')
        
        if self.df is None or self.df.empty:
            return
        
        # Identifica coluna de valor da causa (prioriza "Atual" se existir)
        valor_col = None
        # Primeiro tenta "Valor da Causa Atual"
        for col in self.df.columns:
            if 'valor da causa atual' in str(col).lower():
                valor_col = col
                break
        
        # Se não encontrou "Atual", tenta "Valor da Causa"
        if valor_col is None:
            for col in self.df.columns:
                if 'valor da causa' in str(col).lower() and 'atual' not in str(col).lower():
                    valor_col = col
                    break
        
        # Aplica limpeza de valores
        if valor_col:
            self.df['valor_numerico'] = self.df[valor_col].apply(self._clean_currency)
        elif 'Valor da Causa Atual' in self.df.columns:
            self.df['valor_numerico'] = self.df['Valor da Causa Atual'].apply(self._clean_currency)
        elif 'Valor da Causa' in self.df.columns:
            self.df['valor_numerico'] = self.df['Valor da Causa'].apply(self._clean_currency)
        else:
            # Se nenhuma coluna de valor for encontrada, cria coluna zerada
            self.df['valor_numerico'] = 0.0

    def _get_column(self, possible_names):
        """Identifica coluna por possíveis nomes (case insensitive, ignora encoding)."""
        if self.df is None:
            return None
        
        df_cols_lower = [str(col).lower().strip() for col in self.df.columns]
        
        for possible_name in possible_names:
            possible_lower = str(possible_name).lower().strip()
            for idx, col_lower in enumerate(df_cols_lower):
                if possible_lower in col_lower or col_lower in possible_lower:
                    return self.df.columns[idx]
        
        return None

    def get_full_data(self):
        """Retorna todos os dados processados: KPIs, gráficos e processos."""
        if self.df is None or self.df.empty: 
            return None
        
        # Identifica coluna Status (é a coluna que existe no arquivo)
        status_col = self._get_column(['Status', 'status', 'STATUS'])
        if status_col is None:
            return None
        
        # Filtros baseados na coluna Status (CORRIGIDO)
        df_andamento = self.df[self.df[status_col].astype(str).str.contains('ANDAMENTO', case=False, na=False)]
        df_encerrados = self.df[self.df[status_col].astype(str).str.contains('ENCERRADO', case=False, na=False)]
        df_entradas = self.df[self.df[status_col].astype(str).str.contains('ENTRADA', case=False, na=False)]

        # Cálculo de Saving (diferença entre Valor da Causa e Valor pago)
        valor_col = self._get_column(['Valor', 'valor'])
        if valor_col and len(df_encerrados) > 0:
            valor_pago = df_encerrados[valor_col].apply(self._clean_currency).sum()
            valor_causa_encerrados = df_encerrados['valor_numerico'].sum() if 'valor_numerico' in df_encerrados.columns else 0
            saving = valor_causa_encerrados - valor_pago
        else:
            saving = 0.0

        # Identifica colunas para gráficos
        processo_col = self._get_column(['Número do Processo', 'Numero do Processo', 'Processo', 'Número do Processo '])
        tipo_col = self._get_column(['Descricao do Tipo de Ação', 'Tipo de Ação', 'Descricao do Tipo de Acao'])
        responsavel_col = self._get_column(['Usuario de Inclusao', 'Usuário de Inclusão', 'Responsavel', 'Usuario de Inclusao'])

        # Prepara dados de gráficos
        top10_labels = []
        top10_values = []
        if processo_col and 'valor_numerico' in df_andamento.columns and len(df_andamento) > 0:
            top10 = df_andamento.nlargest(10, 'valor_numerico')
            top10_labels = top10[processo_col].astype(str).tolist()
            top10_values = top10['valor_numerico'].tolist()

        tipo_labels = []
        tipo_values = []
        if tipo_col and 'valor_numerico' in df_andamento.columns and len(df_andamento) > 0:
            tipo_group = df_andamento.groupby(tipo_col)['valor_numerico'].sum().nlargest(5)
            tipo_labels = tipo_group.index.astype(str).tolist()
            tipo_values = tipo_group.values.tolist()

        responsavel_labels = []
        responsavel_values = []
        if responsavel_col and 'valor_numerico' in df_andamento.columns and len(df_andamento) > 0:
            resp_group = df_andamento.groupby(responsavel_col)['valor_numerico'].sum().nlargest(10)
            responsavel_labels = resp_group.index.astype(str).tolist()
            responsavel_values = resp_group.values.tolist()

        # Prepara processos para tabela
        processes = []
        if processo_col and 'valor_numerico' in df_andamento.columns and len(df_andamento) > 0:
            top_processes = df_andamento.nlargest(50, 'valor_numerico')
            data_col = self._get_column(['Data de Entrada', 'Data de Distribuição', 'Data de distribuicao', 'Data de entrada'])
            
            for _, row in top_processes.iterrows():
                process_data = {
                    'processo': str(row[processo_col]) if processo_col and not pd.isna(row.get(processo_col, '')) else 'Não Informado',
                    'valor': float(row['valor_numerico']) if 'valor_numerico' in row else 0.0,
                    'tipo': str(row[tipo_col]) if tipo_col and not pd.isna(row.get(tipo_col, '')) else 'Não Informado',
                    'data': str(row[data_col]) if data_col and not pd.isna(row.get(data_col, '')) else 'Não Informado',
                    'responsavel': str(row[responsavel_col]) if responsavel_col and not pd.isna(row.get(responsavel_col, '')) else 'Não Informado'
                }
                processes.append(process_data)

        return {
            "kpis": {
                "valor_andamento": float(df_andamento['valor_numerico'].sum()) if 'valor_numerico' in df_andamento.columns else 0.0,
                "total_entradas": int(len(df_entradas)),
                "saving": float(max(0, saving)),
                "total_encerrados": int(len(df_encerrados))
            },
            "charts": {
                "top10_causas": {
                    "labels": top10_labels,
                    "values": top10_values
                },
                "valor_por_tipo": {
                    "labels": tipo_labels,
                    "values": tipo_values
                },
                "valor_por_responsavel": {
                    "labels": responsavel_labels,
                    "values": responsavel_values
                }
            },
            "processes": processes
        }