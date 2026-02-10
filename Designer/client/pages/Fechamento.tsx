import React, { useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Trophy, Plus, Check, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Fechamento() {
  const [selectedTrimestre, setSelectedTrimestre] = useState(1);

  return (
    <MainLayout currentTrimestre={selectedTrimestre} onTrimestreChange={setSelectedTrimestre}>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Fechamento do Trimestre</h1>
        <p className="text-gray-600 mt-2">
          Acompanhe o desempenho dos alunos e finalize suas notas
        </p>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Turmas Ativas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-gray-500 mt-1">Aguardando fechamento</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Alunos Totais</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-gray-500 mt-1">Em todas as turmas</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-</div>
            <p className="text-xs text-gray-500 mt-1">Nenhuma turma</p>
          </CardContent>
        </Card>
      </div>

      {/* Empty State */}
      <Card className="text-center py-16">
        <CardContent>
          <Trophy size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="font-semibold text-gray-900 mb-2">
            Nenhuma turma para fechar
          </h3>
          <p className="text-sm text-gray-500 mb-6">
            Crie turmas e registre atividades para acompanhar e fechar trimestres
          </p>
          <Button className="bg-blue-600 hover:bg-blue-700">
            <Plus size={20} className="mr-2" />
            Ir para Turmas
          </Button>
        </CardContent>
      </Card>

      {/* Tips */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex gap-3">
            <Check size={20} className="text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-900">
                Como fechar um trimestre
              </p>
              <p className="text-xs text-green-800 mt-1">
                Acesse a turma, revise todas as notas e clique em "Fechar Trimestre"
              </p>
            </div>
          </div>
        </div>

        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex gap-3">
            <AlertCircle size={20} className="text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-900">
                Importante
              </p>
              <p className="text-xs text-blue-800 mt-1">
                Após fechar o trimestre, as notas terão um histórico que pode ser consultado
              </p>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
