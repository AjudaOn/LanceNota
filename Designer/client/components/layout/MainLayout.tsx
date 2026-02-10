import React, { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface MainLayoutProps {
  children: React.ReactNode;
  currentTurma?: { id: string; nome: string } | null;
  currentTrimestre?: number;
  onTrimestreChange?: (trimestre: number) => void;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  currentTurma,
  currentTrimestre = 1,
  onTrimestreChange,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden lg:ml-0">
        {/* Topbar */}
        <Topbar
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
          currentTurma={currentTurma}
          currentTrimestre={currentTrimestre}
          onTrimestreChange={onTrimestreChange}
        />

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 lg:p-6 max-w-7xl mx-auto w-full">{children}</div>
        </main>
      </div>
    </div>
  );
};
