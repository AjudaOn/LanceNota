import React, { createContext, useContext, useState, useEffect } from "react";
import { Professor } from "@shared/api";

interface AuthContextType {
  professor: Professor | null;
  isLoggedIn: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [professor, setProfessor] = useState<Professor | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user is already logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const storedProfessor = localStorage.getItem("professor");
        if (storedProfessor) {
          setProfessor(JSON.parse(storedProfessor));
        }
      } catch (error) {
        console.error("Failed to restore auth session:", error);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.message || "Login failed");
      }

      if (data.professor) {
        setProfessor(data.professor);
        localStorage.setItem("professor", JSON.stringify(data.professor));
      }
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    setProfessor(null);
    localStorage.removeItem("professor");
  };

  return (
    <AuthContext.Provider value={{ professor, isLoggedIn: !!professor, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
