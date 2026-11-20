/* NOx pilot UI: no third-party resources; credentials and drafts live in memory. */
'use strict';
(function (root) {
  function makeOutbox(idFactory) {
    let pending = null;
    let busy = false;
    return {
      get pending() { return pending; },
      get busy() { return busy; },
      async send(experimentId, text, transport) {
        if (busy) throw new Error('Un envoi est déjà en cours.');
        if (!pending) {
          if (!experimentId || !text.trim()) throw new Error('Expérience et note requises.');
          pending = Object.freeze({event_id: idFactory(), experiment_id: experimentId, text: text.trim()});
        }
        busy = true;
        try {
          const result = await transport(pending);
          if (result.event_id !== pending.event_id || result.experiment_id !== pending.experiment_id ||
              result.text !== pending.text || result.status !== 'draft_local') {
            throw new Error('Confirmation inattendue : état de sauvegarde à vérifier.');
          }
          pending = null;
          return result;
        } finally { busy = false; }
      }
    };
  }
  function apiError(status, body) {
    if (status === 401) return 'Jeton refusé. Reconnecter la session.';
    if (status === 409) return 'Identifiant déjà utilisé avec un contenu différent. Vérifier le journal avant toute nouvelle saisie.';
    if (status === 404) return 'Projet, expérience ou route introuvable. Vérifier que le pilote NOx est à jour.';
    if (status === 422) return 'Données refusées : vérifier les identifiants, les champs et leur longueur.';
    return 'Erreur API ' + status + (typeof body?.detail === 'string' ? ' : ' + body.detail.slice(0,300) : '.');
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {makeOutbox, apiError};
  if (!root.document) return;
  const $ = id => document.getElementById(id);
  const state = {token: '', connected:false, project:'', experiment:'', projects:[], experiments:[], session:0, context:0, projectRequest:0, experimentRequest:0, eventsRequest:0};
  const outbox = makeOutbox(() => root.crypto.randomUUID());
  const drafts = new Map();
  function rememberDraft() { if(state.experiment) { const text=$('note-text').value; if(text.trim())drafts.set(state.experiment,text);else drafts.delete(state.experiment); } }
  function restoreDraft() { $('note-text').value=drafts.get(state.experiment)||''; }
  function status(id, message, error=false) { $(id).textContent=message; $(id).className=error?'error':''; }
  function controls() {
    const pending=!!outbox.pending;
    $('connect').disabled=state.connected;
    $('disconnect').disabled=!state.token;
    $('project-select').disabled=!state.connected||pending;
    $('experiment-select').disabled=!state.connected||!state.project||pending;
    $('create-project').disabled=!state.connected||pending;
    $('create-experiment').disabled=!state.connected||!state.project||pending;
    $('note-text').disabled=!state.connected||!state.experiment||pending;
    $('save-note').disabled=!state.connected||!state.experiment||outbox.busy;
    $('save-note').textContent=outbox.busy?'Envoi en cours…':pending?'Réessayer le même brouillon':'Enregistrer le brouillon local';
    $('refresh-events').disabled=!state.connected||!state.experiment;
    $('active-experiment').textContent=state.experiment||'Aucune expérience';
  }
  async function api(path, method='GET', data) {
    const token=state.token, session=state.session;
    if (!token) throw Error('Session déconnectée.');
    let response;
    try { response=await fetch(path,{method,credentials:'omit',cache:'no-store',headers:{Authorization:'Bearer '+token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined}); }
    catch { throw Error('Connexion interrompue. La sauvegarde peut avoir abouti : réessayer le même brouillon pour vérifier.'); }
    let body;try {body=await response.json();}catch {throw Error('Réponse illisible : état de sauvegarde à vérifier.');}
    if (!response.ok) {
      if (response.status===401 && state.token===token && state.session===session) {state.connected=false;controls();}
      throw Error(apiError(response.status,body));
    }
    if (state.token!==token || state.session!==session) throw Error('La session a changé pendant la requête. Reconnecter et vérifier le journal.');
    return body;
  }
  function options(id, items, prompt, selected) {
    const select=$(id);select.replaceChildren();const empty=document.createElement('option');empty.value='';empty.textContent=prompt;select.append(empty);
    items.forEach(item=>{const option=document.createElement('option');option.value=item.id;option.textContent=item.id+' · '+item.name;select.append(option);});
    select.value=selected;
  }
  function clearExperiment() {
    rememberDraft();++state.experimentRequest;++state.eventsRequest;
    state.experiment='';state.experiments=[];restoreDraft();
    options('experiment-select',[],'Choisir une expérience','');$('events').replaceChildren();
    status('journal-status','Aucune expérience sélectionnée.');
  }
  async function loadProjects(selected=state.project) {
    const request=++state.projectRequest, session=state.session, context=state.context;
    const project=state.project, experiment=state.experiment;
    const values=await api('/projects');
    if(request!==state.projectRequest||session!==state.session||context!==state.context||
       project!==state.project||experiment!==state.experiment)return false;
    if(!Array.isArray(values))throw Error('Liste de projets inattendue.');
    const next=values.some(p=>p.id===selected)?selected:'';
    if(next!==state.project){clearExperiment();++state.context;}
    state.projects=values;state.project=next;
    options('project-select',values,'Choisir un projet',state.project);controls();return true;
  }
  async function loadExperiments(selected='') {
    clearExperiment();
    const request=state.experimentRequest, project=state.project, context=state.context, session=state.session;
    controls();if(!project)return;
    const values=await api('/experiments?project_id='+encodeURIComponent(project));
    if(request!==state.experimentRequest||project!==state.project||context!==state.context||session!==state.session)return;
    if(!Array.isArray(values))throw Error('Liste d’expériences inattendue.');
    state.experiments=values;state.experiment=values.some(e=>e.id===selected)?selected:'';
    options('experiment-select',values,'Choisir une expérience',state.experiment);restoreDraft();controls();
    if(state.experiment)await loadEvents();
  }
  function eventNode(event) {
    const li=document.createElement('li');li.className='event';const meta=document.createElement('div');meta.className='event-meta';
    const label=document.createElement('strong');label.textContent=event.kind==='note'?'Note · brouillon local':event.source==='simulated'?'Mesure simulée':'Événement';
    const date=document.createElement('span');date.textContent=event.recorded_at?new Date(event.recorded_at).toLocaleString('fr-CA'):'';
    const source=document.createElement('span');source.textContent=event.status+' · '+event.event_id;meta.append(label,date,source);
    const content=document.createElement('p');content.textContent=event.kind==='note'?event.text:(String(event.value)+' '+event.unit+' · '+event.device_id);
    li.append(meta,content);return li;
  }
  async function loadEvents() {
    const request=++state.eventsRequest, experiment=state.experiment;
    if(!experiment){$('events').replaceChildren();status('journal-status','Aucune expérience sélectionnée.');return;}
    status('journal-status','Chargement…');
    const values=await api('/events?experiment_id='+encodeURIComponent(experiment)+'&limit=100');
    if(request!==state.eventsRequest||experiment!==state.experiment)return;
    if(!Array.isArray(values))throw Error('Journal inattendu.');
    $('events').replaceChildren(...values.map(eventNode));status('journal-status',values.length?values.length+' événement(s) affiché(s), du plus récent au plus ancien.':'Aucun événement pour cette expérience.');
  }
  $('connection-form').addEventListener('submit',async event=>{
    event.preventDefault();const session=++state.session;++state.projectRequest;++state.experimentRequest;++state.eventsRequest;
    $('connect').disabled=true;state.token=$('token').value.trim();$('token').value='';
    try {const health=await api('/health');state.connected=true;status('connection-status','Connecté · '+(health.mode==='simulation_only'?'simulation uniquement':'mode '+health.mode));await loadProjects();if(session===state.session&&outbox.pending)status('note-status','Brouillon non confirmé conservé en mémoire. Réessayer le même envoi.');}
    catch(error){if(session===state.session){state.connected=false;status('connection-status',error.message,true);}}finally{controls();}
  });
  $('disconnect').onclick=()=>{++state.session;++state.projectRequest;++state.experimentRequest;++state.eventsRequest;state.token='';state.connected=false;$('events').replaceChildren();status('connection-status','Déconnecté. Jeton effacé. Les brouillons restent en mémoire jusqu’à la fermeture de cette page.');status('journal-status','Reconnecter pour consulter le journal.');if(outbox.pending)status('note-status','Sauvegarde non confirmée : brouillon et identifiant conservés. Reconnecter puis réessayer le même envoi.');controls();};
  $('project-form').onsubmit=async event=>{
    event.preventDefault();if(outbox.pending)return;
    const context=state.context, session=state.session;$('create-project').disabled=true;
    const payload={id:$('project-id').value.trim(),name:$('project-name').value.trim()};
    try{await api('/projects','POST',payload);status('project-status','Projet confirmé : '+payload.id);
      if(context===state.context&&session===state.session&&!outbox.pending){const applied=await loadProjects(payload.id);if(applied&&state.project===payload.id)await loadExperiments();}
    }catch(error){status('project-status',error.message,true);}finally{controls();}
  };
  $('experiment-form').onsubmit=async event=>{
    event.preventDefault();if(outbox.pending){status('experiment-status','Confirmer le brouillon en attente avant de changer d’expérience.',true);return;}
    const context=state.context, session=state.session;$('create-experiment').disabled=true;
    const payload={id:$('experiment-id').value.trim(),project_id:state.project,name:$('experiment-name').value.trim()};
    try{await api('/experiments','POST',payload);status('experiment-status','Expérience confirmée : '+payload.id);
      if(context===state.context&&session===state.session&&payload.project_id===state.project&&!outbox.pending)await loadExperiments(payload.id);
    }catch(error){status('experiment-status',error.message,true);}finally{controls();}
  };
  $('project-select').onchange=async()=>{if(outbox.pending)return;++state.context;state.project=$('project-select').value;try{await loadExperiments();status('note-status','Choisir une expérience pour écrire une note.');}catch(error){status('experiment-status',error.message,true);}};
  $('experiment-select').onchange=async()=>{if(outbox.pending)return;++state.context;rememberDraft();state.experiment=$('experiment-select').value;restoreDraft();controls();status('note-status','Note non enregistrée.');try{await loadEvents();}catch(error){status('journal-status',error.message,true);}};
  $('note-form').onsubmit=async event=>{
    event.preventDefault();if(outbox.busy)return;
    if(!state.connected||!state.experiment){status('note-status','Se connecter et choisir une expérience.',true);return;}
    try {
      const sending=outbox.send(state.experiment,$('note-text').value,payload=>api('/notes','POST',payload));controls();status('note-status','Envoi du brouillon…');
      const result=await sending;drafts.delete(result.experiment_id);$('note-text').value='';status('note-status','Brouillon local confirmé · '+result.event_id+'. Aucun envoi au cahier externe.');
      try{await loadEvents();}catch(error){status('journal-status','Brouillon confirmé, mais actualisation du journal impossible : '+error.message,true);}
    } catch(error){status('note-status',error.message+' Le contenu et son identifiant sont conservés en mémoire pour réessayer.',true);}finally{controls();}
  };
  $('refresh-events').onclick=async()=>{try{await loadEvents();}catch(error){status('journal-status',error.message,true);}};
  root.addEventListener('beforeunload',event=>{if(outbox.pending||$('note-text').value.trim()||drafts.size){event.preventDefault();event.returnValue='';}});
  controls();
})(typeof globalThis!=='undefined'?globalThis:this);
