"use strict";
require("dotenv").config();
const path=require("path"),crypto=require("crypto"),express=require("express"),helmet=require("helmet"),rateLimit=require("express-rate-limit"),session=require("express-session"),connectPgSimple=require("connect-pg-simple"),{Pool}=require("pg");
const app=express(),production=process.env.NODE_ENV==="production",port=Number(process.env.PORT||3000);
if(!process.env.SESSION_SECRET||process.env.SESSION_SECRET.length<32)throw new Error("SESSION_SECRET debe tener al menos 32 caracteres.");
if(!process.env.DATABASE_URL)throw new Error("Configura DATABASE_URL en .env.");
if(production)app.set("trust proxy",1);
const pool=new Pool({connectionString:process.env.DATABASE_URL,max:20,idleTimeoutMillis:30000,connectionTimeoutMillis:5000});
pool.on("error",error=>console.error("PostgreSQL pool error",error.message));
const PgStore=connectPgSimple(session);
app.disable("x-powered-by");
app.use(helmet({contentSecurityPolicy:{directives:{defaultSrc:["'self'"],scriptSrc:["'self'"],styleSrc:["'self'","'unsafe-inline'"],imgSrc:["'self'","data:"],objectSrc:["'none'"],baseUri:["'self'"],frameAncestors:["'none'"],upgradeInsecureRequests:null}}}));
app.use(express.json({limit:"2mb",strict:true}));
app.use(session({store:new PgStore({pool:pool,tableName:"web_sessions",createTableIfMissing:true,pruneSessionInterval:60}),name:"kairos.sid",secret:process.env.SESSION_SECRET,resave:false,saveUninitialized:false,rolling:true,cookie:{httpOnly:true,secure:production,sameSite:"lax",maxAge:8*60*60*1000}}));
const authLimiter=rateLimit({windowMs:15*60*1000,limit:12,standardHeaders:true,legacyHeaders:false,message:{error:"Demasiados intentos. Espera unos minutos y prueba otra vez."}});
const asyncRoute=fn=>(req,res,next)=>Promise.resolve(fn(req,res,next)).catch(next);
function sameOrigin(req,res,next){const origin=req.get("origin"),expected=process.env.APP_ORIGIN?new URL(process.env.APP_ORIGIN).origin:req.protocol+"://"+req.get("host");if(!origin||origin!==expected)return res.status(403).json({error:"Origen de solicitud no permitido."});next()}
function requireAuth(req,res,next){if(!req.session.userId)return res.status(401).json({error:"Inicia sesión para continuar."});next()}
function publicUser(row){return {id:row.id,name:row.name,email:row.email}}
function derive(password,salt){return new Promise((resolve,reject)=>crypto.scrypt(password,salt,64,{N:16384,r:8,p:1,maxmem:64*1024*1024},(err,key)=>err?reject(err):resolve(key)))}
async function hashPassword(password){const salt=crypto.randomBytes(16).toString("hex"),key=await derive(password,salt);return "scrypt$"+salt+"$"+key.toString("hex")}
async function verifyPassword(password,stored){const parts=String(stored||"").split("$");if(parts.length!==3||parts[0]!=="scrypt")return false;try{const expected=Buffer.from(parts[2],"hex"),actual=await derive(password,parts[1]);return expected.length===actual.length&&crypto.timingSafeEqual(expected,actual)}catch(err){return false}}
function establishSession(req,id){return new Promise((resolve,reject)=>req.session.regenerate(err=>{if(err)return reject(err);req.session.userId=id;req.session.save(err=>err?reject(err):resolve())}))}
function destroySession(req){return new Promise((resolve,reject)=>req.session.destroy(err=>err?reject(err):resolve()))}
function validEmail(value){return typeof value==="string"&&value.length<=254&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)}
const publicFiles=new Set(["index.html","styles.css","ai-agent.js","auth-client.js","app.js","enhancements.js","fonts/inter-variable-latin.woff2","fonts/poppins-400-latin.woff2","fonts/poppins-500-latin.woff2","fonts/poppins-600-latin.woff2","fonts/poppins-700-latin.woff2","fonts/poppins-800-latin.woff2"]);
app.get("/api/health",asyncRoute(async(req,res)=>{await pool.query("SELECT 1");res.json({status:"ok"})}));
app.post("/api/auth/register",sameOrigin,authLimiter,asyncRoute(async(req,res)=>{
 const name=String(req.body.name||"").trim(),email=String(req.body.email||"").trim().toLowerCase(),password=String(req.body.password||"");
 if(name.length<1||name.length>80)return res.status(400).json({error:"Escribe un nombre de 1 a 80 caracteres."});
 if(!validEmail(email))return res.status(400).json({error:"Escribe un correo electrónico válido."});
 if(password.length<10||Buffer.byteLength(password,"utf8")>256)return res.status(400).json({error:"La contraseña debe tener al menos 10 caracteres."});
 const id=crypto.randomUUID(),passwordHash=await hashPassword(password);
 try{const result=await pool.query("INSERT INTO app_users(id,name,email,password_hash) VALUES($1,$2,$3,$4) RETURNING id,name,email",[id,name,email,passwordHash]);await establishSession(req,id);res.status(201).json({user:publicUser(result.rows[0])})}
 catch(err){if(err.code==="23505")return res.status(409).json({error:"Ese correo ya está registrado."});throw err}
}));
app.post("/api/auth/login",sameOrigin,authLimiter,asyncRoute(async(req,res)=>{
 const email=String(req.body.email||"").trim().toLowerCase(),password=String(req.body.password||"");
 if(!validEmail(email)||!password)return res.status(401).json({error:"Correo o contraseña incorrectos."});
 const result=await pool.query("SELECT id,name,email,password_hash FROM app_users WHERE email=$1",[email]),row=result.rows[0];
 if(!row||!(await verifyPassword(password,row.password_hash)))return res.status(401).json({error:"Correo o contraseña incorrectos."});
 await establishSession(req,row.id);res.json({user:publicUser(row)});
}));
app.get("/api/auth/me",requireAuth,asyncRoute(async(req,res)=>{const result=await pool.query("SELECT id,name,email FROM app_users WHERE id=$1",[req.session.userId]);if(!result.rows[0]){await destroySession(req);return res.status(401).json({error:"La cuenta ya no existe."})}res.json({user:publicUser(result.rows[0])})}));
app.post("/api/auth/logout",sameOrigin,requireAuth,asyncRoute(async(req,res)=>{await destroySession(req);res.clearCookie("kairos.sid",{httpOnly:true,secure:production,sameSite:"lax"});res.json({ok:true})}));
app.get("/api/planner/state",requireAuth,asyncRoute(async(req,res)=>{const result=await pool.query("SELECT data FROM planner_data WHERE user_id=$1",[req.session.userId]);res.json({data:result.rows[0]?result.rows[0].data:null})}));
app.put("/api/planner/state",sameOrigin,requireAuth,asyncRoute(async(req,res)=>{
 const data=req.body&&req.body.data;
 if(!data||!Array.isArray(data.subjects)||!Array.isArray(data.tasks)||!data.settings||typeof data.settings!=="object")return res.status(400).json({error:"Los datos de planificación no tienen un formato válido."});
 if(Buffer.byteLength(JSON.stringify(data),"utf8")>2*1024*1024)return res.status(413).json({error:"La copia de planificación supera el límite de 2 MB."});
 await pool.query("INSERT INTO planner_data(user_id,data,updated_at) VALUES($1,$2::jsonb,NOW()) ON CONFLICT(user_id) DO UPDATE SET data=EXCLUDED.data,updated_at=NOW()",[req.session.userId,JSON.stringify(data)]);res.json({ok:true});
}));
app.get(["/","/index.html","/styles.css","/ai-agent.js","/auth-client.js","/app.js","/enhancements.js","/fonts/:font"],(req,res)=>{const name=req.path==="/"?"index.html":req.path.slice(1);if(!publicFiles.has(name))return res.sendStatus(404);res.sendFile(path.join(__dirname,name))});
app.use((err,req,res,next)=>{console.error("Request error",err.message);if(res.headersSent)return next(err);res.status(500).json({error:"Ocurrió un error del servidor. Inténtalo de nuevo."})});
async function main(){
 await pool.query("CREATE TABLE IF NOT EXISTS app_users(id TEXT PRIMARY KEY,name VARCHAR(80) NOT NULL,email VARCHAR(254) NOT NULL UNIQUE,password_hash TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())");
 await pool.query("CREATE TABLE IF NOT EXISTS planner_data(user_id TEXT PRIMARY KEY REFERENCES app_users(id) ON DELETE CASCADE,data JSONB NOT NULL,updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())");
 const server=app.listen(port,()=>console.log("Electiva de Danzas disponible en el puerto "+port));
 const shutdown=()=>server.close(()=>pool.end().finally(()=>process.exit(0)));process.on("SIGTERM",shutdown);process.on("SIGINT",shutdown)
}
main().catch(err=>{console.error("No pude iniciar el servidor:",err.message);process.exit(1)});
