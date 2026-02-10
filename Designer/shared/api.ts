/**
 * Shared code between client and server
 * Useful to share types between client and server
 * and/or small pure JS functions that can be used on both client and server
 */

// Demo
export interface DemoResponse {
  message: string;
}

// Auth Types
export interface AuthResponse {
  success: boolean;
  message?: string;
  professor?: Professor;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  nome: string;
  email: string;
  senha: string;
}

// Professor
export interface Professor {
  id: string;
  nome: string;
  email: string;
  escola?: string;
  created_at: string;
}

// Turma (Class)
export interface Turma {
  id: string;
  professor_id: string;
  nome: string;
  disciplina?: string;
  ano_serie?: string;
  trimestre_atual: number;
  created_at: string;
  updated_at: string;
}

// Aluno (Student)
export interface Aluno {
  id: string;
  turma_id: string;
  nome_completo: string;
  matricula?: string;
  status: "ativo" | "inativo";
  created_at: string;
}

// Atividade (Activity/Assignment)
export interface Atividade {
  id: string;
  turma_id: string;
  titulo: string;
  descricao?: string;
  data?: string;
  trimestre: number;
  peso: number;
  nota_maxima: number;
  status: "rascunho" | "publicada" | "fechada";
  created_at: string;
  updated_at: string;
}

// AvaliacaoAluno (Student Grade)
export interface AvaliacaoAluno {
  id: string;
  atividade_id: string;
  aluno_id: string;
  nota?: number;
  comentario?: string;
  comentario_longo?: string;
  updated_at: string;
}

// Calculated/Derived types
export interface MediaAluno {
  aluno_id: string;
  nome_completo: string;
  total_pontos: number;
  media: number;
  atividades_avaliadas: number;
  atividades_total: number;
}

export interface AvaliacaoWithAluno extends AvaliacaoAluno {
  aluno_nome?: string;
}

// API Response types
export interface TurmaResponse {
  success: boolean;
  turma?: Turma;
  turmas?: Turma[];
  message?: string;
}

export interface AlunoResponse {
  success: boolean;
  aluno?: Aluno;
  alunos?: Aluno[];
  message?: string;
}

export interface AtividadeResponse {
  success: boolean;
  atividade?: Atividade;
  atividades?: Atividade[];
  message?: string;
}

export interface AvaliacaoResponse {
  success: boolean;
  avaliacao?: AvaliacaoAluno;
  avaliacoes?: AvaliacaoAluno[];
  message?: string;
}
