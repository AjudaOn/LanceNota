# LanceNotas — Documento de Sistema (Draft)

## 1. Visão
Sistema para professor gerenciar turmas, alunos, atividades e lançar notas/comentários, com visão de fechamento trimestral (total e média por aluno).

## 2. Escopo (MVP)
- Autenticação (Professor)
- Turmas (CRUD)
- Alunos (CRUD por turma + importação opcional)
- Atividades (CRUD por turma)
- Notas/comentários por aluno em cada atividade
- Fechamento do trimestre (cálculo e visualização)

## 3. Usuários e Permissões
- Perfil único no MVP: **Professor**
- Regra: ver/editar apenas seus próprios dados

## 4. Modelo de Dados (base)
Conforme `IdeiadoSistema.txt`:
- Professor
- Turma
- Aluno
- Atividade
- AvaliacaoAluno (nota + comentário por aluno/atividade)

## 5. Regras de Cálculo (MVP)
- Somar notas das atividades do trimestre por aluno
- Média simples: `soma_notas / qtd_atividades_avaliadas`
- Nota vazia (“não avaliado”) não entra no divisor

## 6. Telas
Fonte: `Designer/` (a confirmar e mapear tela → rota Flask)
- Login
- Dashboard
- Turmas (lista/detalhe)
- Alunos (lista/importação)
- Atividades (lista/criação/edição)
- Lançamento de notas (por atividade)
- Fechamento do Trimestre

## 7. Stack e Arquitetura (proposta)
- Backend: Flask (Blueprints)
- Views: Jinja templates
- Persistência: (pendente decisão) SQLite dev / Postgres prod
- ORM/migrations: (pendente decisão)
- Auth: sessão/cookies + proteção de rotas

## 8. Próximos Passos
- Completar leitura do `IdeiadoSistema.txt`
- Inventariar `Designer/` e mapear telas para rotas
- Decidir DB + ORM/migrations

