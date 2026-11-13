import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import AppLayout from "./components/app/AppLayout.jsx";
import Dashboard from "./pages/app/Dashboard.jsx";
import Clients from "./pages/app/Clients.jsx";
import Missions from "./pages/app/Missions.jsx";
import MissionDetail from "./pages/app/MissionDetail.jsx";
import Abonnement from "./pages/app/Abonnement.jsx";
import Assistant from "./pages/app/Assistant.jsx";
import ModulesHub from "./pages/app/ModulesHub.jsx";
import { LangProvider } from "./i18n.jsx";
import { PaiementRetour, PaiementPage } from "./pages/Paiement.jsx";

function Private({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="state-msg">Chargement…</div>;
  return user ? children : <Navigate to="/connexion" replace />;
}

function Public({ children }) {
  const { ready } = useAuth();
  return ready ? children : <div className="state-msg">Chargement…</div>;
}

export default function App() {
  return (
    <LangProvider><AuthProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/connexion" element={<Public><Login /></Public>} />
        <Route path="/inscription" element={<Public><Register /></Public>} />
        <Route path="/paiement/retour" element={<PaiementRetour />} />
        <Route path="/paiement/:ref" element={<PaiementPage />} />
        <Route path="/paiement/test/:ref" element={<PaiementPage />} />
        <Route path="/espace" element={<Private><AppLayout /></Private>}>
          <Route index element={<Dashboard />} />
          <Route path="clients" element={<Clients />} />
          <Route path="missions" element={<Missions />} />
          <Route path="missions/:id" element={<MissionDetail />} />
          <Route path="abonnement" element={<Abonnement />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="modules" element={<ModulesHub />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider></LangProvider>
  );
}
