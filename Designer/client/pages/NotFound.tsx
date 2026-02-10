import { useLocation, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle, Home } from "lucide-react";

const NotFound = () => {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname,
    );
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="text-center max-w-md">
        <AlertCircle size={64} className="mx-auto text-orange-500 mb-6 opacity-80" />
        <h1 className="text-5xl font-bold text-gray-900 mb-3">404</h1>
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Página não encontrada</h2>
        <p className="text-gray-600 mb-8">
          Desculpe, a página que você está procurando não existe ou foi movida.
        </p>
        
        <div className="space-y-3">
          <Button 
            onClick={() => navigate("/")}
            className="w-full bg-blue-600 hover:bg-blue-700"
            size="lg"
          >
            <Home size={18} className="mr-2" />
            Voltar ao Dashboard
          </Button>
          <Button 
            onClick={() => navigate("/turmas")}
            variant="outline"
            className="w-full"
            size="lg"
          >
            Ir para Turmas
          </Button>
        </div>

        <p className="text-xs text-gray-500 mt-8">
          Código do erro: {location.pathname}
        </p>
      </div>
    </div>
  );
};

export default NotFound;
