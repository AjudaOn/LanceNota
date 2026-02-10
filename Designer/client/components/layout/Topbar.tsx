import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Menu, ChevronDown, LogOut, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface TopbarProps {
  onMenuClick: () => void;
  currentTurma?: { id: string; nome: string } | null;
  currentTrimestre?: number;
  onTrimestreChange?: (trimestre: number) => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  onMenuClick,
  currentTurma,
  currentTrimestre = 1,
  onTrimestreChange,
}) => {
  const navigate = useNavigate();
  const { professor, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");

  const handleLogout = () => {
    logout();
    setTimeout(() => {
      window.location.href = "/login";
    }, 0);
  };

  const handleNavigateSettings = () => {
    navigate("/settings");
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
      <div className="flex items-center justify-between h-16 px-4 lg:px-6">
        {/* Left Section - Menu & Turma */}
        <div className="flex items-center gap-4 flex-1">
          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="lg:hidden"
          >
            <Menu size={20} />
          </Button>

          {/* Current Turma Display */}
          {currentTurma && (
            <div className="hidden md:flex items-center gap-4">
              <div>
                <p className="text-xs text-gray-500 font-medium">TURMA SELECIONADA</p>
                <p className="text-sm font-semibold text-gray-900">{currentTurma.nome}</p>
              </div>

              {/* Trimestre Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 font-medium">TRIMESTRE:</span>
                <select
                  value={currentTrimestre}
                  onChange={(e) => onTrimestreChange?.(parseInt(e.target.value))}
                  className="text-sm font-medium border border-gray-300 rounded-md px-3 py-1.5 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={1}>1º</option>
                  <option value={2}>2º</option>
                  <option value={3}>3º</option>
                  <option value={4}>4º</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Right Section - Search & User Menu */}
        <div className="flex items-center gap-4">
          {/* Search Box - Hidden on mobile */}
          <div className="hidden md:flex items-center">
            <input
              type="text"
              placeholder="Buscar alunos, atividades..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-sm bg-gray-100 border border-gray-200 rounded-lg px-4 py-2 w-64 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition"
            />
          </div>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="flex items-center gap-2 hover:bg-gray-100"
              >
                <div className="hidden md:flex flex-col items-end">
                  <p className="text-sm font-medium text-gray-900">
                    {professor?.nome || "Professor"}
                  </p>
                  <p className="text-xs text-gray-500">{professor?.email}</p>
                </div>
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-medium text-sm">
                  {professor?.nome?.charAt(0) || "P"}
                </div>
                <ChevronDown size={16} className="text-gray-500" />
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" className="w-56">
              <div className="px-4 py-3 md:hidden">
                <p className="font-medium text-gray-900">{professor?.nome}</p>
                <p className="text-sm text-gray-500">{professor?.email}</p>
              </div>

              <DropdownMenuSeparator className="md:hidden" />

              <DropdownMenuItem onClick={handleNavigateSettings} className="cursor-pointer">
                <Settings size={16} className="mr-2" />
                <span>Configurações</span>
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-red-600">
                <LogOut size={16} className="mr-2" />
                <span>Sair</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
};
