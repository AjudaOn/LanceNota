import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";
import { BookOpen, AlertCircle, Eye, EyeOff, ArrowRight, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (!email || !password) {
        setError("Por favor, preencha todos os campos");
        return;
      }

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        setError("Por favor, insira um email válido");
        return;
      }

      await login(email, password);
      toast.success("Login realizado com sucesso!");
      navigate("/");
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Falha ao fazer login. Tente novamente.";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setEmail("demo@example.com");
    setPassword("demo123");
    
    // Simulate a small delay to show the fields are being filled
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Trigger login
    const form = document.querySelector("form") as HTMLFormElement;
    if (form) {
      form.dispatchEvent(new Event("submit", { bubbles: true }));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-900 to-slate-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: "2s" }}></div>
        <div className="absolute top-1/2 left-1/2 w-80 h-80 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-10 animate-pulse" style={{ animationDelay: "4s" }}></div>
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Floating Card with Glassmorphism Effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-2xl blur-xl"></div>
        
        <Card className="relative border border-blue-400/30 bg-slate-900/80 backdrop-blur-xl shadow-2xl">
          {/* Top Accent Line */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent rounded-t-2xl"></div>

          {/* Logo Section */}
          <div className="pt-8 px-6 text-center border-b border-blue-400/10">
            <div className="inline-flex items-center justify-center relative mb-4">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur-lg opacity-75"></div>
              <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 text-white flex items-center justify-center shadow-xl transform hover:scale-110 transition-transform">
                <BookOpen size={32} strokeWidth={1.5} />
              </div>
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-blue-300 bg-clip-text text-transparent mb-2">
              EduClass
            </h1>
            <p className="text-blue-200/70 text-sm font-medium">Gestão Acadêmica Inteligente</p>
          </div>

          <CardContent className="pt-8 pb-6">
            {/* Form Title */}
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-white mb-1">Bem-vindo!</h2>
              <p className="text-sm text-blue-200/60">Entre com suas credenciais para continuar</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Error Alert */}
              {error && (
                <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-lg backdrop-blur-sm animate-in fade-in slide-in-from-top-2">
                  <AlertCircle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}

              {/* Email Field */}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-blue-100">
                  Email
                </Label>
                <div className="relative">
                  <Input
                    id="email"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                    className="h-11 bg-slate-800/50 border border-blue-400/20 text-white placeholder:text-slate-500 focus:border-blue-400/50 focus:bg-slate-800/80 focus:ring-2 focus:ring-blue-500/20 rounded-lg transition-all"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium text-blue-100">
                  Senha
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                    className="h-11 bg-slate-800/50 border border-blue-400/20 text-white placeholder:text-slate-500 focus:border-blue-400/50 focus:bg-slate-800/80 focus:ring-2 focus:ring-blue-500/20 rounded-lg transition-all pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-blue-300 transition-colors"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-11 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none mt-6"
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Entrando...
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2">
                    Entrar
                    <ArrowRight size={18} />
                  </div>
                )}
              </Button>

              {/* Demo Button */}
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={isLoading}
                className="w-full h-11 border border-blue-400/30 text-blue-300 font-medium rounded-lg hover:bg-blue-500/10 hover:border-blue-400/50 transition-all flex items-center justify-center gap-2"
              >
                <Sparkles size={16} />
                Usar Credenciais Demo
              </button>

              {/* Forgot Password Link */}
              <div className="text-center pt-2">
                <a
                  href="#"
                  className="text-sm text-blue-300 hover:text-blue-200 font-medium transition-colors"
                  onClick={(e) => {
                    e.preventDefault();
                    toast.info("Funcionalidade em breve");
                  }}
                >
                  Esqueci minha senha
                </a>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Demo Credentials Info */}
        <div className="mt-6 p-4 bg-blue-500/10 border border-blue-400/20 rounded-xl backdrop-blur-sm">
          <p className="text-xs text-blue-200 font-semibold mb-2 flex items-center gap-2">
            <Sparkles size={14} />
            Credenciais de Demonstração
          </p>
          <div className="space-y-1 text-xs text-blue-300/80 font-mono">
            <p>Email: <span className="text-blue-200">demo@example.com</span></p>
            <p>Senha: <span className="text-blue-200">demo123</span></p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-blue-300/60 mt-6">
          © 2024 EduClass. Gestão Acadêmica Inteligente.
        </p>
      </div>
    </div>
  );
}
