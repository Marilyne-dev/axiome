import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import useAsync from "../../components/app/useAsync.js";
import { getMission, getMissions } from "../../api.js";
import { ErrorBox, Loading, Verrou } from "../../components/app/ui.jsx";
import { FIcon, Select } from "../../components/app/FormKit.jsx";
import "../../audit.css";

/* Page du menu « Travaux d'audit » : on choisit une mission, puis l'outil (Vue) s'ouvre dessus.
   La mission choisie est dans l'adresse (?mission=12) : le lien se partage et survit au rafraîchissement. */
export default function ParMission({ eyebrow, titre, sous, Vue }) {
  const [sp, setSp] = useSearchParams();
  const id = sp.get("mission") || "";
  const liste = useAsync(getMissions);
  const mission = useAsync(() => (id ? getMission(id) : Promise.resolve(null)), [id]);

  useEffect(() => { // une seule mission : on la sélectionne d'office
    if (!id && liste.data?.length === 1) setSp({ mission: String(liste.data[0].id) }, { replace: true });
  }, [id, liste.data]); // eslint-disable-line

  return (
    <>
      <div className="page-head"><div><p className="eyebrow">{eyebrow}</p><h1>{titre}</h1>{sous && <p className="muted">{sous}</p>}</div></div>
      {liste.status === 402 && <Verrou />}
      {liste.error && liste.status !== 402 && <ErrorBox message={liste.error} onRetry={liste.reload} />}
      {liste.loading && !liste.data && <Loading />}
      {liste.data && !liste.data.length && (
        <div className="app-card empty"><div className="empty-ico"><FIcon n="briefcase" size={34} /></div>
          <h3>Aucune mission pour le moment</h3><p>Ouvrez d'abord une mission : cet outil s'applique au dossier d'une mission.</p>
          <Link className="btn btn-primary" style={{ marginTop: 18 }} to="/espace/missions">Aller aux missions</Link></div>)}
      {liste.data?.length > 0 && (
        <div className="app-card pm-pick">
          <Select label="Mission" icon="briefcase" value={id} onChange={(e) => setSp({ mission: e.target.value })}>
            <option value="" disabled hidden></option>
            {liste.data.map((x) => <option key={x.id} value={x.id}>{x.intitule} — {x.client}{x.exercice ? ` (${x.exercice})` : ""}</option>)}
          </Select>
          {id && mission.data && <Link className="pm-open" to={`/espace/missions/${mission.data.id}`}>Ouvrir le dossier complet →</Link>}
        </div>)}
      {liste.data?.length > 1 && !id && <p className="muted pm-hint">Choisissez une mission pour continuer.</p>}
      {id && mission.loading && !mission.data && <Loading />}
      {id && mission.error && (mission.status === 402 ? <Verrou /> : <ErrorBox message={mission.error} onRetry={mission.reload} />)}
      {mission.data && <div key={mission.data.id} className="pm-body"><Vue m={mission.data} reload={mission.reload} /></div>}
    </>
  );
}
