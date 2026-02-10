import React, { useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { Settings, Bell, Eye, Lock, Download } from "lucide-react";

export default function Configuracoes() {
  const { professor } = useAuth();
  const [selectedTrimestre, setSelectedTrimestre] = useState(1);

  return (
    <MainLayout currentTrimestre={selectedTrimestre} onTrimestreChange={setSelectedTrimestre}>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Configurações</h1>
        <p className="text-gray-600 mt-2">Personalize sua conta e preferências</p>
      </div>

      {/* Profile Settings */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Perfil</CardTitle>
          <CardDescription>Informações da sua conta</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label htmlFor="nome">Nome Completo</Label>
              <Input
                id="nome"
                defaultValue={professor?.nome || ""}
                disabled
                className="mt-2"
              />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                defaultValue={professor?.email || ""}
                disabled
                className="mt-2"
              />
            </div>
            <div className="pt-4 border-t border-gray-200">
              <Button variant="outline">Editar Perfil</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell size={20} />
            Notificações
          </CardTitle>
          <CardDescription>Gerencie suas preferências de notificação</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium text-gray-900">Avisos de Atividades</p>
                <p className="text-sm text-gray-500">Receber notificações sobre novas atividades</p>
              </div>
              <input type="checkbox" defaultChecked className="w-5 h-5" />
            </div>
            <div className="flex items-center justify-between py-2 border-t border-gray-200">
              <div>
                <p className="font-medium text-gray-900">Recordações de Avaliação</p>
                <p className="text-sm text-gray-500">Ser lembrado de avaliar alunos pendentes</p>
              </div>
              <input type="checkbox" defaultChecked className="w-5 h-5" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Privacy Settings */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock size={20} />
            Segurança
          </CardTitle>
          <CardDescription>Gerencie a segurança da sua conta</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Button variant="outline" className="w-full justify-start">
              <Lock size={16} className="mr-2" />
              Alterar Senha
            </Button>
            <Button variant="outline" className="w-full justify-start">
              <Eye size={16} className="mr-2" />
              Atividade de Login Recente
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Data Export */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download size={20} />
            Dados e Exportação
          </CardTitle>
          <CardDescription>Exporte seus dados e relatórios</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Button variant="outline" className="w-full justify-start">
              <Download size={16} className="mr-2" />
              Exportar Dados (CSV)
            </Button>
            <p className="text-sm text-gray-500">
              Exporte todas as suas turmas, alunos e notas em formato CSV
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-200 bg-red-50">
        <CardHeader>
          <CardTitle className="text-red-600">Zona de Perigo</CardTitle>
          <CardDescription>Ações irreversíveis</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" className="w-full justify-start">
            Deletar Conta
          </Button>
          <p className="text-sm text-red-700 mt-3">
            Esta ação é irreversível. Todos os seus dados serão deletados permanentemente.
          </p>
        </CardContent>
      </Card>
    </MainLayout>
  );
}
