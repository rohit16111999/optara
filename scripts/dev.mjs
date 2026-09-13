import {spawn,spawnSync} from 'node:child_process';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const next=path.join(root,'frontend/node_modules/next/dist/bin/next');
if(!existsSync(python)||!existsSync(next)){console.error('Dependencies are missing. Run .\\setup.ps1 (Windows) or uv sync and npm install --prefix frontend.');process.exit(1);}
const children=[];
const launch=(name,bin,args,cwd)=>{
 const child=spawn(bin,args,{cwd,stdio:'inherit',windowsHide:true,env:{...process.env,PYTHONUTF8:'1'}});children.push(child);
 child.on('error',()=>{console.error(`${name} could not start.`);shutdown(1);});
 child.on('exit',code=>{if(!stopping){console.error(`${name} exited (${code}).`);shutdown(code||0);}});
 return child;
};
let stopping=false;
function shutdown(code=0){if(stopping)return;stopping=true;for(const child of children){if(child.exitCode!==null)continue;if(process.platform==='win32')spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});else child.kill('SIGTERM');}setTimeout(()=>process.exit(code),400);}
process.on('SIGINT',()=>shutdown());process.on('SIGTERM',()=>shutdown());
console.log('OPTARA · Intelligence, Optimized.\nUI http://127.0.0.1:3000\nAPI http://127.0.0.1:8000/docs\nCtrl+C stops both services.');
const backend=launch('Backend',python,['-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000'],root);
const frontend=launch('Frontend',process.execPath,[next,process.argv.includes('--production')?'start':'dev','--hostname','127.0.0.1','--port','3000'],path.join(root,'frontend'));
mkdirSync(path.join(root,'.runtime'),{recursive:true});writeFileSync(path.join(root,'.runtime/processes.json'),JSON.stringify({supervisor:process.pid,backend:backend.pid,frontend:frontend.pid},null,2));
