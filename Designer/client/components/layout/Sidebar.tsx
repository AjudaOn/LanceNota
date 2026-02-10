import React from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  BookOpen,
  FileText,
  Trophy,
  Settings,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { logout } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  const menuItems = [
    { icon: BarChart3, label: "Dashboard", path: "/" },
    { icon: BookOpen, label: "Turmas", path: "/turmas" },
    { icon: FileText, label: "Atividades", path: "/atividades" },
    { icon: Trophy, label: "Fechamento", path: "/fechamento" },
    { icon: Settings, label: "Configurações", path: "/settings" },
  ];

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 lg:hidden z-40"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 h-screen w-64 bg-gradient-to-b from-slate-900 to-slate-800 text-white transform transition-transform duration-300 ease-in-out z-50 lg:translate-x-0 lg:static lg:h-auto lg:bg-sidebar lg:text-foreground shadow-lg",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Close Button Mobile */}
        <div className="lg:hidden flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <BookOpen size={24} className="text-blue-400" />
            <span className="font-bold text-lg">EduClass</span>
          </div>
          <button onClick={onClose} className="text-white hover:text-gray-300">
            <X size={24} />
          </button>
        </div>

        {/* Desktop Logo */}
        <div className="hidden lg:flex items-center gap-3 p-6 border-b border-sidebar-border">
          <div className="w-10 h-10 rounded-lg bg-blue-600 text-white flex items-center justify-center">
            <BookOpen size={20} />
          </div>
          <div>
            <div className="font-bold text-white">EduClass</div>
            <div className="text-xs text-sidebar-foreground">Gestão Acadêmica</div>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 overflow-y-auto py-4 lg:py-6 px-3 lg:px-4">
          <div className="space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={onClose}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors font-medium text-sm",
                    active
                      ? "bg-blue-600 text-white lg:bg-sidebar-accent lg:text-sidebar-accent-foreground"
                      : "text-white lg:text-sidebar-foreground hover:bg-slate-700 lg:hover:bg-sidebar-accent/50"
                  )}
                >
                  <Icon size={20} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Logout Button */}
        <div className="border-t border-slate-700 lg:border-sidebar-border p-4">
          <Button
            onClick={handleLogout}
            variant="ghost"
            className="w-full justify-start gap-3 text-white lg:text-foreground hover:bg-slate-700 lg:hover:bg-sidebar-accent/50"
          >
            <LogOut size={20} />
            <span>Sair</span>
          </Button>
        </div>
      </aside>
    </>
  );
};
