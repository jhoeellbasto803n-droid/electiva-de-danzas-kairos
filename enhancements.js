(() => {
"use strict";
const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
let timer=null,deadline=0,remaining=25*60,totalSeconds=25*60,running=false,staged=[];
const app=()=>window.Electiva, state=()=>app().getState();
function pad(n){return String(n).padStart(2,"0")}
function dateKey(d){return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())}
function localInputDate(d){return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+"T"+pad(d.getHours())+":"+pad(d.getMinutes())}
function escapeHtml(v){return String(v||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function renderFocus(){
 const st=state(),select=$("#focus-task"),old=select.value;
 const tasks=st.tasks.filter(t=>!t.done);
 select.innerHTML='<option value="">Sesión libre · sin actividad</option>'+tasks.map(t=>'<option value="'+escapeHtml(t.id)+'">'+escapeHtml(t.title)+'</option>').join("");
 if(old&&tasks.some(t=>t.id===old))select.value=old; const importSelect=$("#import-subject"),importOld=importSelect.value; importSelect.innerHTML=st.subjects.length?'<option value="">Elige una materia</option>'+st.subjects.map(x=>'<option value="'+escapeHtml(x.id)+'">'+escapeHtml(x.name)+'</option>').join(""):'<option value="">Crea una materia primero</option>'; if(importOld&&st.subjects.some(x=>x.id===importOld))importSelect.value=importOld; $("#import-confirm").disabled=!importSelect.value;
 const sessions=st.focusSessions||[],today=dateKey(new Date()),todays=sessions.filter(s=>s.endedAt&&dateKey(new Date(s.endedAt))===today);
 const mins=todays.reduce((n,s)=>n+Number(s.minutes||0),0);
 $("#focus-today").textContent=mins+" min hoy";$("#focus-count").textContent=todays.length+" sesiones";
 const minsByTask={};sessions.forEach(s=>{if(s.taskId)minsByTask[s.taskId]=(minsByTask[s.taskId]||0)+Number(s.minutes||0)});
 $$(".task").forEach(card=>{const id=card.querySelector("[data-done]")?.dataset.done,meta=card.querySelector(".task-meta");if(id&&meta&&minsByTask[id]&&!meta.querySelector(".focus-total")){const span=document.createElement("span");span.className="focus-total";span.textContent="Estudio registrado: "+minsByTask[id]+" min";meta.append(span)}});
 $(".subject").forEach(card=>{const del=card.querySelector("[data-delete-subject]"),group=del?.parentElement;if(group&&!group.querySelector("[data-edit-subject]")){const edit=document.createElement("button");edit.className="mini";edit.dataset.editSubject=del.dataset.deleteSubject;edit.textContent="Editar";group.insertBefore(edit,del)}});paintTimer();
}
function paintTimer(){
 const mins=Math.floor(remaining/60),secs=remaining%60;$("#focus-clock").textContent=pad(mins)+":"+pad(secs);
 const progress=totalSeconds?1-remaining/totalSeconds:0;$("#focus-clock").style.background="radial-gradient(circle,#fff 59%,transparent 61%),conic-gradient(#826bd2 "+Math.round(progress*360)+"deg,#e9e5f6 0deg)";
 $("#focus-start").textContent=running?"Pausar":(remaining===totalSeconds?"Iniciar sesión":"Continuar");
 $("#focus-stop").disabled=remaining===totalSeconds;
 $("#focus-task").disabled=running||remaining<totalSeconds;
 $("[data-focus-minutes]").forEach(b=>b.disabled=running||remaining<totalSeconds);
}
function setDuration(minutes){if(running)return;totalSeconds=Number(minutes)*60;remaining=totalSeconds;$$("[data-focus-minutes]").forEach(b=>b.classList.toggle("selected",Number(b.dataset.focusMinutes)===Number(minutes)));paintTimer()}
function finishSession(completed){
 if(timer){clearInterval(timer);timer=null}
 const elapsed=Math.floor((totalSeconds-remaining)/60),st=state();
 if(elapsed>=1){st.focusSessions=st.focusSessions||[];st.focusSessions.push({id:app().uid(),taskId:$("#focus-task").value||null,minutes:elapsed,plannedMinutes:Math.round(totalSeconds/60),completed,endedAt:new Date().toISOString()});app().save();renderFocus()}
 running=false;remaining=totalSeconds;paintTimer();
 if(elapsed>=1)app().toast(completed?"¡Bloque completado! Registré "+elapsed+" minutos.":"Sesión guardada: "+elapsed+" minutos.");
 else app().toast("La sesión fue demasiado corta para registrarla.");
}
function bindFocus(){
 $$("[data-focus-minutes]").forEach(b=>b.addEventListener("click",()=>setDuration(b.dataset.focusMinutes)));
 $("#focus-start").addEventListener("click",()=>{
  if(running){remaining=Math.max(0,Math.ceil((deadline-Date.now())/1000));clearInterval(timer);timer=null;running=false;paintTimer();return}
  if(remaining===totalSeconds){totalSeconds=Number($(".focus-duration .selected")?.dataset.focusMinutes||25)*60;remaining=totalSeconds}
  running=true;deadline=Date.now()+remaining*1000;paintTimer();timer=setInterval(()=>{remaining=Math.max(0,Math.ceil((deadline-Date.now())/1000));paintTimer();if(remaining===0)finishSession(true)},250);
 });
 $("#focus-stop").addEventListener("click",()=>{if(remaining<totalSeconds)finishSession(false)});
}
function parseCsv(text){
 const first=text.split(/\r?\n/,1)[0]||"",delimiter=(first.match(/;/g)||[]).length>(first.match(/,/g)||[]).length?";":",",rows=[];let row=[],cell="",quote=false;
 for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quote&&text[i+1]==='"'){cell+='"';i++}else quote=!quote}else if(c===delimiter&&!quote){row.push(cell);cell=""}else if((c==="\n"||c==="\r")&&!quote){if(c==="\r"&&text[i+1]==="\n")i++;row.push(cell);if(row.some(x=>x.trim()))rows.push(row);row=[];cell=""}else cell+=c}
 row.push(cell);if(row.some(x=>x.trim()))rows.push(row);return rows;
}
function norm(s){return String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"").trim()}
function column(headers,names){return headers.findIndex(h=>names.includes(norm(h)))}
function parseHumanDate(raw){
 const s=String(raw||"").trim();if(!s)return "";
 let m=s.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?:[ ,T]+(\d{1,2}):(\d{2}))?$/);
 if(m)return m[3]+"-"+pad(m[2])+"-"+pad(m[1])+"T"+pad(m[4]||23)+":"+pad(m[5]||59);
 m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(m)return m[1]+"-"+m[2]+"-"+m[3]+"T23:59";
 const d=new Date(s);return isNaN(d.getTime())?"":localInputDate(d);
}
function parseIcsDate(raw){
 if(!raw)return "";
 const v=String(raw).trim(),m=v.match(/^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z)?)?$/);
 if(!m){return parseHumanDate(v)}
 if(!m[4])return m[1]+"-"+m[2]+"-"+m[3]+"T23:59";
 if(m[7])return localInputDate(new Date(Date.UTC(Number(m[1]),Number(m[2])-1,Number(m[3]),Number(m[4]),Number(m[5]),Number(m[6]||0))));
 return m[1]+"-"+m[2]+"-"+m[3]+"T"+m[4]+":"+m[5];
}
function decodeIcs(s){return String(s||"").replace(/\\n/gi," · ").replace(/\\,/g,",").replace(/\\;/g,";").replace(/\\\\/g,"\\").trim()}
function parseIcs(text){
 const lines=text.replace(/\r\n/g,"\n").replace(/\r/g,"\n").split("\n"),unfolded=[];
 lines.forEach(line=>{if(/^[ \t]/.test(line)&&unfolded.length)unfolded[unfolded.length-1]+=line.slice(1);else unfolded.push(line)});
 const events=[];let e=null;
 unfolded.forEach(line=>{if(line==="BEGIN:VEVENT"||line==="BEGIN:VTODO"){e={};return}if(line==="END:VEVENT"||line==="END:VTODO"){if(e)events.push(e);e=null;return}if(!e)return;const ix=line.indexOf(":");if(ix<0)return;const left=line.slice(0,ix),key=left.split(";")[0].toUpperCase(),value=line.slice(ix+1);e[key]=value});
 return events.map(e=>{const title=decodeIcs(e.SUMMARY),due=parseIcsDate(e.DUE||e.DTSTART),desc=decodeIcs(e.DESCRIPTION);return{title,due,weight:extractWeight(desc),hours:extractHours(desc),description:desc,sourceUrl:e.URL||""}}).filter(x=>x.title&&x.due)
}
function extractWeight(text){const m=String(text||"").match(/(?:ponderaci[oó]n|peso|vale)?\s*(\d{1,3}(?:[.,]\d+)?)\s*%/i);return m?Number(m[1].replace(",",".")):null}
function extractHours(text){const m=String(text||"").match(/(?:duraci[oó]n|estimad[oa])\s*(\d+(?:[.,]\d+)?)\s*(?:h|horas?)/i);return m?Number(m[1].replace(",",".")):null}
function parseCsvEvents(text){
 const rows=parseCsv(text);if(rows.length<2)throw Error("El CSV no contiene filas de datos.");
 const h=rows[0],ti=column(h,["title","summary","subject","assignment","assignmentname","activity","actividad","tarea","nombre"]),di=column(h,["due","duedate","deadline","fecha","fechalimite","date","fechaentrega"]),wi=column(h,["weight","ponderacion","porcentaje","percentage","gradeweight"]),hi=column(h,["hours","horas","estimatedhours","tiempoestimado"]),si=column(h,["description","descripcion","notes","notas","details","detalle"]),ui=column(h,["url","link","enlace"]);
 if(ti<0||di<0)throw Error("No reconocí las columnas. El CSV debe incluir actividad/título y fecha/fecha límite.");
 const events=rows.slice(1).map(r=>({title:(r[ti]||"").trim(),due:parseHumanDate(r[di]),weight:wi>=0&&r[wi]&&isFinite(Number(r[wi].replace("%","").replace(",",".")))?Number(r[wi].replace("%","").replace(",",".")):null,hours:hi>=0&&r[hi]?Number(r[hi].replace(",", ".")):null,description:si>=0?(r[si]||"").trim():"",sourceUrl:ui>=0?(r[ui]||"").trim():""})).filter(x=>x.title&&x.due&&isFinite(new Date(x.due).getTime()));
 return {events,skipped:rows.length-1-events.length}
}
function parseCalendarFile(name,text){
 if(name.toLowerCase().endsWith(".ics"))return {events:parseIcs(text),skipped:0,kind:"ICS"};
 return Object.assign(parseCsvEvents(text),{kind:"CSV"})
}
function renderPreview(events,skipped,name){
 const box=$("#import-preview");box.hidden=false;
 const dup=events.filter(e=>state().tasks.some(t=>t.title.toLowerCase()===e.title.toLowerCase()&&t.due===e.due));
 const good=events.filter(e=>!dup.includes(e));staged=good.map(e=>({...e,fileName:name}));
 $("#import-message").textContent=(good.length?""+good.length+" actividad(es) detectadas":"No encontré actividades nuevas.")+(skipped?", "+skipped+" fila(s) sin título o fecha omitidas.":"")+(dup.length?", "+dup.length+" duplicado(s) omitidos.":"")+" Revisa la fecha importada; la ponderación puede estar vacía.";
 box.innerHTML=good.slice(0,18).map(e=>'<div class="preview-row"><b>'+escapeHtml(e.title)+'</b><small>'+escapeHtml(new Intl.DateTimeFormat("es-CO",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(e.due)))+(e.weight===null?" · peso por confirmar":" · "+e.weight+"%")+'</small></div>').join("")+(good.length>18?'<div class="preview-row"><b>+'+(good.length-18)+' más</b><small>Se importarán también</small></div>':"");
 $("#import-confirm").hidden=!good.length;$("#import-confirm").disabled=!$("#import-subject").value;
}
async function loadCalendar(file){
 if(!file)return;try{
  const parsed=parseCalendarFile(file.name,await file.text());
  if(!state().subjects.length){app().toast("Primero crea una materia para asignar las actividades.");return}
  renderPreview(parsed.events,parsed.skipped,file.name);if(parsed.kind==="ICS")$("#import-message").textContent+=" En eventos .ics uso la fecha DUE; si no existe, uso DTSTART.";
 }catch(e){$("#import-preview").hidden=true;$("#import-confirm").hidden=true;$("#import-message").textContent=e.message||"No pude leer ese archivo.";app().toast("No pude importar el archivo.")}
}
function bindImport(){
 $("#calendar-file").addEventListener("change",e=>loadCalendar(e.target.files[0]));
 $("#import-subject").addEventListener("change",()=>{$("#import-confirm").disabled=!$("#import-subject").value});
 $("#import-confirm").addEventListener("click",()=>{
  const sid=$("#import-subject").value;if(!sid||!staged.length)return;
  const st=state(),known=new Set(st.tasks.map(t=>t.title.toLowerCase()+"|"+t.due));let count=0;
  staged.forEach(e=>{const key=e.title.toLowerCase()+"|"+e.due;if(known.has(key))return;known.add(key);
   const missing=e.weight===null||!isFinite(e.weight);
   st.tasks.push({id:app().uid(),title:e.title,subjectId:sid,due:e.due,weight:missing?0:e.weight,hours:e.hours&&isFinite(e.hours)?e.hours:1,optional:false,done:false,confirmed:false,imported:true,source:"Importado desde "+e.fileName+". Fecha por verificar."+(missing?" Ponderación sin identificar; regístrala manualmente.":"")+((e.description)?" "+e.description:"")+(e.sourceUrl?" "+e.sourceUrl:"")});
   count++;
  });
  app().save();app().render();staged=[];$("#calendar-file").value="";$("#import-preview").hidden=true;$("#import-confirm").hidden=true;$("#import-message").textContent="Importadas "+count+" actividad(es). Completa los datos y confirma cada una en Actividades → Por confirmar.";app().toast(count+" actividad(es) importadas para revisar.");
 });
 $("#import-backup").addEventListener("change",async e=>{const f=e.target.files[0];if(!f)return;try{if(f.size>5*1024*1024)throw Error("La copia supera el límite de 5 MB.");const data=JSON.parse(await f.text());if(!Array.isArray(data.tasks)||!Array.isArray(data.subjects))throw Error("El archivo no parece ser una copia válida de ELECTIVA DE DANZAS.");if(!confirm("La copia reemplazará las materias, actividades y sesiones guardadas. ¿Continuar?"))return;data.settings=data.settings||{availableHours:5,reminders:true,changes:true};data.focusSessions=Array.isArray(data.focusSessions)?data.focusSessions:[];localStorage.setItem("electiva-danzas-v1",JSON.stringify(data));location.reload()}catch(err){app().toast(err.message||"No pude leer esa copia.")}finally{e.target.value=""}});
}
function bindSubjectEdit(){
 $("#add-subject").addEventListener("click",()=>{$("#subject-id").value="";$("#subject-modal-title").textContent="Nueva materia"},true);
 $("#subjects-list").addEventListener("click",e=>{const b=e.target.closest("[data-edit-subject]");if(!b)return;e.stopImmediatePropagation();const s=state().subjects.find(x=>x.id===b.dataset.editSubject);if(!s)return;$("#subject-form").reset();$("#subject-id").value=s.id;$("#subject-modal-title").textContent="Editar materia";$("#subject-name").value=s.name;$("#subject-grade").value=s.grade;$("#subject-modal").hidden=false;$("#subject-name").focus()},true);
 $("#subject-form").addEventListener("submit",e=>{const id=$("#subject-id").value;if(!id)return;e.preventDefault();e.stopImmediatePropagation();const st=state(),s=st.subjects.find(x=>x.id===id),name=$("#subject-name").value.trim();if(st.subjects.some(x=>x.id!==id&&x.name.toLowerCase()===name.toLowerCase())){app().toast("Esa materia ya está registrada.");return}s.name=name;s.grade=Number($("#subject-grade").value);app().save();$("#subject-modal").hidden=true;$("#subject-id").value="";app().render();app().toast("Materia actualizada.")},true);
}
function defaultWeekHours(total){
 const map={0:0,1:0,2:0,3:0,4:0,5:0,6:0},order=[1,2,3,4,5,6,0];
 let ticks=Math.max(0,Math.round((Number(total)||0)*2)),i=0;
 while(ticks>0){map[order[i%order.length]]+=.5;ticks--;i++}
 return map;
}
function ensureWeekHours(){
 const st=state(),current=st.settings.weekdayHours;
 if(!current||typeof current!=="object"||Array.isArray(current)){st.settings.weekdayHours=defaultWeekHours(st.settings.availableHours);app().save();return}
 let changed=false;
 for(let i=0;i<7;i++){if(!Number.isFinite(Number(current[i]))||Number(current[i])<0){current[i]=0;changed=true}else current[i]=Math.min(24,Number(current[i]))}
 if(changed)app().save();
}
function dateDiff(a,b){
 const x=new Date(a.getFullYear(),a.getMonth(),a.getDate()),y=new Date(b.getFullYear(),b.getMonth(),b.getDate());
 return Math.round((Date.UTC(y.getFullYear(),y.getMonth(),y.getDate())-Date.UTC(x.getFullYear(),x.getMonth(),x.getDate()))/86400000);
}
function fmtHours(n){return Number(n.toFixed(2)).toLocaleString("es-CO",{maximumFractionDigits:2})}
function renderPlan(){
 ensureWeekHours();
 const st=state(),hours=st.settings.weekdayHours,base=new Date();base.setHours(0,0,0,0);
 const dates=Array.from({length:7},(_,i)=>{const d=new Date(base);d.setDate(d.getDate()+i);return d});
 const total=dates.reduce((n,d)=>n+(Number(hours[d.getDay()])||0),0);
 $("#plan-total-hours").textContent=fmtHours(total)+" h / 7 días";
 const dayLabels=dates.map(d=>new Intl.DateTimeFormat("es-CO",{weekday:"short",day:"numeric",month:"short"}).format(d));
 $("#plan-days").innerHTML=dates.map((d,i)=>'<label class="plan-day-setting"><span>'+escapeHtml(dayLabels[i])+'</span><span><input type="number" min="0" max="24" step=".5" value="'+(Number(hours[d.getDay()])||0)+'" data-day-hours="'+d.getDay()+'" aria-label="Horas disponibles el '+escapeHtml(dayLabels[i])+'"> h</span></label>').join("");
 const pending=st.tasks.filter(t=>!t.done),unconfirmed=pending.filter(t=>!t.confirmed).length;
 const tasks=pending.filter(t=>t.confirmed&&t.due&&dateDiff(base,new Date(t.due))<=6);
 tasks.sort((x,y)=>new Date(x.due)-new Date(y.due)||Number(y.weight||0)-Number(x.weight||0));
 const capacity=dates.map(d=>Number(hours[d.getDay()])||0),left=capacity.slice(),slots=dates.map(()=>[]);
 const outstanding=[];
 tasks.forEach(t=>{
  const dueIndex=Math.max(0,Math.min(6,dateDiff(base,new Date(t.due))));
  let rem=Math.max(0,Number(t.hours)||0);
  for(let i=0;i<=dueIndex&&rem>.001;i++){
   while(left[i]>.001&&rem>.001){
    const block=Math.min(1.5,left[i],rem);
    slots[i].push({task:t,hours:block});left[i]-=block;rem-=block;
   }
  }
  if(rem>.001)outstanding.push({task:t,hours:rem});
 });
 const remaining=outstanding.reduce((n,x)=>n+x.hours,0);
 $("#plan-task-count").textContent=tasks.length+" actividad(es) · "+fmtHours(tasks.reduce((n,t)=>n+(Number(t.hours)||0),0))+" h estimadas";
 const status=$("#plan-status");
 if(!tasks.length)status.innerHTML='<b>Una semana más ligera</b><span>No hay actividades confirmadas con fecha de entrega en los próximos 7 días.'+(unconfirmed?' '+unconfirmed+' actividad(es) por confirmar no se incluyen.':'')+'</span><button class="outline" data-go="tasks">Revisar actividades →</button>';
 else if(remaining>.001)status.innerHTML='<b>El tiempo disponible no alcanza todavía</b><span>Quedan '+fmtHours(remaining)+' h estimadas sin ubicar. Revisa tus horas, divide el trabajo o conversa con tu docente sobre prioridades.'+(unconfirmed?' '+unconfirmed+' actividad(es) por confirmar quedan fuera.':'')+'</span><button class="outline" data-go="tasks">Revisar actividades →</button>';
 else status.innerHTML='<b>Las actividades confirmadas caben en tu disponibilidad</b><span>El orden sigue la fecha de entrega; en caso de empate, prioriza la ponderación. Ajusta cualquier día para reflejar tu semana real.'+(unconfirmed?' '+unconfirmed+' actividad(es) por confirmar quedan fuera.':'')+'</span>';
 $("#plan-grid").innerHTML=dates.map((d,i)=>{
  const used=capacity[i]-left[i],items=slots[i].length?slots[i].map(s=>'<article class="plan-slot"><div><b>'+escapeHtml(s.task.title)+'</b><small>'+escapeHtml(st.subjects.find(x=>x.id===s.task.subjectId)?.name||"Materia")+' · '+fmtHours(s.hours)+' h</small></div><button class="mini" data-start-task="'+escapeHtml(s.task.id)+'">Enfocarme</button></article>').join(""):'<div class="plan-free">'+(capacity[i]?'Día libre para adelantar o descansar.':'Aún no asignaste horas disponibles.')+'</div>';
  return '<section class="card plan-day-card"><div class="plan-day-head"><div><small>DÍA '+(i+1)+'</small><h3>'+escapeHtml(dayLabels[i])+'</h3></div><strong>'+fmtHours(used)+' <small>/ '+fmtHours(capacity[i])+' h</small></strong></div><div class="plan-bar"><i style="width:'+(capacity[i]?Math.min(100,used/capacity[i]*100):0)+'%"></i></div><div class="plan-slots">'+items+'</div></section>';
 }).join("");
 if(tasks.length&&remaining>.001){
  $("#plan-grid").insertAdjacentHTML("beforeend",'<section class="plan-overflow"><b>Por ubicar: '+fmtHours(remaining)+' h</b><div>'+outstanding.map(x=>'<span>'+escapeHtml(x.task.title)+' · '+fmtHours(x.hours)+' h</span>').join("")+'</div></section>');
 }
}
function rebalanceWeek(total){
 const st=state(),map=defaultWeekHours(total);
 st.settings.weekdayHours=map;
}
function bindPlan(){
 $("#plan-days").addEventListener("change",e=>{
  const input=e.target.closest("[data-day-hours]");if(!input)return;
  const day=Number(input.dataset.dayHours),st=state(),value=Math.max(0,Math.min(24,Number(input.value)||0));
  st.settings.weekdayHours[day]=value;st.settings.availableHours=Object.values(st.settings.weekdayHours).reduce((n,x)=>n+(Number(x)||0),0);
  app().save();app().render();app().toast("Disponibilidad semanal actualizada.");
 });
 $("#available-hours").addEventListener("change",e=>{
  rebalanceWeek(Math.max(0,Math.min(168,Number(e.target.value)||0)));
 },true);
 $("#plan-status").addEventListener("click",e=>{if(e.target.closest("[data-go=tasks]"))app().switchView("tasks")});
 $("#plan-grid").addEventListener("click",e=>{
  const button=e.target.closest("[data-start-task]");if(!button)return;
  $("#focus-task").value=button.dataset.startTask;app().switchView("dashboard");
  setTimeout(()=>$("#focus-card").scrollIntoView({behavior:"smooth",block:"center"}),80);
 });
}
function bindAll(){bindFocus();bindImport();bindSubjectEdit();bindPlan()}
window.renderEnhancements=()=>{renderFocus();renderPlan()};
if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",()=>{bindAll();window.renderEnhancements()},{once:true})}else{bindAll();window.renderEnhancements()}
})();





