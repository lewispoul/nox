'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

// Instrument the actual browser script only inside the test VM; no test hook is shipped.
const source=fs.readFileSync(path.join(__dirname,'../../../chemlab/web/app.js'),'utf8');
function harness() {
  const nodes=new Map();const calls=[];
  function element(){return {value:'',textContent:'',className:'',disabled:false,children:[],handlers:{},
    append(...children){this.children.push(...children);},replaceChildren(...children){this.children=children;},
    addEventListener(name,handler){this.handlers[name]=handler;}};}
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);},createElement:element};
  const context=vm.createContext({document,crypto:{randomUUID:()=> 'note-fixed-id'},addEventListener(){},
    fetch(url,options){return new Promise((resolve,reject)=>calls.push({url,options,resolve,reject}));}});
  const instrumented=source.replace(/  controls\(\);\n\}\)\(/,'  controls();\n  root.__ui={state, loadProjects, loadExperiments, outbox};\n})( ');
  assert.notEqual(instrumented,source);vm.runInContext(instrumented,context);
  const ui=context.__ui;Object.assign(ui.state,{token:'same-token',connected:true,project:'P1',experiment:'E1',session:1});
  function resolve(index,body){calls[index].resolve({ok:true,status:200,json:async()=>body});}
  return {ui,nodes,document,calls,resolve};
}
const projects=[{id:'P1',name:'First'},{id:'P2',name:'Second'}];
(async()=>{
  // Exact reviewed race: old P1 refresh returns after a new P2/E2 selection.
  let h=harness();let flight=h.ui.loadProjects('P1');
  h.ui.state.project='P2';h.ui.state.experiment='E2';++h.ui.state.context;
  h.resolve(0,projects);assert.equal(await flight,false);
  assert.equal(h.ui.state.project,'P2');assert.equal(h.ui.state.experiment,'E2');

  // A valid project change must invalidate the old experiment and its requests.
  h=harness();h.document.getElementById('note-text').value='Draft for E1';
  flight=h.ui.loadProjects('P2');h.resolve(0,projects);assert.equal(await flight,true);
  assert.equal(h.ui.state.project,'P2');assert.equal(h.ui.state.experiment,'');
  assert.equal(h.document.getElementById('note-text').value,'');
  assert.equal(h.ui.state.experimentRequest,1);assert.equal(h.ui.state.eventsRequest,1);

  // Only the newest project-list request may apply, even when replies reverse order.
  h=harness();const earlier=h.ui.loadProjects('P1'),later=h.ui.loadProjects('P2');
  h.resolve(1,projects);assert.equal(await later,true);h.resolve(0,projects);assert.equal(await earlier,false);
  assert.equal(h.ui.state.project,'P2');assert.equal(h.ui.state.experiment,'');

  // A reconnect with the identical token is still a new session.
  h=harness();flight=h.ui.loadProjects('P1');++h.ui.state.session;
  h.resolve(0,projects);await assert.rejects(flight,/session a changé/);
  assert.equal(h.ui.state.project,'P1');assert.equal(h.ui.state.experiment,'E1');

  // Disconnect during POST cannot silently clear or claim confirmation of a note.
  h=harness();h.document.getElementById('note-text').value='Pending observation';
  const submitted=h.document.getElementById('note-form').onsubmit({preventDefault(){}});
  assert.equal(h.ui.outbox.busy,true);const original=h.ui.outbox.pending;
  h.document.getElementById('disconnect').onclick();
  assert.equal(h.ui.state.token,'');assert.equal(h.ui.outbox.pending,original);
  assert.match(h.document.getElementById('connection-status').textContent,/brouillons restent en mémoire/);
  // Same token is reused after reconnect; generation must still invalidate old reply.
  h.ui.state.token='same-token';h.ui.state.connected=true;
  h.resolve(0,{...original,status:'draft_local'});await submitted;
  assert.equal(h.ui.outbox.pending,original);assert.equal(h.ui.outbox.busy,false);
  assert.equal(h.document.getElementById('note-text').value,'Pending observation');
  assert.match(h.document.getElementById('note-status').textContent,/conservés en mémoire/);
  assert(!h.document.getElementById('note-status').textContent.includes('Brouillon local confirmé'));
  console.log('NOx UI races: late project replies, project/experiment consistency, session generation and disconnect during note passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
