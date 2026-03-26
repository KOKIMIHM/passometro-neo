import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Passômetro UTI Neo", layout="wide")

# --- INICIALIZANDO A MEMÓRIA DO APLICATIVO ---
# Isso é necessário para o botão "Copiar" conseguir preencher as caixas sozinho
if "form_leito" not in st.session_state: st.session_state.form_leito = ""
if "form_idade" not in st.session_state: st.session_state.form_idade = ""
if "form_vent" not in st.session_state: st.session_state.form_vent = ""
if "form_dados" not in st.session_state: st.session_state.form_dados = ""
if "form_prop" not in st.session_state: st.session_state.form_prop = ""

# Função que busca o último registro de um leito específico
def copiar_ultimo_registro():
    arquivo = "historico_plantao.csv"
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo, sep=';')
        # Filtra a tabela para achar só as linhas do leito que está digitado
        leito_atual = st.session_state.form_leito
        if leito_atual != "":
            df_filtrado = df[df["Leito"] == leito_atual]
            if not df_filtrado.empty:
                ultima_linha = df_filtrado.iloc[-1] # Pega a última anotação desse leito
                
                # Preenche a memória do app com os dados antigos
                st.session_state.form_idade = str(ultima_linha.get("Idade/Dias", ""))
                st.session_state.form_vent = str(ultima_linha.get("Ventilação", ""))
                st.session_state.form_dados = str(ultima_linha.get("Dados Clínicos", ""))
                st.session_state.form_prop = str(ultima_linha.get("Proposta Terapêutica", ""))
            else:
                st.warning(f"Nenhum registro anterior encontrado para o leito {leito_atual}.")
        else:
            st.warning("Por favor, digite o número do Leito antes de clicar em Copiar.")
    else:
        st.warning("Ainda não há histórico salvo para copiar.")

# ==========================================
# INÍCIO DA INTERFACE
# ==========================================
st.title("Passômetro - Fisioterapia UTI Neonatal")
st.divider()

st.subheader("Informações do Plantão")
col_data, col_turno = st.columns(2)

with col_data:
    data_plantao = st.date_input("Data do Plantão", format="DD/MM/YYYY")
with col_turno:
    turno = st.radio("Turno", ["Diurno (7h - 19h)", "Noturno (19h - 7h)"], horizontal=True)

st.divider()

# --- SESSÃO: DADOS DO PACIENTE ---
st.subheader("Paciente e Parâmetros")

# Botão de copiar antes das caixas de texto
st.button("🔄 Copiar último registro deste Leito", on_click=copiar_ultimo_registro, type="secondary")

col1, col2 = st.columns(2)

with col1:
    # O "key" conecta a caixa de texto com a memória do app
    leito = st.text_input("Leito e Nome do Paciente", key="form_leito")
with col2:
    idade = st.text_input("Idade Gestacional / Dias de Vida", key="form_idade")

# Caixas de texto para o handover
ventilacao = st.text_area("Parâmetros Ventilatórios Atuais (VM/VNI/Cateter)", height=100, key="form_vent")
dados = st.text_area("Dados Clínicos e Intercorrências", height=100, key="form_dados")

st.subheader("Proposta Terapêutica")
proposta = st.text_area("Condutas", height=100, key="form_prop")

# Botão de salvar
if st.button("Salvar Plantão", type="primary"):
    if leito == "":
        st.error("O campo 'Leito' é obrigatório!")
    else:
        novo_registro = {
            "Data do Registro": [datetime.now().strftime("%d/%m/%Y %H:%M")],
            "Data do Plantão": [data_plantao.strftime("%d/%m/%Y")],
            "Turno": [turno],
            "Leito": [leito],
            "Idade/Dias": [idade],
            "Ventilação": [ventilacao],
            "Dados Clínicos": [dados],
            "Proposta Terapêutica": [proposta]
        }
        
        tabela_pandas = pd.DataFrame(novo_registro)
        nome_do_arquivo = "historico_plantao.csv"
        arquivo_existe = os.path.exists(nome_do_arquivo)
        
        tabela_pandas.to_csv(nome_do_arquivo, mode='a', index=False, header=not arquivo_existe, sep=';', encoding='utf-8-sig')
        
        st.success(f"Passômetro do leito {leito} salvo com sucesso!")

# --- NOVA SESSÃO: EDIÇÃO DIRETA NA TABELA ---
st.divider()
st.subheader("📚 Histórico e Edição")
st.caption("Dê um duplo clique em qualquer célula abaixo para editar o texto. Depois clique em 'Salvar Alterações'.")

if os.path.exists("historico_plantao.csv"):
    tabela_historico = pd