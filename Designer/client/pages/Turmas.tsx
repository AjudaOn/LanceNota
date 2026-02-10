import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Plus,
  Search,
  MoreVertical,
  Users,
  BookOpen,
  ChevronRight,
  Trash2,
  Edit,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Turma {
  id: string;
  nome: string;
  disciplina?: string;
  ano_serie?: string;
  alunos_count?: number;
  atividades_count?: number;
  created_at: string;
  updated_at: string;
}

export default function Turmas() {
  const navigate = useNavigate();
  const { turmaId } = useParams();
  const { isLoggedIn } = useAuth();
  const [turmas, setTurmas] = useState<Turma[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedTrimestre, setSelectedTrimestre] = useState(1);

  // New turma form state
  const [newTurma, setNewTurma] = useState({
    nome: "",
    disciplina: "",
    ano_serie: "",
  });

  useEffect(() => {
    if (!isLoggedIn) {
      navigate("/login");
      return;
    }

    // Load turmas from localStorage
    const loadTurmas = () => {
      const stored = localStorage.getItem("turmas");
      if (stored) {
        setTurmas(JSON.parse(stored));
      } else {
        // Create some sample turmas
        const sampleTurmas: Turma[] = [
          {
            id: "1",
            nome: "7º A - Matemática",
            disciplina: "Matemática",
            ano_serie: "7º Ano",
            alunos_count: 28,
            atividades_count: 5,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          {
            id: "2",
            nome: "8º B - Português",
            disciplina: "Português",
            ano_serie: "8º Ano",
            alunos_count: 25,
            atividades_count: 3,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ];
        setTurmas(sampleTurmas);
        localStorage.setItem("turmas", JSON.stringify(sampleTurmas));
      }
      setIsLoading(false);
    };

    setTimeout(loadTurmas, 300);
  }, [isLoggedIn, navigate]);

  const handleCreateTurma = () => {
    if (!newTurma.nome.trim()) {
      toast.error("Nome da turma é obrigatório");
      return;
    }

    const turma: Turma = {
      id: Date.now().toString(),
      nome: newTurma.nome,
      disciplina: newTurma.disciplina,
      ano_serie: newTurma.ano_serie,
      alunos_count: 0,
      atividades_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const updatedTurmas = [...turmas, turma];
    setTurmas(updatedTurmas);
    localStorage.setItem("turmas", JSON.stringify(updatedTurmas));
    localStorage.setItem("turmas", JSON.stringify(updatedTurmas));

    toast.success("Turma criada com sucesso!");
    setNewTurma({ nome: "", disciplina: "", ano_serie: "" });
    setIsDialogOpen(false);
  };

  const handleDeleteTurma = (id: string) => {
    const updatedTurmas = turmas.filter((t) => t.id !== id);
    setTurmas(updatedTurmas);
    localStorage.setItem("turmas", JSON.stringify(updatedTurmas));
    toast.success("Turma deletada com sucesso!");
  };

  const filteredTurmas = turmas.filter(
    (t) =>
      t.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.disciplina?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // If turmaId is selected, show detail view (placeholder for now)
  if (turmaId) {
    return (
      <MainLayout currentTurma={{ id: turmaId, nome: "Turma" }} currentTrimestre={selectedTrimestre} onTrimestreChange={setSelectedTrimestre}>
        <div className="mb-6">
          <Button
            variant="outline"
            onClick={() => navigate("/turmas")}
            className="mb-4"
          >
            ← Voltar
          </Button>
          <h1 className="text-3xl font-bold text-gray-900">Detalhe da Turma</h1>
          <p className="text-gray-600 mt-2">
            Gerencie alunos, atividades e notas desta turma
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Alunos</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Atividades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Média Geral</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">-</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Avaliações</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <Card className="border-2 border-dashed border-gray-300 hover:border-blue-500 cursor-pointer transition-colors">
            <CardContent className="pt-6 flex items-center justify-center min-h-[120px]">
              <div className="flex flex-col items-center gap-2 text-center">
                <Plus size={24} className="text-blue-600" />
                <h3 className="font-semibold text-gray-900">Adicionar Aluno</h3>
              </div>
            </CardContent>
          </Card>

          <Card className="border-2 border-dashed border-gray-300 hover:border-green-500 cursor-pointer transition-colors">
            <CardContent className="pt-6 flex items-center justify-center min-h-[120px]">
              <div className="flex flex-col items-center gap-2 text-center">
                <Plus size={24} className="text-green-600" />
                <h3 className="font-semibold text-gray-900">Importar CSV</h3>
              </div>
            </CardContent>
          </Card>

          <Card className="border-2 border-dashed border-gray-300 hover:border-purple-500 cursor-pointer transition-colors">
            <CardContent className="pt-6 flex items-center justify-center min-h-[120px]">
              <div className="flex flex-col items-center gap-2 text-center">
                <Plus size={24} className="text-purple-600" />
                <h3 className="font-semibold text-gray-900">Criar Atividade</h3>
              </div>
            </CardContent>
          </Card>

          <Card className="border-2 border-dashed border-gray-300 hover:border-orange-500 cursor-pointer transition-colors">
            <CardContent className="pt-6 flex items-center justify-center min-h-[120px]">
              <div className="flex flex-col items-center gap-2 text-center">
                <Plus size={24} className="text-orange-600" />
                <h3 className="font-semibold text-gray-900">Ver Notas</h3>
              </div>
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout currentTrimestre={selectedTrimestre} onTrimestreChange={setSelectedTrimestre}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Minhas Turmas</h1>
        <p className="text-gray-600 mt-2">Gerencie suas turmas, alunos e atividades</p>
      </div>

      {/* Search and Create Button */}
      <div className="flex flex-col md:flex-row gap-4 mb-8">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-3 text-gray-400" size={20} />
          <Input
            placeholder="Buscar turma por nome ou disciplina..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Plus size={20} className="mr-2" />
              Criar Turma
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Criar Nova Turma</DialogTitle>
              <DialogDescription>
                Adicione uma nova turma com nome, disciplina e série
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="nome">Nome da Turma *</Label>
                <Input
                  id="nome"
                  placeholder="Ex: 7º A - Matemática"
                  value={newTurma.nome}
                  onChange={(e) => setNewTurma({ ...newTurma, nome: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="disciplina">Disciplina</Label>
                <Input
                  id="disciplina"
                  placeholder="Ex: Matemática"
                  value={newTurma.disciplina}
                  onChange={(e) => setNewTurma({ ...newTurma, disciplina: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="ano_serie">Ano/Série</Label>
                <Input
                  id="ano_serie"
                  placeholder="Ex: 7º Ano"
                  value={newTurma.ano_serie}
                  onChange={(e) => setNewTurma({ ...newTurma, ano_serie: e.target.value })}
                />
              </div>
              <Button
                onClick={handleCreateTurma}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                Criar Turma
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Turmas Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-200 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filteredTurmas.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTurmas.map((turma) => (
            <Card
              key={turma.id}
              className="hover:shadow-lg transition-all cursor-pointer hover:scale-105"
              onClick={() => navigate(`/turmas/${turma.id}`)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{turma.nome}</CardTitle>
                    <CardDescription>{turma.disciplina || "Sem disciplina"}</CardDescription>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="sm">
                        <MoreVertical size={16} />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem className="cursor-pointer">
                        <Edit size={16} className="mr-2" />
                        Editar
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="cursor-pointer text-red-600"
                        onClick={() => handleDeleteTurma(turma.id)}
                      >
                        <Trash2 size={16} className="mr-2" />
                        Deletar
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {turma.ano_serie && (
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Série:</span> {turma.ano_serie}
                    </p>
                  )}
                  <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-200">
                    <div className="flex items-center gap-2">
                      <Users size={16} className="text-blue-600" />
                      <div>
                        <p className="text-xs text-gray-500">Alunos</p>
                        <p className="text-lg font-bold text-gray-900">
                          {turma.alunos_count || 0}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <BookOpen size={16} className="text-green-600" />
                      <div>
                        <p className="text-xs text-gray-500">Atividades</p>
                        <p className="text-lg font-bold text-gray-900">
                          {turma.atividades_count || 0}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <CardContent>
            <BookOpen size={48} className="mx-auto text-gray-300 mb-4" />
            <h3 className="font-semibold text-gray-900 mb-2">Nenhuma turma encontrada</h3>
            <p className="text-sm text-gray-500 mb-4">
              {searchQuery
                ? "Nenhuma turma corresponde à sua busca"
                : "Comece criando sua primeira turma"}
            </p>
            <Button onClick={() => setIsDialogOpen(true)} className="bg-blue-600 hover:bg-blue-700">
              <Plus size={20} className="mr-2" />
              Criar Turma
            </Button>
          </CardContent>
        </Card>
      )}
    </MainLayout>
  );
}
