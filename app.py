import os
import streamlit as st
import psycopg2
import sqlite3
import pandas as pd
from datetime import datetime
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Pega a URI do PostgreSQL da variável de ambiente
POSTGRES_URI = os.getenv("POSTGRES_URI")
if not POSTGRES_URI:
    raise ValueError("Variável de ambiente POSTGRES_URI não definida!")

# Conexão com PostgreSQL (Neon)
conn_pg = psycopg2.connect(POSTGRES_URI)
cursor_pg = conn_pg.cursor()

# Conexão com SQLite
conn_sqlite = sqlite3.connect("relatorios.db", check_same_thread=False)
cursor_sqlite = conn_sqlite.cursor()

def criar_tabela_sqlite():
    cursor_sqlite.execute("""
        CREATE TABLE IF NOT EXISTS relatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            nome TEXT,
            matricula TEXT,
            acao TEXT,
            hora TEXT,
            obs TEXT
        )
    """)
    conn_sqlite.commit()


# Valida login no PostgreSQL
def validar_login(email, senha):
    cursor_pg.execute("SELECT senha FROM usuarios WHERE email = %s", (email,))
    resultado = cursor_pg.fetchone()
    if resultado:
        senha_hash = resultado[0]
        return bcrypt.checkpw(senha.encode(), senha_hash.encode())
    return False

# Recupera nome e matrícula do usuário logado
def get_nome_matricula(email):
    cursor_pg.execute("SELECT nome, matricula FROM usuarios WHERE email = %s", (email,))
    resultado = cursor_pg.fetchone()
    if resultado:
        return resultado[0], resultado[1]
    return None, None

# Tela de login
def login():
    st.title("Login - Sistema de Relatórios da Biblioteca")
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if validar_login(email, senha):
            st.session_state.logado = True
            st.session_state.email = email
            st.success("Login realizado com sucesso!")
        else:
            st.error("E-mail ou senha inválidos.")

# Tela para cadastro de novos usuários (disponível somente após login)
def cadastro_usuario():
    st.subheader("Cadastrar novo usuário")
    novo_email = st.text_input("E-mail do novo usuário")
    novo_nome = st.text_input("Nome completo")
    nova_matricula = st.text_input("Matrícula")
    nova_senha = st.text_input("Senha", type="password")
    confirmar_senha = st.text_input("Confirmar senha", type="password")
    if st.button("Cadastrar usuário"):
        if not (novo_email and novo_nome and nova_matricula and nova_senha and confirmar_senha):
            st.error("Por favor, preencha todos os campos.")
            return
        if nova_senha != confirmar_senha:
            st.error("As senhas não coincidem.")
            return
        # Verificar se email já existe
        cursor_pg.execute("SELECT 1 FROM usuarios WHERE email = %s", (novo_email,))
        if cursor_pg.fetchone():
            st.error("Usuário com este e-mail já existe.")
            return
        # Criar hash da senha
        senha_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
        # Inserir no PostgreSQL
        cursor_pg.execute(
            "INSERT INTO usuarios (email, nome, matricula, senha) VALUES (%s, %s, %s, %s)",
            (novo_email, novo_nome, nova_matricula, senha_hash)
        )
        conn_pg.commit()
        st.success(f"Usuário {novo_nome} cadastrado com sucesso!")

# Tela de relatórios
def tela_relatorios():
    st.title("Relatórios da Biblioteca")
    st.markdown(f"Usuário: **{st.session_state.email}**")
    nome, matricula = get_nome_matricula(st.session_state.email)
    st.markdown(f"Nome: **{nome}** | Matrícula: **{matricula}**")

    # Formulário para criar relatório
    acao = st.selectbox("Tipo de ação:", ["Atendimento", "Orientação", "Suporte", "Outro"])
    obs = st.text_area("Observações:")

    if st.button("Salvar relatório"):
        hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor_sqlite.execute("""
            INSERT INTO relatorios (email, nome, matricula, acao, hora, obs)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (st.session_state.email, nome, matricula, acao, hora_atual, obs))
        conn_sqlite.commit()
        st.success("Relatório salvo com sucesso!")

    # Mostrar relatórios anteriores
    st.subheader("Seus relatórios anteriores")
    cursor_sqlite.execute("""
        SELECT nome, matricula, acao, hora, obs
        FROM relatorios
        WHERE email = ?
        ORDER BY hora DESC
    """, (st.session_state.email,))
    dados = cursor_sqlite.fetchall()

    if dados:
        df = pd.DataFrame(dados, columns=["Nome", "Matrícula", "Ação", "Data/Hora", "Observações"])
        st.dataframe(df)
    else:
        st.info("Nenhum relatório encontrado.")

# App principal
def main():
    st.set_page_config(page_title="Relatórios - Biblioteca SIBI", layout="centered")
    criar_tabela_sqlite()

    if "logado" not in st.session_state:
        st.session_state.logado = False

    if st.session_state.logado:
        tela_relatorios()
        st.markdown("---")
        cadastro_usuario()
        if st.button("Logout"):
            st.session_state.logado = False
            st.session_state.email = ""
            st.experimental_rerun()
    else:
        login()

if __name__ == "__main__":
    main()
