import { RequestHandler } from "express";
import { AuthResponse, LoginRequest, Professor } from "@shared/api";

// Simple in-memory user store for demo
const demoUsers: Record<string, { password: string; professor: Professor }> = {
  "demo@example.com": {
    password: "demo123",
    professor: {
      id: "1",
      nome: "Professor Demo",
      email: "demo@example.com",
      escola: "Escola Exemplo",
      created_at: new Date().toISOString(),
    },
  },
};

export const handleLogin: RequestHandler = (req, res) => {
  const { email, password } = req.body as LoginRequest;

  // Validate input
  if (!email || !password) {
    return res.json({
      success: false,
      message: "Email e senha são obrigatórios",
    } as AuthResponse);
  }

  // Check if user exists
  const user = demoUsers[email.toLowerCase()];
  
  if (!user || user.password !== password) {
    return res.json({
      success: false,
      message: "Email ou senha inválidos",
    } as AuthResponse);
  }

  // Login successful
  return res.json({
    success: true,
    message: "Login realizado com sucesso",
    professor: user.professor,
  } as AuthResponse);
};

export const handleLogout: RequestHandler = (_req, res) => {
  res.json({
    success: true,
    message: "Logout realizado com sucesso",
  } as AuthResponse);
};
