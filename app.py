import streamlit as st
import psycopg2
import sqlite3
import pandas as pd
from datetime import datetime
import bcrypt
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Conexão com PostgreSQL (Neon)
conn_pg = psycopg2.connect(os.getenv("POSTGRES_URI"))
cursor_pg = conn_pg.cursor()

# Conexão com SQLite
conn_sqlite = sqlite3.connect("relatorios.db", check_same_thread=False)
cursor_sqlite = conn_sqlite.cursor()

# Criar tabela SQLite se não existir
def criar_tabela_sqlite():
    cursor_sqlite.execute('''
        CREATE TABLE IF NOT EXISTS relatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            nome TEXT,
            matricula TEXT,
            acao TEXT,
            hora TEXT,
            obs TEXT
        )
    ''')
    conn_sqlite.commit()

# Validação de login
def validar_login(email, senha):
    cursor_pg.execute("SELECT senha FROM usuarios WHERE email = %s", (email,))
    resultado = cursor_pg.fetchone()
    if resultado:
        senha_hash = resultado[0]
        return bcrypt.checkpw(senha.encode(), senha_hash.encode())
    return False

# Tela de login
def login():
    st.markdown("""
        <h2 style='text-align: center; color: #004080;'>Login - Sistema SIBI</h2>
    """, unsafe_allow_html=True)

    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if validar_login(email, senha):
            st.session_state.logado = True
            st.session_state.email = email
            cursor_pg.execute("SELECT nome, matricula FROM usuarios WHERE email = %s", (email,))
            dados = cursor_pg.fetchone()
            st.session_state.nome = dados[0]
            st.session_state.matricula = dados[1]
            st.success("Login realizado com sucesso!")
        else:
            st.error("E-mail ou senha inválidos.")

# Tela de relatórios
def tela_relatorios():
    st.markdown("""
        <h2 style='color: #004080;'>Painel de Relatórios</h2>
        <hr>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown(f"""
            <div style='background-color: #e6f0ff; padding: 10px; border-radius: 8px;'>
                <strong>Usuário:</strong> {st.session_state.nome} ({st.session_state.email})<br>
                <strong>Matrícula:</strong> {st.session_state.matricula}
            </div>
        """, unsafe_allow_html=True)

    st.subheader("Novo Relatório")
    acao = st.selectbox("Tipo de ação:", ["Atendimento", "Orientação", "Suporte", "Outro"])
    obs = st.text_area("Observações:")

    if st.button("Salvar relatório"):
        hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor_sqlite.execute("""
            INSERT INTO relatorios (email, nome, matricula, acao, hora, obs)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (st.session_state.email, st.session_state.nome, st.session_state.matricula, acao, hora_atual, obs))
        conn_sqlite.commit()
        st.success("Relatório salvo com sucesso!")

    st.subheader("Histórico de Relatórios")
    cursor_sqlite.execute("""
        SELECT nome, matricula, acao, hora, obs FROM relatorios
        WHERE email = ?
        ORDER BY hora DESC
    """, (st.session_state.email,))
    dados = cursor_sqlite.fetchall()

    if dados:
        df = pd.DataFrame(dados, columns=["Nome", "Matrícula", "Ação", "Data/Hora", "Observações"])
        st.dataframe(df)
    else:
        st.info("Nenhum relatório encontrado.")

# Tela de cadastro de novo usuário
def cadastrar_usuario():
    st.subheader("Cadastrar Novo Usuário")
    nome = st.text_input("Nome Completo")
    email = st.text_input("E-mail")
    matricula = st.text_input("Matrícula")
    senha = st.text_input("Senha", type="password")
    if st.button("Cadastrar"):
        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        cursor_pg.execute("INSERT INTO usuarios (nome, email, matricula, senha) VALUES (%s, %s, %s, %s)",
                         (nome, email, matricula, senha_hash))
        conn_pg.commit()
        st.success("Usuário cadastrado com sucesso!")

# App principal
def main():
    st.set_page_config(page_title="Sistema de Relatórios - SIBI UniFTC/UNEX", layout="centered")
    criar_tabela_sqlite()

    if "logado" not in st.session_state:
        st.session_state.logado = False

    st.markdown("""
        <style>
            .css-18e3th9 {
                padding-top: 1rem;
                padding-bottom: 1rem;
                padding-left: 2rem;
                padding-right: 2rem;
                background-color: #f4f6f9;
            }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.logado:
        menu = st.sidebar.radio("Menu", ["Relatórios", "Cadastrar Usuário", "Sair"])

        if menu == "Relatórios":
            tela_relatorios()
        elif menu == "Cadastrar Usuário":
            cadastrar_usuario()
        elif menu == "Sair":
            st.session_state.logado = False
            st.experimental_rerun()
    else:
        login()

if __name__ == "__main__":
    main()
