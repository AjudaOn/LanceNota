import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BookOpen,
  Users,
  FileText,
  AlertCircle,
  Plus,
  ChevronRight,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface Turma {
  id: string;
  nome: string;
  disciplina?: string;
  alunos_count?: number;
  updated_at: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { professor, isLoggedIn } = useAuth();
  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    turmas_total: 0,
    alunos_total: 0,
    atividades_pendentes: 0,
  });

  useEffect(() => {
    if (!isLoggedIn) {
      navigate("/login");
      return;
    }

    // Load turmas from localStorage for demo
    const loadTurmas = () => {
      const stored = localStorage.getItem("turmas");
      if (stored) {
        const allTurmas = JSON.parse(stored);
        setTurmas(allTurmas.slice(0, 4)); // Show last 4 turmas
        setStats({
          turmas_total: allTurmas.length,
          alunos_total: allTurmas.reduce((sum: number, t: Turma) => sum + (t.alunos_count || 0), 0),
          atividades_pendentes: Math.floor(Math.random() * 5) + 1,
        });
      }
      setIsLoading(false);
    };

    // Simulate loading delay
    setTimeout(loadTurmas, 500);
  }, [isLoggedIn, navigate]);

  return (
    <MainLayout>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Bem-vindo, {professor?.nome?.split(" ")[0]}! 👋
        </h1>
        <p className="text-gray-600 mt-2">Aqui está um resumo da sua atividade acadêmica</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Turmas Card */}
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-gray-600">Turmas Ativas</CardTitle>
              <div className="p-2 bg-blue-100 rounded-lg">
                <BookOpen size={20} className="text-blue-600" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">{stats.turmas_total}</div>
            <p className="text-xs text-gray-500 mt-2">
              {stats.turmas_total > 0 ? "Todas ativas" : "Nenhuma turma criada"}
            </p>
          </CardContent>
        </Card>

        {/* Alunos Card */}
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-gray-600">Total de Alunos</CardTitle>
              <div className="p-2 bg-green-100 rounded-lg">
                <Users size={20} className="text-green-600" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">{stats.alunos_total}</div>
            <p className="text-xs text-gray-500 mt-2">Matriculados em suas turmas</p>
          </CardContent>
        </Card>

        {/* Atividades Pendentes Card */}
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-gray-600">
                Avaliações Pendentes
              </CardTitle>
              <div className="p-2 bg-orange-100 rounded-lg">
                <FileText size={20} className="text-orange-600" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">{stats.atividades_pendentes}</div>
            <p className="text-xs text-gray-500 mt-2">Aguardando sua avaliação</p>
          </CardContent>
        </Card>

        {/* Performance Card */}
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-gray-600">Desempenho</CardTitle>
              <div className="p-2 bg-purple-100 rounded-lg">
                <TrendingUp size={20} className="text-purple-600" />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">↗ 12%</div>
            <p className="text-xs text-gray-500 mt-2">Melhoria no trimestre</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        {/* Create Turma */}
        <Card className="border-2 border-dashed border-gray-300 hover:border-blue-500 cursor-pointer transition-colors">
          <CardContent className="pt-6 flex items-center justify-center min-h-[120px]">
            <button
              onClick={() => navigate("/turmas")}
              className="flex flex-col items-center gap-2 text-center w-full"
            >
              <div className="p-3 bg-blue-100 rounded-lg">
                <Plus size={24} className="text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900">Criar Turma</h3>
              <p className="text-xs text-gray-500">Adicione uma nova turma</p>
            </button>
          </CardContent>
        </Card>

        {/* Import Students */}
        <Card className="border-2 border-dashed border-gray-300 hover:border-green-500 cursor-pointer transition-colors">
          <CardContent className="pt-6 flex items-center justify-center min-h-[120px]">
            <button
              onClick={() => navigate("/turmas")}
              className="flex flex-col items-center gap-2 text-center w-full"
            >
              <div className="p-3 bg-green-100 rounded-lg">
                <Plus size={24} className="text-green-600" />
              </div>
              <h3 className="font-semibold text-gray-900">Importar Alunos</h3>
              <p className="text-xs text-gray-500">Via CSV</p>
            </button>
          </CardContent>
        </Card>

        {/* Create Activity */}
        <Card className="border-2 border-dashed border-gray-300 hover:border-purple-500 cursor-pointer transition-colors">
          <CardContent className="pt-6 flex items-center justify-center min-h-[120px]">
            <button
              onClick={() => navigate("/atividades")}
              className="flex flex-col items-center gap-2 text-center w-full"
            >
              <div className="p-3 bg-purple-100 rounded-lg">
                <Plus size={24} className="text-purple-600" />
              </div>
              <h3 className="font-semibold text-gray-900">Criar Atividade</h3>
              <p className="text-xs text-gray-500">Adicione uma nova atividade</p>
            </button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Turmas */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Turmas Recentes</CardTitle>
              <CardDescription>Suas turmas acessadas recentemente</CardDescription>
            </div>
            <Button variant="outline" onClick={() => navigate("/turmas")}>
              Ver Todas
              <ChevronRight size={16} className="ml-2" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-16 bg-gray-200 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : turmas.length > 0 ? (
            <div className="space-y-3">
              {turmas.map((turma) => (
                <div
                  key={turma.id}
                  onClick={() => navigate(`/turmas/${turma.id}`)}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{turma.nome}</h3>
                    <p className="text-sm text-gray-500">
                      {turma.disciplina || "Sem disciplina"} • {turma.alunos_count || 0} alunos
                    </p>
                  </div>
                  <ChevronRight size={20} className="text-gray-400" />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <AlertCircle size={48} className="mx-auto text-gray-300 mb-4" />
              <h3 className="font-semibold text-gray-900 mb-2">Nenhuma turma criada</h3>
              <p className="text-sm text-gray-500 mb-4">Comece criando sua primeira turma</p>
              <Button onClick={() => navigate("/turmas")} className="bg-blue-600 hover:bg-blue-700">
                Criar Turma
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </MainLayout>
  );
}
