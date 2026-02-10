import React, { useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardContent } from "@/components/ui/card";
import { FileText, Plus, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function Atividades() {
  const [selectedTrimestre, setSelectedTrimestre] = useState(1);

  return (
    <MainLayout currentTrimestre={selectedTrimestre} onTrimestreChange={setSelectedTrimestre}>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Atividades</h1>
        <p className="text-gray-600 mt-2">
          Gerencie todas as suas atividades, avisos e avaliações
        </p>
      </div>

      {/* Search and Create */}
      <div className="flex flex-col md:flex-row gap-4 mb-8">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-3 text-gray-400" size={20} />
          <Input placeholder="Buscar atividades..." className="pl-10" />
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700">
          <Plus size={20} className="mr-2" />
          Criar Atividade
        </Button>
      </div>

      {/* Empty State */}
      <Card className="text-center py-16">
        <CardContent>
          <FileText size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="font-semibold text-gray-900 mb-2">
            Nenhuma atividade criada
          </h3>
          <p className="text-sm text-gray-500 mb-6">
            Comece criando uma nova atividade para suas turmas
          </p>
          <Button className="bg-blue-600 hover:bg-blue-700">
            <Plus size={20} className="mr-2" />
            Criar Atividade
          </Button>
        </CardContent>
      </Card>

      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-900">
          💡 <strong>Dica:</strong> Aqui você pode criar atividades, avaliações e
          acompanhar o progresso de seus alunos em tempo real.
        </p>
      </div>
    </MainLayout>
  );
}
