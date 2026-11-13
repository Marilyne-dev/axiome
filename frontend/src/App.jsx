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
import ParMission from "./pages/app/ParMission.jsx";
import ImportFec from "./pages/app/missionTabs/ImportFec.jsx";
import Risques from "./pages/app/missionTabs/Risques.jsx";
import Circularisation from "./pages/app/missionTabs/Circularisation.jsx";
import Rapports from "./pages/app/missionTabs/Rapports.jsx";
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
    <AuthProvider>
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
          <Route path="import-fec" element={<ParMission eyebrow="Données" titre="Import FEC" sous="Importez le fichier des écritures comptables (DGFiP) d'une mission : il devient la balance du dossier." Vue={ImportFec} />} />
          <Route path="risques" element={<ParMission eyebrow="Risques" titre="Cartographie des risques" sous="Choisissez une mission pour consulter et alimenter sa cartographie." Vue={Risques} />} />
          <Route path="circularisation" element={<ParMission eyebrow="Confirmations externes" titre="Circularisation" sous="Suivez les demandes de confirmation envoyées aux banques, clients, fournisseurs et autres tiers." Vue={Circularisation} />} />
          <Route path="rapports" element={<ParMission eyebrow="Livrables" titre="Rapports" sous="Générez les documents du dossier (Word ou PDF) pour la mission de votre choix." Vue={Rapports} />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
